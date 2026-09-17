from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID


@dataclass
class UserModel:
    id: UUID
    name: str
    email: str
    password_hash: Optional[str] = None
    mobile_number: Optional[str] = None
    google_id: Optional[str] = None
    role: str = "customer"
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class RefreshTokenModel:
    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    revoked: bool = False
    created_at: Optional[datetime] = None


@dataclass
class CategoryModel:
    id: UUID
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ProductModel:
    id: UUID
    name: str
    main_image_url: str
    price: Decimal
    category_ids: List[UUID] = field(default_factory=list)
    other_image_urls: List[str] = field(default_factory=list)
    description: Optional[str] = None
    related_product_ids: List[UUID] = field(default_factory=list)
    product_description: Optional[str] = None
    faqs: List[Dict[str, Any]] = field(default_factory=list)
    is_active: bool = True
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class UserAddressModel:
    id: UUID
    user_id: UUID
    full_name: str
    phone: str
    address_line_1: str
    city: str
    state: str
    postal_code: str
    address_line_2: Optional[str] = None
    country: str = "India"
    is_default: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class CartModel:
    id: UUID
    user_id: UUID
    coupon_code: Optional[str] = None
    coupon_discount_type: Optional[str] = None
    coupon_discount_value: Optional[Decimal] = None
    coupon_discount_amount: Decimal = Decimal("0.00")
    subtotal: Decimal = Decimal("0.00")
    total_discount: Decimal = Decimal("0.00")
    shipping_amount: Decimal = Decimal("0.00")
    total_amount: Decimal = Decimal("0.00")
    is_deleted: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class CartItemModel:
    id: UUID
    cart_id: UUID
    product_id: UUID
    quantity: int = 1
    offer_id: Optional[UUID] = None
    unit_price: Decimal = Decimal("0.00")
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = None
    discount_amount: Decimal = Decimal("0.00")
    final_unit_price: Decimal = Decimal("0.00")
    total_price: Decimal = Decimal("0.00")
    is_deleted: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class WishlistItemModel:
    id: UUID
    user_id: UUID
    product_id: UUID
    is_deleted: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None


@dataclass
class OrderModel:
    id: UUID
    user_id: UUID
    status: str
    payment_status: str
    subtotal: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    total_amount: Decimal
    shipping_address: Dict[str, Any]
    currency: str = "INR"
    coupon_code: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None
    is_active: bool = True
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class OrderItemModel:
    id: UUID
    order_id: UUID
    product_name: str
    price: Decimal
    quantity: int
    unit_price: Decimal
    discount_value: Decimal
    discount_amount: Decimal
    final_unit_price: Decimal
    total_price: Decimal
    product_id: Optional[UUID] = None
    product_image_url: Optional[str] = None
    discount_type: Optional[str] = None
    is_active: bool = True
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ReviewModel:
    id: UUID
    product_id: UUID
    rating: int
    user_id: Optional[UUID] = None
    comment: Optional[str] = None
    image_urls: List[str] = field(default_factory=list)
    is_general: bool = False
    is_verified: bool = False
    is_active: bool = True
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class CountryModel:
    id: UUID
    name: str
    code: str
    is_active: bool = True
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class OfferModel:
    id: UUID
    name: str
    offer_type: str
    discount_type: str
    discount_value: Decimal
    start_date: datetime
    end_date: datetime
    description: Optional[str] = None
    coupon_code: Optional[str] = None
    minimum_order_amount: Decimal = Decimal("0.00")
    maximum_discount_amount: Optional[Decimal] = None
    usage_limit: Optional[int] = None
    used_count: int = 0
    is_active: bool = True
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class OfferProductModel:
    offer_id: UUID
    product_id: UUID


