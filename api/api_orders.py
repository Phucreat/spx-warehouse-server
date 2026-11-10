from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Order
from schemas import OrderResponse
import datetime

router = APIRouter(prefix="/api/v1/orders", tags=["Order Management & Logistics"])

@router.get("", response_model=List[OrderResponse])
def get_orders(
    status: Optional[str] = None,
    chute_id: Optional[int] = None,
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Lấy danh sách đơn hàng cho giao diện quản trị kho & in tem"""
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    if chute_id is not None:
        query = query.filter(Order.destination_chute_id == chute_id)
    if q:
        query = query.filter(
            (Order.tracking_code.ilike(f"%{q}%")) |
            (Order.order_code.ilike(f"%{q}%")) |
            (Order.recipient_name.ilike(f"%{q}%")) |
            (Order.recipient_phone.ilike(f"%{q}%"))
        )
    return query.order_by(Order.id.desc()).offset(offset).limit(limit).all()

@router.get("/{id_or_code}", response_model=OrderResponse)
def get_order_by_id_or_code(id_or_code: str, db: Session = Depends(get_db)):
    """Tìm đơn hàng theo ID, mã đơn hàng hoặc mã vận đơn SPX"""
    query = db.query(Order)
    if id_or_code.isdigit():
        order = query.filter((Order.id == int(id_or_code)) | (Order.order_code == id_or_code)).first()
    else:
        order = query.filter((Order.tracking_code == id_or_code) | (Order.order_code == id_or_code)).first()

    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    return order

@router.patch("/{order_id}/status")
def update_order_status(order_id: int, status: str, db: Session = Depends(get_db)):
    """Cập nhật trạng thái đơn hàng (VD: PENDING -> LABEL_PRINTED -> IN_SORTING -> SORTED)"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    
    order.status = status
    if status == "SORTED":
        order.sorted_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    return {"success": True, "message": f"Đã cập nhật trạng thái đơn hàng sang {status}"}
