"""
ROBOT RECEPTIONIST — NOISE HANDLER MODULE
Handles speech recognition in noisy environments.

STT modes:
  - LOCAL (USE_LOCAL_STT=True):
    Robot mic → record on robot → download to PC → Google STT
  - ROBOT (USE_LOCAL_STT=False):
    Robot mic → robot internal STT → English

Noise handling strategy:
  1. Listen → Timeout → Retry (max 2 times)
  2. Retry with extended timeout
  3. If still failing → fallback to hand gesture recognition
  4. Map gesture → default question
"""

import asyncio
import logging
import tempfile
import os
from typing import Optional

from mini.apis.api_sence import (
    StartSpeechRecognise,
    ObjectRecognise,
    ObjectRecogniseType,
)
from mini.apis.api_sound import (
    RobotAudioStartRecord,
)
from mini.apis.base_api import MiniApiResultType

from config import (
    USE_LOCAL_STT,
    LOCAL_STT_LANGUAGE,
    ROBOT_IP,
    LISTEN_TIMEOUT_MS,
    LISTEN_TIMEOUT_EXTENDED_MS,
    MAX_RETRY_LISTEN,
    GESTURE_FALLBACK_TIMEOUT,
    NOISE_RETRY_MESSAGES,
    NOISE_FALLBACK_MESSAGE,
    GESTURE_TO_QUESTION,
)

logger = logging.getLogger("noise_handler")

# Check if speech_recognition is available
_sr_available = False
try:
    import speech_recognition as sr
    _sr_available = True
except ImportError:
    pass


