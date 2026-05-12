"""
╔══════════════════════════════════════════════════════════════╗
║           ROBOT LỄ TÂN — ACTIONS MODULE                    ║
║  Chào hỏi, cử chỉ, TTS, di chuyển robot                   ║
╚══════════════════════════════════════════════════════════════╝

Module này xử lý mọi hành động vật lý của robot:
  - TTS (Text-to-Speech): Phát giọng nói
  - Gesture: Vẫy tay, gật đầu, lắc đầu, cúi chào...
  - Movement: Moving tiến/lùi/trái/phải
  - Expression: Hiệu ứng mắt robot
  - Greeting: Greeting visitor theo giới tính (kết hợp TTS + Gesture)
"""

import asyncio
import logging
import random
from typing import Optional, List

from mini.apis.api_sound import StartPlayTTS, StopPlayTTS
from mini.apis.api_action import (
    PlayAction,
    GetActionList,
    MoveRobot,
    MoveRobotDirection,
    RobotActionType,
)
from mini.apis.api_expression import PlayExpression
from mini.apis.api_behavior import StartBehavior, StopBehavior
from mini.apis.base_api import MiniApiResultType

from config import (
    GREETINGS,
    GOODBYE_MESSAGES,
    ASK_CONTINUE_MESSAGE,
    GESTURE_WAVE,
    GESTURE_NOD,
    GESTURE_SHAKE_HEAD,
    GESTURE_BOW,
    GESTURE_LISTEN,
    GESTURE_DANCE,
)

logger = logging.getLogger("actions")


