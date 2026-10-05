from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Full name of the user")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=6, max_length=128, description="Plaintext password")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, description="Password")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Cryptographic refresh token")


class GoogleLoginRequest(BaseModel):
    credential: str = Field(..., min_length=1, description="Google ID token / credential")


class UserSummaryResponse(BaseModel):
    id: UUID
    name: str
    email: str
    mobile_number: Optional[str] = None
    role: str
    country_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    country_code: Optional[str] = None
    user: UserSummaryResponse
