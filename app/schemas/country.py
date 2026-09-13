from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class CountryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Country name", examples=["India", "United States"])
    code: str = Field(..., min_length=1, max_length=20, description="Country code (ISO 2/3 letter code or ISO standard)", examples=["IN", "US"])
    is_active: bool = Field(True, description="Whether the country is active for shipping and address selection")

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Country name cannot be empty or only whitespace")
        return cleaned

    @field_validator("code")
    @classmethod
    def clean_code(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("Country code cannot be empty or only whitespace")
        return cleaned


class CountryCreate(CountryBase):
    pass


class CountryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Country name")
    code: Optional[str] = Field(None, min_length=1, max_length=20, description="Country code")
    is_active: Optional[bool] = Field(None, description="Active status")

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Country name cannot be empty or only whitespace")
            return cleaned
        return v

    @field_validator("code")
    @classmethod
    def clean_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip().upper()
            if not cleaned:
                raise ValueError("Country code cannot be empty or only whitespace")
            return cleaned
        return v


class CountryResponse(CountryBase):
    id: UUID
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
