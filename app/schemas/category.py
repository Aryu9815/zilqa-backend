from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from app.utils.helpers import resolve_media_url, strip_media_url_prefix


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    image_url: Optional[str] = Field(None, description="Category banner or icon URL")
    priority: Optional[int] = Field(999, description="Display priority")
    slug: Optional[str] = Field(None, description="Category slug")
    seo_title: Optional[str] = Field(None, description="SEO title")
    seo_description: Optional[str] = Field(None, description="SEO description")
    og_title: Optional[str] = Field(None, description="OG title")
    og_description: Optional[str] = Field(None, description="OG description")
    og_image: Optional[str] = Field(None, description="OG image URL")


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
    priority: Optional[int] = None
    slug: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None

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


class CategoryProductsUpdate(BaseModel):
    product_ids: list[UUID] = Field(..., description="List of product UUIDs")
