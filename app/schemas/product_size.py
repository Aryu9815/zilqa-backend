from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ProductSizeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Size label (e.g. S, M, L, 16, 17, 18)")
    category_id: Optional[UUID] = Field(None, description="Optional Category UUID this size belongs to")
    display_order: Optional[int] = Field(0, ge=0, description="Display order for UI sorting")
    is_active: Optional[bool] = Field(True, description="Whether size is active")


class ProductSizeCreate(ProductSizeBase):
    pass


class ProductSizeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="Size label")
    category_id: Optional[UUID] = Field(None, description="Category UUID")
    display_order: Optional[int] = Field(None, ge=0, description="Display order")
    is_active: Optional[bool] = Field(None, description="Whether size is active")


class ProductSizeResponse(ProductSizeBase):
    id: UUID
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime
    category_name: Optional[str] = None

    model_config = {"from_attributes": True}
