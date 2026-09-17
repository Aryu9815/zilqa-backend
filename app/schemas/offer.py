from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator


class OfferType(str, Enum):
    PRODUCT_DISCOUNT = "Product Discount"
    CATEGORY_DISCOUNT = "Category Discount"
    COUPON_CODE = "Coupon Code"
    CART_DISCOUNT = "Cart Discount"
    FLASH_SALE = "Flash Sale"
    FIRST_ORDER_DISCOUNT = "First Order Discount"
    FREE_SHIPPING = "Free Shipping"
    MINIMUM_ORDER_DISCOUNT = "Minimum Order Discount"
    LIMITED_TIME_OFFER = "Limited-Time Offer"
    PERCENTAGE_DISCOUNT = "Percentage Discount"
    FIXED_AMOUNT_DISCOUNT = "Fixed Amount Discount"


# Canonical mapping for normalizing various casing/snake_case inputs
OFFER_TYPE_NORMALIZATION = {
    "product discount": OfferType.PRODUCT_DISCOUNT,
    "product_discount": OfferType.PRODUCT_DISCOUNT,
    "category discount": OfferType.CATEGORY_DISCOUNT,
    "category_discount": OfferType.CATEGORY_DISCOUNT,
    "coupon code": OfferType.COUPON_CODE,
    "coupon_code": OfferType.COUPON_CODE,
    "cart discount": OfferType.CART_DISCOUNT,
    "cart_discount": OfferType.CART_DISCOUNT,
    "flash sale": OfferType.FLASH_SALE,
    "flash_sale": OfferType.FLASH_SALE,
    "first order discount": OfferType.FIRST_ORDER_DISCOUNT,
    "first_order_discount": OfferType.FIRST_ORDER_DISCOUNT,
    "free shipping": OfferType.FREE_SHIPPING,
    "free_shipping": OfferType.FREE_SHIPPING,
    "minimum order discount": OfferType.MINIMUM_ORDER_DISCOUNT,
    "minimum_order_discount": OfferType.MINIMUM_ORDER_DISCOUNT,
    "limited-time offer": OfferType.LIMITED_TIME_OFFER,
    "limited time offer": OfferType.LIMITED_TIME_OFFER,
    "limited_time_offer": OfferType.LIMITED_TIME_OFFER,
    "percentage discount": OfferType.PERCENTAGE_DISCOUNT,
    "percentage_discount": OfferType.PERCENTAGE_DISCOUNT,
    "fixed amount discount": OfferType.FIXED_AMOUNT_DISCOUNT,
    "fixed_amount_discount": OfferType.FIXED_AMOUNT_DISCOUNT,
}


def normalize_offer_type(val: Any) -> OfferType:
    if isinstance(val, OfferType):
        return val
    if isinstance(val, str):
        cleaned = val.strip().lower().replace("-", " ")
        # Try direct match or key lookup
        for k, v in OFFER_TYPE_NORMALIZATION.items():
            if cleaned == k.replace("-", " "):
                return v
        # Also try matching canonical value lowercase
        for member in OfferType:
            if cleaned == member.value.lower().replace("-", " "):
                return member
    allowed_names = [t.value for t in OfferType]
    raise ValueError(f"Invalid offer_type '{val}'. Only the following offer types are allowed: {', '.join(allowed_names)}")


class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


