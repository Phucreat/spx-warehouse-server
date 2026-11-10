import re
import random
import unicodedata
from config import CHUTE_DEFINITIONS

def strip_accents(text: str) -> str:
    """Loại bỏ dấu tiếng Việt để tìm kiếm không dấu linh hoạt"""
    if not text:
        return ""
    text = unicodedata.normalize('NFD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    return text.replace('đ', 'd').replace('Đ', 'D').lower().strip()

def determine_chute(province: str, district: str = "") -> dict:
    """
    Xác định Rổ phân loại (Chute ID: 1..5 hoặc 0 - Reject) 
    và sinh mã định tuyến (Routing Code) giống Shopee Xpress
    """
    prov_clean = strip_accents(province)
    
    matched_chute = None
    for chute in CHUTE_DEFINITIONS:
        if chute["chute_id"] == 0:
            continue
        for p in chute["provinces"]:
            if strip_accents(p) in prov_clean or prov_clean in strip_accents(p):
                matched_chute = chute
                break
        if matched_chute:
            break
            
    # Nếu không khớp tỉnh miền Bắc nào -> gán vào sọt lỗi Reject (Chute 0)
    if not matched_chute:
        return {
            "chute_id": 0,
            "hub_name": "SỌT LỖI / NGOẠI LỆ (Reject Chute)",
            "routing_code": "ERR-REJECT",
            "is_valid": False
        }

    chute_id = matched_chute["chute_id"]
    prefix = matched_chute["routing_prefix"]
    
    # Sinh mã phân vùng con và bưu cục phát (Last-Mile Hub code)
    # Ví dụ: HN-29-01-CG02 (Cầu Giấy 02), HP-16-02-HB01 (Hồng Bàng 01)...
    dist_clean = strip_accents(district)
    dist_code = "LM01"
    if dist_clean:
        # Lấy 2 ký tự đầu viết tắt của quận huyện
        words = dist_clean.split()
        if len(words) >= 2:
            dist_code = f"{words[0][0].upper()}{words[1][0].upper()}{random.randint(10, 99)}"
        else:
            dist_code = f"{dist_clean[:2].upper()}{random.randint(10, 99)}"
            
    sub_zone = f"{random.randint(1, 4):02d}"
    routing_code = f"{prefix}-{sub_zone}-{dist_code}"

    return {
        "chute_id": chute_id,
        "hub_name": matched_chute["name"],
        "routing_code": routing_code,
        "is_valid": True
    }

def generate_order_code() -> str:
    """Sinh mã đơn hàng Shopee chuẩn: 14 ký tự (VD: 2411168MSW6ABM)"""
    import datetime
    today = datetime.datetime.now().strftime("%y%m%d")
    random_chars = ''.join(random.choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=8))
    return f"{today}{random_chars}"

def generate_tracking_code() -> str:
    """Sinh mã vận đơn Shopee Xpress duy nhất: SPXVN + 11 chữ số (VD: SPXVN023856935578)"""
    digits = ''.join(random.choices("0123456789", k=11))
    return f"SPXVN{digits}"