# ═════════════════════════════════════════════
# ActionModule — Hành động robot
# ═════════════════════════════════════════════
class ActionModule:
    """Controls all physical robot actions.

    Kết hợp TTS, gesture, movement, expression để tạo
    trải nghiệm tự nhiên cho khách.

    Methods:
        say() — Phát giọng nói (TTS)
        perform_gesture() — Thực hiện cử chỉ
        greet() — Greeting visitor theo giới tính
        greet_and_gesture() — Chào + cử chỉ đồng thời
        move_forward/backward() — Moving
        show_expression() — Hiệu ứng mắt
        say_goodbye() — Tạm biệt khách
    """

    def __init__(self):
        self._available_actions: List[str] = []

    # ─────────────────────────────────────────
    # TTS — Text-to-Speech
    # ─────────────────────────────────────────
    async def say(self, text: str) -> bool:
        """Play text-to-speech via robot.

        Args:
            text: Văn bản cần phát (tiếng Việt)

        Returns:
            True nếu phát thành công
        """
        if not text or not text.strip():
            logger.warning("⚠️ Empty text, skipping TTS.")
            return False

        try:
            logger.info(f"🗣️ TTS: \"{text[:60]}{'...' if len(text) > 60 else ''}\"")
            tts = StartPlayTTS(is_serial=True, text=text)
            result_type, response = await tts.execute()

            if result_type == MiniApiResultType.Success:
                logger.debug("✅ TTS played successfully.")
                return True
            else:
                logger.warning(f"⚠️ TTS failed: {result_type}")
                return False
        except Exception as e:
            logger.error(f"❌ TTS error: {e}")
            return False

    async def stop_speaking(self) -> bool:
        """Stop currently playing TTS."""
        try:
            tts_stop = StopPlayTTS(is_serial=True)
            await tts_stop.execute()
            return True
        except Exception as e:
            logger.error(f"❌ Error stopping TTS: {e}")
            return False

    # ─────────────────────────────────────────
    # GESTURE — Cử chỉ robot
    # ─────────────────────────────────────────
    async def perform_gesture(self, gesture_name: str) -> bool:
        """Perform a gesture/action.

        Args:
            gesture_name: Tên action nội tại (VD: "010", "wave")

        Returns:
            True nếu thực hiện thành công
        """
        try:
            logger.info(f"🤖 Gesture: {gesture_name}")
            action = PlayAction(is_serial=True, action_name=gesture_name)
            result_type, response = await action.execute()

            if result_type == MiniApiResultType.Success and response.isSuccess:
                logger.debug(f"✅ Gesture '{gesture_name}' completed.")
                return True
            else:
                logger.warning(f"⚠️ Gesture '{gesture_name}' failed.")
                return False
        except Exception as e:
            logger.error(f"❌ Gesture error '{gesture_name}': {e}")
            return False

    async def wave_hand(self) -> bool:
        """Wave hand."""
        return await self.perform_gesture(GESTURE_WAVE)

    async def nod(self) -> bool:
        """Nod head."""
        return await self.perform_gesture(GESTURE_NOD)

    async def shake_head(self) -> bool:
        """Shake head (did not understand)."""
        return await self.perform_gesture(GESTURE_SHAKE_HEAD)

    async def bow(self) -> bool:
        """Bow."""
        return await self.perform_gesture(GESTURE_BOW)

    async def listen_pose(self) -> bool:
        """Raise hand to ear (listening pose)."""
        return await self.perform_gesture(GESTURE_LISTEN)

    async def dance(self) -> bool:
        """Dance."""
        try:
            behavior = StartBehavior(is_serial=True, name=GESTURE_DANCE)
            result_type, response = await behavior.execute()
            return result_type == MiniApiResultType.Success
        except Exception as e:
            logger.error(f"❌ Dance error: {e}")
            return False

    # ─────────────────────────────────────────
    # MOVEMENT — Moving
    # ─────────────────────────────────────────
    async def move_forward(self, steps: int = 2) -> bool:
        """Move forward.

        Args:
            steps: Số bước (mặc định 2)
        """
        return await self._move(MoveRobotDirection.FORWARD, steps)

    async def move_backward(self, steps: int = 2) -> bool:
        """Move backward."""
        return await self._move(MoveRobotDirection.BACKWARD, steps)

    async def _move(self, direction: MoveRobotDirection, steps: int) -> bool:
        """Robot movement helper."""
        try:
            direction_names = {
                MoveRobotDirection.FORWARD: "forward",
                MoveRobotDirection.BACKWARD: "backward",
                MoveRobotDirection.LEFTWARD: "left",
                MoveRobotDirection.RIGHTWARD: "right",
            }
            logger.info(
                f"🚶 Moving {direction_names.get(direction, '?')} "
                f"{steps} step(s)..."
            )
            move = MoveRobot(is_serial=True, direction=direction, step=steps)
            result_type, response = await move.execute()

            if result_type == MiniApiResultType.Success and response.isSuccess:
                logger.debug("✅ Moving completed.")
                return True
            else:
                logger.warning("⚠️ Moving failed.")
                return False
        except Exception as e:
            logger.error(f"❌ Movement error: {e}")
            return False

    # ─────────────────────────────────────────
    # EXPRESSION — Biểu cảm mắt
    # ─────────────────────────────────────────
    async def show_expression(self, express_name: str) -> bool:
        """Display expression on robot eyes.

        Args:
            express_name: Tên biểu cảm (VD: "codemao1")
        """
        try:
            logger.debug(f"😊 Expression: {express_name}")
            expr = PlayExpression(is_serial=True, express_name=express_name)
            result_type, response = await expr.execute()
            return result_type == MiniApiResultType.Success
        except Exception as e:
            logger.error(f"❌ Expression error: {e}")
            return False

    # ─────────────────────────────────────────
    # GREETING — Greeting visitor
    # ─────────────────────────────────────────
    async def greet(self, gender: str = "unknown", age: int = 0) -> bool:
        """Greet visitor via TTS based on gender.

        Args:
            gender: "male" | "female" | "unknown"
            age: Tuổi ước lượng (để điều chỉnh ngôn ngữ)

        Returns:
            True nếu chào thành công
        """
        # Chọn mẫu câu chào
        templates = GREETINGS.get(gender, GREETINGS["unknown"])
        greeting_text = random.choice(templates)

        logger.info(f"👋 Greeting visitor ({gender}, ~{age} years old)")
        return await self.say(greeting_text)

    async def greet_and_gesture(
        self, gender: str = "unknown", age: int = 0
    ) -> bool:
        """Greeting visitor kết hợp TTS và cử chỉ đồng thời.

        Sử dụng asyncio.gather để chạy song song:
          - TTS phát lời chào
          - Robot vẫy tay chào

        Args:
            gender: "male" | "female" | "unknown"
            age: Tuổi ước lượng

        Returns:
            True nếu ít nhất TTS thành công
        """
        templates = GREETINGS.get(gender, GREETINGS["unknown"])
        greeting_text = random.choice(templates)

        logger.info(f"👋🗣️ Greeting + Gesture ({gender}, ~{age} years old)")

        # Chạy đồng thời TTS + Gesture
        results = await asyncio.gather(
            self.say(greeting_text),
            self.wave_hand(),
            return_exceptions=True,
        )

        # Kiểm tra kết quả
        tts_ok = results[0] is True
        gesture_ok = results[1] is True

        if not tts_ok:
            logger.warning("⚠️ Greeting TTS failed")
        if not gesture_ok:
            logger.warning("⚠️ Greeting gesture failed")

        return tts_ok

    # ─────────────────────────────────────────
    # GOODBYE — Tạm biệt khách
    # ─────────────────────────────────────────
    async def say_goodbye(self) -> bool:
        """Say goodbye to visitor (TTS + wave)."""
        goodbye_text = random.choice(GOODBYE_MESSAGES)
        logger.info("👋 Saying goodbye to visitor!")

        results = await asyncio.gather(
            self.say(goodbye_text),
            self.bow(),
            return_exceptions=True,
        )
        return results[0] is True

    # ─────────────────────────────────────────
    # ASK CONTINUE — Hỏi khách còn cần gì?
    # ─────────────────────────────────────────
    async def ask_continue(self) -> bool:
        """Ask visitor if they need more help."""
        return await self.say(ASK_CONTINUE_MESSAGE)

    # ─────────────────────────────────────────
    # UTILITY — Liệt kê actions
    # ─────────────────────────────────────────
    async def list_available_actions(self) -> List[str]:
        """List all built-in robot actions.

        Hữu ích để biết robot hỗ trợ gesture nào.
        """
        try:
            # Lấy action nội tại
            get_actions = GetActionList(
                is_serial=True, action_type=RobotActionType.INNER
            )
            result_type, response = await get_actions.execute()

            if result_type == MiniApiResultType.Success and response.isSuccess:
                actions = list(response.actionList)
                self._available_actions = actions
                logger.info(f"📋 Found {len(actions)} built-in actions:")
                for i, action in enumerate(actions):
                    logger.info(f"   {i+1}. {action}")
                return actions
            return []
        except Exception as e:
            logger.error(f"❌ Error listing actions: {e}")
            return []

    async def list_custom_actions(self) -> List[str]:
        """List custom robot actions."""
        try:
            get_actions = GetActionList(
                is_serial=True, action_type=RobotActionType.CUSTOM
            )
            result_type, response = await get_actions.execute()

            if result_type == MiniApiResultType.Success and response.isSuccess:
                actions = list(response.actionList)
                logger.info(f"📋 Có {len(actions)} custom actions:")
                for action in actions:
                    logger.info(f"   - {action}")
                return actions
            return []
        except Exception as e:
            logger.error(f"❌ Error listing custom actions: {e}")
            return []


# ═════════════════════════════════════════════
# Test module độc lập
# ═════════════════════════════════════════════
async def _test():
    """Test robot actions."""
    from connection import RobotConnection

    async with RobotConnection():
        action = ActionModule()

        # Liệt kê actions
        print("\n── Action list ──")
        await action.list_available_actions()

        # Test chào khách
        print("\n── Test Greeting ──")
        await action.greet_and_gesture(gender="male", age=25)

        await asyncio.sleep(2)

        # Test tạm biệt
        print("\n── Test Goodbye ──")
        await action.say_goodbye()


if __name__ == "__main__":
    asyncio.run(_test())
