# HỆ THỐNG PHÂN LOẠI ĐƠN HÀNG TỰ ĐỘNG - KHO TỔNG SPX MEGA SOC PHÙ CHẨN

> **Tích hợp PC-Control V1:** xem [hướng dẫn PC–DevKit–S3](../Software-PC%20Control/parcel-vision-system/docs/integration_v1.md).
> `cv_station_mock.py` và nút mô phỏng web chỉ ghi mô phỏng, không xác nhận phân loại thật.
> PC-Control mới dùng FastAPI, UDP W5500 và UART hai board; có job ID và phục hồi kết quả.
**Môn học:** Ứng Dụng Máy Tính Trong Đo Lường & Điều Khiển  
**Địa điểm mô phỏng:** Kho Trung Chuyển Shopee Express (SPX) Phù Chẩn - TP. Từ Sơn - Tỉnh Bắc Ninh (Kho Mega SOC lớn nhất miền Bắc).

---

## 1. MÔ HÌNH PHÂN PHỐI & TÊN CÁC RỔ PHÂN LOẠI (CHUTES)
Tại Kho Mega SOC Phù Chẩn, hàng hóa toàn quốc tập kết về và được băng tải phân luồng đi các trung tâm trung chuyển tỉnh/khu vực. Mô hình thực nghiệm được cấu hình thành **5 Rổ Khu Vực + 1 Rổ Lỗi**:

| Mã Rổ (Chute ID) | Tên Rổ Phân Loại (Destination Hub) | Khu Vực Phụ Trách | Mã Định Tuyến Mẫu (Routing Code) |
| :--- | :--- | :--- | :--- |
| **RỔ 1 (Chute 1)** | **HN CENTRAL SOC** | Toàn bộ Hà Nội (Cầu Giấy, Đống Đa, Long Biên, Ba Đình...) | `HN-29-01-CG02` |
| **RỔ 2 (Chute 2)** | **BN-BG HUB** | Bắc Ninh (Từ Sơn, Quế Võ...), Bắc Giang, Lạng Sơn | `BN-99-01-TS01` |
| **RỔ 3 (Chute 3)** | **HP-QN HUB** | Hải Phòng (Hồng Bàng, Lê Chân...), Quảng Ninh, Hải Dương | `HP-16-01-HB01` |
| **RỔ 4 (Chute 4)** | **TN-PT HUB** | Thái Nguyên, Phú Thọ, Vĩnh Phúc, Tuyên Quang, Lào Cai... | `TN-20-01-ST01` |
| **RỔ 5 (Chute 5)** | **ND-TH HUB** | Nam Định, Hà Nam, Thái Bình, Ninh Bình, Thanh Hóa... | `ND-18-01-TP01` |
| **RỔ 0 / REJECT** | **SỌT LỖI / NGOẠI LỆ** | Hàng mờ tem, rách mã, quét 3 lần thất bại hoặc không có trong CSDL | `ERR-REJECT` |

---

## 2. KIẾN TRÚC HỆ THỐNG FULLSTACK & CƠ ĐIỆN TỬ
```
[ Khách Mua Hàng / Cả Lớp ] (Điện thoại / Laptop)
          │
          ▼ Đặt hàng trên Web Shopee Clone (Tự động gán Rổ 1-5)
  ┌─────────────────────────────────────────────────────────┐
  │ FASTAPI SERVER + DATABASE CHUẨN QUAN HỆ                │
  │ • Quản lý sản phẩm, đơn hàng, bảng bưu kiện             │
  │ • Sinh tem vận đơn Shopee Xpress chuẩn A7               │
  │ • RESTful API & WebSocket Real-time                     │
  └──────────┬──────────────────────────────────┬───────────┘
             │ In Tem A7                        │ Tra cứu API
             ▼                                  ▼
    [ Hộp Hàng Trên Băng Tải ]        [ Trạm Computer Vision ]
             │                       (Webcam 2K + OpenCV QR/Barcode)
             ▼                                  │ Gửi lệnh UART
    [ Băng Chuyền Phân Loại ] ◄─────────────────┘
    • Cơ cấu gạt / hút / đẩy kích hoạt vào Rổ 1-5
    • Quét 3 lần lỗi rơi vào Sọt Lỗi (Reject) ở cuối băng tải
```

---

---

## 3. HƯỚNG DẪN KHỞI CHẠY HỆ THỐNG

### Cách 1: Chạy Siêu Tốc Bằng Docker (Khuyên Dùng - 1 Lệnh Là Chạy Ngay)
Hệ thống đã được đóng gói sẵn Docker & Docker Compose chuẩn production:
```bash
# 1. Khởi động container (Tự động build, seed CSDL mẫu và chạy server trên cổng 8090):
docker compose up -d

# 2. Xem log hoạt động của container:
docker compose logs -f

# 3. Dừng hệ thống:
docker compose down
```
> **Lưu ý:** Dữ liệu CSDL SQLite được lưu tự động và bền vững tại thư mục `./data/warehouse.db` trên máy tính của bạn, không bao giờ bị mất dữ liệu khi restart container.

### Cách 2: Chạy Thủ Công Bằng Python (Không dùng Docker)
```bash
# 1. Cài đặt thư viện:
pip install -r requirements.txt

# 2. Khởi tạo dữ liệu mẫu:
python seed_data.py

# 3. Chạy Server:
python -m uvicorn main:app --host 0.0.0.0 --port 8090 --reload
```

