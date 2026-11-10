"""
================================================================================
TRẠM THỊ GIÁC MÁY TÍNH & ĐIỀU KHIỂN CƠ CẤU HIỆN TRƯỜNG (COMPUTER VISION STATION)
Môn: Ứng Dụng Máy Tính Trong Đo Lường & Điều Khiển
Phân loại đơn hàng - Kho SPX Mega SOC Phù Chẩn (Bắc Ninh)
================================================================================

Chức năng:
1. Mở Webcam 2K đọc mã vạch Barcode 1D (Code128) hoặc mã QR 2D từ kiện hàng trên băng chuyền
2. Tra cứu API Server: GET /api/v1/sort/lookup?code=...
3. Thực hiện thuật toán:
   - Nếu mã hợp lệ: Xác định Rổ đích (Chute 1..5), gửi lệnh kích hoạt cơ cấu gắp/hút/đẩy tương ứng
   - Nếu quét 3 lần không hợp lệ hoặc mã không tồn tại -> Đẩy vào SỌT LỖI (Reject)
4. Truyền thông xuống Bo mạch điều khiển (Arduino/ESP32) qua cổng nối tiếp Serial COM (UART)
5. Gửi xác nhận POST /api/v1/sort/confirm về Server để cập nhật SCADA
"""

import sys
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import time
import requests
import cv2

# Cấu hình kết nối Server
SERVER_URL = "http://localhost:8090"

# Cấu hình Cổng COM kết nối Bo Mạch (Arduino/ESP32/PLC)
SERIAL_PORT = "COM3"  # Thay đổi cổng COM nếu có cắm bo mạch thực tế
BAUD_RATE = 9600
SERIAL_ENABLED = False  # Bật True khi cắm cáp USB nối Arduino/ESP32

serial_conn = None
if SERIAL_ENABLED:
    try:
        import serial
        serial_conn = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"[SERIAL] Đã kết nối bo mạch điều khiển tại {SERIAL_PORT}")
    except Exception as e:
        print(f"[SERIAL CẢNH BÁO] Không thể mở cổng {SERIAL_PORT}: {e}. Chạy chế độ mô phỏng lệnh.")

def send_command_to_board(command: str):
    """Gửi lệnh kích hoạt cơ cấu gạt/hút/đẩy xuống Bo Mạch Điều Khiển"""
    print(f"\n>>> [BO MẠCH ĐIỀU KHIỂN] LỆNH CHẤP HÀNH: '{command}'")
    if serial_conn and serial_conn.is_open:
        try:
            serial_conn.write(f"{command}\n".encode('utf-8'))
        except Exception as e:
            print(f"[SERIAL LỖI] {e}")

def process_package(barcode_text: str, attempt_count: int = 1):
    """Xử lý tra cứu bưu kiện và ra quyết định phân loại"""
    print(f"\n-------------------------------------------------------------")
    print(f"[WEBCAM QUÉT] Đọc được chuỗi: '{barcode_text}' (Lần quét: {attempt_count})")
    
    try:
        # 1. Gọi API tra cứu
        resp = requests.get(f"{SERVER_URL}/api/v1/sort/lookup", params={"code": barcode_text, "mark_in_sorting": "false"}, timeout=3)
        if resp.status_code != 200:
            print(f"[LỖI SERVER] HTTP {resp.status_code}")
            return False

        data = resp.json()

        if data["found"] and data["destination_chute_id"] > 0:
            chute_id = data["destination_chute_id"]
            hub_name = data["destination_hub"]
            routing = data["routing_code"]
            recipient = data["recipient_name"]

            print(f"[KHỚP DỮ LIỆU CSDL] Đơn hàng hợp lệ!")
            print(f"  • Người nhận: {recipient}")
            print(f"  • Mã định tuyến: {routing}")
            print(f"  • RỔ PHÂN LOẠI: RỔ {chute_id} -> {hub_name}")

            # 2. Gửi lệnh xuống Bo Mạch Điều Khiển
            # Ví dụ: PISTON_CHUTE_1 hoặc MOTOR_GAT_2
            send_command_to_board(f"ACTUATE_CHUTE_{chute_id}")

            # 3. Gửi xác nhận về Server
            confirm_resp = requests.post(f"{SERVER_URL}/api/v1/sort/confirm", json={
                "tracking_code": data["tracking_code"],
                "chute_id": chute_id,
                "status": "SUCCESS",
                "simulated": True,  # Legacy mock has no hardware DONE feedback.
                "scan_attempts": attempt_count,
                "scanned_from": "Webcam_2K_Station",
                "notes": f"Đã gạt vào Rổ {chute_id} thành công"
            }, timeout=3)
            return True

        else:
            print(f"[CẢNH BÁO] Không tìm thấy mã trong CSDL hoặc đơn lỗi!")
            if attempt_count >= 3:
                print(f"[NGOẠI LỆ] Đã quét đủ 3 lần thất bại -> ĐẨY VÀO SỌT LỖI (REJECT)!")
                send_command_to_board("ACTUATE_REJECT_CHUTE")
                requests.post(f"{SERVER_URL}/api/v1/sort/confirm", json={
                    "tracking_code": barcode_text,
                    "chute_id": 0,
                    "status": "REJECTED",
                    "simulated": True,
                    "scan_attempts": attempt_count,
                    "notes": "Quét 3 lần không hợp lệ -> Phân loại vào sọt lỗi"
                }, timeout=3)
            else:
                print(f"[THỬ LẠI] Quét lần {attempt_count}/3 chưa thành công...")
            return False

    except Exception as e:
        print(f"[LỖI XỬ LÝ] {e}")
        return False

