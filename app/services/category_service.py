from typing import Tuple, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.repositories.category_repository import category_repository
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.common import PaginatedResponse
from app.utils.helpers import calculate_pagination


class CategoryService:

    async def list_categories(
        self, 
        db: AsyncSession,
        page: int = 1, 
        limit: int = 20, 
        is_active: Optional[bool] = None
    ) -> PaginatedResponse[CategoryResponse]:
        records, total = await category_repository.list_categories(db=db, page=page, limit=limit, is_active=is_active)
        items = [CategoryResponse.model_validate(r) for r in records]
        pagination = calculate_pagination(total=total, page=page, limit=limit)
        return PaginatedResponse(data=items, pagination=pagination)

    async def get_category(self, db: AsyncSession, category_id: UUID) -> CategoryResponse:
        record = await category_repository.get_by_id(db, category_id)
        if not record:
            raise NotFoundException(message="Category not found", error_code="CATEGORY_NOT_FOUND")
        return CategoryResponse.model_validate(record)

    async def create_category(self, db: AsyncSession, category_in: CategoryCreate) -> CategoryResponse:
        existing = await category_repository.get_by_name(db, category_in.name, include_deleted=True)
        if existing:
            raise ConflictException(
                message=f"Category with name '{category_in.name}' already exists",
                error_code="CATEGORY_NAME_EXISTS"
            )
        record = await category_repository.create(db, category_in)
        return CategoryResponse.model_validate(record)

    async def update_category(self, db: AsyncSession, category_id: UUID, category_in: CategoryUpdate) -> CategoryResponse:
        existing = await category_repository.get_by_id(db, category_id, include_deleted=False)
        if not existing:
            raise NotFoundException(message="Category not found", error_code="CATEGORY_NOT_FOUND")

        if category_in.name and category_in.name.lower() != existing.name.lower():
            duplicate = await category_repository.get_by_name(db, category_in.name, include_deleted=True)
            if duplicate:
                raise ConflictException(
                    message=f"Category with name '{category_in.name}' already exists",
                    error_code="CATEGORY_NAME_EXISTS"
                )

        record = await category_repository.update(db, category_id, category_in)
        assert record is not None
        return CategoryResponse.model_validate(record)

    async def delete_category(self, db: AsyncSession, category_id: UUID) -> None:
        deleted = await category_repository.delete(db, category_id, soft=True)
        if not deleted:
            raise NotFoundException(message="Category not found", error_code="CATEGORY_NOT_FOUND")


category_service = CategoryService()