def normalize_discount_type(val: Any) -> DiscountType:
    if isinstance(val, DiscountType):
        return val
    if isinstance(val, str):
        cleaned = val.strip().lower()
        if cleaned in ("percentage", "percent", "%"):
            return DiscountType.PERCENTAGE
        if cleaned in ("fixed", "fixed_amount", "amount", "flat"):
            return DiscountType.FIXED
    raise ValueError(f"Invalid discount_type '{val}'. Allowed discount types are 'percentage' or 'fixed'.")


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class OfferBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Offer display name")
    description: Optional[str] = Field(None, description="Detailed offer description / terms")
    offer_type: OfferType = Field(..., description="Strictly one of the 11 allowed offer types")
    discount_type: DiscountType = Field(..., description="Discount type: percentage or fixed")
    discount_value: Decimal = Field(..., gt=0, decimal_places=2, description="Discount magnitude (percentage or flat amount)")
    coupon_code: Optional[str] = Field(None, max_length=50, description="Coupon code if applicable")
    minimum_order_amount: Decimal = Field(Decimal("0.00"), ge=0, decimal_places=2, description="Minimum order/cart subtotal required")
    maximum_discount_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2, description="Maximum discount cap for percentage offers")
    start_date: datetime = Field(..., description="Offer validity start timestamp")
    end_date: datetime = Field(..., description="Offer validity end timestamp")
    usage_limit: Optional[int] = Field(None, gt=0, description="Maximum overall redemptions permitted")
    is_active: bool = Field(True, description="Whether this offer is active")

    product_ids: List[UUID] = Field(default_factory=list, description="Target product IDs")

    @field_validator("offer_type", mode="before")
    @classmethod
    def validate_offer_type(cls, v: Any) -> OfferType:
        return normalize_offer_type(v)

    @field_validator("discount_type", mode="before")
    @classmethod
    def validate_discount_type(cls, v: Any) -> DiscountType:
        return normalize_discount_type(v)

    @field_validator("coupon_code", mode="before")
    @classmethod
    def normalize_coupon_code(cls, v: Any) -> Optional[str]:
        if isinstance(v, str):
            stripped = v.strip().upper()
            return stripped if stripped else None
        return v

    @model_validator(mode="after")
    def validate_offer_rules(self) -> "OfferBase":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be strictly after start_date")

        if self.discount_type == DiscountType.PERCENTAGE and self.discount_value > Decimal("100.00"):
            raise ValueError("Percentage discount_value cannot exceed 100%")

        # Specific type rules
        if self.offer_type == OfferType.COUPON_CODE and not self.coupon_code:
            raise ValueError("coupon_code is mandatory for 'Coupon Code' offer type")

        if self.offer_type == OfferType.PERCENTAGE_DISCOUNT and self.discount_type != DiscountType.PERCENTAGE:
            raise ValueError("offer_type 'Percentage Discount' requires discount_type to be 'percentage'")

        if self.offer_type == OfferType.FIXED_AMOUNT_DISCOUNT and self.discount_type != DiscountType.FIXED:
            raise ValueError("offer_type 'Fixed Amount Discount' requires discount_type to be 'fixed'")

        return self


class OfferCreate(OfferBase):
    pass


class OfferUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    offer_type: Optional[OfferType] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    coupon_code: Optional[str] = Field(None, max_length=50)
    minimum_order_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    maximum_discount_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    usage_limit: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None

    product_ids: Optional[List[UUID]] = None


    @field_validator("offer_type", mode="before")
    @classmethod
    def validate_offer_type(cls, v: Any) -> Optional[OfferType]:
        if v is None:
            return None
        return normalize_offer_type(v)

    @field_validator("discount_type", mode="before")
    @classmethod
    def validate_discount_type(cls, v: Any) -> Optional[DiscountType]:
        if v is None:
            return None
        return normalize_discount_type(v)

    @field_validator("coupon_code", mode="before")
    @classmethod
    def normalize_coupon_code(cls, v: Any) -> Optional[str]:
        if isinstance(v, str):
            stripped = v.strip().upper()
            return stripped if stripped else None
        return v

    @model_validator(mode="after")
    def validate_offer_rules(self) -> "OfferUpdate":
        if self.start_date is not None and self.end_date is not None:
            if self.end_date <= self.start_date:
                raise ValueError("end_date must be strictly after start_date")

        if self.discount_type == DiscountType.PERCENTAGE and self.discount_value is not None:
            if self.discount_value > Decimal("100.00"):
                raise ValueError("Percentage discount_value cannot exceed 100%")

        return self


class OfferBriefResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    offer_type: str
    discount_type: str
    discount_value: Decimal
    coupon_code: Optional[str] = None
    start_date: datetime
    end_date: datetime
    minimum_order_amount: Decimal = Decimal("0.00")
    maximum_discount_amount: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class OfferResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    offer_type: str
    discount_type: str
    discount_value: Decimal
    coupon_code: Optional[str] = None
    minimum_order_amount: Decimal = Decimal("0.00")
    maximum_discount_amount: Optional[Decimal] = None
    start_date: datetime
    end_date: datetime
    usage_limit: Optional[int] = None
    used_count: int = 0
    is_active: bool
    is_deleted: bool = False
    product_ids: List[UUID] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}



class CouponValidateRequest(BaseModel):
    coupon_code: str = Field(..., min_length=1, max_length=50, description="Coupon code to validate")
    cart_subtotal: Optional[Decimal] = Field(None, ge=0, description="Optional cart subtotal to calculate exact discount")


class CouponValidateResponse(BaseModel):
    is_valid: bool
    message: str
    coupon_code: str
    discount_amount: Decimal = Decimal("0.00")
    final_amount: Optional[Decimal] = None
    offer: Optional[OfferBriefResponse] = None
