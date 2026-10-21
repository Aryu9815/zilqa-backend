from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.db.database import get_db
from app.models.admin import Admin
from app.schemas.common import PaginatedResponse, ResponseEnvelope
from app.schemas.product_size import ProductSizeCreate, ProductSizeResponse, ProductSizeUpdate
from app.services.product_size_service import product_size_service

public_router = APIRouter(prefix="/product-sizes", tags=["Product Sizes"])
admin_router = APIRouter(prefix="/admin/product-sizes", tags=["Product Sizes"])


# =============================================================================
# PUBLIC PRODUCT SIZES ENDPOINTS
# =============================================================================

@public_router.get(
    "",
    response_model=PaginatedResponse[ProductSizeResponse],
    summary="List product sizes (Public)"
)
async def list_product_sizes(
    category_id: Optional[UUID] = Query(None, description="Filter by Category UUID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(100, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[ProductSizeResponse]:
    return await product_size_service.list_sizes(
        db,
        category_id=category_id,
        is_active=True,
        page=page,
        limit=limit
    )


@public_router.get(
    "/{size_id}",
    response_model=ResponseEnvelope[ProductSizeResponse],
    summary="Get single product size by ID (Public)"
)
async def get_product_size(
    size_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> ResponseEnvelope[ProductSizeResponse]:
    size = await product_size_service.get_size(db, size_id)
    return ResponseEnvelope(
        success=True,
        message="Product size retrieved successfully",
        data=size
    )


# =============================================================================
# ADMIN PRODUCT SIZES ENDPOINTS
# =============================================================================

@admin_router.get(
    "",
    response_model=PaginatedResponse[ProductSizeResponse],
    summary="List all product sizes including inactive (Admin only)"
)
async def admin_list_product_sizes(
    category_id: Optional[UUID] = Query(None, description="Filter by Category UUID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(100, ge=1, le=100, description="Items per page"),
    current_admin: Admin = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[ProductSizeResponse]:
    return await product_size_service.list_sizes(
        db,
        category_id=category_id,
        is_active=is_active,
        page=page,
        limit=limit
    )


@admin_router.get(
    "/{size_id}",
    response_model=ResponseEnvelope[ProductSizeResponse],
    summary="Get single product size details (Admin only)"
)
async def admin_get_product_size(
    size_id: UUID,
    current_admin: Admin = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> ResponseEnvelope[ProductSizeResponse]:
    size = await product_size_service.get_size(db, size_id)
    return ResponseEnvelope(
        success=True,
        message="Product size retrieved successfully",
        data=size
    )


@admin_router.post(
    "",
    response_model=ResponseEnvelope[ProductSizeResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create product size (Admin only)"
)
async def create_product_size(
    size_in: ProductSizeCreate,
    current_admin: Admin = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> ResponseEnvelope[ProductSizeResponse]:
    created = await product_size_service.create_size(db, size_in)
    return ResponseEnvelope(
        success=True,
        message="Product size created successfully",
        data=created
    )


@admin_router.put(
    "/{size_id}",
    response_model=ResponseEnvelope[ProductSizeResponse],
    summary="Update product size (Admin only)"
)
async def update_product_size(
    size_id: UUID,
    size_in: ProductSizeUpdate,
    current_admin: Admin = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> ResponseEnvelope[ProductSizeResponse]:
    updated = await product_size_service.update_size(db, size_id, size_in)
    return ResponseEnvelope(
        success=True,
        message="Product size updated successfully",
        data=updated
    )


@admin_router.delete(
    "/{size_id}",
    response_model=ResponseEnvelope[None],
    summary="Soft-delete/deactivate product size (Admin only)"
)
async def delete_product_size(
    size_id: UUID,
    current_admin: Admin = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> ResponseEnvelope[None]:
    await product_size_service.delete_size(db, size_id, soft=True)
    return ResponseEnvelope(
        success=True,
        message="Product size deleted successfully"
    )
