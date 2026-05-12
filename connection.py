"""
╔══════════════════════════════════════════════════════════════╗
║          ROBOT LỄ TÂN — CONNECTION MODULE                   ║
║  Quản lý kết nối WebSocket tới robot Alpha Mini             ║
╚══════════════════════════════════════════════════════════════╝

Module này xử lý:
  - MockDevice: Wrapper IP để SDK không bị AttributeError
  - RobotConnection: Quản lý lifecycle kết nối (connect/release)
  - Retry logic khi kết nối failed
  - Context manager (async with) cho clean code
"""

import asyncio
import logging

import mini.mini_sdk as MiniSdk
from mini.apis.api_sound import ChangeRobotVolume
from mini.apis.api_setup import StopRunProgram
from mini.apis.api_config import SetRobotLanguage, GetRobotLanguage
from mini.apis.base_api import MiniApiResultType

from config import (
    ROBOT_IP,
    ROBOT_PORT,
    ROBOT_NAME,
    ROBOT_VOLUME,
    CONNECTION_RETRY,
    CONNECTION_RETRY_DELAY,
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
)

# ─────────────────────────────────────────────
# Logger
# ─────────────────────────────────────────────
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
logger = logging.getLogger("connection")


# ═════════════════════════════════════════════
# MockDevice — Bọc IP để tương thích với SDK
# ═════════════════════════════════════════════
class MockDevice:
    """Giả lập cấu trúc WiFiDevice mà MiniSdk.connect() yêu cầu.

    SDK alphamini kỳ vọng object có các thuộc tính:
      - address: IP address
      - name: tên thiết bị
      - port: cổng WebSocket (mặc định 5100)

    Nếu truyền string IP trực tiếp sẽ gây AttributeError.
    """

    def __init__(self, ip: str, port: int = 5100, name: str = "AlphaMini"):
        self.address = ip
        self.name = name
        self.port = port

    def __repr__(self) -> str:
        return f"MockDevice(ip={self.address}, port={self.port}, name={self.name})"


