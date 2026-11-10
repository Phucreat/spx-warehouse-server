import sys
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import datetime
import random
from database import engine, SessionLocal, Base
from models import Category, Product, Order, OrderItem, SortingLog, User
from routing_engine import determine_chute, generate_order_code, generate_tracking_code
from config import ORIGIN_HUB
from auth import hash_password

SAMPLE_CATEGORIES = [
    {"name": "Thiết bị IoT & Vi điều khiển", "icon": "cpu", "slug": "iot-hardware"},
    {"name": "Điện thoại & Phụ kiện", "icon": "smartphone", "slug": "dien-thoai-phu-kien"},
    {"name": "Thời trang Nam / Nữ", "icon": "shirt", "slug": "thoi-trang"},
    {"name": "Đồ gia dụng & Tiện ích", "icon": "home", "slug": "gia-dung"},
    {"name": "Sách & Dụng cụ học tập", "icon": "book-open", "slug": "sach-hoc-tap"}
]

from add_more_products import EXPANDED_PRODUCTS as SAMPLE_PRODUCTS

# Các đơn hàng mẫu có sẵn đại diện cho 5 rổ phân loại và 1 đơn rổ lỗi
SAMPLE_ORDERS = [
    {
        "name": "Nguyễn Văn An",
        "phone": "0981234567",
        "province": "Hà Nội",
        "district": "Cầu Giấy",
        "address": "Số 144 Xuân Thủy, Dịch Vọng Hậu",
        "item_idx": 0,  # ESP32
        "quantity": 2
    },
    {
        "name": "Trần Thị Mai",
        "phone": "0972345678",
        "province": "Bắc Ninh",
        "district": "Từ Sơn",
        "address": "Khu phố Đồng Kỵ, Phường Đồng Kỵ",
        "item_idx": 1,  # Arduino
        "quantity": 1
    },
    {
        "name": "Lê Hoàng Nam",
        "phone": "0913456789",
        "province": "Hải Phòng",
        "district": "Hồng Bàng",
        "address": "Số 28 Hoàng Văn Thụ",
        "item_idx": 2,  # Servo
        "quantity": 3
    },
    {
        "name": "Phạm Quốc Tuấn",
        "phone": "0964567890",
        "province": "Thái Nguyên",
        "district": "Sông Công",
        "address": "Đường Cách Mạng Tháng Tám, Phường Mỏ Chè",
        "item_idx": 3,  # Relay
        "quantity": 2
    },
    {
        "name": "Vũ Minh Hằng",
        "phone": "0935678901",
        "province": "Nam Định",
        "district": "Thành phố Nam Định",
        "address": "Số 68 Trần Hưng Đạo",
        "item_idx": 4,  # Cảm biến quang
        "quantity": 1
    },
    {
        "name": "Kiện Hàng Test Ngoại Lệ",
        "phone": "0909999999",
        "province": "Tỉnh Không Hợp Lệ",
        "district": "Chưa rõ",
        "address": "Địa chỉ bưu kiện lỗi quét nhầm",
        "item_idx": 5,  # Cáp sạc
        "quantity": 1
    }
]

