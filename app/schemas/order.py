from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from app.schemas.address import AddressResponse
from app.utils.helpers import resolve_media_url


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class OrderCreate(BaseModel):
    address_id: UUID = Field(..., description="UUID of delivery address belonging to user")
    payment_method: str = Field(..., min_length=2, max_length=50, description="Payment method, e.g. 'credit_card', 'upi', 'cod'")


class OrderStatusUpdate(BaseModel):
    status: OrderStatus = Field(..., description="Target order status")


class PaymentStatusUpdate(BaseModel):
    payment_status: PaymentStatus = Field(..., description="Target payment status")


class OrderItemResponse(BaseModel):
    id: UUID
    product_id: Optional[UUID] = None
    product_name: str
    product_image_url: Optional[str] = None
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    @field_validator("product_image_url", mode="before")
    @classmethod
    def format_product_image_url(cls, v: Any) -> Any:
        return resolve_media_url(v)

    model_config = {"from_attributes": True}


class OrderCustomerInfo(BaseModel):
    id: UUID
    name: str
    email: str


class OrderResponse(BaseModel):
    id: UUID
    user_id: UUID
    customer: Optional[OrderCustomerInfo] = None
    address_id: Optional[UUID] = None
    shipping_address: Optional[AddressResponse] = None
    status: str
    payment_status: str
    payment_method: str
    subtotal: Decimal
    discount: Decimal
    shipping_fee: Decimal
    total_amount: Decimal
    items: List[OrderItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
