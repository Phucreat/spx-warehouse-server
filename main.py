import sys
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import asyncio
from contextlib import asynccontextmanager
from typing import Optional, List
from pathlib import Path
from fastapi import FastAPI, Depends, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, selectinload

from database import engine, Base, get_db
from models import Product, Category, Order, SortingLog, User
from config import SERVER_HOST, SERVER_PORT, DEBUG, ORIGIN_HUB, format_vn_time, resolve_robot_bin
from auth import get_current_user, logout_user
from api.api_store import router as store_router
from api.api_orders import router as orders_router
from api.api_station import (
    router as station_router,
    ws_manager,
    watch_sorting_logs_loop,
    _fetch_max_sorting_log_id,
)
from api.api_seller import router as seller_router, filter_orders_by_tab
from api.api_auth import router as auth_router

# Khởi tạo CSDL
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi chạy luồng nền theo dõi Supabase sorting_logs từ Software-PC Control."""
    stop_event = asyncio.Event()
    try:
        initial_id = await asyncio.wait_for(
            asyncio.to_thread(_fetch_max_sorting_log_id), timeout=4.0
        )
    except Exception:
        initial_id = 0
    watcher_task = asyncio.create_task(
        watch_sorting_logs_loop(stop_event, initial_id=initial_id)
    )
    try:
        yield
    finally:
        stop_event.set()
        try:
            await asyncio.wait_for(watcher_task, timeout=3.0)
        except Exception:
            watcher_task.cancel()


app = FastAPI(
    title="SPX Mega SOC Phù Chẩn - Hệ Thống Vận Hành TMĐT & Phân Loại Bưu Kiện",
    description="Hệ thống 3 phân hệ độc lập: 1) Sàn Shopaa Mall (Khách hàng), 2) Kênh Người Bán (Seller Centre), 3) Trung tâm Kho SPX Phù Chẩn & Trạm PC Control Hiện Trường.",
    version="3.1.0",
    lifespan=lifespan,
)

# Cấu hình CORS mở rộng cho phép máy trạm hiện trường & điện thoại truy cập
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent

# Mount Static Files & Templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["vn_time"] = format_vn_time
templates.env.globals["resolve_robot_bin"] = resolve_robot_bin

# Đăng ký API Routers
app.include_router(store_router)
app.include_router(orders_router)
app.include_router(station_router)
app.include_router(seller_router)
app.include_router(auth_router)

# ------------------------------------------------------------------------------
# WEBSOCKET KÊNH TRUYỀN THÔNG HIỆN TRƯỜNG & SCADA
# ------------------------------------------------------------------------------
@app.websocket("/ws/sorting")
async def websocket_sorting_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

# ------------------------------------------------------------------------------
# HỆ THỐNG XÁC THỰC & ĐĂNG NHẬP (NGƯỜI MUA & NGƯỜI BÁN)
# ------------------------------------------------------------------------------

@app.get("/login")
def view_login(request: Request, current_user: Optional[User] = Depends(get_current_user)):
    """Trang đăng nhập Shopaa cho Người Mua"""
    if current_user:
        return RedirectResponse(url="/seller" if current_user.role == "seller" else "/")
    return templates.TemplateResponse(request=request, name="login.html", context={
        "request": request,
        "current_user": None
    })

@app.get("/seller/login")
def view_seller_login(request: Request, msg: str = "", current_user: Optional[User] = Depends(get_current_user)):
    """Trang đăng nhập Kênh Người Bán Shopaa (Seller Centre)"""
    if current_user and current_user.role == "seller":
        return RedirectResponse(url="/seller")
    return templates.TemplateResponse(request=request, name="seller_login.html", context={
        "request": request,
        "msg": msg,
        "current_user": current_user
    })

@app.get("/register")
def view_register(request: Request, current_user: Optional[User] = Depends(get_current_user)):
    """Trang đăng ký tài khoản Khách Hàng"""
    if current_user:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="register.html", context={
        "request": request,
        "current_user": None
    })

@app.get("/logout")
def handle_logout():
    """Đăng xuất người dùng và quay về trang chủ"""
    res = RedirectResponse(url="/", status_code=303)
    logout_user(res)
    return res

# ------------------------------------------------------------------------------
# PHÂN HỆ 1: SÀN MUA SẮM SHOPEE (DÀNH CHO KHÁCH HÀNG / CẢ LỚP)
# ------------------------------------------------------------------------------

@app.get("/")
def view_shopee_store(
    request: Request, 
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Trang chủ mua sắm Shopaa Mall thuần túy cho khách hàng"""
    categories = db.query(Category).order_by(Category.id.asc()).all()
    products = db.query(Product).order_by(Product.id.asc()).all()
    return templates.TemplateResponse(request=request, name="shopee_store.html", context={
        "request": request,
        "categories": categories,
        "products": products,
        "origin_hub": ORIGIN_HUB,
        "current_user": current_user,
        "q": q or "",
        "category_id": category_id
    })

