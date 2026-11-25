import datetime
from sqlalchemy import Boolean, Column, Integer, String, Float, Text, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY as PG_ARRAY
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), default="buyer")  # "buyer" (Người Mua) hoặc "seller" (Người Bán)
    phone = Column(String(20), nullable=True)
    shop_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    orders = relationship("Order", back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    icon = Column(String(50), default="box")
    slug = Column(String(100), unique=True, index=True)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)
    sold_count = Column(Integer, default=120)
    rating = Column(Float, default=4.9)
    weight_g = Column(Integer, default=150)  # Khối lượng gói hàng tính bằng gram
    image_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    stock = Column(Integer, default=999)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    category = relationship("Category", back_populates="products")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_code = Column(String(50), unique=True, index=True, nullable=False)   # Mã đơn hàng Shopee
    tracking_code = Column(String(50), unique=True, index=True, nullable=False) # Mã vận đơn SPX (SPXVN...)
    
    # Thông tin Người gửi (Shop tại Kho Tổng Phù Chẩn)
    sender_name = Column(String(150), default="Tổng Kho Linh Kiện & TMĐT Phù Chẩn")
    sender_address = Column(String(255), default="Số 6 Đường số 5, KCN VSIP, P. Phù Chẩn, TP. Từ Sơn, Bắc Ninh")
    sender_phone = Column(String(20), default="19001221")

    # Thông tin Người nhận (Khách hàng đặt trên web)
    recipient_name = Column(String(150), nullable=False)
    recipient_phone = Column(String(20), nullable=False)
    recipient_province = Column(String(100), nullable=False)
    recipient_district = Column(String(100), nullable=False)
    recipient_address = Column(String(255), nullable=False)

    # Thông tin Logistics & Định tuyến phân loại
    routing_code = Column(String(50), nullable=False)        # VD: HN-29-01-CG02
    destination_hub = Column(String(150), nullable=False)    # Tên Hub đích
    destination_chute_id = Column(Integer, nullable=False)   # Mã rổ phân loại (1..5 hoặc 0)

    # Tài chính & Quy cách
    total_amount = Column(Float, default=0.0)
    cod_amount = Column(Float, default=0.0)
    total_weight_g = Column(Integer, default=100)            # Khối lượng sau đóng gói

    # Trạng thái bưu kiện chuẩn Shopee & SPX Express:
    # PENDING_CONFIRMATION: Chờ người bán xác nhận
    # READY_TO_SHIP: Người bán đã in tem vận đơn & đóng gói
    # ARRIVED_PHU_CHAN_HUB: Đã nhập Kho tổng SPX Phù Chẩn (sẵn sàng lên băng chuyền)
    # IN_SORTING: Bưu kiện đang trên băng chuyền qua trạm camera quét
    # SORTED: Đã phân loại tự động thành công vào Rổ 1..5
    # REJECTED: Quét 3 lần thất bại -> chuyển vào sọt lỗi ngoại lệ
    status = Column(String(50), default="PENDING_CONFIRMATION", index=True)
    qr_payload = Column(String(255), nullable=True)          # Chuỗi dữ liệu cho mã QR
    note = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)            # Thời điểm shop bấm xác nhận & in tem
    hub_received_at = Column(DateTime, nullable=True)         # Thời điểm SPX Phù Chẩn tiếp nhận
    sorted_at = Column(DateTime, nullable=True)               # Thời điểm robot/cơ cấu gạt vào rổ
    label_size = Column(String, nullable=False, default="A7")
    label_printed_at = Column(DateTime(timezone=True), nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    logs = relationship(
        "SortingLog",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="desc(SortingLog.id)",
    )

    @property
    def last_log(self):
        return self.logs[0] if self.logs else None

    @property
    def last_decision(self):
        log = self.last_log
        if not log:
            return None
        if log.decision:
            return log.decision
        return "PASS" if log.status in ("SORTED", "SUCCESS") else ("MANUAL_REVIEW" if log.status == "MANUAL_REVIEW" else "REJECT")

    @property
    def last_reason(self):
        log = self.last_log
        return (log.reason or log.notes) if log else None

    @property
    def last_station_id(self):
        log = self.last_log
        return (log.station_id or log.scanned_from) if log else None

    @property
    def last_scanned_at(self):
        log = self.last_log
        return log.created_at if log else None

    @property
    def has_scan_exception(self) -> bool:
        if self.status == "REJECTED":
            return True
        return self.status != "SORTED" and self.last_decision in ("REJECT", "MANUAL_REVIEW")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, nullable=True)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1)
    price = Column(Float, nullable=False)
    weight_g = Column(Integer, default=100)

    order = relationship("Order", back_populates="items")


class SortReceipt(Base):
    """Idempotency ledger; new table avoids changing existing SQLite columns."""
    __tablename__ = "sort_receipts"
    job_id = Column(String(32), primary_key=True)
    payload = Column(Text, nullable=False)
    response = Column(Text, nullable=False)


class SortingLog(Base):
    __tablename__ = "sorting_logs"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    tracking_code = Column(String(50), index=True, nullable=False)
    chute_id = Column(Integer, nullable=False)               # Rổ được gạt vào (1..5 hoặc 0)
    status = Column(String(50), nullable=False)              # SORTED, REJECTED hoặc MANUAL_REVIEW
    scan_attempts = Column(Integer, default=1)               # Số lần quét thử của camera
    scanned_from = Column(String(100), default="Webcam_2K_Station")
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    inspection_uuid = Column(String(36).with_variant(PG_UUID(as_uuid=True), "postgresql"), unique=True, nullable=True)
    decision = Column(String, nullable=True)                 # PASS, REJECT, MANUAL_REVIEW
    reason = Column(Text, nullable=True)
    qr_ok = Column(Boolean, nullable=True)
    logo_ok = Column(Boolean, nullable=True)
    damage_detected = Column(Boolean, nullable=True)
    damage_types = Column(JSON().with_variant(PG_ARRAY(Text), "postgresql"), nullable=True)
    station_id = Column(String, nullable=True)
    evidence_path = Column(Text, nullable=True)

    order = relationship("Order", back_populates="logs")
