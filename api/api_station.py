from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Order, SortingLog, SortReceipt
from sqlalchemy.exc import IntegrityError
from schemas import PackageLookupResponse, SortConfirmRequest, SortConfirmResponse
from config import CHUTE_DEFINITIONS
import datetime
import json

router = APIRouter(prefix="/api/v1/sort", tags=["Computer Vision & Sorting Control Station"])

# Connection Manager phục vụ WebSocket thời gian thực (SCADA Monitor)
class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(data))
            except Exception:
                pass

ws_manager = WebSocketManager()

@router.get("/lookup", response_model=PackageLookupResponse)
async def lookup_package_for_sorting(
    code: str = Query(..., description="Mã vận đơn SPX hoặc chuỗi QR quét được từ Webcam 2K"),
    mark_in_sorting: bool = True,
    db: Session = Depends(get_db)
):
    """
    API Dành riêng cho Máy tính Thị giác Máy tính (Computer Vision Station).
    Nhận mã barcode/QR từ camera -> tra cứu CSDL -> trả về Rổ phân loại (Chute ID: 1..5 hoặc 0-Reject)
    """
    clean_code = code.strip()
    
    # Tìm kiếm theo tracking_code, order_code hoặc chuỗi qr_payload
    order = db.query(Order).filter(
        (Order.tracking_code == clean_code) |
        (Order.order_code == clean_code) |
        (Order.qr_payload == clean_code)
    ).first()

    if not order:
        # Báo sự kiện mã không tồn tại cho SCADA
        await ws_manager.broadcast({
            "event": "SCAN_FAILED",
            "code": clean_code,
            "message": "Không tìm thấy trong CSDL -> Điều hướng vào Sọt Lỗi (Reject)",
            "chute_id": 0,
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
        })

        return PackageLookupResponse(
            found=False,
            status="NOT_FOUND",
            tracking_code=clean_code,
            destination_chute_id=0,
            destination_hub="SỌT LỖI / NGOẠI LỆ (Reject Chute)",
            action="REJECT",
            message="Mã kiện hàng không tồn tại trong CSDL. Điều hướng vào Sọt Lỗi (Reject)."
        )

    # Đơn hàng hợp lệ
    items_str = ", ".join([f"{it.product_name} (x{it.quantity})" for it in order.items]) if order.items else "Hàng hóa Shopee"
    action = f"SORT_CHUTE_{order.destination_chute_id}" if order.destination_chute_id > 0 else "REJECT"

    # Cập nhật trạng thái bưu kiện đang trên băng chuyền
    if mark_in_sorting and order.status in ("PENDING", "PENDING_CONFIRMATION", "READY_TO_SHIP", "ARRIVED_PHU_CHAN_HUB"):
        order.status = "IN_SORTING"
        db.commit()

    # Báo sự kiện quét thành công lên SCADA qua WebSocket
    await ws_manager.broadcast({
        "event": "SCAN_SUCCESS",
        "tracking_code": order.tracking_code,
        "order_code": order.order_code,
        "routing_code": order.routing_code,
        "destination_hub": order.destination_hub,
        "chute_id": order.destination_chute_id,
        "recipient": f"{order.recipient_name} ({order.recipient_province})",
        "weight_g": order.total_weight_g,
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
    })

    return PackageLookupResponse(
        found=True,
        status=order.status,
        tracking_code=order.tracking_code,
        order_code=order.order_code,
        destination_chute_id=order.destination_chute_id,
        destination_hub=order.destination_hub,
        routing_code=order.routing_code,
        recipient_name=order.recipient_name,
        recipient_province=order.recipient_province,
        total_weight_g=order.total_weight_g,
        items_summary=items_str,
        action=action,
        message=f"Hợp lệ. Điều hướng vào Rổ {order.destination_chute_id}: {order.destination_hub}"
    )