# ═════════════════════════════════════════════
# NoiseHandler
# ═════════════════════════════════════════════
class NoiseHandler:
    """Handles Speech-to-Text in noisy environments.

    Supports 2 STT modes:
      - LOCAL (USE_LOCAL_STT=True):
        Robot mic → record → download to PC → Google STT
      - ROBOT (USE_LOCAL_STT=False):
        Robot mic → robot internal STT (English)

    Strategy:
      1. Listen with standard timeout
      2. If failed → robot responds + retry
      3. If retry also fails → gesture fallback
    """

    def __init__(self, action_module=None, connection=None):
        """
        Args:
            action_module: ActionModule instance for TTS/gesture
            connection: RobotConnection instance for mute/unmute
        """
        self._action = action_module
        self._connection = connection
        self._use_local = USE_LOCAL_STT and _sr_available
        self._recognizer = sr.Recognizer() if _sr_available else None

        if self._use_local:
            logger.info(
                f"🎙️ STT Mode: ROBOT MIC → PC "
                f"(Google STT {LOCAL_STT_LANGUAGE})"
            )
        else:
            if USE_LOCAL_STT and not _sr_available:
                logger.warning(
                    "⚠️ USE_LOCAL_STT=True but speech_recognition not installed. "
                    "Run: pip install SpeechRecognition"
                )
            logger.info("🎙️ STT Mode: ROBOT (built-in English STT)")

    def set_action_module(self, action_module):
        """Inject ActionModule after init."""
        self._action = action_module

    def set_connection(self, connection):
        """Inject RobotConnection after init."""
        self._connection = connection

    # ─────────────────────────────────────────
    # Core: Single listen
    # ─────────────────────────────────────────
    async def single_listen(
        self, timeout_ms: int = LISTEN_TIMEOUT_MS
    ) -> Optional[str]:
        """Listen for speech once.

        Automatically chooses:
          - Local: Robot mic → record → download → Google STT
          - Robot: Robot mic → internal STT (English)

        Args:
            timeout_ms: Maximum listen duration (ms)

        Returns:
            Recognized text, or None
        """
        # Mute robot to suppress 'I didn't hear your voice' message
        if self._connection:
            await self._connection.mute()

        try:
            if self._use_local:
                return await self._robot_record_and_stt(timeout_ms)
            else:
                return await self._robot_listen(timeout_ms)
        finally:
            # Unmute after listening
            if self._connection:
                await self._connection.unmute()

    # ─────────────────────────────────────────
    # LOCAL: Robot Mic → Record → Download → Google STT
    # ─────────────────────────────────────────
    async def _robot_record_and_stt(
        self, timeout_ms: int = LISTEN_TIMEOUT_MS
    ) -> Optional[str]:
        """Record from robot mic → download to PC → Google STT.

        Flow:
          1. RobotAudioStartRecord → robot records
          2. Download audio file from robot via HTTP
          3. Send to Google Speech API
          4. Return recognized text

        Args:
            timeout_ms: Maximum recording duration (ms)

        Returns:
            Recognized text, or None
        """
        logger.info(
            f"🎙️ [LOCAL] Recording via robot mic "
            f"({timeout_ms}ms, STT: {LOCAL_STT_LANGUAGE})..."
        )

        try:
            # Step 1: Robot records
            record_api = RobotAudioStartRecord(
                is_serial=True, time_limit=timeout_ms
            )

            result_type, response = await asyncio.wait_for(
                record_api.execute(),
                timeout=(timeout_ms / 1000) + 10,
            )

            if result_type != MiniApiResultType.Success or response is None:
                logger.info("⏱️ [LOCAL] Recording failed/timeout.")
                return None

            file_id = getattr(response, "id", None)
            if not file_id:
                logger.warning("⚠️ [LOCAL] Robot did not return filename.")
                return None

            logger.info(f"📁 [LOCAL] Robot recorded: {file_id}")

            # Step 2: Download audio from robot
            audio_data = await self._download_robot_audio(file_id)
            if not audio_data:
                logger.warning(
                    "⚠️ [LOCAL] Could not download audio → "
                    "falling back to robot STT..."
                )
                return await self._robot_listen(timeout_ms)

            # Step 3: Google STT
            text = await self._google_stt(audio_data)
            if text:
                logger.info(f'✅ [LOCAL] Heard: "{text}"')
            else:
                logger.info("🔇 [LOCAL] No speech recognized.")
            return text

        except asyncio.CancelledError:
            logger.info("🛑 [LOCAL] Recording cancelled.")
            raise
        except Exception as e:
            logger.error(f"❌ [LOCAL] Error: {e}")
            return None

    async def _download_robot_audio(self, file_id: str) -> Optional[bytes]:
        """Download audio file from robot via HTTP.

        Args:
            file_id: Recording filename (from response.id)

        Returns:
            Audio data bytes, or None
        """
        import urllib.request
        import urllib.error

        url_patterns = [
            f"http://{ROBOT_IP}:9000/audio/{file_id}",
            f"http://{ROBOT_IP}:9000/record/{file_id}",
            f"http://{ROBOT_IP}:9000/{file_id}",
            f"http://{ROBOT_IP}:9090/audio/{file_id}",
            f"http://{ROBOT_IP}:9090/record/{file_id}",
            f"http://{ROBOT_IP}:8008/audio/{file_id}",
            f"http://{ROBOT_IP}:8008/{file_id}",
        ]

        def _try_download():
            for url in url_patterns:
                try:
                    logger.debug(f"📥 Trying: {url}")
                    req = urllib.request.Request(url, method="GET")
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        if resp.status == 200:
                            data = resp.read()
                            logger.info(
                                f"📥 [LOCAL] Downloaded OK: {url} "
                                f"({len(data)} bytes)"
                            )
                            return data
                except (urllib.error.URLError, Exception):
                    continue
            return None

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _try_download)

    async def _google_stt(self, audio_data: bytes) -> Optional[str]:
        """Send audio data to Google Speech API.

        Args:
            audio_data: Raw audio bytes (WAV/AMR)

        Returns:
            Recognized text, or None
        """
        if not self._recognizer:
            return None

        def _recognize_sync():
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False
                ) as tmp:
                    tmp.write(audio_data)
                    tmp_path = tmp.name

                with sr.AudioFile(tmp_path) as source:
                    audio = self._recognizer.record(source)

                text = self._recognizer.recognize_google(
                    audio, language=LOCAL_STT_LANGUAGE
                )
                return text.strip() if text else None

            except sr.UnknownValueError:
                return None
            except sr.RequestError as e:
                logger.error(f"❌ [LOCAL] Google API error: {e}")
                return None
            except Exception as e:
                logger.error(f"❌ [LOCAL] Audio processing error: {e}")
                return None
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, _recognize_sync),
            timeout=15,
        )

    # ─────────────────────────────────────────
    # ROBOT internal STT (English)
    # ─────────────────────────────────────────
    async def _robot_listen(
        self, timeout_ms: int = LISTEN_TIMEOUT_MS
    ) -> Optional[str]:
        """Listen via robot's built-in STT (English).

        Args:
            timeout_ms: Maximum listen duration (ms)

        Returns:
            Recognized text (English) or None
        """
        outer_timeout = (timeout_ms / 1000) + 5

        try:
            logger.info(f"🎙️ [ROBOT] Listening ({timeout_ms}ms)...")
            stt = StartSpeechRecognise(
                is_serial=True, time_limit=timeout_ms
            )

            result_type, response = await asyncio.wait_for(
                stt.execute(), timeout=outer_timeout
            )

            if result_type == MiniApiResultType.Success and response is not None:
                text = getattr(response, "text", "")
                if text and text.strip():
                    logger.info(f'✅ [ROBOT] Heard: "{text}"')
                    return text.strip()
                else:
                    logger.info("🔇 [ROBOT] Nothing heard.")
                    return None
            else:
                logger.info("⏱️ [ROBOT] Listen timeout.")
                return None

        except asyncio.TimeoutError:
            logger.info("⏱️ [ROBOT] Timeout (outer).")
            return None
        except asyncio.CancelledError:
            logger.info("🛑 [ROBOT] Listening cancelled.")
            raise
        except Exception as e:
            logger.error(f"❌ [ROBOT] STT error: {e}")
            return None

    # ─────────────────────────────────────────
    # Listen with Retry
    # ─────────────────────────────────────────
    async def listen_with_retry(
        self, max_retries: int = MAX_RETRY_LISTEN
    ) -> Optional[str]:
        """Listen with retry on failure.

        Flow:
          1. First listen (standard timeout)
          2. If failed → robot responds + retry
          3. Second listen (extended timeout)

        Args:
            max_retries: Maximum number of retries

        Returns:
            Recognized text or None
        """
        # First attempt
        text = await self.single_listen(timeout_ms=LISTEN_TIMEOUT_MS)
        if text:
            return text

        # Retry loop
        for attempt in range(max_retries):
            logger.info(
                f"🔄 Retry listening ({attempt + 1}/{max_retries})..."
            )

            await self._notify_not_heard(attempt)

            text = await self.single_listen(
                timeout_ms=LISTEN_TIMEOUT_EXTENDED_MS
            )
            if text:
                return text

        logger.info("🚫 Still no input after retries.")
        return None

    # ─────────────────────────────────────────
    # Fallback: Hand gesture recognition
    # ─────────────────────────────────────────
    async def fallback_to_gesture(self) -> Optional[str]:
        """Switch to hand gesture recognition mode.

        Returns:
            Default question mapped to gesture, or None
        """
        if self._action:
            await asyncio.gather(
                self._action.say(NOISE_FALLBACK_MESSAGE),
                self._action.listen_pose(),
                return_exceptions=True,
            )

        try:
            logger.info(
                f"🖐️ Waiting for gesture "
                f"(timeout={GESTURE_FALLBACK_TIMEOUT}s)..."
            )
            gesture_api = ObjectRecognise(
                is_serial=True,
                object_type=ObjectRecogniseType.GESTURE,
                timeout=GESTURE_FALLBACK_TIMEOUT,
            )
            result_type, response = await gesture_api.execute()

            if (
                result_type == MiniApiResultType.Success
                and response is not None
            ):
                objects = list(response.objects)
                if objects:
                    gesture_name = objects[0]
                    logger.info(f"🖐️ Gesture detected: {gesture_name}")

                    question = GESTURE_TO_QUESTION.get(gesture_name)
                    if question:
                        logger.info(
                            f"✅ Gesture '{gesture_name}' → "
                            f"question '{question}'"
                        )
                        if self._action:
                            await self._action.say(
                                f"Got it! You want to know about {question}."
                            )
                        return question
                    else:
                        logger.info(
                            f"🤷 Gesture '{gesture_name}' not in mapping."
                        )
                        return None
                else:
                    logger.info("🚫 No gesture detected.")
                    return None
            else:
                logger.info("⏱️ Gesture recognition timeout.")
                return None

        except Exception as e:
            logger.error(f"❌ Gesture recognition error: {e}")
            return None

    # ─────────────────────────────────────────
    # Full flow: Listen → Retry → Gesture
    # ─────────────────────────────────────────
    async def robust_listen(self) -> Optional[str]:
        """Full listening flow with complete fallback.

        Priority:
          1. Listen for speech (retry 2 times)
          2. If failed → hand gesture recognition
          3. If still failed → return None

        Returns:
            Question text, or None
        """
        logger.info("🎧 ── Starting robust_listen ──")

        # Step 1: Listen (with retry)
        text = await self.listen_with_retry()
        if text:
            return text

        # Step 2: Fallback to gesture
        logger.info("🔄 Switching to gesture recognition...")
        question = await self.fallback_to_gesture()
        if question:
            return question

        # Step 3: Total failure
        logger.warning("🚫 Could not communicate with visitor.")
        if self._action:
            await self._action.say(
                "I'm sorry, I couldn't understand. "
                "Please try again later!"
            )
        return None

    # ─────────────────────────────────────────
    # Helper: Notify not heard
    # ─────────────────────────────────────────
    async def _notify_not_heard(self, attempt: int):
        """Robot response when speech not recognized."""
        if not self._action:
            return

        msg_index = min(attempt, len(NOISE_RETRY_MESSAGES) - 1)
        message = NOISE_RETRY_MESSAGES[msg_index]

        await asyncio.gather(
            self._action.say(message),
            self._action.shake_head(),
            return_exceptions=True,
        )

        await asyncio.sleep(0.5)


# ═════════════════════════════════════════════
# Standalone test
# ═════════════════════════════════════════════
async def _test():
    """Test noise handler."""
    from connection import RobotConnection
    from actions import ActionModule

    async with RobotConnection():
        action = ActionModule()
        handler = NoiseHandler(action_module=action)

        print("\n── Test Single Listen (10s) ──")
        print("Say something to the robot...")
        text = await handler.single_listen(timeout_ms=10000)
        print(f"Result: {text}")

        if not text:
            print("\n── Test Gesture Fallback ──")
            question = await handler.fallback_to_gesture()
            print(f"Question from gesture: {question}")


if __name__ == "__main__":
    asyncio.run(_test())