# ═════════════════════════════════════════════
# RobotConnection — Quản lý kết nối robot
# ═════════════════════════════════════════════
class RobotConnection:
    """Quản lý toàn bộ lifecycle kết nối với robot Alpha Mini.

    Hỗ trợ:
      - Retry khi kết nối failed
      - Context manager (async with)
      - Thiết lập âm lượng sau khi kết nối
      - Vào/thoát chế độ lập trình

    Usage:
        async with RobotConnection() as robot:
            # robot đã kết nối, sẵn sàng sử dụng
            ...
    """

    def __init__(
        self,
        ip: str = ROBOT_IP,
        port: int = ROBOT_PORT,
        name: str = ROBOT_NAME,
        volume: float = ROBOT_VOLUME,
    ):
        self._ip = ip
        self._port = port
        self._name = name
        self._volume = volume
        self._connected = False
        self._device = MockDevice(ip=ip, port=port, name=name)

    # ── Properties ──────────────────────────
    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def device(self) -> MockDevice:
        return self._device

    # ── Kết nối ─────────────────────────────
    async def connect(self, max_retries: int = CONNECTION_RETRY) -> bool:
        """Kết nối tới robot với retry logic.

        Args:
            max_retries: Số lần thử tối đa

        Returns:
            True nếu kết nối thành công
        """
        # Thiết lập loại robot (DEDU = Alpha Mini bản giáo dục nội địa)
        MiniSdk.set_robot_type(MiniSdk.RobotType.DEDU)

        for attempt in range(1, max_retries + 1):
            logger.info(
                f"🔌 Đang kết nối tới robot {self._ip}:{self._port} "
                f"(lần {attempt}/{max_retries})..."
            )
            try:
                is_ok = await MiniSdk.connect(self._device)
                if is_ok:
                    self._connected = True
                    logger.info("✅ Kết nối robot thành công!")

                    # Thiết lập âm lượng
                    await self._set_volume(self._volume)
                    return True
                else:
                    logger.warning(f"❌ Kết nối failed (lần {attempt})")
            except Exception as e:
                logger.error(f"❌ Lỗi kết nối (lần {attempt}): {e}")

            if attempt < max_retries:
                logger.info(f"⏳ Chờ {CONNECTION_RETRY_DELAY}s rồi thử lại...")
                await asyncio.sleep(CONNECTION_RETRY_DELAY)

        logger.error("🚫 Không thể kết nối robot sau tất cả các lần thử!")
        return False

    # ── Ngắt kết nối ────────────────────────
    async def disconnect(self):
        """Ngắt kết nối và giải phóng tài nguyên."""
        if self._connected:
            logger.info("🔌 Đang ngắt kết nối robot...")
            try:
                await MiniSdk.release()
                self._connected = False
                logger.info("✅ Đã ngắt kết nối.")
            except Exception as e:
                logger.error(f"⚠️ Lỗi khi ngắt kết nối: {e}")
                self._connected = False

    # ── Chế độ lập trình ────────────────────
    async def enter_program_mode(self) -> bool:
        """Vào chế độ lập trình (cần thiết cho một số lệnh)."""
        if not self._connected:
            logger.error("Chưa kết nối robot!")
            return False
        try:
            result = await MiniSdk.enter_program()
            if result:
                logger.info("✅ Đã vào chế độ lập trình.")
            return result
        except Exception as e:
            logger.error(f"Lỗi vào chế độ lập trình: {e}")
            return False

    async def quit_program_mode(self) -> bool:
        """Thoát chế độ lập trình."""
        if not self._connected:
            return False
        try:
            await MiniSdk.quit_program()
            logger.info("✅ Đã thoát chế độ lập trình.")
            return True
        except Exception as e:
            logger.error(f"Error exiting programming mode: {e}")
            return False

    # ── Âm lượng ────────────────────────────
    async def _set_volume(self, volume: float):
        """Set robot volume."""
        try:
            vol_api = ChangeRobotVolume(is_serial=True, volume=volume)
            await vol_api.execute()
            logger.info(f"🔊 Volume set: {volume:.0%}")
        except Exception as e:
            logger.warning(f"⚠️ Could not set volume: {e}")

    async def mute(self):
        """Mute robot (volume=0) — used during recording.

        Robot sẽ không phát bất kỳ âm thanh nào (ngay cả
        'I didn't hear your voice') while keeping the mic active.
        """
        try:
            vol_api = ChangeRobotVolume(is_serial=True, volume=0.0)
            await vol_api.execute()
            logger.debug("🔇 Robot muted")
        except Exception:
            pass

    async def unmute(self):
        """Restore robot volume to configured level."""
        try:
            vol_api = ChangeRobotVolume(is_serial=True, volume=self._volume)
            await vol_api.execute()
            logger.debug(f"🔊 Robot unmute ({self._volume:.0%})")
        except Exception:
            pass

    # ── Ngôn ngữ ────────────────────────────
    async def set_language(self, lang_code: str = "vi-VN") -> bool:
        """Set robot language (STT/TTS).

        SDK giới hạn enum RobotLanguage chỉ có en_US/ru_RU,
        nhưng protobuf nhận string → ta gửi trực tiếp.

        Robot dùng Google Cloud TTS/ASR format: 'vi-VN', 'zh-CN', 'en-GB'

        Args:
            lang_code: Mã ngôn ngữ (VD: 'vi-VN', 'zh-CN', 'en-US')

        Returns:
            True nếu thành công
        """
        try:
            from mini.apis.cmdid import _PCProgramCmdId
            from mini.pb2.pccodemao_setrobotlanguage_pb2 import (
                SetRobotLanguageRequest,
                SetRobotLanguageResponse,
            )
            from mini.apis.base_api import socket, DEFAULT_TIMEOUT

            request = SetRobotLanguageRequest()
            request.language = lang_code

            cmd_id = _PCProgramCmdId.SET_ROBOT_LANGUAGE.value
            result = await socket.send_msg(cmd_id, request, DEFAULT_TIMEOUT)

            if result:
                data = result.bodyData
                response = SetRobotLanguageResponse()
                response.ParseFromString(data)
                if response.isSuccess:
                    logger.info(f"🌐 Language set: {lang_code}")
                    return True
                else:
                    logger.debug(
                        f"Setting language '{lang_code}' failed: "
                        f"code={response.resultCode}, state={response.state}"
                    )
            else:
                logger.debug(f"Setting language '{lang_code}' timeout")
            return False
        except Exception as e:
            logger.debug(f"Error setting language '{lang_code}': {e}")
            return False

    async def try_set_vietnamese(self) -> bool:
        """Try setting Vietnamese with multiple format codes.

        Robot có thể dùng format khác nhau tùy firmware.
        Thử lần lượt cho đến khi thành công.

        Returns:
            True nếu đặt được tiếng Việt
        """
        # Thử các format phổ biến
        vi_codes = ["vi-VN", "vi_VN", "vi", "VI"]
        for code in vi_codes:
            logger.info(f"🌐 Trying language: {code}...")
            if await self.set_language(code):
                return True

        logger.warning(
            "⚠️ Robot does not support Vietnamese STT. "
            "Using English + bilingual knowledge base."
        )
        return False

    async def get_language(self) -> str:
        """Get current robot language."""
        try:
            lang_api = GetRobotLanguage(is_serial=True)
            result_type, response = await lang_api.execute()
            if result_type == MiniApiResultType.Success and response:
                lang = getattr(response, 'language', 'unknown')
                logger.info(f"🌐 Current language: {lang}")
                return str(lang)
            return "unknown"
        except Exception as e:
            logger.warning(f"⚠️ Could not read language: {e}")
            return "unknown"

    # ── Context Manager ─────────────────────
    async def __aenter__(self):
        """Supports 'async with RobotConnection() as conn:'"""
        success = await self.connect()
        if not success:
            raise ConnectionError(
                f"Could not connect to robot at {self._ip}:{self._port}"
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Auto quit + disconnect when exiting context."""
        # Thoát chế độ lập trình trước — dừng mọi behavior robot
        await self.quit_program_mode()
        await self.disconnect()
        return False  # Không suppress exception


# ═════════════════════════════════════════════
# Test module độc lập
# ═════════════════════════════════════════════
async def _test():
    """Test basic connection."""
    async with RobotConnection() as conn:
        print(f"Robot connected: {conn.is_connected}")
        print(f"Device: {conn.device}")
        await asyncio.sleep(2)
        print("Test complete!")


if __name__ == "__main__":
    asyncio.run(_test())
