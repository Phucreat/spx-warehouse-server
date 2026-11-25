from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from database import get_db
from models import Order
from schemas import OrderResponse
from api.api_station import ws_manager
from config import VN_TZ
import datetime

router = APIRouter(prefix="/api/v1/seller", tags=["Shopaa Seller Centre"])


def filter_orders_by_tab(orders: List[Order], status: Optional[str]) -> List[Order]:
    if not status or status == "ALL":
        return orders
    if status == "REJECTED":
        return [o for o in orders if o.has_scan_exception]
    if status == "ARRIVED_PHU_CHAN_HUB":
        return [
            o for o in orders
            if o.status in ("ARRIVED_PHU_CHAN_HUB", "IN_SORTING") and not o.has_scan_exception
        ]
    return [o for o in orders if o.status == status]


@router.get("/orders", response_model=List[OrderResponse])
def get_seller_orders(
    status: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lấy danh sách đơn hàng cho Kênh Người Bán (Shopee Seller Centre)"""
    query = db.query(Order).options(selectinload(Order.items), selectinload(Order.logs))
    if q:
        query = query.filter(
            (Order.tracking_code.ilike(f"%{q}%")) |
            (Order.order_code.ilike(f"%{q}%")) |
            (Order.recipient_name.ilike(f"%{q}%")) |
            (Order.recipient_phone.ilike(f"%{q}%"))
        )
    all_orders = query.order_by(Order.id.desc()).all()
    return filter_orders_by_tab(all_orders, status)

@router.post("/orders/{order_id}/prepare")
async def prepare_order_and_print(order_id: int, db: Session = Depends(get_db)):
    """
    Người bán bấm 'Chuẩn bị hàng & In tem SPX'.
    Cập nhật trạng thái sang READY_TO_SHIP để dán tem lên kiện hàng vật lý.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    
    now_utc = datetime.datetime.utcnow()
    order.status = "READY_TO_SHIP"
    order.confirmed_at = now_utc
    order.label_size = "A7"
    order.label_printed_at = datetime.datetime.now(datetime.timezone.utc)
    if not order.qr_payload:
        order.qr_payload = order.tracking_code
    db.commit()

    # Báo qua WebSocket
    await ws_manager.broadcast({
        "event": "SELLER_PREPARED",
        "order_code": order.order_code,
        "tracking_code": order.tracking_code,
        "message": f"Shop đã in tem và đóng gói đơn {order.tracking_code}",
        "timestamp": datetime.datetime.now(VN_TZ).strftime("%H:%M:%S")
    })

    return {
        "success": True,
        "message": "Đã xác nhận chuẩn bị hàng và sẵn sàng in tem",
        "order_id": order.id,
        "tracking_code": order.tracking_code,
        "print_url": f"/orders/{order.id}/label"
    }

@router.post("/orders/{order_id}/handover-spx")
async def handover_to_spx_hub(order_id: int, db: Session = Depends(get_db)):
    """
    Người bán bấm 'Giao Cho ĐVVC SPX Phù Chẩn'.
    Kiện hàng được đưa đến Kho Mega SOC Phù Chẩn và sẵn sàng lên băng tải phân loại.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")

    order.status = "ARRIVED_PHU_CHAN_HUB"
    order.hub_received_at = datetime.datetime.utcnow()
    db.commit()

    # Báo ngay cho Trạm SCADA & PC Control
    await ws_manager.broadcast({
        "event": "PARCEL_ARRIVED_HUB",
        "order_code": order.order_code,
        "tracking_code": order.tracking_code,
        "destination_chute": order.destination_chute_id,
        "hub_name": order.destination_hub,
        "message": f"Đơn hàng {order.tracking_code} đã nhập Kho Phù Chẩn, sẵn sàng lên băng tải!",
        "timestamp": datetime.datetime.now(VN_TZ).strftime("%H:%M:%S")
    })

    return {
        "success": True,
        "message": "Đã bàn giao cho SPX Phù Chẩn thành công",
        "order_id": order.id,
        "status": order.status
    }

@router.get("/stats")
def get_seller_stats(db: Session = Depends(get_db)):
    """Thống kê KPI cho Kênh Người Bán (đồng bộ cảnh báo ngoại lệ từ trạm Vision)"""
    orders = db.query(Order).options(selectinload(Order.logs)).all()
    total = len(orders)
    pending = sum(1 for o in orders if o.status == "PENDING_CONFIRMATION" and not o.has_scan_exception)
    ready = sum(1 for o in orders if o.status == "READY_TO_SHIP" and not o.has_scan_exception)
    in_hub = sum(1 for o in orders if o.status in ("ARRIVED_PHU_CHAN_HUB", "IN_SORTING") and not o.has_scan_exception)
    sorted_done = sum(1 for o in orders if o.status == "SORTED")
    rejected = sum(1 for o in orders if o.has_scan_exception)

    return {
        "total_orders": total,
        "pending_confirmation": pending,
        "ready_to_ship": ready,
        "in_hub": in_hub,
        "sorted": sorted_done,
        "rejected": rejected
    }
