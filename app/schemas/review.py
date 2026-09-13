from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from app.utils.helpers import resolve_media_url, resolve_media_urls, strip_media_urls_prefix


class ReviewSortBy(str, Enum):
    NEWEST = "newest"
    OLDEST = "oldest"
    HIGHEST_RATING = "highest_rating"
    LOWEST_RATING = "lowest_rating"


class ReviewCreate(BaseModel):
    product_id: Optional[UUID] = Field(None, description="Target product ID (optional if provided in route path)")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    comment: Optional[str] = Field(None, max_length=2000, description="Review feedback or review text")
    image_urls: List[str] = Field(default_factory=list, max_length=5, description="Up to 5 review image URLs")
    is_general: bool = Field(False, description="Whether this is a general/testimonial review")

    @field_validator("image_urls", mode="before")
    @classmethod
    def normalize_images(cls, v: Any) -> Any:
        if isinstance(v, list):
            return strip_media_urls_prefix(v)
        return v


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5, description="Updated rating from 1 to 5")
    comment: Optional[str] = Field(None, max_length=2000, description="Updated review comment")
    image_urls: Optional[List[str]] = Field(None, max_length=5, description="Updated review image URLs")
    is_general: Optional[bool] = None

    @field_validator("image_urls", mode="before")
    @classmethod
    def normalize_images(cls, v: Any) -> Any:
        if isinstance(v, list):
            return strip_media_urls_prefix(v)
        return v


class ReviewStatusUpdate(BaseModel):
    is_active: Optional[bool] = Field(None, description="Toggle review visibility on the storefront")
    is_verified: Optional[bool] = Field(None, description="Manually grant or revoke verified purchase badge")


class ReviewResponse(BaseModel):
    id: UUID
    product_id: UUID
    user_id: Optional[UUID] = None
    user_name: Optional[str] = None
    product_name: Optional[str] = None
    product_main_image_url: Optional[str] = None
    rating: int
    comment: Optional[str] = None
    image_urls: List[str] = []
    is_general: bool = False
    is_verified: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    @field_validator("product_main_image_url", mode="before")
    @classmethod
    def format_product_main_image_url(cls, v: Any) -> Any:
        return resolve_media_url(v)

    @field_validator("image_urls", mode="before")
    @classmethod
    def format_image_urls(cls, v: Any) -> Any:
        if isinstance(v, list):
            return resolve_media_urls(v)
        return v

    model_config = {"from_attributes": True}


class ReviewSummaryResponse(BaseModel):
    product_id: UUID
    average_rating: float = 0.0
    total_reviews: int = 0
    rating_breakdown: Dict[int, int] = Field(
        default_factory=lambda: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        description="Count of reviews for each star rating (1 to 5)"
    )

    model_config = {"from_attributes": True}
