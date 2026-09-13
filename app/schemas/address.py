from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class AddressBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150, description="Recipient full name")
    phone: str = Field(..., min_length=7, max_length=30, description="Contact phone number")
    address_line_1: str = Field(..., min_length=3, description="Street address, house number")
    address_line_2: Optional[str] = Field(None, description="Apartment, suite, unit, etc.")
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    postal_code: str = Field(..., min_length=3, max_length=20)
    country: str = Field("India", min_length=2, max_length=100)
    is_default: bool = Field(False, description="Set as default shipping address")


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    phone: Optional[str] = Field(None, min_length=7, max_length=30)
    address_line_1: Optional[str] = Field(None, min_length=3)
    address_line_2: Optional[str] = None
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=100)
    postal_code: Optional[str] = Field(None, min_length=3, max_length=20)
    country: Optional[str] = Field(None, min_length=2, max_length=100)
    is_default: Optional[bool] = None


class AddressResponse(AddressBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
