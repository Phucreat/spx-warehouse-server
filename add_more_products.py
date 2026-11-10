import sys
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import random
from database import SessionLocal
from models import Category, Product

EXPANDED_PRODUCTS = [
    # ----------------------------------------------------
    # NHÓM 1: Thiết bị IoT & Vi điều khiển (iot-hardware)
    # ----------------------------------------------------
    {
        "category_slug": "iot-hardware",
        "name": "Kit Phát Triển ESP32 NodeMCU 30 Chân Wi-Fi + Bluetooth",
        "price": 85000,
        "original_price": 120000,
        "sold_count": 2450,
        "rating": 5.0,
        "weight_g": 35,
        "image_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=500&auto=format&fit=crop&q=60",
        "description": "Vi điều khiển lõi kép ESP32 phục vụ thu thập dữ liệu IoT, truyền thông Wi-Fi/Bluetooth về Server."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Bo Mạch Arduino Uno R3 (Kèm Cáp Nạp USB)",
        "price": 95000,
        "original_price": 130000,
        "sold_count": 1820,
        "rating": 4.9,
        "weight_g": 60,
        "image_url": "https://images.unsplash.com/photo-1608564697071-ddf911d81370?w=500&auto=format&fit=crop&q=60",
        "description": "Bo mạch nhúng chuẩn học tập, điều khiển động cơ bước, servo cơ cấu gạt phân loại hàng."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Động Cơ Servo MG996R Bánh Răng Kim Loại Lực Kéo 13kg",
        "price": 68000,
        "original_price": 95000,
        "sold_count": 940,
        "rating": 4.8,
        "weight_g": 65,
        "image_url": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500&auto=format&fit=crop&q=60",
        "description": "Servo mô men xoắn lớn phù hợp làm tay gạt phân loại bưu kiện trên băng chuyền."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Module Relay 4 Kênh 5V Cách Ly Quang PC817",
        "price": 38000,
        "original_price": 55000,
        "sold_count": 1320,
        "rating": 4.9,
        "weight_g": 75,
        "image_url": "https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=500&auto=format&fit=crop&q=60",
        "description": "Dùng để kích van điện từ khí nén, xilanh đẩy hoặc đóng cắt băng tải."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Cảm Biến Tiệm Cận Quang Chữ U / Quang Điện E3F-DS30C4",
        "price": 52000,
        "original_price": 75000,
        "sold_count": 780,
        "rating": 4.9,
        "weight_g": 90,
        "image_url": "https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=500&auto=format&fit=crop&q=60",
        "description": "Cảm biến phát hiện bưu kiện đi qua trạm quét camera để kích hoạt chụp ảnh."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Mạch Nhúng Máy Tính Đơn Bo Raspberry Pi 4 Model B (4GB RAM)",
        "price": 1450000,
        "original_price": 1850000,
        "sold_count": 520,
        "rating": 5.0,
        "weight_g": 110,
        "image_url": "https://images.unsplash.com/photo-1517055729445-fa7d27394b48?w=500&auto=format&fit=crop&q=60",
        "description": "Máy tính nhúng chạy hệ điều hành Linux, xử lý ảnh thị giác máy tính OpenCV và điều khiển trạm phân loại."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Kit Học Tập Vi Điều Khiển STM32F103C8T6 Blue Pill Kèm Mạch Nạp ST-Link V2",
        "price": 75000,
        "original_price": 110000,
        "sold_count": 890,
        "rating": 4.9,
        "weight_g": 45,
        "image_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=500&auto=format&fit=crop&q=60",
        "description": "Kit vi điều khiển ARM Cortex-M3 32-bit hiệu năng cao cho hệ thống điều khiển thời gian thực."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Màn Hình LCD 1602 Xanh Lá Kèm Module Giao Tiếp I2C",
        "price": 39000,
        "original_price": 55000,
        "sold_count": 1430,
        "rating": 4.8,
        "weight_g": 50,
        "image_url": "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=500&auto=format&fit=crop&q=60",
        "description": "Hiển thị thông tin mã vận đơn, tên rổ phân loại và trạng thái quét tại trạm hiện trường."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Cảm Biến Siêu Âm Đo Khoảng Cách HC-SR04 Độ Chính Xác Cao",
        "price": 22000,
        "original_price": 35000,
        "sold_count": 2890,
        "rating": 4.9,
        "weight_g": 25,
        "image_url": "https://images.unsplash.com/photo-1581092162384-8987c1d64718?w=500&auto=format&fit=crop&q=60",
        "description": "Đo khoảng cách vật thể từ 2cm - 400cm, ứng dụng phát hiện bưu kiện đầy rổ hoặc vật cản."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Module Cảm Biến Nhiệt Độ & Độ Ẩm Kỹ Thuật Số DHT22 (AM2302)",
        "price": 58000,
        "original_price": 80000,
        "sold_count": 960,
        "rating": 4.9,
        "weight_g": 30,
        "image_url": "https://images.unsplash.com/photo-1563770660941-20978e870e26?w=500&auto=format&fit=crop&q=60",
        "description": "Giám sát nhiệt độ và độ ẩm nhà kho thông minh bảo quản hàng hóa."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Động Cơ Bước 28BYJ-48 5V Kèm Mạch Điều Khiển ULN2003",
        "price": 28000,
        "original_price": 45000,
        "sold_count": 1650,
        "rating": 4.7,
        "weight_g": 55,
        "image_url": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500&auto=format&fit=crop&q=60",
        "description": "Động cơ bước điều khiển góc quay chính xác cho cơ cấu quay rổ bưu kiện."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Bộ Đầu Đọc Thẻ RFID RC522 13.56MHz Kèm Thẻ Trắng & Móc Khóa",
        "price": 34000,
        "original_price": 50000,
        "sold_count": 1120,
        "rating": 4.8,
        "weight_g": 30,
        "image_url": "https://images.unsplash.com/photo-1563013544-824ae1b704d3?w=500&auto=format&fit=crop&q=60",
        "description": "Module đọc thẻ tần số 13.56MHz ứng dụng định danh thùng hàng và nhân viên kho."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Mạch Hạ Áp DC-DC LM2596 Có Đồng Hồ LED Hiển Thị Điện Áp",
        "price": 32000,
        "original_price": 48000,
        "sold_count": 2100,
        "rating": 4.9,
        "weight_g": 35,
        "image_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=500&auto=format&fit=crop&q=60",
        "description": "Mạch chuyển đổi nguồn điện DC 4-40V xuống 1.25-37V ổn định cho hệ thống vi điều khiển."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Nguồn Tổ Ong Chuyển Mạch 12V 10A Vỏ Nhôm Tản Nhiệt",
        "price": 135000,
        "original_price": 190000,
        "sold_count": 670,
        "rating": 4.8,
        "weight_g": 450,
        "image_url": "https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=500&auto=format&fit=crop&q=60",
        "description": "Nguồn công suất lớn cấp cho động cơ băng tải và van khí nén của mô hình phân loại."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Cảm Biến Khí Gas & Báo Khói MQ-2 Cho Nhà Thông Minh",
        "price": 29000,
        "original_price": 45000,
        "sold_count": 890,
        "rating": 4.8,
        "weight_g": 25,
        "image_url": "https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=500&auto=format&fit=crop&q=60",
        "description": "Phát hiện rò rỉ khí gas LPG, khói cảnh báo cháy nổ tại kho hàng trung chuyển."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Cảm Biến Cân Nặng Loadcell 5kg Kèm Module Khuếch Đại HX711",
        "price": 65000,
        "original_price": 95000,
        "sold_count": 730,
        "rating": 4.9,
        "weight_g": 85,
        "image_url": "https://images.unsplash.com/photo-1581092162384-8987c1d64718?w=500&auto=format&fit=crop&q=60",
        "description": "Cân trọng lượng bưu kiện tự động khi đi qua bàn cân của trạm phân loại."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Mạch Thu Phát Không Dây NRF24L01+ 2.4GHz Kèm Anten Khuyếch Đại 1100m",
        "price": 55000,
        "original_price": 80000,
        "sold_count": 1280,
        "rating": 4.8,
        "weight_g": 35,
        "image_url": "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=500&auto=format&fit=crop&q=60",
        "description": "Truyền nhận tín hiệu điều khiển không dây giữa trạm chính và các cơ cấu chấp hành xa."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Đồng Hồ Đo Vạn Năng Kỹ Thuật Số Tự Động Thang Đo ZOYI ZT-X",
        "price": 290000,
        "original_price": 380000,
        "sold_count": 450,
        "rating": 5.0,
        "weight_g": 280,
        "image_url": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500&auto=format&fit=crop&q=60",
        "description": "Đo điện áp, dòng điện, điện trở, tụ điện, tần số phục vụ đo lường và sửa chữa mạch điều khiển."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Mỏ Hàn Thiếc Điều Chỉnh Nhiệt Độ 60W Kèm 5 Mũi Hàn & Thiếc Hàn",
        "price": 115000,
        "original_price": 160000,
        "sold_count": 890,
        "rating": 4.8,
        "weight_g": 220,
        "image_url": "https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=500&auto=format&fit=crop&q=60",
        "description": "Bộ hàn mạch điện tử thông minh, điều chỉnh nhiệt độ từ 200 - 450 độ C."
    },
    {
        "category_slug": "iot-hardware",
        "name": "Mạch Chuyển Đổi Giao Tiếp USB Sang TTL UART CP2102 6 Chân",
        "price": 26000,
        "original_price": 40000,
        "sold_count": 2300,
        "rating": 4.9,
        "weight_g": 15,
        "image_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=500&auto=format&fit=crop&q=60",
        "description": "Nạp chương trình và giao tiếp cổng COM ảo với PC Control qua chuẩn Serial UART."
    },

    # ----------------------------------------------------
    # NHÓM 2: Điện thoại & Phụ kiện (dien-thoai-phu-kien)
    # ----------------------------------------------------
    {
        "category_slug": "dien-thoai-phu-kien",
        "name": "Cáp Sạc Nhanh Type-C To Type-C 100W Dây Bọc Dù Chống Đứt",
        "price": 45000,
        "original_price": 90000,
        "sold_count": 5200,
        "rating": 4.9,
        "weight_g": 40,
        "image_url": "https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=500&auto=format&fit=crop&q=60",
        "description": "Cáp sạc siêu bền hỗ trợ sạc nhanh laptop, điện thoại công suất 100W."
    },
    {
        "category_slug": "dien-thoai-phu-kien",
        "name": "Tai Nghe Bluetooth True Wireless Không Dây Chống Ồn ENC",
        "price": 185000,
        "original_price": 290000,
        "sold_count": 3120,
        "rating": 4.8,
        "weight_g": 120,
        "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=500&auto=format&fit=crop&q=60",
        "description": "Âm bass mạnh mẽ, pin trâu 30 giờ, kết nối Bluetooth 5.3 cực nhạy."
    },
    {
        "category_slug": "dien-thoai-phu-kien",
        "name": "Giá Đỡ Điện Thoại Hợp Kim Nhôm Để Bàn Xoay 360 Độ",
        "price": 49000,
        "original_price": 85000,
        "sold_count": 4200,
        "rating": 5.0,
        "weight_g": 160,
        "image_url": "https://images.unsplash.com/photo-1586105251261-72a756497a11?w=500&auto=format&fit=crop&q=60",
        "description": "Giá đỡ kim loại chắc chắn, gấp gọn tiện lợi mang theo."
    },
    {
        "category_slug": "dien-thoai-phu-kien",
        "name": "Củ Sạc Nhanh GaN 65W 3 Cổng Type-C & USB Tiết Kiệm Không Gian",
        "price": 289000,
        "original_price": 420000,
        "sold_count": 1890,
        "rating": 4.9,
        "weight_g": 140,
        "image_url": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=500&auto=format&fit=crop&q=60",
        "description": "Công nghệ GaN tản nhiệt tốt, sạc nhanh cùng lúc 3 thiết bị Laptop, iPad, Smartphone."
    },
    {
        "category_slug": "dien-thoai-phu-kien",
        "name": "Pin Sạc Dự Phòng 20000mAh Hỗ Trợ Sạc Nhanh PD 22.5W Màn Hình LED",
        "price": 320000,
        "original_price": 450000,
        "sold_count": 2750,
        "rating": 4.9,
        "weight_g": 410,
        "image_url": "https://images.unsplash.com/photo-1609592426868-b80775d71c84?w=500&auto=format&fit=crop&q=60",
        "description": "Dung lượng lớn 20000mAh, sạc được 4-5 lần điện thoại, an toàn đạt chuẩn hàng không."
    },
    {
        "category_slug": "dien-thoai-phu-kien",
        "name": "Ốp Lưng Chống Sốc Trong Suốt 4 Góc Đệm Khí Chống Va Đập",
        "price": 35000,
        "original_price": 60000,
        "sold_count": 6400,
        "rating": 4.8,
        "weight_g": 45,
        "image_url": "https://images.unsplash.com/photo-1601593346740-925612772716?w=500&auto=format&fit=crop&q=60",
        "description": "Chất liệu TPU cao cấp chống ố vàng, bảo vệ cụm camera nhô cao."
    },
    {
        "category_slug": "dien-thoai-phu-kien",
        "name": "Kính Cường Lực 9D Chống Nhìn Trộm Full Viền Bo Cong",
        "price": 42000,
        "original_price": 75000,
        "sold_count": 5100,
        "rating": 4.8,
        "weight_g": 30,
        "image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=500&auto=format&fit=crop&q=60",
        "description": "Độ cứng 9H chống trầy xước, góc nghiêng 30 độ không thấy màn hình bảo mật tuyệt đối."
    },
    {
        "category_slug": "dien-thoai-phu-kien",
        "name": "Dây Đeo Đồng Hồ Thông Minh Silicon Mềm Thoáng Khí 20mm/22mm",
        "price": 39000,
        "original_price": 65000,
        "sold_count": 1420,
        "rating": 4.7,
        "weight_g": 35,
        "image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500&auto=format&fit=crop&q=60",
        "description": "Silicon thân thiện với da tay, chống thấm mồ hôi khi vận động thể thao."
    },
    {
        "category_slug": "dien-thoai-phu-kien",
        "name": "Chuột Không Dây Silent Click 2 Chế Độ Bluetooth 5.2 & Wireless 2.4G",
        "price": 119000,
        "original_price": 180000,
        "sold_count": 3200,
        "rating": 4.9,
        "weight_g": 95,
        "image_url": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=500&auto=format&fit=crop&q=60",
        "description": "Nút bấm êm ái không gây tiếng ồn, pin sạc Type-C dùng được 2 tháng."
    },
    {
        "category_slug": "dien-thoai-phu-kien",
        "name": "Bàn Phím Cơ Không Dây 3 Mode Hot-Swap RGB 87 Phím Red Switch",
        "price": 499000,
        "original_price": 750000,
        "sold_count": 980,
        "rating": 4.9,
        "weight_g": 780,
        "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=500&auto=format&fit=crop&q=60",
        "description": "Switch êm ái, đèn LED RGB 16.8 triệu màu, kết nối Bluetooth, 2.4G và cáp Type-C."
    },
    {
        "category_slug": "dien-thoai-phu-kien",
        "name": "Cổng Chuyển Đổi Hub Type-C 8 Trong 1 Sang HDMI 4K, USB 3.0 & LAN",
        "price": 350000,
        "original_price": 500000,
        "sold_count": 1150,
        "rating": 4.9,
        "weight_g": 110,
        "image_url": "https://images.unsplash.com/photo-1544652478-6653e09f18a2?w=500&auto=format&fit=crop&q=60",
        "description": "Mở rộng kết nối toàn diện cho Macbook và laptop mỏng nhẹ, vỏ nhôm nguyên khối."
    },
    {
        "category_slug": "dien-thoai-phu-kien",
        "name": "Loa Bluetooth Mini Cầm Tay Chống Nước Bass Cực Mạnh",
        "price": 175000,
        "original_price": 260000,
        "sold_count": 2100,
        "rating": 4.8,
        "weight_g": 310,
        "image_url": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=500&auto=format&fit=crop&q=60",
        "description": "Chuẩn chống nước IPX7, pin phát nhạc liên tục 8 tiếng, nhỏ gọn tiện dã ngoại."
    },
    {
        "category_slug": "dien-thoai-phu-kien",
        "name": "Tai Nghe Gaming Chụp Tai Có Mic Khử Ồn Đèn LED RGB Âm Vòm 7.1",
        "price": 245000,
        "original_price": 380000,
        "sold_count": 1670,
        "rating": 4.8,
        "weight_g": 380,
        "image_url": "https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=500&auto=format&fit=crop&q=60",
        "description": "Đệm tai êm ái bọc da cao cấp, micro thu âm đàm thoại rõ ràng trong trẻo."
    },
    {
        "category_slug": "dien-thoai-phu-kien",
        "name": "Thẻ Nhớ MicroSD SanDisk Ultra 128GB Tốc Độ Cao 100MB/s",
        "price": 165000,
        "original_price": 240000,
        "sold_count": 4800,
        "rating": 5.0,
        "weight_g": 15,
        "image_url": "https://images.unsplash.com/photo-1562975079-6a3f1eb9a272?w=500&auto=format&fit=crop&q=60",
        "description": "Tốc độ đọc ghi 100MB/s chuyên dụng cho camera an ninh, điện thoại và máy ảnh."
    },
    {
        "category_slug": "dien-thoai-phu-kien",
        "name": "Gậy Chụp Ảnh Selfie Tripod 3 Chân Kèm Điều Khiển Bluetooth Từ Xa",
        "price": 89000,
        "original_price": 140000,
        "sold_count": 3150,
        "rating": 4.7,
        "weight_g": 195,
        "image_url": "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=500&auto=format&fit=crop&q=60",
        "description": "Kéo dài tối đa 1.1 mét, chân đế kiềng 3 chân kim loại chắc chắn chống rung lắc."
    },

    # ----------------------------------------------------
    # NHÓM 3: Thời trang Nam / Nữ (thoi-trang)
    # ----------------------------------------------------
    {
        "category_slug": "thoi-trang",
        "name": "Áo Thun Unisex Cotton 100% Form Rộng Cổ Tròn Basic",
        "price": 89000,
        "original_price": 150000,
        "sold_count": 8900,
        "rating": 4.9,
        "weight_g": 200,
        "image_url": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500&auto=format&fit=crop&q=60",
        "description": "Chất liệu cotton mềm mại, thấm hút mồ hôi, thoáng mát mùa hè."
    },
    {
        "category_slug": "thoi-trang",
        "name": "Mũ Lưỡi Trai Nón Kèm Logo Thêu Nổi Phong Cách Hàn Quốc",
        "price": 39000,
        "original_price": 70000,
        "sold_count": 3400,
        "rating": 4.8,
        "weight_g": 85,
        "image_url": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=500&auto=format&fit=crop&q=60",
        "description": "Thiết kế năng động, dễ phối đồ khi đi học, đi chơi."
    },
    {
        "category_slug": "thoi-trang",
        "name": "Áo Khoác Dù Bomber 2 Lớp Chống Nước Chống Gió Cao Cấp",
        "price": 169000,
        "original_price": 250000,
        "sold_count": 2150,
        "rating": 4.8,
        "weight_g": 380,
        "image_url": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=500&auto=format&fit=crop&q=60",
        "description": "Vải dù tráng nano chống bám nước, lớp lót dù thấm hút mồ hôi, cản gió giữ ấm."
    },
    {
        "category_slug": "thoi-trang",
        "name": "Quần Short Đũi Nam Nữ Mặc Nhà Đi Chơi Cực Mát Có Dây Rút",
        "price": 65000,
        "original_price": 99000,
        "sold_count": 4300,
        "rating": 4.8,
        "weight_g": 190,
        "image_url": "https://images.unsplash.com/photo-1591195853828-11db59a44f6b?w=500&auto=format&fit=crop&q=60",
        "description": "Vải đũi xước tự nhiên mềm mịn, cạp chun co giãn vận động cực kỳ thoải mái."
    },
    {
        "category_slug": "thoi-trang",
        "name": "Áo Polo Nam Ngắn Tay Vải Cá Sấu Cotton Co Giãn 4 Chiều",
        "price": 129000,
        "original_price": 195000,
        "sold_count": 3200,
        "rating": 4.9,
        "weight_g": 240,
        "image_url": "https://images.unsplash.com/photo-1625910513413-568e64c39958?w=500&auto=format&fit=crop&q=60",
        "description": "Form áo đứng dáng chuẩn slimfit, cổ áo dệt bo dầy dặn không bai dão."
    },
    {
        "category_slug": "thoi-trang",
        "name": "Túi Tote Vải Canvas Dày Dặn Phong Cách Vintage Đựng Vừa Laptop",
        "price": 49000,
        "original_price": 85000,
        "sold_count": 2800,
        "rating": 4.9,
        "weight_g": 160,
        "image_url": "https://images.unsplash.com/photo-1544816155-12df9643f363?w=500&auto=format&fit=crop&q=60",
        "description": "Có khóa kéo miệng an toàn và ngăn phụ nhỏ tiện lợi đựng điện thoại, chìa khóa."
    },
    {
        "category_slug": "thoi-trang",
        "name": "Combo 5 Đôi Tất Vớ Cổ Ngắn Cotton Khử Mùi Thoáng Khí",
        "price": 45000,
        "original_price": 80000,
        "sold_count": 7800,
        "rating": 4.9,
        "weight_g": 120,
        "image_url": "https://images.unsplash.com/photo-1586350977771-b3b0abd50c82?w=500&auto=format&fit=crop&q=60",
        "description": "Sợi cotton dệt lưới thoáng khí, đệm gót silicon chống tuột gót khi đi giày thể thao."
    },
    {
        "category_slug": "thoi-trang",
        "name": "Kính Mát Thời Trang Unisex Tròng Phân Cực Chống Tia UV400",
        "price": 79000,
        "original_price": 130000,
        "sold_count": 1650,
        "rating": 4.8,
        "weight_g": 60,
        "image_url": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=500&auto=format&fit=crop&q=60",
        "description": "Gọng kim loại thanh mảnh, tròng polarized làm dịu mắt và chống lóa khi lái xe ban ngày."
    },
    {
        "category_slug": "thoi-trang",
        "name": "Thắt Lưng Nam Da Thật Khóa Tự Động Hợp Kim Chống Rỉ",
        "price": 95000,
        "original_price": 160000,
        "sold_count": 2400,
        "rating": 4.9,
        "weight_g": 210,
        "image_url": "https://images.unsplash.com/photo-1624222247344-550fb60583dc?w=500&auto=format&fit=crop&q=60",
        "description": "Dây da 3 lớp bền bỉ dập vân tinh tế, đầu khóa trượt không cần đục lỗ tiện dụng."
    },
    {
        "category_slug": "thoi-trang",
        "name": "Dép Quai Ngang Unisex Đúc Nguyên Khối Chống Trơn Trượt",
        "price": 59000,
        "original_price": 95000,
        "sold_count": 5600,
        "rating": 4.8,
        "weight_g": 290,
        "image_url": "https://images.unsplash.com/photo-1603808033192-082d6919d3e1?w=500&auto=format&fit=crop&q=60",
        "description": "Chất liệu EVA siêu nhẹ và đàn hồi êm chân, đế có rãnh thoát nước chống trượt."
    },
    {
        "category_slug": "thoi-trang",
        "name": "Balo Thời Trang Hàn Quốc Đa Ngăn Chống Nước Có Ngăn Laptop",
        "price": 189000,
        "original_price": 290000,
        "sold_count": 1850,
        "rating": 4.9,
        "weight_g": 550,
        "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500&auto=format&fit=crop&q=60",
        "description": "Vải Oxford cao cấp chống xước, ngăn đệm mút chống sốc đựng laptop 15.6 inch an toàn."
    },
    {
        "category_slug": "thoi-trang",
        "name": "Ví Nam Dáng Đứng Da Bò Bền Đẹp Nhiều Ngăn Tiện Lợi",
        "price": 119000,
        "original_price": 180000,
        "sold_count": 1350,
        "rating": 4.8,
        "weight_g": 130,
        "image_url": "https://images.unsplash.com/photo-1627123424574-724758594e93?w=500&auto=format&fit=crop&q=60",
        "description": "Thiết kế nhỏ gọn vừa túi quần, đựng thẻ ATM, căn cước và tiền mặt tiện lợi."
    },

    # ----------------------------------------------------
    # NHÓM 4: Đồ gia dụng & Tiện ích (gia-dung)
    # ----------------------------------------------------
    {
        "category_slug": "gia-dung",
        "name": "Bình Giữ Nhiệt Inox 304 Cao Cấp 500ml Có Lưới Lọc Trà",
        "price": 75000,
        "original_price": 135000,
        "sold_count": 2100,
        "rating": 4.9,
        "weight_g": 280,
        "image_url": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=500&auto=format&fit=crop&q=60",
        "description": "Giữ nhiệt nóng lạnh 12 tiếng liên tục, chống rỉ sét tuyệt đối."
    },
    {
        "category_slug": "gia-dung",
        "name": "Quạt Cầm Tay Mini Tích Điện 3 Tốc Độ Gió Cổng USB Type-C",
        "price": 55000,
        "original_price": 95000,
        "sold_count": 4800,
        "rating": 4.7,
        "weight_g": 140,
        "image_url": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?w=500&auto=format&fit=crop&q=60",
        "description": "Gió êm dịu, pin sạc 2000mAh dùng liên tục 5 giờ."
    },
    {
        "category_slug": "gia-dung",
        "name": "Đèn Học Để Bàn LED Chống Cận Thị 3 Chế Độ Ánh Sáng Cảm Ứng",
        "price": 125000,
        "original_price": 190000,
        "sold_count": 2350,
        "rating": 4.9,
        "weight_g": 350,
        "image_url": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=500&auto=format&fit=crop&q=60",
        "description": "Ánh sáng tự nhiên không nhấp nháy, xoay gập 180 độ, pin tích điện tiện lợi khi mất điện."
    },
    {
        "category_slug": "gia-dung",
        "name": "Ấm Đun Nước Siêu Tốc Inox 2 Lớp Cách Nhiệt Chống Bỏng 1.8L",
        "price": 149000,
        "original_price": 220000,
        "sold_count": 3100,
        "rating": 4.8,
        "weight_g": 850,
        "image_url": "https://images.unsplash.com/photo-1574269909862-7e1d70bb8078?w=500&auto=format&fit=crop&q=60",
        "description": "Đun sôi nước chỉ trong 3 phút, tự động ngắt điện khi sôi an toàn tuyệt đối."
    },
    {
        "category_slug": "gia-dung",
        "name": "Hộp Cơm Giữ Nhiệt Văn Phòng 3 Tầng Inox 304 Kèm Túi & Đũa Thìa",
        "price": 165000,
        "original_price": 260000,
        "sold_count": 1780,
        "rating": 4.9,
        "weight_g": 620,
        "image_url": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500&auto=format&fit=crop&q=60",
        "description": "Ruột inox 304 tiêu chuẩn vệ sinh thực phẩm, gioăng cao su chống tràn canh tuyệt đối."
    },
    {
        "category_slug": "gia-dung",
        "name": "Ổ Cắm Điện Thông Minh Đa Năng 4 Cổng USB & 3 Chân Cắm Chống Cháy",
        "price": 115000,
        "original_price": 180000,
        "sold_count": 2900,
        "rating": 4.9,
        "weight_g": 390,
        "image_url": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=500&auto=format&fit=crop&q=60",
        "description": "Dây dài 2 mét lõi đồng nguyên chất chịu tải 2500W, có công tắc ngắt nguồn an toàn."
    },
    {
        "category_slug": "gia-dung",
        "name": "Cân Điện Tử Nhà Bếp Đo Tiểu Ly Độ Chính Xác 0.1g Đến 5kg",
        "price": 79000,
        "original_price": 120000,
        "sold_count": 3400,
        "rating": 4.9,
        "weight_g": 260,
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=500&auto=format&fit=crop&q=60",
        "description": "Mặt kính chịu lực hoặc inox sạch sẽ, có chức năng trừ bì tare cân gia vị, làm bánh."
    },
    {
        "category_slug": "gia-dung",
        "name": "Máy Hút Bụi Cầm Tay Mini Không Dây Lực Hút Khỏe Dành Cho Bàn Làm Việc",
        "price": 155000,
        "original_price": 240000,
        "sold_count": 1890,
        "rating": 4.7,
        "weight_g": 420,
        "image_url": "https://images.unsplash.com/photo-1558317374-067fb5f30001?w=500&auto=format&fit=crop&q=60",
        "description": "Động cơ hút mạnh 6000Pa hút sạch bụi bàn phím, vụn giấy và nội thất ô tô."
    },
    {
        "category_slug": "gia-dung",
        "name": "Máy Xay Sinh Tố Cầm Tay Mini 6 Lưỡi Thép Sạc Pin Tiện Dụng",
        "price": 139000,
        "original_price": 210000,
        "sold_count": 2150,
        "rating": 4.8,
        "weight_g": 480,
        "image_url": "https://images.unsplash.com/photo-1570222094114-d054a817e56b?w=500&auto=format&fit=crop&q=60",
        "description": "Xay sinh tố hoa quả trực tiếp thành bình uống, mang đi tập gym hay văn phòng."
    },
    {
        "category_slug": "gia-dung",
        "name": "Đèn Pin LED Siêu Sáng Chiếu Xa 500m Nhôm Hàng Không Chống Nước",
        "price": 98000,
        "original_price": 160000,
        "sold_count": 1450,
        "rating": 4.8,
        "weight_g": 230,
        "image_url": "https://images.unsplash.com/photo-1517524008697-84bbe3c3fd98?w=500&auto=format&fit=crop&q=60",
        "description": "Chip LED P50 công suất cao, zoom chỉnh tiêu cự gom sáng hoặc tỏa rộng."
    },
    {
        "category_slug": "gia-dung",
        "name": "Bộ Dụng Cụ Vặn Ốc Vít Đa Năng 24 Đầu Thép S2 Có Hộp Nhôm",
        "price": 85000,
        "original_price": 135000,
        "sold_count": 2600,
        "rating": 4.9,
        "weight_g": 270,
        "image_url": "https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=500&auto=format&fit=crop&q=60",
        "description": "Đầu vít nam châm hít ốc chắc chắn, dùng tháo lắp điện thoại, laptop, thiết bị điện tử."
    },
    {
        "category_slug": "gia-dung",
        "name": "Máy Phun Sương Tạo Ẩm Không Khí Mini Đèn LED Đổi Màu Cổng USB",
        "price": 69000,
        "original_price": 110000,
        "sold_count": 2400,
        "rating": 4.7,
        "weight_g": 180,
        "image_url": "https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=500&auto=format&fit=crop&q=60",
        "description": "Khuếch tán sương nano mịn không làm ướt bàn, giữ ẩm phòng điều hòa hanh khô."
    },

    # ----------------------------------------------------
    # NHÓM 5: Sách & Dụng cụ học tập (sach-hoc-tap)
    # ----------------------------------------------------
    {
        "category_slug": "sach-hoc-tap",
        "name": "Sổ Tay Bìa Da Vintage A5 Giấy Dày Chống Lóa Kèm Bút Ký",
        "price": 42000,
        "original_price": 65000,
        "sold_count": 1950,
        "rating": 5.0,
        "weight_g": 220,
        "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=500&auto=format&fit=crop&q=60",
        "description": "Sổ ghi chép dự án kỹ thuật, bài giảng đại học sang trọng."
    },
    {
        "category_slug": "sach-hoc-tap",
        "name": "Bộ Thước Kẻ Đo Đa Năng Kỹ Thuật Cơ Khí Độ Chính Xác Cao",
        "price": 32000,
        "original_price": 50000,
        "sold_count": 1100,
        "rating": 4.9,
        "weight_g": 110,
        "image_url": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=500&auto=format&fit=crop&q=60",
        "description": "Dụng cụ đo lường và thiết kế mạch điện tử, cơ khí mô hình."
    },
    {
        "category_slug": "sach-hoc-tap",
        "name": "Sách: Lập Trình Hệ Thống Nhúng & IoT Với ESP32 / FreeRTOS Thực Chiến",
        "price": 135000,
        "original_price": 180000,
        "sold_count": 890,
        "rating": 5.0,
        "weight_g": 420,
        "image_url": "https://images.unsplash.com/photo-1532012164546-f432f2e3edd4?w=500&auto=format&fit=crop&q=60",
        "description": "Hướng dẫn chi tiết từ lập trình đa nhiệm FreeRTOS, kết nối Wi-Fi, MQTT đến xây dựng ứng dụng Web Server điều khiển thiết bị."
    },
    {
        "category_slug": "sach-hoc-tap",
        "name": "Sách: Kỹ Thuật Đo Lường & Điều Khiển Tự Động Trong Công Nghiệp",
        "price": 145000,
        "original_price": 200000,
        "sold_count": 1250,
        "rating": 4.9,
        "weight_g": 460,
        "image_url": "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=500&auto=format&fit=crop&q=60",
        "description": "Giáo trình chuẩn chuyên ngành tự động hóa, cảm biến, hệ thống SCADA và PLC trong dây chuyền sản xuất."
    },
    {
        "category_slug": "sach-hoc-tap",
        "name": "Máy Tính Bỏ Túi Khoa Học Casio fx-580VN X Chính Hãng",
        "price": 680000,
        "original_price": 750000,
        "sold_count": 3400,
        "rating": 5.0,
        "weight_g": 210,
        "image_url": "https://images.unsplash.com/photo-1594980596870-8aa52a78d8cd?w=500&auto=format&fit=crop&q=60",
        "description": "Dòng máy tính khoa học tốc độ cao 521 tính năng, ngôn ngữ tiếng Việt hỗ trợ giải hệ phương trình và ma trận."
    },
    {
        "category_slug": "sach-hoc-tap",
        "name": "Hộp Bút Học Sinh Đa Ngăn Vải Oxford Chống Thấm Nước Cỡ Lớn",
        "price": 48000,
        "original_price": 80000,
        "sold_count": 2100,
        "rating": 4.8,
        "weight_g": 130,
        "image_url": "https://images.unsplash.com/photo-1585776245993-876a44569932?w=500&auto=format&fit=crop&q=60",
        "description": "Sức chứa lên tới 50 cây bút và máy tính bỏ túi, nhiều ngăn chia phân loại khoa học."
    },
    {
        "category_slug": "sach-hoc-tap",
        "name": "Bộ 6 Cây Bút Dạ Quang Pastel Nhẹ Mắt Highlight Ghi Chú Đọc Sách",
        "price": 35000,
        "original_price": 60000,
        "sold_count": 4200,
        "rating": 4.9,
        "weight_g": 95,
        "image_url": "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=500&auto=format&fit=crop&q=60",
        "description": "Màu sắc vintage pastel nhẹ dịu không làm lóa mắt, mực nhanh khô không thấm qua trang sau."
    },
    {
        "category_slug": "sach-hoc-tap",
        "name": "Bút Ký Kim Loại Khắc Tên Cao Cấp Ngòi Gel 0.5mm Đen Sang Trọng",
        "price": 55000,
        "original_price": 95000,
        "sold_count": 1890,
        "rating": 4.9,
        "weight_g": 40,
        "image_url": "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=500&auto=format&fit=crop&q=60",
        "description": "Thân bút kim loại đầm tay, mực ra đều trơn tru, thích hợp ký tài liệu và làm quà tặng."
    },
    {
        "category_slug": "sach-hoc-tap",
        "name": "Bảng Vẽ Điện Tử Cảm Ứng Lực Đồ Họa 8192 Mức Kèm Bút Không Dùng Pin",
        "price": 399000,
        "original_price": 590000,
        "sold_count": 860,
        "rating": 4.9,
        "weight_g": 380,
        "image_url": "https://images.unsplash.com/photo-1561998338-13ad7883b60f?w=500&auto=format&fit=crop&q=60",
        "description": "Hỗ trợ học tập trực tuyến, vẽ kỹ thuật và ghi chú trực tiếp lên slide bài giảng PowerPoint."
    },
    {
        "category_slug": "sach-hoc-tap",
        "name": "Giá Kẹp Đọc Sách Đỡ iPad Bằng Gỗ Tự Nhiên Chống Mỏi Cổ Gù Lưng",
        "price": 89000,
        "original_price": 140000,
        "sold_count": 1200,
        "rating": 4.8,
        "weight_g": 450,
        "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=500&auto=format&fit=crop&q=60",
        "description": "Điều chỉnh 5 nấc độ nghiêng, 2 cần kẹp trang giữ sách chắc chắn không bị lật."
    },
    {
        "category_slug": "sach-hoc-tap",
        "name": "Bút Lông Bảng Trắng Xóa Được Combo 4 Cây (Đen, Xanh, Đỏ, Lục)",
        "price": 28000,
        "original_price": 45000,
        "sold_count": 3100,
        "rating": 4.8,
        "weight_g": 75,
        "image_url": "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=500&auto=format&fit=crop&q=60",
        "description": "Mực đậm nét, dễ dàng lau sạch bằng khăn mềm không để lại vệt ố trên bảng trắng."
    }
]

