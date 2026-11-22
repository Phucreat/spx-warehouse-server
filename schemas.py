from typing import List, Optional, Literal
from pydantic import BaseModel, Field
import datetime

class CategoryResponse(BaseModel):
    id: int
    name: str
    icon: Optional[str] = "box"
    slug: str

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    id: int
    category_id: Optional[int]
    name: str
    price: float
    original_price: Optional[float]
    sold_count: int
    rating: float
    weight_g: int
    image_url: Optional[str]
    description: Optional[str]
    stock: int

    class Config:
        from_attributes = True


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = 1


class OrderCreate(BaseModel):
    recipient_name: str
    recipient_phone: str
    recipient_province: str
    recipient_district: str
    recipient_address: str
    note: Optional[str] = None
    items: List[OrderItemCreate]


class OrderItemResponse(BaseModel):
    id: int
    product_name: str
    quantity: int
    price: float
    weight_g: int

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    order_code: str
    tracking_code: str
    sender_name: str
    sender_address: str
    sender_phone: str
    recipient_name: str
    recipient_phone: str
    recipient_province: str
    recipient_district: str
    recipient_address: str
    routing_code: str
    destination_hub: str
    destination_chute_id: int
    total_amount: float
    cod_amount: float
    total_weight_g: int
    status: str
    qr_payload: Optional[str] = None
    label_size: str = "A7"
    label_printed_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    sorted_at: Optional[datetime.datetime]
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True


# Schema dành riêng cho Trạm Thị giác Máy tính (Computer Vision) & Bo mạch
class PackageLookupResponse(BaseModel):
    found: bool
    status: str
    tracking_code: str
    order_code: Optional[str] = None
    destination_chute_id: int
    destination_hub: str
    routing_code: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_province: Optional[str] = None
    total_weight_g: Optional[int] = None
    items_summary: Optional[str] = None
    action: str  # "SORT_CHUTE_1", "SORT_CHUTE_2", ..., "REJECT"
    message: str


class SortConfirmRequest(BaseModel):
    tracking_code: str = Field(min_length=1, max_length=50)
    chute_id: int = Field(ge=0, le=5)
    status: Literal["SUCCESS", "REJECTED"] = "SUCCESS"
    scan_attempts: int = Field(default=1, ge=1, le=100)
    job_id: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    simulated: bool = False
    scanned_from: Optional[str] = "Webcam_2K_Station"
    notes: Optional[str] = None


class SortConfirmResponse(BaseModel):
    success: bool
    message: str
    tracking_code: str
    chute_id: int
    order_status: str
