from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.offer import OfferBriefResponse
from app.utils.helpers import resolve_media_url


class CartItemCreate(BaseModel):
    product_id: UUID = Field(..., description="UUID of product to add")
    quantity: int = Field(1, ge=1, description="Quantity to add (must be at least 1)")


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1, description="Updated quantity (must be at least 1)")


class CartProductSnapshot(BaseModel):
    id: UUID
    name: str
    main_image_url: str
    price: Decimal
    is_active: bool = True
    original_price: Optional[Decimal] = None
    discount_amount: Decimal = Decimal("0.00")
    discounted_price: Optional[Decimal] = None
    final_price: Optional[Decimal] = None
    offer_id: Optional[UUID] = None
    offer_data: Optional[OfferBriefResponse] = None

    @model_validator(mode="after")
    def populate_pricing_defaults(self) -> "CartProductSnapshot":
        if self.original_price is None:
            self.original_price = self.price
        if self.final_price is None:
            self.final_price = max(Decimal("0.00"), self.original_price - self.discount_amount)
        if self.discounted_price is None:
            self.discounted_price = self.final_price
        return self

    @field_validator("main_image_url", mode="before")
    @classmethod
    def format_main_image_url(cls, v: Any) -> Any:
        return resolve_media_url(v)

    model_config = {"from_attributes": True}


# Alias for backward compatibility
CartItemProductInfo = CartProductSnapshot


class CartItemResponse(BaseModel):
    id: UUID
    product: CartProductSnapshot
    quantity: int
    subtotal: Decimal
    offer_id: Optional[UUID] = None
    unit_price: Optional[Decimal] = None
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = None
    discount_amount: Decimal = Decimal("0.00")
    final_unit_price: Optional[Decimal] = None
    total_price: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class CartResponse(BaseModel):
    id: UUID
    items: List[CartItemResponse] = []
    total_items: int = 0
    coupon_code: Optional[str] = None
    coupon_discount_type: Optional[str] = None
    coupon_discount_value: Optional[Decimal] = None
    coupon_discount_amount: Decimal = Decimal("0.00")
    subtotal: Decimal = Decimal("0.00")
    total_discount: Decimal = Decimal("0.00")
    shipping_amount: Decimal = Decimal("0.00")
    total_amount: Decimal = Decimal("0.00")
    final_amount: Decimal = Decimal("0.00")
    applied_offer: Optional[OfferBriefResponse] = None
    currency: str = "USD"
    country_code: Optional[str] = None

    @model_validator(mode="after")
    def compute_defaults(self) -> "CartResponse":
        if self.final_amount == Decimal("0.00") and self.total_amount > Decimal("0.00"):
            self.final_amount = self.total_amount
        elif self.total_amount == Decimal("0.00") and self.final_amount > Decimal("0.00"):
            self.total_amount = self.final_amount
        elif self.final_amount == Decimal("0.00") and self.subtotal > Decimal("0.00"):
            self.final_amount = max(Decimal("0.00"), self.subtotal - self.total_discount + self.shipping_amount)
            self.total_amount = self.final_amount
        return self

    model_config = {"from_attributes": True}


class ApplyCouponRequest(BaseModel):
    coupon_code: str = Field(..., min_length=1, max_length=100, description="Coupon or privilege code to apply to cart")


class BillCartItemInput(BaseModel):
    product_id: UUID = Field(..., description="Product UUID")
    quantity: int = Field(1, ge=1, description="Quantity")


class BillItemDetail(BaseModel):
    product_id: UUID
    product_name: str
    product_image_url: Optional[str] = None
    quantity: int
    original_unit_price: Decimal
    product_discount_unit: Decimal = Decimal("0.00")
    final_unit_price: Decimal
    gross_subtotal: Decimal
    product_discount_total: Decimal = Decimal("0.00")
    net_subtotal: Decimal
    applied_offer: Optional[OfferBriefResponse] = None

    @field_validator("product_image_url", mode="before")
    @classmethod
    def format_product_image_url(cls, v: Any) -> Any:
        return resolve_media_url(v)

    model_config = {"from_attributes": True}


class LiveBillRequest(BaseModel):
    items: Optional[List[BillCartItemInput]] = Field(None, description="Optional items list for guest or preview calculation")
    coupon_code: Optional[str] = Field(None, max_length=100, description="Coupon or privilege code")
    address_id: Optional[UUID] = Field(None, description="Saved address ID")
    shipping_address: Optional[Dict[str, Any]] = Field(None, description="Direct shipping address JSON")


class LiveBillResponse(BaseModel):
    items: List[BillItemDetail] = []
    total_items: int = 0
    items_count: int = 0

    # Gross & Product Level Discounts
    subtotal_amount: Decimal = Decimal("0.00")
    product_discount_amount: Decimal = Decimal("0.00")
    net_items_amount: Decimal = Decimal("0.00")

    # Coupon Discount
    coupon_code: Optional[str] = None
    is_coupon_applied: bool = False
    coupon_discount_amount: Decimal = Decimal("0.00")
    coupon_message: Optional[str] = None
    applied_coupon: Optional[OfferBriefResponse] = None

    # Delivery & Shipping
    delivery_charge: Decimal = Decimal("0.00")
    is_free_delivery: bool = True
    free_delivery_threshold: Decimal = Decimal("150.00")
    amount_needed_for_free_delivery: Decimal = Decimal("0.00")
    delivery_title: str = "Insured Luxury Express Delivery"
    estimated_delivery_days: str = "3-5 Business Days"

    # Packaging & Taxes
    gift_packaging_charge: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    is_tax_included: bool = True
    tax_description: str = "Inclusive of all luxury taxes and GST"

    # Summary & Totals
    total_discount_amount: Decimal = Decimal("0.00")
    total_savings_amount: Decimal = Decimal("0.00")
    total_savings_percentage: Decimal = Decimal("0.00")
    total_amount: Decimal = Decimal("0.00")
    currency: str = "USD"
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    exchange_rate: Optional[Decimal] = None
    exchange_available: Optional[bool] = False

    model_config = {"from_attributes": True}
