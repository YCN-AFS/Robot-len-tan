"""
ROBOT RECEPTIONIST — VISION MODULE
Person detection & gender recognition via robot camera SDK.

Uses the robot's native camera + AI to:
  - Detect if someone is standing in front of the robot
  - Analyze gender (male/female) and estimate age
  - Wait for a person to appear (polling loop)
  - Take photos

Note: Alpha Mini SDK has built-in face recognition AI running
natively on the robot — no need for OpenCV/DeepFace/MediaPipe.
All processing is done on-device.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from mini.apis.api_sence import (
    FaceDetect,
    FaceAnalysis,
    TakePicture,
    TakePictureType,
)
from mini.apis.base_api import MiniApiResultType

from config import (
    FACE_DETECT_TIMEOUT,
    FACE_ANALYSIS_TIMEOUT,
    PERSON_POLL_INTERVAL,
    GENDER_THRESHOLD,
)

logger = logging.getLogger("vision")


# ═════════════════════════════════════════════
# Data Classes
# ═════════════════════════════════════════════
@dataclass
class PersonInfo:
    """Information about a detected person."""

    detected: bool = False
    gender: str = "unknown"       # "male" | "female" | "unknown"
    gender_score: int = 0         # [0-100]: <50=Female, >=50=Male
    age: int = 0                  # Estimated age
    face_width: int = 0           # Face size in frame
    face_height: int = 0
    face_count: int = 0           # Number of faces detected

    @property
    def gender_label(self) -> str:
        """Return gender as display string."""
        return {"male": "Male", "female": "Female", "unknown": "Unknown"}[self.gender]

    @property
    def gender_vi(self) -> str:
        """Vietnamese gender label (kept for log compatibility)."""
        return {"male": "Nam", "female": "Nữ", "unknown": "Unknown"}[self.gender]


# ═════════════════════════════════════════════
# VisionModule — Face detection & analysis
# ═════════════════════════════════════════════
class VisionModule:
    """Vision module using robot camera.

    All AI processing runs natively on the robot via SDK —
    no need to send images to the PC.

    Methods:
        detect_person() — Check if someone is present
        analyze_person() — Analyze gender + age
        wait_for_person() — Wait until someone appears
        take_photo() — Capture a photo
    """

    def __init__(self):
        self._last_person_info: Optional[PersonInfo] = None

    # ── Detect person ────────────────────────
    async def detect_person(self, timeout: int = FACE_DETECT_TIMEOUT) -> PersonInfo:
        """Check if someone is standing in front of the robot.

        Uses FaceDetect API — counts faces visible to robot camera.

        Args:
            timeout: Detection wait time (seconds)

        Returns:
            PersonInfo with detected=True if someone found
        """
        info = PersonInfo()

        try:
            logger.debug(f"👁️ Scanning for faces (timeout={timeout}s)...")
            face_detect = FaceDetect(is_serial=True, timeout=timeout)
            result_type, response = await face_detect.execute()

            if result_type == MiniApiResultType.Success and response is not None:
                count = response.count
                info.face_count = count
                if count > 0:
                    info.detected = True
                    logger.info(f"👤 Detected {count} person(s)!")
                else:
                    logger.debug("🚫 No one detected.")
            else:
                logger.debug("⏱️ Face scan timed out or failed.")
        except Exception as e:
            logger.error(f"❌ Face detection error: {e}")

        return info

    # ── Analyze gender & age ─────────────────
    async def analyze_person(
        self, timeout: int = FACE_ANALYSIS_TIMEOUT
    ) -> PersonInfo:
        """Analyze gender and age of person in front of robot.

        FaceAnalysis SDK returns:
          - gender: [0-100], <50 = Female, >=50 = Male
          - age: estimated age
          - width, height: face size in frame

        When multiple people detected, returns the largest face
        (closest to camera).

        Args:
            timeout: Analysis wait time (seconds)

        Returns:
            Fully populated PersonInfo
        """
        info = PersonInfo()

        try:
            logger.info("🔍 Analyzing face...")
            analysis = FaceAnalysis(is_serial=True, timeout=timeout)
            result_type, response = await analysis.execute()

            if result_type == MiniApiResultType.Success and response is not None:
                face_infos = response.faceInfos

                if face_infos and len(face_infos) > 0:
                    face = face_infos[0]  # Largest/closest face
                    info.detected = True
                    info.gender_score = face.gender
                    info.age = face.age
                    info.face_width = face.width
                    info.face_height = face.height
                    info.face_count = len(face_infos)

                    if face.gender < GENDER_THRESHOLD:
                        info.gender = "female"
                    else:
                        info.gender = "male"

                    logger.info(
                        f"✅ Analysis complete: "
                        f"Gender={info.gender_vi} (score={face.gender}), "
                        f"Age≈{face.age}, "
                        f"Face={face.width}x{face.height}px"
                    )
                else:
                    logger.info("🚫 No face could be analyzed.")
            else:
                logger.warning("⏱️ Face analysis timed out.")

        except Exception as e:
            logger.error(f"❌ Face analysis error: {e}")

        self._last_person_info = info
        return info

    # ── Wait for person ──────────────────────
    async def wait_for_person(
        self,
        poll_interval: float = PERSON_POLL_INTERVAL,
        stop_event: Optional[asyncio.Event] = None,
    ) -> PersonInfo:
        """Poll until a person is detected.

        Continuously scans robot camera at poll_interval rate.
        When a person is detected, automatically analyzes gender & age.

        Args:
            poll_interval: Time between scans (seconds)
            stop_event: Event to stop the loop from outside

        Returns:
            PersonInfo when a person is detected
        """
        logger.info(
            f"👀 Waiting for visitors "
            f"(scanning every {poll_interval}s)..."
        )

        while True:
            if stop_event and stop_event.is_set():
                logger.info("🛑 Stop signal received.")
                return PersonInfo()

            detect_info = await self.detect_person()

            if detect_info.detected:
                logger.info("🎉 Visitor detected! Analyzing...")
                person_info = await self.analyze_person()

                if person_info.detected:
                    return person_info

                # If analyze failed but detect succeeded → return basic info
                detect_info.gender = "unknown"
                return detect_info

            await asyncio.sleep(poll_interval)

    # ── Take photo ───────────────────────────
    async def take_photo(self) -> Optional[str]:
        """Capture a photo using the robot camera.

        Returns:
            Photo path on robot (sdcard/...) or None on failure
        """
        try:
            logger.info("📸 Taking photo...")
            take_pic = TakePicture(
                is_serial=True,
                take_picture_type=TakePictureType.IMMEDIATELY,
            )
            result_type, response = await take_pic.execute()

            if result_type == MiniApiResultType.Success and response is not None:
                pic_path = response.picPath
                logger.info(f"✅ Photo saved: {pic_path}")
                return pic_path
            else:
                logger.warning("⏱️ Photo capture failed.")
                return None
        except Exception as e:
            logger.error(f"❌ Photo error: {e}")
            return None

    # ── Last detection info ──────────────────
    @property
    def last_person(self) -> Optional[PersonInfo]:
        """Return the most recently detected person's info."""
        return self._last_person_info


# ═════════════════════════════════════════════
# Standalone test
# ═════════════════════════════════════════════
async def _test():
    """Test face detection & analysis."""
    from connection import RobotConnection

    async with RobotConnection():
        vision = VisionModule()

        print("\n── Test Detect Person ──")
        info = await vision.detect_person()
        print(f"Detected: {info.detected}, Count: {info.face_count}")

        print("\n── Test Analyze Person ──")
        info = await vision.analyze_person()
        print(
            f"Gender: {info.gender_label}, Score: {info.gender_score}, "
            f"Age: {info.age}"
        )

        print("\n── Test Take Photo ──")
        path = await vision.take_photo()
        print(f"Photo path: {path}")


if __name__ == "__main__":
    asyncio.run(_test())