def sync_products():
    db = SessionLocal()
    try:
        categories = {c.slug: c.id for c in db.query(Category).all()}
        print(f"Loaded {len(categories)} categories: {list(categories.keys())}")
        
        existing_products = {p.name: p for p in db.query(Product).all()}
        print(f"Currently in DB: {len(existing_products)} products.")

        added_count = 0
        updated_count = 0

        for item in EXPANDED_PRODUCTS:
            slug = item["category_slug"]
            cat_id = categories.get(slug)
            name = item["name"]

            if name in existing_products:
                p = existing_products[name]
                p.category_id = cat_id
                p.price = item["price"]
                p.original_price = item["original_price"]
                p.sold_count = item["sold_count"]
                p.rating = item["rating"]
                p.weight_g = item["weight_g"]
                p.image_url = item["image_url"]
                p.description = item["description"]
                updated_count += 1
            else:
                p = Product(
                    category_id=cat_id,
                    name=name,
                    price=item["price"],
                    original_price=item["original_price"],
                    sold_count=item["sold_count"],
                    rating=item["rating"],
                    weight_g=item["weight_g"],
                    image_url=item["image_url"],
                    description=item["description"],
                    stock=random.randint(200, 999)
                )
                db.add(p)
                added_count += 1

        db.commit()
        total_now = db.query(Product).count()
        print(f"Đã thêm mới: {added_count} sản phẩm, Cập nhật: {updated_count} sản phẩm.")
        print(f"Tổng số sản phẩm hiện có trong CSDL: {total_now} sản phẩm!")
    finally:
        db.close()

if __name__ == "__main__":
    sync_products()
