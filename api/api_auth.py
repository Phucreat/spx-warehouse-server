from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from models import User
from auth import verify_password, hash_password, login_user, logout_user, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

class LoginPayload(BaseModel):
    username: str
    password: str
    expected_role: Optional[str] = None

class RegisterPayload(BaseModel):
    username: str
    password: str
    full_name: str
    phone: Optional[str] = None

@router.post("/login")
def login(payload: LoginPayload, response: Response, db: Session = Depends(get_db)):
    """Đăng nhập người dùng (Buyer hoặc Seller)"""
    user = db.query(User).filter(User.username == payload.username.strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Tên đăng nhập hoặc mật khẩu không chính xác")

    # Nếu đăng nhập từ Kênh Người Bán mà tài khoản là Người Mua -> Báo lỗi phân quyền
    if payload.expected_role == "seller" and user.role != "seller":
        raise HTTPException(
            status_code=403, 
            detail="Tài khoản này là Khách Hàng (Người Mua). Vui lòng đăng nhập tài khoản Người Bán ('seller' / '123') để vào Kênh Người Bán!"
        )

    login_user(response, user)
    
    redirect_url = "/seller" if user.role == "seller" else "/"
    return {
        "success": True,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "redirect_url": redirect_url
    }

@router.post("/register")
def register(payload: RegisterPayload, response: Response, db: Session = Depends(get_db)):
    """Đăng ký tài khoản Khách Hàng (Người Mua) mới"""
    existing = db.query(User).filter(User.username == payload.username.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tên đăng nhập này đã được sử dụng. Vui lòng chọn tên khác.")

    if len(payload.password) < 3:
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 3 ký tự")

    new_user = User(
        username=payload.username.strip(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        phone=payload.phone.strip() if payload.phone else None,
        role="buyer"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    login_user(response, new_user)

    return {
        "success": True,
        "username": new_user.username,
        "full_name": new_user.full_name,
        "role": new_user.role,
        "redirect_url": "/"
    }

@router.post("/logout")
def logout(response: Response):
    """Đăng xuất người dùng"""
    logout_user(response)
    return {"success": True}
