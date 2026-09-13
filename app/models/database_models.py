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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class CartItemModel:
    id: UUID
    cart_id: UUID
    product_id: UUID
    quantity: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class WishlistItemModel:
    id: UUID
    user_id: UUID
    product_id: UUID
    created_at: Optional[datetime] = None


@dataclass
class OrderModel:
    id: UUID
    user_id: UUID
    status: str
    payment_status: str
    payment_method: str
    subtotal: Decimal
    discount: Decimal
    shipping_fee: Decimal
    total_amount: Decimal
    address_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class OrderItemModel:
    id: UUID
    order_id: UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    product_id: Optional[UUID] = None
    product_image_url: Optional[str] = None


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
