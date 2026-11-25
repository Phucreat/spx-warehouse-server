from typing import List, Optional, Set
import asyncio
import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from config import (
    CHUTE_DEFINITIONS,
    ROBOT_BIN_DEFINITIONS,
    VN_TZ,
    format_vn_time,
    resolve_robot_bin,
)
from database import SessionLocal, get_db, is_sqlite
from models import Order, SortReceipt, SortingLog
from schemas import (
    PackageLookupResponse,
    SortConfirmRequest,
    SortConfirmResponse,
    SortingLogResponse,
)

router = APIRouter(prefix="/api/v1/sort", tags=["Computer Vision & Sorting Control Station"])


# Connection Manager phục vụ WebSocket thời gian thực (SCADA Monitor, Seller, Tracking)
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
        dead_connections: List[WebSocket] = []
        payload_text = json.dumps(data, ensure_ascii=False, default=str)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload_text)
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)


ws_manager = WebSocketManager()

# Tập ID các bản ghi sorting_logs đã được endpoint /confirm phát WebSocket trực tiếp
_locally_broadcast_log_ids: Set[int] = set()


def _now_vn_hms() -> str:
    return datetime.datetime.now(VN_TZ).strftime("%H:%M:%S")


def serialize_sorting_log(log: SortingLog, order: Optional[Order] = None) -> dict:
    """Chuẩn hóa 1 dòng sorting_logs (từ Software-PC Control hoặc API) sang dict thống nhất."""
    ord_obj = order or log.order
    decision = log.decision
    if not decision:
        if log.status in ("SORTED", "SUCCESS"):
            decision = "PASS"
        elif log.status == "MANUAL_REVIEW":
            decision = "MANUAL_REVIEW"
        else:
            decision = "REJECT"

    bin_info = resolve_robot_bin(decision, log.chute_id)
    raw_damages = log.damage_types
    if isinstance(raw_damages, list):
        damage_list = [str(x) for x in raw_damages]
    elif isinstance(raw_damages, (tuple, set)):
        damage_list = [str(x) for x in raw_damages]
    else:
        damage_list = []

    ts_vn = format_vn_time(log.created_at, "%H:%M:%S") or _now_vn_hms()
    reason_text = log.reason or log.notes or ""

    return {
        "id": log.id,
        "inspection_uuid": str(log.inspection_uuid) if log.inspection_uuid else None,
        "order_id": log.order_id,
        "tracking_code": log.tracking_code,
        "order_code": ord_obj.order_code if ord_obj else None,
        "routing_code": ord_obj.routing_code if ord_obj else None,
        "destination_hub": ord_obj.destination_hub if ord_obj else (
            "SỌT LỖI / NGOẠI LỆ (Reject Chute)" if log.chute_id == 0 else f"Rổ {log.chute_id}"
        ),
        "chute_id": log.chute_id,
        "robot_bin": bin_info["bin_key"],
        "robot_bin_label": bin_info["label"],
        "status": log.status,
        "decision": decision,
        "reason": reason_text,
        "notes": log.notes or reason_text,
        "qr_ok": log.qr_ok,
        "logo_ok": log.logo_ok,
        "damage_detected": log.damage_detected,
        "damage_types": damage_list,
        "station_id": log.station_id or log.scanned_from or "VISION-01",
        "scanned_from": log.scanned_from or "MACHINE_VISION",
        "scan_attempts": log.scan_attempts or 1,
        "evidence_path": log.evidence_path,
        "created_at": log.created_at,
        "timestamp_vn": ts_vn,
    }


def _fetch_max_sorting_log_id() -> int:
    db = SessionLocal()
    try:
        max_id = db.query(func.max(SortingLog.id)).scalar()
        return int(max_id or 0)
    finally:
        db.close()


def _fetch_new_sorting_logs(after_id: int) -> tuple[int, List[dict]]:
    db = SessionLocal()
    try:
        rows = (
            db.query(SortingLog)
            .options(joinedload(SortingLog.order))
            .filter(SortingLog.id > after_id)
            .order_by(SortingLog.id.asc())
            .limit(50)
            .all()
        )
        if not rows:
            return after_id, []

        events: List[dict] = []
        newest_id = after_id
        for row in rows:
            newest_id = max(newest_id, row.id)
            if row.id in _locally_broadcast_log_ids:
                _locally_broadcast_log_ids.discard(row.id)
                continue
            item = serialize_sorting_log(row, row.order)
            events.append({
                "event": "STATION_INSPECTION",
                **item,
                "timestamp": item["timestamp_vn"],
            })
        return newest_id, events
    finally:
        db.close()