@app.get("/my-orders")
def view_my_orders(
    request: Request, 
    status: str = "", 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Trang 'Đơn Mua Của Tôi' của khách hàng"""
    query = db.query(Order).options(selectinload(Order.items), selectinload(Order.logs))
    
    # Nếu người mua đã đăng nhập và có đơn riêng, chỉ hiển thị đơn của người đó
    if current_user and current_user.role == "buyer":
        user_orders_count = db.query(Order).filter(Order.user_id == current_user.id).count()
        if user_orders_count > 0:
            query = query.filter(Order.user_id == current_user.id)
            
    all_orders = query.order_by(Order.id.desc()).all()
    orders = filter_orders_by_tab(all_orders, status) if status else all_orders
    return templates.TemplateResponse(request=request, name="my_orders.html", context={
        "request": request,
        "orders": orders,
        "current_status": status,
        "current_user": current_user
    })

@app.get("/orders/{order_id}/tracking")
def view_order_tracking(
    request: Request, 
    order_id: int, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Trang theo dõi tiến trình vận chuyển bưu kiện (Live Tracking Timeline)"""
    order = (
        db.query(Order)
        .options(selectinload(Order.items), selectinload(Order.logs))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    return templates.TemplateResponse(request=request, name="order_tracking.html", context={
        "request": request,
        "order": order,
        "current_user": current_user
    })

@app.get("/orders/{order_id}/success")
def view_order_success(
    request: Request, 
    order_id: int, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Trang thông báo đặt hàng thành công chuẩn Người Mua (Không in tem, không mã tuyến kho)"""
    order = (
        db.query(Order)
        .options(selectinload(Order.items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    return templates.TemplateResponse(request=request, name="order_success.html", context={
        "request": request,
        "order": order,
        "current_user": current_user
    })

# ------------------------------------------------------------------------------
# PHÂN HỆ 2: KÊNH NGƯỜI BÁN SHOPEE (SELLER CENTRE - CHO THÀNH VIÊN NHÓM)
# ------------------------------------------------------------------------------

@app.get("/seller")
def view_seller_centre(
    request: Request, 
    status: str = "", 
    q: str = "", 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Cổng Kênh Người Bán Shopaa (Shopaa Seller Centre) - Bắt buộc tài khoản Người Bán"""
    if not current_user or current_user.role != "seller":
        return RedirectResponse(url="/seller/login?msg=required", status_code=303)

    from api.api_seller import get_seller_stats
    stats = get_seller_stats(db)

    query = db.query(Order).options(selectinload(Order.items), selectinload(Order.logs))
    if q:
        query = query.filter(
            (Order.tracking_code.ilike(f"%{q}%")) |
            (Order.order_code.ilike(f"%{q}%")) |
            (Order.recipient_name.ilike(f"%{q}%"))
        )
    all_orders = query.order_by(Order.id.desc()).all()
    orders = filter_orders_by_tab(all_orders, status)

    return templates.TemplateResponse(request=request, name="seller_centre.html", context={
        "request": request,
        "orders": orders,
        "stats": stats,
        "current_status": status,
        "q": q,
        "current_user": current_user
    })

@app.get("/orders/{order_id}/label")
def view_shipping_label(
    request: Request, 
    order_id: int, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Phiếu mã vận đơn chuẩn Shopaa Express A7 (In tem bưu kiện từ Kênh Người Bán)"""
    order = (
        db.query(Order)
        .options(selectinload(Order.items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    return templates.TemplateResponse(request=request, name="shipping_label.html", context={
        "request": request,
        "order": order,
        "current_user": current_user
    })

# ------------------------------------------------------------------------------
# PHÂN HỆ 3: TRUNG TÂM KHO SPX MEGA SOC PHÙ CHẨN & TRẠM PC CONTROL SCADA
# ------------------------------------------------------------------------------

@app.get("/spx-hub")
def view_spx_hub(
    request: Request, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Cổng điều hành trung tâm Kho Mega SOC Phù Chẩn và SCADA Băng Tải"""
    sample_orders = db.query(Order).filter(Order.status.in_(["ARRIVED_PHU_CHAN_HUB", "READY_TO_SHIP", "PENDING_CONFIRMATION"])).limit(5).all()
    if not sample_orders:
        sample_orders = db.query(Order).limit(5).all()

    return templates.TemplateResponse(request=request, name="spx_hub.html", context={
        "request": request,
        "sample_orders": sample_orders,
        "current_user": current_user
    })

# Điều hướng tương thích các URL cũ
@app.get("/station/monitor")
def redirect_old_monitor():
    return RedirectResponse(url="/spx-hub")

@app.get("/admin/orders")
def redirect_old_admin():
    return RedirectResponse(url="/seller")

if __name__ == "__main__":
    import uvicorn
    print(f"Khởi động Server Hệ Thống Shopaa & SPX Phù Chẩn tại http://{SERVER_HOST}:{SERVER_PORT}")
    uvicorn.run("main:app", host=SERVER_HOST, port=SERVER_PORT, reload=DEBUG)
