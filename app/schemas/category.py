from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from app.utils.helpers import resolve_media_url, strip_media_url_prefix


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    image_url: Optional[str] = Field(None, description="Category banner or icon URL")


class CategoryCreate(CategoryBase):
    @field_validator("image_url", mode="before")
    @classmethod
    def normalize_image_url(cls, v: Any) -> Any:
        if isinstance(v, str):
            return strip_media_url_prefix(v)
        return v


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None
    image_url: Optional[str] = None

    @field_validator("image_url", mode="before")
    @classmethod
    def normalize_image_url(cls, v: Any) -> Any:
        if isinstance(v, str):
            return strip_media_url_prefix(v)
        return v


class CategoryResponse(CategoryBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    @field_validator("image_url", mode="before")
    @classmethod
    def format_image_url(cls, v: Any) -> Any:
        return resolve_media_url(v)

    model_config = {"from_attributes": True}
