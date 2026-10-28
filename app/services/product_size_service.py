from typing import Optional, List, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.repositories.category_repository import category_repository
from app.repositories.product_size_repository import product_size_repository
from app.schemas.common import PaginatedResponse
from app.schemas.product_size import (
    ProductSizeCreate,
    ProductSizeResponse,
    ProductSizesFlowResponse,
    ProductSizeUpdate,
)
from app.utils.helpers import calculate_pagination


class ProductSizeService:

    def _to_response(self, size: Any) -> ProductSizeResponse:
        cat_name = None
        if hasattr(size, "category") and size.category:
            cat_name = getattr(size.category, "name", None)

        data = {
            "id": size.id,
            "name": size.name,
            "category_id": size.category_id,
            "country_code": getattr(size, "country_code", None),
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
        country_code: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        limit: int = 100,
    ) -> PaginatedResponse[ProductSizeResponse]:
        is_active_only = is_active if is_active is not None else False
        records, total = await product_size_repository.list_sizes(
            db=db,
            category_id=category_id,
            country_code=country_code,
            is_active_only=is_active_only,
            include_deleted=False,
            page=page,
            limit=limit,
        )
        items = [self._to_response(r) for r in records]
        pagination = calculate_pagination(total=total, page=page, limit=limit)
        return PaginatedResponse(data=items, pagination=pagination)
    
    async def get_sizes(
        self,
        db: AsyncSession,
        category_ids: List[UUID],
    ) -> PaginatedResponse[ProductSizeResponse]:

        size_categories = await product_size_repository.get_unique_categories(db)
        matching_categories = set(size_categories) & set(category_ids)
        all_sizes: List[ProductSizeResponse] = []
        seen_ids = set()

        for cat_id in matching_categories:
            records, total = await product_size_repository.list_sizes(
                db=db,
                category_id=cat_id,
                is_active_only=True,
                include_deleted=False,
                page=1,
                limit=1000,
            )
            for r in records:
                if r.id not in seen_ids:
                    seen_ids.add(r.id)
                    all_sizes.append(self._to_response(r))

        pagination = calculate_pagination(total=len(all_sizes), page=1, limit=max(len(all_sizes), 1))
        return PaginatedResponse(data=all_sizes, pagination=pagination)

    async def get_available_countries(
        self,
        db: AsyncSession,
        category_id: Optional[UUID] = None,
        is_active: Optional[bool] = True,
    ) -> List[str]:
        is_active_only = is_active if is_active is not None else False
        return await product_size_repository.get_available_countries(
            db=db,
            category_id=category_id,
            is_active_only=is_active_only,
            include_deleted=False,
        )

    async def get_sizes_flow(
        self,
        db: AsyncSession,
        category_id: Optional[UUID] = None,
        country_code: Optional[str] = None,
        is_active: Optional[bool] = True,
    ) -> ProductSizesFlowResponse:
        """
        Flow logic:
        Category -> sizes if country code is not available,
        if available then it becomes Category -> country_code -> sizes.
        """
        is_active_only = is_active if is_active is not None else False

        # 1. Fetch available countries for this category
        available_countries = await product_size_repository.get_available_countries(
            db=db,
            category_id=category_id,
            is_active_only=is_active_only,
            include_deleted=False,
        )

        has_country_codes = len(available_countries) > 0
        selected_code = None

        if has_country_codes:
            if country_code:
                norm_requested = country_code.strip().upper()
                matching = next((c for c in available_countries if c.upper() == norm_requested), None)
                selected_code = matching or norm_requested
            else:
                # Default to the first available country code
                selected_code = available_countries[0]

            records, _ = await product_size_repository.list_sizes(
                db=db,
                category_id=category_id,
                country_code=selected_code,
                is_active_only=is_active_only,
                include_deleted=False,
                page=1,
                limit=100,
            )
        else:
            # No country codes available for this category -> category directly to sizes
            records, _ = await product_size_repository.list_sizes(
                db=db,
                category_id=category_id,
                country_code=None,
                is_active_only=is_active_only,
                include_deleted=False,
                page=1,
                limit=100,
            )

        sizes = [self._to_response(r) for r in records]
        return ProductSizesFlowResponse(
            has_country_codes=has_country_codes,
            available_countries=available_countries,
            selected_country_code=selected_code,
            sizes=sizes,
        )

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