---

## 4. CÁC ĐỊA CHỈ TRUY CẬP 3 PHÂN HỆ ĐỘC LẬP (CHUẨN SHOPEE THỰC TẾ)

1. **PHÂN HỆ 1: SÀN MUA SẮM SHOPEE MALL (CHO KHÁCH HÀNG / CẢ LỚP):**
   - **Trang chủ Shopee:** `http://localhost:8090/`
     * Khách hàng vào chọn sản phẩm, thêm vào giỏ, nhập họ tên, SĐT và địa chỉ nhận hàng miền Bắc để đặt hàng.
     * Bấm nút **"Quét Trên ĐT"** ở thanh menu để hiện mã QR to đùng cho mọi người quét camera vào đặt hàng trên điện thoại!
   - **Đơn Mua Của Tôi (Tracking Timeline):** `http://localhost:8090/my-orders`
     * Xem lại tất cả đơn đã đặt. Bấm **"Theo Dõi Vận Chuyển"** (`/orders/{id}/tracking`) để xem thanh tiến trình (Timeline) nhảy tự động theo thời gian thực khi hàng chạy trên băng tải!

2. **PHÂN HỆ 2: KÊNH NGƯỜI BÁN SHOPEE (SHOPEE SELLER CENTRE - CHO THÀNH VIÊN NHÓM):**
   - **Cổng Người Bán:** `http://localhost:8090/seller`
     * Thành viên nhóm đăng nhập vào xem các đơn hàng khách vừa đặt.
     * Bấm **"Chuẩn Bị & In Tem A7"**: Mở phiếu in mã vận đơn Shopee Xpress chuẩn khổ A7 (74x105 mm, có Barcode 1D Code128, mã QR 2D, mã định tuyến to đậm). Nhóm in ra và dán trực tiếp lên hộp hàng thật ngoài đời.
     * Bấm **"Bàn Giao SPX"**: Kiện hàng sẵn sàng được đưa lên băng chuyền tại mô hình phân loại.

3. **PHÂN HỆ 3: KHO TỔNG SPX MEGA SOC PHÙ CHẨN & TRẠM PC CONTROL SCADA:**
   - **Cổng Điều Hành Kho & SCADA:** `http://localhost:8090/spx-hub`
     * Màn hình trực quan giám sát băng tải, 5 Rổ khu vực + 1 Sọt Lỗi.
     * Bảng bàn giao tiếp nhận bưu kiện từ Shop và đếm số lượng hàng rơi vào từng rổ qua WebSocket.
   - **Tài Liệu Swagger API (Chuẩn Quốc Tế):** `http://localhost:8090/docs`

---

## 5. HƯỚNG DẪN ĐƯA CƠ SỞ DỮ LIỆU & WEB LÊN PUBLIC INTERNET (ĐẲNG CẤP BẢO VỆ ĐỒ ÁN)

### Cách 1: Sử dụng PostgreSQL Cloud Miễn Phí (Supabase hoặc Neon.tech)
1. Đăng ký tài khoản miễn phí tại [Neon.tech](https://neon.tech) hoặc [Supabase.com](https://supabase.com).
2. Tạo một Database mới, copy chuỗi kết nối **Connection String** dạng:
   ```env
   DATABASE_URL=postgresql://neondb_owner:xxxx@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```
3. Mở file `.env` trong thư mục dự án và dán chuỗi trên vào `DATABASE_URL`.
4. Chạy lại `python seed_data.py` -> Toàn bộ dữ liệu sẽ được lưu trực tiếp trên Cloud PostgreSQL! Thầy cô có thể mở web quản trị của Supabase/Neon xem các bảng CSDL chuyên nghiệp.

### Cách 2: Public Web ra Internet Miễn Phí bằng Cloudflare Tunnel (Có HTTPS)
Tải công cụ `cloudflared` hoặc dùng `ngrok`:
```bash
# Sử dụng Cloudflare Tunnel (Không cần đăng ký tài khoản, hoàn toàn miễn phí):
cloudflared tunnel --url http://localhost:8090
```
Hệ thống sẽ cung cấp một đường link công khai dạng `https://xxxx.trycloudflare.com`. Thầy cô hay bạn bè dùng 4G ở bất kỳ đâu đều truy cập được!

---

## 6. HƯỚNG DẪN KẾT NỐI TRẠM THỊ GIÁC MÁY TÍNH (COMPUTER VISION)

Chạy file `cv_station_mock.py` trên máy tính nối với Webcam 2K:
```bash
python cv_station_mock.py
```
- **Chế độ 1 (Webcam thực tế):** Bật camera quét tem mã QR dán trên hộp hàng chạy trên băng tải.
- **Chế độ 2 (Mô phỏng tự động):** Giả lập tuần tự các kiện hàng chạy qua trạm và kích hoạt rổ 1-5, kèm kịch bản kiện hàng lỗi quét 3 lần thất bại rơi vào sọt Reject.
- **Kết nối Bo Mạch Điều Khiển:** Mở `cv_station_mock.py`, sửa `SERIAL_ENABLED = True` và đặt cổng COM của Arduino/ESP32 (ví dụ `COM3`) để gửi lệnh UART điều khiển xilanh/servo.
