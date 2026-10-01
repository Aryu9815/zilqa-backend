from fastapi import APIRouter, Depends, Query, status, UploadFile, File
from typing import Any, Dict, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.dependencies import require_admin
from app.models.admin import Admin
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
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[CategoryResponse]:
    return await category_service.list_categories(db, page=page, limit=limit)


@public_router.get(
    "/{category_id}",
    response_model=ResponseEnvelope[CategoryResponse],
    summary="Get single category by ID (Public)"
)
async def get_category(category_id: UUID, db: AsyncSession = Depends(get_db)) -> ResponseEnvelope[CategoryResponse]:
    category = await category_service.get_category(db, category_id)
    return ResponseEnvelope(
        success=True,
        message="Category retrieved successfully",
        data=category
    )


# =============================================================================
# ADMIN CATEGORY ENDPOINTS
# =============================================================================

@admin_router.get(
    "",
    response_model=PaginatedResponse[CategoryResponse],
    summary="List all categories (Admin only)"
)
async def admin_list_categories(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_admin: Admin = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[CategoryResponse]:
    return await category_service.list_categories(db, page=page, limit=limit, is_active=is_active)


@admin_router.post(
    "",
    response_model=ResponseEnvelope[CategoryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create category (Admin only)"
)
async def create_category(
    category_in: CategoryCreate,
    current_admin: Admin = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> ResponseEnvelope[CategoryResponse]:
    created = await category_service.create_category(db, category_in)
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
    current_admin: Admin = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> ResponseEnvelope[CategoryResponse]:
    updated = await category_service.update_category(db, category_id, category_in)
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
    current_admin: Admin = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> ResponseEnvelope[None]:
    await category_service.delete_category(db, category_id)
    return ResponseEnvelope(
        success=True,
        message="Category deleted successfully"
    )

@admin_router.post(
    "/{category_id}/image",
    response_model=ResponseEnvelope[CategoryResponse],
    summary="Upload category image (Admin only)"
)
async def upload_category_image(
    category_id: UUID,
    file: UploadFile = File(...),
    current_admin: Admin = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> ResponseEnvelope[CategoryResponse]:
    from app.repositories.category_repository import category_repository
    category = await category_repository.upload_image(db, category_id, file)
    if not category:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Category not found")
        
    return ResponseEnvelope(
        success=True,
        message="Category image uploaded successfully",
        data=CategoryResponse.model_validate(category)
    )

from app.schemas.category import CategoryProductsUpdate

@admin_router.post(
    "/{category_id}/products",
    response_model=ResponseEnvelope[None],
    summary="Add products to category (Admin only)"
)
async def add_products_to_category(
    category_id: UUID,
    payload: CategoryProductsUpdate,
    current_admin: Admin = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> ResponseEnvelope[None]:
    from app.repositories.category_repository import category_repository
    success = await category_repository.add_products(db, category_id, payload.product_ids)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Category not found")
        
    return ResponseEnvelope(
        success=True,
        message="Products added to category successfully"
    )

@admin_router.delete(
    "/{category_id}/products",
    response_model=ResponseEnvelope[None],
    summary="Remove products from category (Admin only)"
)
async def remove_products_from_category(
    category_id: UUID,
    payload: CategoryProductsUpdate,
    current_admin: Admin = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> ResponseEnvelope[None]:
    from app.repositories.category_repository import category_repository
    success = await category_repository.remove_products(db, category_id, payload.product_ids)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Category not found")
        
    return ResponseEnvelope(
        success=True,
        message="Products removed from category successfully"
    )