@router.post("/confirm", response_model=SortConfirmResponse)
async def confirm_sorting_result(
    payload: SortConfirmRequest,
    db: Session = Depends(get_db)
):
    """
    Ghi nhận kết quả sau khi cơ cấu gạt/hút/đẩy hoặc băng tải đã phân loại kiện hàng vào rổ.
    Đồng thời cập nhật trạng thái đơn hàng và lưu log kiểm định.
    """
    fingerprint = json.dumps(payload.model_dump(), sort_keys=True, ensure_ascii=False)
    if payload.job_id:
        receipt = db.get(SortReceipt, payload.job_id)
        if receipt:
            if receipt.payload != fingerprint:
                raise HTTPException(409, "job_id đã được dùng với nội dung khác")
            return SortConfirmResponse(**json.loads(receipt.response))
    if (payload.status == "SUCCESS") != (payload.chute_id > 0):
        raise HTTPException(422, "SUCCESS yêu cầu rổ 1..5; REJECTED yêu cầu rổ 0")
    order = db.query(Order).filter(Order.tracking_code == payload.tracking_code).first()
    if payload.status == "SUCCESS" and (
        order is None or order.destination_chute_id != payload.chute_id
    ):
        raise HTTPException(409, "Không tìm thấy đơn hoặc rổ đích không khớp")
    if not payload.simulated and order and order.status in ("SORTED", "REJECTED"):
        raise HTTPException(409, "Đơn đã có kết quả phân loại; cần xử lý lại thủ công")
    
    order_id = order.id if order else None
    new_status = "SORTED" if payload.status == "SUCCESS" else "REJECTED"

    response = SortConfirmResponse(
        success=True,
        message="Mô phỏng, không đổi trạng thái đơn" if payload.simulated else "Đã lưu kết quả phân loại",
        tracking_code=payload.tracking_code,
        chute_id=payload.chute_id,
        order_status="SIMULATED" if payload.simulated else new_status,
    )
    if payload.job_id:
        db.add(SortReceipt(job_id=payload.job_id, payload=fingerprint,
                           response=response.model_dump_json()))
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            receipt = db.get(SortReceipt, payload.job_id)
            if receipt and receipt.payload == fingerprint:
                return SortConfirmResponse(**json.loads(receipt.response))
            raise HTTPException(409, "Xung đột job_id")
    if payload.simulated:
        db.commit()
        return response

    if order:
        changed = db.query(Order).filter(
            Order.id == order.id, ~Order.status.in_(["SORTED", "REJECTED"])
        ).update({"status": new_status, "sorted_at": datetime.datetime.now(datetime.timezone.utc)},
                 synchronize_session=False)
        if changed != 1:
            db.rollback()
            raise HTTPException(409, "Đơn vừa được xác nhận bởi giao dịch khác")

    # Ghi log lịch sử phân loại
    log_entry = SortingLog(
        order_id=order_id,
        tracking_code=payload.tracking_code,
        chute_id=payload.chute_id,
        status=payload.status,
        scan_attempts=payload.scan_attempts,
        scanned_from=payload.scanned_from,
        notes=payload.notes or ("Đã phân loại vào rổ thành công - Đang vận chuyển đến trạm chuyển phát" if payload.status == "SUCCESS" else "Phân loại vào sọt lỗi")
    )
    db.add(log_entry)
    db.commit()

    # Báo sự kiện đã gạt xong lên SCADA Dashboard
    await ws_manager.broadcast({
        "event": "SORT_CONFIRMED",
        "tracking_code": payload.tracking_code,
        "chute_id": payload.chute_id,
        "status": payload.status,
        "scan_attempts": payload.scan_attempts,
        "notes": log_entry.notes,
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
    })

    return response

@router.get("/chutes")
def get_chute_list():
    """Lấy danh sách cấu hình các rổ phân loại (Chutes 1..5 và Chute 0)"""
    return CHUTE_DEFINITIONS

@router.get("/stats")
def get_sorting_statistics(db: Session = Depends(get_db)):
    """Thống kê sản lượng phân loại thời gian thực"""
    total_orders = db.query(Order).count()
    sorted_count = db.query(Order).filter(Order.status == "SORTED").count()
    pending_count = db.query(Order).filter(Order.status.in_(["PENDING", "LABEL_PRINTED", "PENDING_CONFIRMATION", "READY_TO_SHIP", "ARRIVED_PHU_CHAN_HUB", "IN_SORTING"])).count()
    rejected_count = db.query(Order).filter(Order.status == "REJECTED").count()

    # Thống kê số lượng theo từng rổ từ bảng sorting_logs
    chute_counts = {c["chute_id"]: 0 for c in CHUTE_DEFINITIONS}
    chute_data = db.query(
        SortingLog.chute_id,
        func.count(SortingLog.id)
    ).filter(SortingLog.status == "SUCCESS").group_by(SortingLog.chute_id).all()

    for cid, count in chute_data:
        if cid in chute_counts:
            chute_counts[cid] = count

    # Số lượng bưu kiện trong sọt lỗi (Reject)
    reject_logs_count = db.query(SortingLog).filter(
        (SortingLog.chute_id == 0) | (SortingLog.status == "REJECTED")
    ).count()
    chute_counts[0] = max(chute_counts.get(0, 0), reject_logs_count, rejected_count)

    return {
        "total_orders": total_orders,
        "sorted_count": sorted_count,
        "pending_count": pending_count,
        "rejected_count": rejected_count,
        "success_rate": round((sorted_count / total_orders * 100) if total_orders > 0 else 100.0, 1),
        "chute_counts": chute_counts
    }
