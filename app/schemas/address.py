import re
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


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

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\(\)]", "", v.strip())
        if not re.match(r"^\+?[1-9]\d{6,14}$", cleaned):
            raise ValueError("Phone number must be a valid international format (e.g. +919876543210)")
        return cleaned

    @field_validator("country", "state", "city")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        val = v.strip()
        if len(val) < 2:
            raise ValueError("Value must be at least 2 characters")
        return val


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

    @field_validator("phone")
    @classmethod
    def validate_update_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = re.sub(r"[\s\-\(\)]", "", v.strip())
        if not re.match(r"^\+?[1-9]\d{6,14}$", cleaned):
            raise ValueError("Phone number must be a valid international format (e.g. +919876543210)")
        return cleaned

    @field_validator("country", "state", "city")
    @classmethod
    def validate_update_non_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        val = v.strip()
        if len(val) < 2:
            raise ValueError("Value must be at least 2 characters")
        return val


class AddressResponse(AddressBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
