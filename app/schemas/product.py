import json
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl, computed_field, field_validator, model_validator

from app.utils.helpers import (
    resolve_media_url,
    resolve_media_urls,
    strip_media_url_prefix,
    strip_media_urls_prefix,
)


class ProductSortBy(str, Enum):
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    NEWEST = "newest"
    OLDEST = "oldest"
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"


class ProductFAQ(BaseModel):
    question: str = Field(..., min_length=1, description="FAQ question")
    answer: str = Field(..., min_length=1, description="FAQ answer")


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Product title")
    main_image_url: str = Field(..., description="Primary image URL")
    other_image_urls: List[str] = Field(default_factory=list, max_length=10, description="Additional image URLs")
    price: Decimal = Field(..., ge=0, decimal_places=2, description="Product price in INR/USD")
    category_ids: List[UUID] = Field(default_factory=list, description="Associated Category UUIDs")
    description: Optional[str] = Field(None, description="Short product description")
    product_description: Optional[str] = Field(None, description="Detailed product description / story / specs")
    related_product_ids: List[UUID] = Field(default_factory=list, description="Associated related product UUIDs")
    faqs: List[ProductFAQ] = Field(default_factory=list, description="Product frequently asked questions")
    is_active: bool = Field(True, description="Whether product is live on storefront")

    @field_validator("main_image_url", mode="before")
    @classmethod
    def normalize_main_image(cls, v: Any) -> Any:
        if isinstance(v, str):
            return strip_media_url_prefix(v)
        return v

    @field_validator("other_image_urls", mode="before")
    @classmethod
    def normalize_other_images(cls, v: Any) -> Any:
        if isinstance(v, list):
            return strip_media_urls_prefix(v)
        return v

    @field_validator("faqs", mode="before")
    @classmethod
    def parse_faqs(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        if v is None:
            return []
        return v

    @field_validator("related_product_ids", mode="before")
    @classmethod
    def parse_related_ids(cls, v: Any) -> Any:
        if v is None:
            return []
        return v

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_category_id(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if "category_ids" not in values and "category_id" in values and values["category_id"]:
                values["category_ids"] = [values["category_id"]]
        return values


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    main_image_url: Optional[str] = None
    other_image_urls: Optional[List[str]] = Field(None, max_length=10)
    price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    category_ids: Optional[List[UUID]] = None
    description: Optional[str] = None
    product_description: Optional[str] = None
    related_product_ids: Optional[List[UUID]] = None
    faqs: Optional[List[ProductFAQ]] = None
    is_active: Optional[bool] = None

    @field_validator("main_image_url", mode="before")
    @classmethod
    def normalize_main_image(cls, v: Any) -> Any:
        if isinstance(v, str):
            return strip_media_url_prefix(v)
        return v

    @field_validator("other_image_urls", mode="before")
    @classmethod
    def normalize_other_images(cls, v: Any) -> Any:
        if isinstance(v, list):
            return strip_media_urls_prefix(v)
        return v

    @field_validator("faqs", mode="before")
    @classmethod
    def parse_faqs(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v

    @field_validator("related_product_ids", mode="before")
    @classmethod
    def parse_related_ids(cls, v: Any) -> Any:
        return v

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_category_id(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if "category_ids" not in values and "category_id" in values and values["category_id"]:
                values["category_ids"] = [values["category_id"]]
        return values


class ProductResponse(BaseModel):
    id: UUID
    name: str
    main_image_url: str
    other_image_urls: List[str] = []
    price: Decimal
    category_ids: List[UUID] = []
    category_names: List[str] = []
    description: Optional[str] = None
    product_description: Optional[str] = None
    related_product_ids: List[UUID] = []
    faqs: List[ProductFAQ] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("faqs", mode="before")
    @classmethod
    def parse_faqs(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        if v is None:
            return []
        return v

    @field_validator("main_image_url", mode="before")
    @classmethod
    def format_main_image_url(cls, v: Any) -> Any:
        return resolve_media_url(v)

    @field_validator("other_image_urls", mode="before")
    @classmethod
    def format_other_image_urls(cls, v: Any) -> Any:
        if isinstance(v, list):
            return resolve_media_urls(v)
        return v

    @field_validator("related_product_ids", mode="before")
    @classmethod
    def parse_related_ids(cls, v: Any) -> Any:
        if v is None:
            return []
        return v

    @computed_field
    @property
    def category_id(self) -> Optional[UUID]:
        return self.category_ids[0] if self.category_ids else None

    @computed_field
    @property
    def category_name(self) -> Optional[str]:
        return self.category_names[0] if self.category_names else None

    model_config = {"from_attributes": True}
