from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Product, Category, Order, OrderItem, User
from schemas import CategoryResponse, ProductResponse, OrderCreate, OrderResponse
from routing_engine import determine_chute, generate_order_code, generate_tracking_code
from config import ORIGIN_HUB
from auth import get_current_user
import datetime

router = APIRouter(prefix="/api/v1", tags=["Shopaa Storefront"])

@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    """Lấy danh sách danh mục hàng hóa"""
    return db.query(Category).all()

@router.get("/products", response_model=List[ProductResponse])
def get_products(
    category_id: Optional[int] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lấy danh sách sản phẩm mẫu Shopee (hỗ trợ lọc theo danh mục hoặc từ khóa tìm kiếm)"""
    query = db.query(Product)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    return query.all()

@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product_detail(product_id: int, db: Session = Depends(get_db)):
    """Xem chi tiết 1 sản phẩm"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    return product

@router.post("/orders", response_model=OrderResponse)
def create_order(
    payload: OrderCreate, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Tạo đơn hàng mới từ giao diện mua sắm Shopee.
    Hệ thống tự động:
    1. Phân tích địa chỉ người nhận -> gán Rổ đích (Chute 1..5) và Routing Code
    2. Sinh mã đơn hàng Shopee và mã vận đơn SPX duy nhất
    3. Lưu trữ vào CSDL chuẩn quan hệ (gắn với tài khoản Người Mua nếu đã đăng nhập)
    """
    if not payload.items:
        raise HTTPException(status_code=400, detail="Đơn hàng phải có ít nhất 1 sản phẩm")

    # Lấy thông tin sản phẩm và tính tổng tiền, khối lượng
    total_amount = 0.0
    total_weight = 20  # Khối lượng bao bì cơ bản 20g
    items_to_save = []

    for it in payload.items:
        prod = db.query(Product).filter(Product.id == it.product_id).first()
        if not prod:
            raise HTTPException(status_code=404, detail=f"Sản phẩm ID {it.product_id} không tồn tại")
        
        subtotal = prod.price * it.quantity
        total_amount += subtotal
        total_weight += prod.weight_g * it.quantity

        items_to_save.append({
            "product_id": prod.id,
            "product_name": prod.name,
            "quantity": it.quantity,
            "price": prod.price,
            "weight_g": prod.weight_g
        })

    # Định tuyến kho tự động dựa trên địa chỉ nhận
    routing_info = determine_chute(payload.recipient_province, payload.recipient_district)
    order_code = generate_order_code()
    tracking_code = generate_tracking_code()

    new_order = Order(
        order_code=order_code,
        tracking_code=tracking_code,
        sender_name=ORIGIN_HUB["name"],
        sender_address=ORIGIN_HUB["address"],
        sender_phone=ORIGIN_HUB["phone"],
        recipient_name=payload.recipient_name,
        recipient_phone=payload.recipient_phone,
        recipient_province=payload.recipient_province,
        recipient_district=payload.recipient_district,
        recipient_address=payload.recipient_address,
        routing_code=routing_info["routing_code"],
        destination_hub=routing_info["hub_name"],
        destination_chute_id=routing_info["chute_id"],
        total_amount=total_amount,
        cod_amount=total_amount,  # Giả định thanh toán COD khi nhận hàng giống Shopee
        total_weight_g=total_weight,
        status="PENDING_CONFIRMATION",
        qr_payload=tracking_code,
        note=payload.note,
        label_size="A7",
        user_id=current_user.id if current_user else None,
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db.add(new_order)
    db.flush()

    for item_data in items_to_save:
        order_item = OrderItem(
            order_id=new_order.id,
            **item_data
        )
        db.add(order_item)

    db.commit()
    db.refresh(new_order)

    # Thông báo cho Seller Centre qua WebSocket
    from api.api_station import ws_manager
    import asyncio
    try:
        asyncio.create_task(ws_manager.broadcast({
            "event": "NEW_ORDER_PLACED",
            "order_code": new_order.order_code,
            "tracking_code": new_order.tracking_code,
            "recipient": new_order.recipient_name,
            "total_amount": new_order.total_amount,
            "message": f"Khách hàng {new_order.recipient_name} vừa đặt đơn hàng mới!",
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
        }))
    except Exception:
        pass

    return new_order
