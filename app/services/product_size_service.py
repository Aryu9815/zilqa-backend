from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.repositories.category_repository import category_repository
from app.repositories.product_size_repository import product_size_repository
from app.schemas.common import PaginatedResponse
from app.schemas.product_size import ProductSizeCreate, ProductSizeResponse, ProductSizeUpdate
from app.utils.helpers import calculate_pagination


class ProductSizeService:

    def _to_response(self, size: any) -> ProductSizeResponse:
        cat_name = None
        if hasattr(size, "category") and size.category:
            cat_name = getattr(size.category, "name", None)

        data = {
            "id": size.id,
            "name": size.name,
            "category_id": size.category_id,
            "display_order": size.display_order,
            "is_active": size.is_active,
            "is_deleted": size.is_deleted,
            "created_at": size.created_at,
            "updated_at": size.updated_at,
            "category_name": cat_name,
        }
        return ProductSizeResponse.model_validate(data)

    async def list_sizes(
        self,
        db: AsyncSession,
        category_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        limit: int = 100,
    ) -> PaginatedResponse[ProductSizeResponse]:
        is_active_only = is_active if is_active is not None else False
        records, total = await product_size_repository.list_sizes(
            db=db,
            category_id=category_id,
            is_active_only=is_active_only,
            include_deleted=False,
            page=page,
            limit=limit,
        )
        items = [self._to_response(r) for r in records]
        pagination = calculate_pagination(total=total, page=page, limit=limit)
        return PaginatedResponse(data=items, pagination=pagination)

    async def get_size(self, db: AsyncSession, size_id: UUID) -> ProductSizeResponse:
        record = await product_size_repository.get_by_id(db, size_id, include_deleted=False)
        if not record:
            raise NotFoundException(message="Product size not found", error_code="PRODUCT_SIZE_NOT_FOUND")
        return self._to_response(record)

    async def create_size(self, db: AsyncSession, size_in: ProductSizeCreate) -> ProductSizeResponse:
        if size_in.category_id:
            category = await category_repository.get_by_id(db, size_in.category_id)
            if not category:
                raise BadRequestException(
                    message=f"Category with ID '{size_in.category_id}' does not exist",
                    error_code="CATEGORY_NOT_FOUND",
                )

        record = await product_size_repository.create(db, size_in)
        return self._to_response(record)

    async def update_size(
        self,
        db: AsyncSession,
        size_id: UUID,
        size_in: ProductSizeUpdate,
    ) -> ProductSizeResponse:
        existing = await product_size_repository.get_by_id(db, size_id, include_deleted=False)
        if not existing:
            raise NotFoundException(message="Product size not found", error_code="PRODUCT_SIZE_NOT_FOUND")

        if size_in.category_id:
            category = await category_repository.get_by_id(db, size_in.category_id)
            if not category:
                raise BadRequestException(
                    message=f"Category with ID '{size_in.category_id}' does not exist",
                    error_code="CATEGORY_NOT_FOUND",
                )

        updated = await product_size_repository.update(db, size_id, size_in)
        assert updated is not None
        return self._to_response(updated)

    async def delete_size(self, db: AsyncSession, size_id: UUID, soft: bool = True) -> None:
        deleted = await product_size_repository.delete(db, size_id, soft=soft)
        if not deleted:
            raise NotFoundException(message="Product size not found", error_code="PRODUCT_SIZE_NOT_FOUND")


product_size_service = ProductSizeService()
