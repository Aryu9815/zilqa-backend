from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator

from app.utils.helpers import resolve_media_url


class OrderStatus(str, Enum):
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class OrderCreate(BaseModel):
    address_id: Optional[UUID] = Field(None, description="UUID of delivery address belonging to user")
    shipping_address: Optional[Dict[str, Any]] = Field(None, description="Direct shipping address JSON object")
    payment_method: Optional[str] = Field("razorpay", max_length=50, description="Payment method, e.g. 'razorpay', 'cod'")
    coupon_code: Optional[str] = Field(None, max_length=100, description="Optional coupon code applied to order")
    razorpay_order_id: Optional[str] = Field(None, description="Razorpay order ID if already initialized")
    razorpay_payment_id: Optional[str] = Field(None, description="Razorpay payment ID from gateway")
    razorpay_signature: Optional[str] = Field(None, description="Razorpay payment signature")


class RazorpayOrderCreateRequest(BaseModel):
    address_id: Optional[UUID] = Field(None, description="UUID of saved address")
    shipping_address: Optional[Dict[str, Any]] = Field(None, description="Direct shipping address JSON object")
    coupon_code: Optional[str] = Field(None, max_length=100, description="Optional coupon code")


class RazorpayOrderResponse(BaseModel):
    razorpay_order_id: str
    amount: int = Field(..., description="Amount in Paise (e.g. 199900 for ₹1999.00)")
    currency: str = "INR"
    key_id: str
    subtotal: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    total_amount: Decimal
    coupon_code: Optional[str] = None


class RazorpayPaymentVerifyRequest(BaseModel):
    razorpay_order_id: str = Field(..., description="Razorpay order ID")
    razorpay_payment_id: str = Field(..., description="Razorpay payment ID")
    razorpay_signature: str = Field(..., description="Razorpay cryptographic signature")
    address_id: Optional[UUID] = Field(None, description="UUID of saved address")
    shipping_address: Optional[Dict[str, Any]] = Field(None, description="Direct shipping address JSON")
    coupon_code: Optional[str] = Field(None, max_length=100, description="Optional coupon code")


class OrderStatusUpdate(BaseModel):
    status: OrderStatus = Field(..., description="Target order status")


class PaymentStatusUpdate(BaseModel):
    payment_status: PaymentStatus = Field(..., description="Target payment status")


class OrderItemResponse(BaseModel):
    id: UUID
    order_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    product_name: str
    product_image_url: Optional[str] = None
    price: Decimal
    quantity: int
    unit_price: Decimal
    discount_type: Optional[str] = None
    discount_value: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    final_unit_price: Decimal
    total_price: Decimal
    subtotal: Optional[Decimal] = None
    is_active: bool = True
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode="after")
    def populate_subtotal_alias(self) -> "OrderItemResponse":
        if self.subtotal is None:
            self.subtotal = self.total_price
        return self

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
    status: str
    payment_status: str
    subtotal: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    total_amount: Decimal
    currency: str = "INR"
    coupon_code: Optional[str] = None
    shipping_address: Any = None
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None
    items: List[OrderItemResponse] = []
    is_active: bool = True
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime

    # Aliases for backward compatibility
    discount: Optional[Decimal] = None
    shipping_fee: Optional[Decimal] = None
    payment_method: Optional[str] = "razorpay"
    address_id: Optional[UUID] = None

    @model_validator(mode="after")
    def populate_backward_compat(self) -> "OrderResponse":
        if self.discount is None:
            self.discount = self.discount_amount
        if self.shipping_fee is None:
            self.shipping_fee = self.shipping_amount
        if isinstance(self.shipping_address, dict) and "id" in self.shipping_address and self.address_id is None:
            try:
                self.address_id = UUID(str(self.shipping_address["id"]))
            except (ValueError, TypeError):
                pass
        return self

    model_config = {"from_attributes": True}
