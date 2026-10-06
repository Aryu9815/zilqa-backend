from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: str = "customer"
    is_active: bool
    country_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    email: Optional[EmailStr] = None
    country_code: Optional[str] = None
    current_password: Optional[str] = Field(None, min_length=6)
    new_password: Optional[str] = Field(None, min_length=6, max_length=128)
