import asyncio
import logging
import mini.mini_sdk as MiniSdk
from mini.apis.api_sound import StartPlayTTS

# Bật log để dễ theo dõi quá trình kết nối
logging.basicConfig(level=logging.INFO)

# Tạo một class giả lập cấu trúc thiết bị mà SDK yêu cầu
class MockDevice:
    def __init__(self, ip):
        self.address = ip
        self.name = "AlphaMini"
        self.port = 5100  # Port mặc định của Websocket trên Alpha Mini

async def main():
    # Khởi tạo loại robot
    MiniSdk.set_robot_type(MiniSdk.RobotType.DEDU)
    
    # KẾT NỐI: Cần thay IP này bằng IP thực tế của Alpha Mini
    ROBOT_IP = "192.168.100.141" 
    
    print(f"Đang gọi Alpha Mini tại {ROBOT_IP}...")
    
    # Bọc IP vào object trước khi kết nối
    target_device = MockDevice(ROBOT_IP)
    is_connected = await MiniSdk.connect(target_device)
    
    if is_connected:
        print("Kết nối thành công! Đang gửi lệnh...")
        
        # Test chức năng Text-to-Speech (Đọc văn bản)
        tts_action = StartPlayTTS(text="Chào Hội, hệ thống Python đã được kết nối!")
        await tts_action.execute()
        
        # Giải phóng kết nối sau khi xong việc
        await MiniSdk.release()
    else:
        print("Lỗi kết nối. Hãy check lại IP và chắc chắn cả 2 thiết bị chung mạng Wi-Fi.")

if __name__ == '__main__':
    asyncio.run(main())