def init_seed_data():
    """Khởi tạo cấu trúc bảng và nạp dữ liệu mẫu ban đầu"""
    print("Khởi tạo cấu trúc Database...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 0. Thêm tài khoản Người Bán (Kênh Người Bán) và Người Mua mẫu
        if db.query(User).count() == 0:
            print("Đang nạp tài khoản Người Bán và Người Mua mẫu...")
            sample_users = [
                User(
                    username="seller",
                    password_hash=hash_password("123"),
                    full_name="Trần Đức - Trưởng Nhóm (Người Bán)",
                    role="seller",
                    shop_name="Tổng Kho Linh Kiện & TMĐT Phù Chẩn Official",
                    phone="0988123456"
                ),
                User(
                    username="nhom1",
                    password_hash=hash_password("123"),
                    full_name="Nhóm 1 - Đo Lường & Điều Khiển",
                    role="seller",
                    shop_name="Tổng Kho Linh Kiện & TMĐT Phù Chẩn Official",
                    phone="0988654321"
                ),
                User(
                    username="nguoimua",
                    password_hash=hash_password("123"),
                    full_name="Nguyễn Văn A (Khách Hàng)",
                    role="buyer",
                    phone="0987654321"
                ),
                User(
                    username="khachhang",
                    password_hash=hash_password("123"),
                    full_name="Lê Thị B (Khách Hàng)",
                    role="buyer",
                    phone="0912345678"
                )
            ]
            db.add_all(sample_users)
            db.commit()
            print("Đã tạo sẵn 2 tài khoản Người Bán ('seller', 'nhom1') và 2 tài khoản Người Mua ('nguoimua', 'khachhang') với mật khẩu '123'.")

        # 1. Thêm danh mục
        if db.query(Category).count() == 0:
            print("Đang nạp danh mục sản phẩm...")
            cat_map = {}
            for cat_data in SAMPLE_CATEGORIES:
                cat = Category(**cat_data)
                db.add(cat)
                db.flush()
                cat_map[cat.slug] = cat.id
            db.commit()
            print("Đã thêm danh mục thành công.")
        else:
            cat_map = {c.slug: c.id for c in db.query(Category).all()}

        # 2. Thêm sản phẩm
        if db.query(Product).count() == 0:
            print("Đang nạp danh sách sản phẩm mẫu...")
            for p_data in SAMPLE_PRODUCTS:
                slug = p_data.pop("category_slug")
                cat_id = cat_map.get(slug)
                prod = Product(**p_data, category_id=cat_id)
                db.add(prod)
            db.commit()
            print("Đã nạp 14 sản phẩm đa dạng thành công.")

        # 3. Thêm các đơn hàng mẫu sẵn sàng cho in tem và chạy thử
        if db.query(Order).count() == 0:
            print("Đang tạo các đơn hàng mẫu cho 5 Rổ phân loại...")
            all_products = db.query(Product).all()
            for idx, sample in enumerate(SAMPLE_ORDERS):
                prod = all_products[sample["item_idx"] % len(all_products)]
                qty = sample["quantity"]
                total_val = prod.price * qty
                total_w = prod.weight_g * qty + 20  # + bao bì đóng gói

                routing_info = determine_chute(sample["province"], sample["district"])
                order_code = generate_order_code()
                tracking_code = generate_tracking_code()

                sample_statuses = ["PENDING_CONFIRMATION", "READY_TO_SHIP", "ARRIVED_PHU_CHAN_HUB", "SORTED", "ARRIVED_PHU_CHAN_HUB", "PENDING_CONFIRMATION"]
                status_to_assign = sample_statuses[idx % len(sample_statuses)] if routing_info["chute_id"] != 0 else "PENDING_CONFIRMATION"

                order = Order(
                    order_code=order_code,
                    tracking_code=tracking_code,
                    sender_name=ORIGIN_HUB["name"],
                    sender_address=ORIGIN_HUB["address"],
                    sender_phone=ORIGIN_HUB["phone"],
                    recipient_name=sample["name"],
                    recipient_phone=sample["phone"],
                    recipient_province=sample["province"],
                    recipient_district=sample["district"],
                    recipient_address=sample["address"],
                    routing_code=routing_info["routing_code"],
                    destination_hub=routing_info["hub_name"],
                    destination_chute_id=routing_info["chute_id"],
                    total_amount=total_val,
                    cod_amount=total_val,
                    total_weight_g=total_w,
                    status=status_to_assign,
                    qr_payload=tracking_code,
                    created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=random.randint(2, 10)),
                    confirmed_at=datetime.datetime.utcnow() - datetime.timedelta(hours=1) if status_to_assign != "PENDING_CONFIRMATION" else None,
                    hub_received_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=30) if status_to_assign in ("ARRIVED_PHU_CHAN_HUB", "SORTED") else None,
                    sorted_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=10) if status_to_assign == "SORTED" else None
                )
                db.add(order)
                db.flush()

                item = OrderItem(
                    order_id=order.id,
                    product_id=prod.id,
                    product_name=prod.name,
                    quantity=qty,
                    price=prod.price,
                    weight_g=prod.weight_g
                )
                db.add(item)
            db.commit()
            print("Đã tạo 6 đơn hàng mẫu đại diện cho các Rổ phân loại.")

        print("Nạp dữ liệu hoàn tất! CSDL đã sẵn sàng 100%.")

    finally:
        db.close()

if __name__ == "__main__":
    init_seed_data()