async def watch_sorting_logs_loop(
    stop_event: asyncio.Event,
    poll_interval_s: float = 1.2,
    initial_id: Optional[int] = None,
):
    """
    Luồng nền đồng bộ thời gian thực giữa Software-PC Control (ghi thẳng Supabase sorting_logs)
    và Web Server (SCADA /spx-hub, Kênh Người Bán /seller, Theo dõi vận đơn /orders/{id}/tracking).
    """
    last_id = initial_id if initial_id is not None else 0
    if initial_id is None:
        try:
            last_id = await asyncio.to_thread(_fetch_max_sorting_log_id)
        except Exception:
            last_id = 0

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=poll_interval_s)
            break
        except asyncio.TimeoutError:
            pass

        try:
            last_id, new_events = await asyncio.to_thread(_fetch_new_sorting_logs, last_id)
            for ev in new_events:
                await ws_manager.broadcast(ev)
        except Exception:
            # Mất mạng tạm thời tới Supabase không được làm dừng watcher
            await asyncio.sleep(2.0)


@router.get("/lookup", response_model=PackageLookupResponse)
async def lookup_package_for_sorting(
    code: str = Query(..., description="Mã vận đơn SPX hoặc chuỗi QR quét được từ Webcam 2K"),
    mark_in_sorting: bool = True,
    db: Session = Depends(get_db),
):
    """
    API tra cứu bưu kiện cho trạm kiểm thử hoặc kết nối REST trực tiếp.
    Nhận mã barcode/QR -> tra cứu CSDL -> trả về Rổ phân loại (Chute ID: 1..5 hoặc 0-Reject).
    """
    clean_code = code.strip()

    order = (
        db.query(Order)
        .filter(
            (func.upper(Order.tracking_code) == clean_code.upper())
            | (func.upper(Order.order_code) == clean_code.upper())
            | (Order.qr_payload == clean_code)
        )
        .first()
    )

    if not order:
        await ws_manager.broadcast({
            "event": "SCAN_FAILED",
            "code": clean_code,
            "tracking_code": clean_code,
            "message": "Không tìm thấy trong CSDL -> Điều hướng vào Sọt Lỗi (Reject)",
            "chute_id": 0,
            "robot_bin": "LOI",
            "robot_bin_label": "THÙNG LỖI / CẦN XEM LẠI",
            "timestamp": _now_vn_hms(),
        })

        return PackageLookupResponse(
            found=False,
            status="NOT_FOUND",
            tracking_code=clean_code,
            destination_chute_id=0,
            destination_hub="SỌT LỖI / NGOẠI LỆ (Reject Chute)",
            action="REJECT",
            message="Mã kiện hàng không tồn tại trong CSDL. Điều hướng vào Sọt Lỗi (Reject).",
        )

    items_str = (
        ", ".join([f"{it.product_name} (x{it.quantity})" for it in order.items])
        if order.items
        else "Hàng hóa Shopaa"
    )
    action = f"SORT_CHUTE_{order.destination_chute_id}" if order.destination_chute_id > 0 else "REJECT"
    bin_info = resolve_robot_bin(
        "PASS" if order.destination_chute_id > 0 else "REJECT",
        order.destination_chute_id,
    )

    if mark_in_sorting and order.status in (
        "PENDING",
        "PENDING_CONFIRMATION",
        "READY_TO_SHIP",
        "ARRIVED_PHU_CHAN_HUB",
    ):
        order.status = "IN_SORTING"
        db.commit()

    await ws_manager.broadcast({
        "event": "SCAN_SUCCESS",
        "tracking_code": order.tracking_code,
        "order_code": order.order_code,
        "routing_code": order.routing_code,
        "destination_hub": order.destination_hub,
        "chute_id": order.destination_chute_id,
        "robot_bin": bin_info["bin_key"],
        "robot_bin_label": bin_info["label"],
        "recipient": f"{order.recipient_name} ({order.recipient_province})",
        "weight_g": order.total_weight_g,
        "timestamp": _now_vn_hms(),
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
        message=f"Hợp lệ. Điều hướng vào Rổ {order.destination_chute_id}: {order.destination_hub} ({bin_info['label']})",
    )


@router.post("/confirm", response_model=SortConfirmResponse)
async def confirm_sorting_result(
    payload: SortConfirmRequest,
    db: Session = Depends(get_db),
):
    """
    Ghi nhận kết quả phân loại qua REST API (hoặc mô phỏng trên Web SCADA).
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

    order = (
        db.query(Order)
        .filter(func.upper(Order.tracking_code) == payload.tracking_code.strip().upper())
        .first()
    )
    if payload.status == "SUCCESS" and (
        order is None or order.destination_chute_id != payload.chute_id
    ):
        raise HTTPException(409, "Không tìm thấy đơn hoặc rổ đích không khớp")

    if not payload.simulated and order and order.status in ("SORTED", "REJECTED"):
        raise HTTPException(409, "Đơn đã có kết quả phân loại; cần xử lý lại thủ công")

    order_id = order.id if order else None
    log_status = "SORTED" if payload.status == "SUCCESS" else "REJECTED"
    log_decision = "PASS" if payload.status == "SUCCESS" else "REJECT"
    bin_info = resolve_robot_bin(log_decision, payload.chute_id)

    response = SortConfirmResponse(
        success=True,
        message="Mô phỏng trên Web, không ghi đè trạng thái đơn thật" if payload.simulated else "Đã lưu kết quả phân loại",
        tracking_code=payload.tracking_code,
        chute_id=payload.chute_id,
        order_status="SIMULATED" if payload.simulated else log_status,
    )

    if payload.job_id:
        db.add(
            SortReceipt(
                job_id=payload.job_id,
                payload=fingerprint,
                response=response.model_dump_json(),
            )
        )
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
        await ws_manager.broadcast({
            "event": "SORT_CONFIRMED",
            "simulated": True,
            "tracking_code": payload.tracking_code,
            "chute_id": payload.chute_id,
            "robot_bin": bin_info["bin_key"],
            "robot_bin_label": bin_info["label"],
            "status": payload.status,
            "decision": log_decision,
            "scan_attempts": payload.scan_attempts,
            "notes": payload.notes or "[Mô phỏng Web] Kiểm tra luồng điều hướng rổ & thùng robot",
            "timestamp": _now_vn_hms(),
        })
        return response

    note_text = payload.notes or (
        "Đã phân loại vào rổ thành công - Đang vận chuyển đến trạm chuyển phát"
        if payload.status == "SUCCESS"
        else "Phân loại vào sọt lỗi"
    )
    log_entry = SortingLog(
        order_id=order_id,
        tracking_code=payload.tracking_code,
        chute_id=payload.chute_id,
        status=log_status,
        decision=log_decision,
        reason=note_text,
        scan_attempts=payload.scan_attempts,
        scanned_from=payload.scanned_from,
        notes=note_text,
    )
    db.add(log_entry)
    db.flush()

    # Nếu chạy SQLite cục bộ (không có PostgreSQL trigger trg_sorting_logs_apply), tự đồng bộ orders
    if is_sqlite and order and log_decision == "PASS":
        now_utc = datetime.datetime.utcnow()
        order.status = "SORTED"
        order.sorted_at = now_utc
        if not order.hub_received_at:
            order.hub_received_at = now_utc

    _locally_broadcast_log_ids.add(log_entry.id)
    db.commit()

    await ws_manager.broadcast({
        "event": "SORT_CONFIRMED",
        "simulated": False,
        "id": log_entry.id,
        "tracking_code": payload.tracking_code,
        "chute_id": payload.chute_id,
        "robot_bin": bin_info["bin_key"],
        "robot_bin_label": bin_info["label"],
        "status": payload.status,
        "decision": log_decision,
        "scan_attempts": payload.scan_attempts,
        "station_id": payload.scanned_from or "API",
        "notes": log_entry.notes,
        "reason": log_entry.reason,
        "timestamp": _now_vn_hms(),
    })

    return response


@router.get("/logs", response_model=List[SortingLogResponse])
def get_recent_sorting_logs(
    limit: int = Query(default=25, ge=1, le=200),
    decision: Optional[str] = Query(default=None, description="Lọc theo PASS, REJECT, MANUAL_REVIEW"),
    db: Session = Depends(get_db),
):
    """Lấy lịch sử các lần kiểm tra & phân loại từ trạm Software-PC Control trên Supabase."""
    query = db.query(SortingLog).options(joinedload(SortingLog.order))
    if decision:
        norm = decision.strip().upper()
        if norm == "EXCEPTIONS":
            query = query.filter(
                (SortingLog.decision.in_(["REJECT", "MANUAL_REVIEW"]))
                | (SortingLog.status.in_(["REJECTED", "MANUAL_REVIEW"]))
            )
        else:
            query = query.filter(SortingLog.decision == norm)

    logs = query.order_by(SortingLog.id.desc()).limit(limit).all()
    return [serialize_sorting_log(log, log.order) for log in logs]


@router.get("/chutes")
def get_chute_list():
    """Lấy danh sách cấu hình các rổ phân loại (Chutes 1..5 và Chute 0)"""
    return CHUTE_DEFINITIONS


@router.get("/robot-bins")
def get_robot_bins():
    """Lấy cấu hình 3 thùng vật lý của cánh tay Robot 6 trục (khớp SortingStation)."""
    return ROBOT_BIN_DEFINITIONS


@router.get("/stats")
def get_sorting_statistics(db: Session = Depends(get_db)):
    """Thống kê sản lượng phân loại thời gian thực đồng bộ giữa orders và sorting_logs."""
    orders = db.query(Order).options(joinedload(Order.logs)).all()
    total_orders = len(orders)

    sorted_orders = [o for o in orders if o.status == "SORTED"]
    sorted_count = len(sorted_orders)
    in_sorting_count = sum(1 for o in orders if o.status == "IN_SORTING")

    # Đơn hàng có cảnh báo ngoại lệ ở lần quét gần nhất (chưa SORTED) hoặc status == REJECTED
    exception_orders = [o for o in orders if o.has_scan_exception]

    pending_count = sum(
        1
        for o in orders
        if o.status in (
            "PENDING",
            "LABEL_PRINTED",
            "PENDING_CONFIRMATION",
            "READY_TO_SHIP",
            "ARRIVED_PHU_CHAN_HUB",
            "IN_SORTING",
        )
        and not o.has_scan_exception
    )

    total_logs_count = db.query(func.count(SortingLog.id)).scalar() or 0
    manual_review_count = (
        db.query(func.count(SortingLog.id))
        .filter(
            (SortingLog.decision == "MANUAL_REVIEW")
            | (SortingLog.status == "MANUAL_REVIEW")
        )
        .scalar()
        or 0
    )

    # Các kiện lỗi không gắn được mã đơn (VD: QR rách/mờ -> tracking_code = 'UNKNOWN', order_id IS NULL)
    unlinked_exception_logs = (
        db.query(func.count(SortingLog.id))
        .filter(
            SortingLog.order_id.is_(None),
            (SortingLog.decision.in_(["REJECT", "MANUAL_REVIEW"]))
            | (SortingLog.status.in_(["REJECTED", "MANUAL_REVIEW"])),
        )
        .scalar()
        or 0
    )

    total_exception_logs = (
        db.query(func.count(SortingLog.id))
        .filter(
            (SortingLog.decision.in_(["REJECT", "MANUAL_REVIEW"]))
            | (SortingLog.status.in_(["REJECTED", "MANUAL_REVIEW"]))
        )
        .scalar()
        or 0
    )

    rejected_count = len(exception_orders) + int(unlinked_exception_logs)

    # Thống kê số lượng từng rổ (1..5): lấy max giữa số đơn SORTED của rổ đó và số mã vận đơn PASS trong sorting_logs
    chute_counts = {c["chute_id"]: 0 for c in CHUTE_DEFINITIONS}
    sorted_by_chute: dict[int, int] = {}
    for o in sorted_orders:
        if o.destination_chute_id in chute_counts and o.destination_chute_id > 0:
            sorted_by_chute[o.destination_chute_id] = sorted_by_chute.get(o.destination_chute_id, 0) + 1

    log_chute_data = (
        db.query(SortingLog.chute_id, func.count(func.distinct(SortingLog.tracking_code)))
        .filter(
            SortingLog.chute_id > 0,
            (SortingLog.decision == "PASS") | (SortingLog.status.in_(["SORTED", "SUCCESS"])),
        )
        .group_by(SortingLog.chute_id)
        .all()
    )
    log_by_chute = {int(cid): int(cnt) for cid, cnt in log_chute_data}

    for cid in (1, 2, 3, 4, 5):
        chute_counts[cid] = max(sorted_by_chute.get(cid, 0), log_by_chute.get(cid, 0))

    chute_counts[0] = max(rejected_count, int(total_exception_logs))

    robot_bin_counts = {
        "DONG_BANG": chute_counts[1] + chute_counts[3] + chute_counts[5],
        "TRUNG_DU": chute_counts[2] + chute_counts[4],
        "LOI": chute_counts[0],
    }

    return {
        "total_orders": total_orders,
        "sorted_count": sorted_count,
        "in_sorting_count": in_sorting_count,
        "pending_count": pending_count,
        "rejected_count": rejected_count,
        "manual_review_count": int(manual_review_count),
        "total_inspections": int(total_logs_count),
        "success_rate": round((sorted_count / total_orders * 100) if total_orders > 0 else 100.0, 1),
        "chute_counts": chute_counts,
        "robot_bin_counts": robot_bin_counts,
    }
