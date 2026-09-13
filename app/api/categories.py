from typing import Any, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import require_admin
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.common import PaginatedResponse, ResponseEnvelope
from app.services.category_service import category_service

public_router = APIRouter(prefix="/categories", tags=["Categories"])
admin_router = APIRouter(prefix="/admin/categories", tags=["Categories"])


# =============================================================================
# PUBLIC CATEGORY ENDPOINTS
# =============================================================================

@public_router.get(
    "",
    response_model=PaginatedResponse[CategoryResponse],
    summary="List all categories (Public, Paginated)"
)
async def list_categories(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
) -> PaginatedResponse[CategoryResponse]:
    return await category_service.list_categories(page=page, limit=limit)


@public_router.get(
    "/{category_id}",
    response_model=ResponseEnvelope[CategoryResponse],
    summary="Get single category by ID (Public)"
)
async def get_category(category_id: UUID) -> ResponseEnvelope[CategoryResponse]:
    category = await category_service.get_category(category_id)
    return ResponseEnvelope(
        success=True,
        message="Category retrieved successfully",
        data=category
    )


# =============================================================================
# ADMIN CATEGORY ENDPOINTS
# =============================================================================

@admin_router.post(
    "",
    response_model=ResponseEnvelope[CategoryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create category (Admin only)"
)
async def create_category(
    category_in: CategoryCreate,
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[CategoryResponse]:
    created = await category_service.create_category(category_in)
    return ResponseEnvelope(
        success=True,
        message="Category created successfully",
        data=created
    )


@admin_router.put(
    "/{category_id}",
    response_model=ResponseEnvelope[CategoryResponse],
    summary="Update category (Admin only)"
)
async def update_category(
    category_id: UUID,
    category_in: CategoryUpdate,
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[CategoryResponse]:
    updated = await category_service.update_category(category_id, category_in)
    return ResponseEnvelope(
        success=True,
        message="Category updated successfully",
        data=updated
    )


@admin_router.delete(
    "/{category_id}",
    response_model=ResponseEnvelope[None],
    summary="Delete category (Admin only)"
)
async def delete_category(
    category_id: UUID,
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[None]:
    await category_service.delete_category(category_id)
    return ResponseEnvelope(
        success=True,
        message="Category deleted successfully"
    )
