from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, UploadFile, File, Form
from app.core.dependencies import require_admin
from app.schemas.common import PaginatedResponse, ResponseEnvelope
from app.schemas.product import ProductCreate, ProductResponse, ProductSortBy, ProductUpdate
from app.services.product_service import product_service


public_router = APIRouter(prefix="/products", tags=["Products"])
admin_router = APIRouter(prefix="/admin/products", tags=["Products"])


@public_router.get(
    "",
    response_model=PaginatedResponse[ProductResponse],
    summary="List products with filtering, search, sorting & pagination (Public)"
)
async def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    category_id: Optional[UUID] = Query(None, description="Filter by single Category UUID"),
    category_ids: Optional[List[UUID]] = Query(None, description="Filter by multiple Category UUIDs"),
    min_price: Optional[Decimal] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[Decimal] = Query(None, ge=0, description="Maximum price filter"),
    search: Optional[str] = Query(None, description="Search term in product name/description"),
    sort_by: Optional[ProductSortBy] = Query(ProductSortBy.NEWEST, description="Sort criteria")
, db: AsyncSession = Depends(get_db)) -> PaginatedResponse[ProductResponse]:
    return await product_service.list_products(db, 
        page=page,
        limit=limit,
        category_id=category_id,
        category_ids=category_ids,
        min_price=min_price,
        max_price=max_price,
        search=search,
        sort_by=sort_by,
        is_active_only=True
    )


@public_router.get(
    "/{product_id}",
    response_model=ResponseEnvelope[ProductResponse],
    summary="Get single product details (Public)"
)
async def get_product(product_id: UUID, db: AsyncSession = Depends(get_db)) -> ResponseEnvelope[ProductResponse]:
    product = await product_service.get_product(db, product_id, is_active_only=True)
    return ResponseEnvelope(
        success=True,
        message="Product retrieved successfully",
        data=product
    )


@public_router.get(
    "/{product_id}/related",
    response_model=ResponseEnvelope[List[ProductResponse]],
    summary="Get related products for a product (Public)"
)
async def get_related_products(product_id: UUID, db: AsyncSession = Depends(get_db)) -> ResponseEnvelope[List[ProductResponse]]:
    related_products = await product_service.get_related_products(db, product_id)
    return ResponseEnvelope(
        success=True,
        message="Related products retrieved successfully",
        data=related_products
    )


# ADMIN PRODUCT ENDPOINTS

@admin_router.post(
    "",
    response_model=ResponseEnvelope[ProductResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create product (Admin only)"
)
async def create_product(
    product_in: ProductCreate,
    current_admin: Any = Depends(require_admin)
, db: AsyncSession = Depends(get_db)) -> ResponseEnvelope[ProductResponse]:
    print('creation started')
    product = await product_service.create_product(db, product_in)
    print("product created ....................")
    return ResponseEnvelope(
        success=True,
        message="Product created successfully",
        data=product
    )


@admin_router.put(
    "/{product_id}",
    response_model=ResponseEnvelope[ProductResponse],
    summary="Update product (Admin only)"
)
async def update_product(
    product_id: UUID,
    product_in: ProductUpdate,
    current_admin: Any = Depends(require_admin)
, db: AsyncSession = Depends(get_db)) -> ResponseEnvelope[ProductResponse]:
    product = await product_service.update_product(db, product_id, product_in)
    return ResponseEnvelope(
        success=True,
        message="Product updated successfully",
        data=product
    )


@admin_router.delete(
    "/{product_id}",
    response_model=ResponseEnvelope[None],
    summary="Soft-delete/deactivate product (Admin only)"
)
async def delete_product(
    product_id: UUID,
    current_admin: Any = Depends(require_admin)
, db: AsyncSession = Depends(get_db)) -> ResponseEnvelope[None]:
    await product_service.delete_product(db, product_id)
    return ResponseEnvelope(
        success=True,
        message="Product deactivated successfully"
    )


# images

from app.repositories.product_repository import product_repository

@admin_router.post("/{product_id}/images/main")
async def upload_main_image(
    product_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: Any = Depends(require_admin)
):
    image = await product_repository.upload_main_image(db, product_id, file)
    if not image:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {
        "success": True,
        "message": "Main image uploaded successfully",
        "data": image,
    }

@admin_router.post("/{product_id}/images/other")
async def upload_other_images(
    product_id: UUID,
    images: str = Form(...),
    files: List[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
    current_admin: Any = Depends(require_admin)
):
    import json
    from fastapi import HTTPException
    
    try:
        images_data = json.loads(images)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid images JSON format")
        
    result = await product_repository.upload_other_images(db, product_id, images_data, files)
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {
        "success": True,
        "message": "Other images uploaded successfully",
        "data": result,
    }