def run_camera_mode():
    """Chế độ quét trực tiếp qua Webcam (Webcam 2K + OpenCV)"""
    print("\n[CHẾ ĐỘ WEBCAM] Đang khởi động camera...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[LỖI] Không thể mở Webcam. Kiểm tra lại kết nối camera!")
        return

    qr_detector = cv2.QRCodeDetector()
    last_detected = ""
    last_time = 0

    print("[WEBCAM SẴN SÀNG] Giơ tem vận đơn Shopee Xpress trước ống kính (Nhấn 'q' để thoát)...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Phát hiện mã QR
        retval, decoded_info, points, _ = qr_detector.detectAndDecodeMulti(frame)

        if retval and decoded_info:
            for info in decoded_info:
                if info and (info != last_detected or (time.time() - last_time > 4)):
                    last_detected = info
                    last_time = time.time()
                    
                    # Vẽ khung xanh quanh mã
                    if points is not None:
                        pts = points[0].astype(int)
                        cv2.polylines(frame, [pts], True, (0, 255, 0), 3)

                    # Xử lý phân loại
                    process_package(info, attempt_count=1)

        cv2.putText(frame, "SPX Mega SOC - Camera Gantry Station", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 140, 255), 2)
        cv2.imshow("Trang Thai Camera Quet Ma Don Hang", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def run_auto_simulation():
    """Chế độ tự động giả lập băng chuyền chạy mẫu (không cần bật camera)"""
    print("\n[CHẾ ĐỘ MÔ PHỎNG] Bắt đầu giả lập chu kỳ kiện hàng chạy qua trạm quét...")
    
    # Lấy danh sách đơn từ Server
    try:
        r = requests.get(f"{SERVER_URL}/api/v1/orders", params={"limit": 6})
        orders = r.json()
    except Exception as e:
        print(f"[LỖI KẾT NỐI] Không thể lấy danh sách đơn từ Server: {e}")
        return

    if not orders:
        print("[THÔNG BÁO] Không có đơn hàng nào trong CSDL. Hãy tạo đơn trên Web Shopee!")
        return

    for idx, order in enumerate(orders):
        time.sleep(2)
        tracking = order["tracking_code"]
        print(f"\n>>> KIỆN HÀNG THỨ {idx + 1} TIẾN VÀO TRẠM QUÉT CAMERA...")
        process_package(tracking, attempt_count=1)

    # Thử nghiệm 1 kiện hàng lỗi quét 3 lần
    time.sleep(2)
    print("\n>>> KIỆN HÀNG LỖI (MÃ KHÔNG XÁC ĐỊNH) TIẾN VÀO BĂNG CHUYỀN...")
    for attempt in range(1, 4):
        time.sleep(1)
        process_package("SPX_UNKNOWN_ERR_999", attempt_count=attempt)

if __name__ == "__main__":
    print("="*60)
    print(" HỆ THỐNG THỊ GIÁC MÁY TÍNH - KHO SPX MEGA SOC PHÙ CHẨN")
    print("="*60)
    print("1. Chạy quét trực tiếp bằng Webcam")
    print("2. Chạy giả lập tự động băng chuyền (Auto Demo)")
    print("="*60)
    
    choice = input("Nhập lựa chọn (1 hoặc 2) [Mặc định 2]: ").strip()
    if choice == "1":
        run_camera_mode()
    else:
        run_auto_simulation()
