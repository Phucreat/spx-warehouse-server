import hmac
import hashlib
import time
from typing import Optional
from fastapi import Request, Response, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User
from config import SECRET_KEY

# Khóa bí mật ký session token
AUTH_SECRET = SECRET_KEY.encode('utf-8')
COOKIE_NAME = "spx_session"

def hash_password(password: str) -> str:
    """Băm mật khẩu sử dụng SHA-256 kèm salt bí mật"""
    salted = f"{password}:{SECRET_KEY}".encode('utf-8')
    return hashlib.sha256(salted).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """So khớp mật khẩu nhập vào với mã băm trong CSDL"""
    return hash_password(plain_password) == hashed_password

def generate_session_token(user: User) -> str:
    """Tạo chuỗi token phiên: user_id:role:timestamp:hmac_signature"""
    ts = str(int(time.time()))
    payload = f"{user.id}:{user.role}:{ts}"
    sig = hmac.new(AUTH_SECRET, payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"

def parse_session_token(token: str) -> Optional[int]:
    """Kiểm tra chữ ký và trả về user_id nếu token hợp lệ"""
    try:
        parts = token.split(":")
        if len(parts) != 4:
            return None
        user_id_str, role, ts_str, sig = parts
        payload = f"{user_id_str}:{role}:{ts_str}"
        expected_sig = hmac.new(AUTH_SECRET, payload.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # Kiểm tra tính toàn vẹn chữ ký
        if not hmac.compare_digest(sig, expected_sig):
            return None
            
        # Kiểm tra thời hạn 7 ngày
        ts = int(ts_str)
        if time.time() - ts > 7 * 86400:
            return None
            
        return int(user_id_str)
    except Exception:
        return None

def login_user(response: Response, user: User):
    """Lưu session token vào Cookie trình duyệt"""
    token = generate_session_token(user)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=7 * 86400,
        httponly=True,
        samesite="lax",
        path="/"
    )

def logout_user(response: Response):
    """Xóa cookie phiên"""
    response.delete_cookie(key=COOKIE_NAME, path="/")

def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Dependency FastAPI: Lấy thông tin user hiện tại từ Cookie (nếu có)"""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    user_id = parse_session_token(token)
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()
