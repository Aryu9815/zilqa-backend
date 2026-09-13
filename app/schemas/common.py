from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, description="Number of items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: List[T]
    pagination: PaginationMeta


class ResponseEnvelope(BaseModel, Generic[T]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: str
    errors: Optional[Any] = None
