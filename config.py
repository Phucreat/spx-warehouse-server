import os
import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Múi giờ Việt Nam (GMT+7) để hiển thị đồng nhất thời gian từ Supabase UTC
VN_TZ = datetime.timezone(datetime.timedelta(hours=7))


def to_vn_time(dt: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
    """Chuyển đổi datetime lưu theo giờ UTC trên Supabase sang giờ Việt Nam (GMT+7)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(VN_TZ)


def format_vn_time(dt: Optional[datetime.datetime], fmt: str = "%d/%m/%Y %H:%M") -> str:
    """Format datetime sang chuỗi giờ Việt Nam an toàn cho Jinja2 & WebSocket."""
    vn_dt = to_vn_time(dt)
    return vn_dt.strftime(fmt) if vn_dt else ""

# Load file .env nếu có
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Cấu hình CSDL (Mặc định dùng SQLite local nếu không có DATABASE_URL PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./warehouse.db")

# Nếu chuỗi kết nối là PostgreSQL từ Supabase/Neon thường bắt đầu bằng postgres:// -> chuẩn hóa thành postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Nếu dùng SQLite, đảm bảo thư mục chứa file db đã tồn tại
if DATABASE_URL.startswith("sqlite:///"):
    try:
        db_path_str = DATABASE_URL.replace("sqlite:///", "")
        db_path = Path(db_path_str)
        if db_path.parent and str(db_path.parent) != ".":
            db_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8090"))
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
SECRET_KEY = os.getenv("SECRET_KEY", "spx-mega-soc-phu-chan-secret-2026")

# Thông tin Kho nguồn (Phù Chẩn - Từ Sơn - Bắc Ninh Mega SOC)
ORIGIN_HUB = {
    "name": os.getenv("ORIGIN_HUB_NAME", "KHO TỔNG SPX MEGA SOC PHÙ CHẨN"),
    "address": os.getenv("ORIGIN_HUB_ADDRESS", "Số 6 Đường số 5, KCN VSIP, Phường Phù Chẩn, TP. Từ Sơn, Tỉnh Bắc Ninh"),
    "phone": os.getenv("ORIGIN_HUB_PHONE", "1900 1221"),
    "routing_prefix": os.getenv("ORIGIN_ROUTING_PREFIX", "BN-PC01"),
}

# Cấu hình các Rổ phân loại (Chutes) tại hiện trường
CHUTE_DEFINITIONS = [
    {
        "chute_id": 1,
        "name": "HN CENTRAL SOC (Hà Nội Trung Tâm)",
        "routing_prefix": "HN-29",
        "description": "Toàn bộ khu vực Hà Nội (Cầu Giấy, Đống Đa, Ba Đình, Hoàn Kiếm, Long Biên, Hoàng Mai...)",
        "color": "#2563eb",  # Blue
        "provinces": ["Hà Nội", "Ha Noi"]
    },
    {
        "chute_id": 2,
        "name": "BN-BG HUB (Bắc Ninh - Bắc Giang - Lạng Sơn)",
        "routing_prefix": "BN-99",
        "description": "Bắc Ninh, Bắc Giang, Lạng Sơn và các cửa khẩu biên giới",
        "color": "#16a34a",  # Green
        "provinces": ["Bắc Ninh", "Bac Ninh", "Bắc Giang", "Bac Giang", "Lạng Sơn", "Lang Son"]
    },
    {
        "chute_id": 3,
        "name": "HP-QN HUB (Duyên Hải: Hải Phòng - Quảng Ninh)",
        "routing_prefix": "HP-16",
        "description": "Hải Phòng, Quảng Ninh, Hải Dương (Cụm duyên hải phía Đông)",
        "color": "#0891b2",  # Cyan
        "provinces": ["Hải Phòng", "Hai Phong", "Quảng Ninh", "Quang Ninh", "Hải Dương", "Hai Duong"]
    },
    {
        "chute_id": 4,
        "name": "TN-PT HUB (Trung Du & Tây Bắc: Thái Nguyên - Phú Thọ)",
        "routing_prefix": "TN-20",
        "description": "Thái Nguyên, Phú Thọ, Vĩnh Phúc, Tuyên Quang, Yên Bái, Lào Cai, Hà Giang, Cao Bằng",
        "color": "#d97706",  # Amber
        "provinces": [
            "Thái Nguyên", "Thai Nguyen", "Phú Thọ", "Phu Tho", "Vĩnh Phúc", "Vinh Phuc",
            "Tuyên Quang", "Tuyen Quang", "Yên Bái", "Yen Bai", "Lào Cai", "Lao Cai",
            "Hà Giang", "Ha Giang", "Cao Bằng", "Cao Bang", "Bắc Kạn", "Bac Kan",
            "Sơn La", "Son La", "Hòa Bình", "Hoa Binh", "Điện Biên", "Dien Bien", "Lai Châu", "Lai Chau"
        ]
    },
    {
        "chute_id": 5,
        "name": "ND-TH HUB (Đồng Bằng Nam Sông Hồng & Bắc Trung Bộ)",
        "routing_prefix": "ND-18",
        "description": "Nam Định, Hà Nam, Thái Bình, Ninh Bình, Thanh Hóa, Nghệ An, Hà Tĩnh",
        "color": "#9333ea",  # Purple
        "provinces": [
            "Nam Định", "Nam Dinh", "Hà Nam", "Ha Nam", "Thái Bình", "Thai Binh",
            "Ninh Bình", "Ninh Binh", "Thanh Hóa", "Thanh Hoa", "Nghệ An", "Nghe An", "Hà Tĩnh", "Ha Tinh"
        ]
    },
    {
        "chute_id": 0,
        "name": "SỌT LỖI / NGOẠI LỆ (Reject Chute)",
        "routing_prefix": "ERR-REJECT",
        "description": "Quét lỗi QR/tem/hư hỏng, cần kiểm tra lại hoặc không tồn tại trong CSDL",
        "color": "#dc2626",  # Red
        "provinces": []
    }
]

# Cấu hình ánh xạ 3 Thùng Vật Lý của Cánh Tay Robot 6 Trục (khớp 100% SortingStation/config/station.yaml)
ROBOT_BIN_DEFINITIONS = [
    {
        "bin_key": "DONG_BANG",
        "label": "THÙNG ĐỒNG BẰNG",
        "chutes": [1, 3, 5],
        "description": "Rổ 1 (Hà Nội), Rổ 3 (Hải Phòng - Quảng Ninh), Rổ 5 (Nam Định - Thanh Hóa)",
        "color": "#26a269",
    },
    {
        "bin_key": "TRUNG_DU",
        "label": "THÙNG TRUNG DU - MIỀN NÚI",
        "chutes": [2, 4],
        "description": "Rổ 2 (Bắc Ninh - Bắc Giang - Lạng Sơn), Rổ 4 (Thái Nguyên - Phú Thọ)",
        "color": "#2f81f7",
    },
    {
        "bin_key": "LOI",
        "label": "THÙNG LỖI / CẦN XEM LẠI",
        "chutes": [0],
        "description": "Kiện REJECT (lỗi QR/tem/móp thùng), MANUAL_REVIEW hoặc mã ngoại lệ",
        "color": "#f85149",
    },
]

ROBOT_CHUTE_TO_BIN = {
    1: "DONG_BANG",
    3: "DONG_BANG",
    5: "DONG_BANG",
    2: "TRUNG_DU",
    4: "TRUNG_DU",
    0: "LOI",
}

ROBOT_BIN_BY_KEY = {b["bin_key"]: b for b in ROBOT_BIN_DEFINITIONS}


def resolve_robot_bin(decision: Optional[str], chute_id: Optional[int]) -> dict:
    """Ánh xạ quyết định Vision + mã rổ sang thùng vật lý của Robot 6 trục (khớp SortingSettings.resolve_bin)."""
    norm_decision = (decision or "").upper()
    if norm_decision == "PASS" and chute_id in (1, 2, 3, 4, 5):
        key = ROBOT_CHUTE_TO_BIN.get(chute_id, "LOI")
    else:
        key = "LOI"
    return ROBOT_BIN_BY_KEY[key]
