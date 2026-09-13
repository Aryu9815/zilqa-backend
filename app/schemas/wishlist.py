from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, computed_field, field_validator

from app.utils.helpers import resolve_media_url


class WishlistProductSnapshot(BaseModel):
    id: UUID
    name: str
    main_image_url: str
    price: Decimal
    is_active: bool
    category_ids: List[UUID] = []

    @field_validator("main_image_url", mode="before")
    @classmethod
    def format_main_image_url(cls, v: Any) -> Any:
        return resolve_media_url(v)

    @computed_field
    @property
    def category_id(self) -> Optional[UUID]:
        return self.category_ids[0] if self.category_ids else None

    model_config = {"from_attributes": True}


class WishlistItemResponse(BaseModel):
    id: UUID
    product: WishlistProductSnapshot
    created_at: datetime

    model_config = {"from_attributes": True}


class WishlistResponse(BaseModel):
    items: List[WishlistItemResponse] = []
    total_items: int = 0
