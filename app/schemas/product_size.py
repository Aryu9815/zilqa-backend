from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class ProductSizeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Size label (e.g. S, M, L, 16, 17, 18)")
    category_id: Optional[UUID] = Field(None, description="Optional Category UUID this size belongs to")
    country_code: Optional[str] = Field(None, max_length=50, description="Optional Country Code (e.g. IN, US, UK)")
    display_order: Optional[int] = Field(0, ge=0, description="Display order for UI sorting")
    is_active: Optional[bool] = Field(True, description="Whether size is active")

    @field_validator("country_code", mode="before")
    @classmethod
    def normalize_country_code(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            cleaned = v.strip().upper()
            return cleaned if cleaned else None
        return v


class ProductSizeCreate(ProductSizeBase):
    pass


class ProductSizeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="Size label")
    category_id: Optional[UUID] = Field(None, description="Category UUID")
    country_code: Optional[str] = Field(None, max_length=50, description="Optional Country Code")
    display_order: Optional[int] = Field(None, ge=0, description="Display order")
    is_active: Optional[bool] = Field(None, description="Whether size is active")

    @field_validator("country_code", mode="before")
    @classmethod
    def normalize_country_code(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            cleaned = v.strip().upper()
            return cleaned if cleaned else None
        return v


class ProductSizeResponse(ProductSizeBase):
    id: UUID
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime
    category_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ProductSizesFlowResponse(BaseModel):
    has_country_codes: bool = Field(..., description="Whether sizes in this category use country codes")
    available_countries: List[str] = Field(default_factory=list, description="Available country codes for this category")
    selected_country_code: Optional[str] = Field(None, description="Active or requested country code")
    sizes: List[ProductSizeResponse] = Field(default_factory=list, description="Resolved list of sizes")
