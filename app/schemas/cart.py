from decimal import Decimal
from typing import Any, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

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

    model_config = {"from_attributes": True}


class CartResponse(BaseModel):
    id: UUID
    items: List[CartItemResponse] = []
    total_items: int = 0
    subtotal: Decimal = Decimal("0.00")

    model_config = {"from_attributes": True}
