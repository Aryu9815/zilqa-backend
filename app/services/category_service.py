from typing import Tuple
from uuid import UUID

from app.core.exceptions import ConflictException, NotFoundException
from app.repositories.category_repository import category_repository
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.common import PaginatedResponse
from app.utils.helpers import calculate_pagination


class CategoryService:

    async def list_categories(self, page: int = 1, limit: int = 20) -> PaginatedResponse[CategoryResponse]:
        records, total = await category_repository.list_categories(page=page, limit=limit)
        items = [CategoryResponse.model_validate(dict(r)) for r in records]
        pagination = calculate_pagination(total=total, page=page, limit=limit)
        return PaginatedResponse(data=items, pagination=pagination)

    async def get_category(self, category_id: UUID) -> CategoryResponse:
        record = await category_repository.get_by_id(category_id)
        if not record:
            raise NotFoundException(message="Category not found", error_code="CATEGORY_NOT_FOUND")
        return CategoryResponse.model_validate(dict(record))

    async def create_category(self, category_in: CategoryCreate) -> CategoryResponse:
        existing = await category_repository.get_by_name(category_in.name, include_deleted=True)
        if existing:
            raise ConflictException(
                message=f"Category with name '{category_in.name}' already exists",
                error_code="CATEGORY_NAME_EXISTS"
            )
        record = await category_repository.create(category_in)
        return CategoryResponse.model_validate(dict(record))

    async def update_category(self, category_id: UUID, category_in: CategoryUpdate) -> CategoryResponse:
        existing = await category_repository.get_by_id(category_id, include_deleted=False)
        if not existing:
            raise NotFoundException(message="Category not found", error_code="CATEGORY_NOT_FOUND")

        if category_in.name and category_in.name.lower() != existing["name"].lower():
            duplicate = await category_repository.get_by_name(category_in.name, include_deleted=True)
            if duplicate:
                raise ConflictException(
                    message=f"Category with name '{category_in.name}' already exists",
                    error_code="CATEGORY_NAME_EXISTS"
                )

        record = await category_repository.update(category_id, category_in)
        assert record is not None
        return CategoryResponse.model_validate(dict(record))

    async def delete_category(self, category_id: UUID) -> None:
        deleted = await category_repository.delete(category_id, soft=True)
        if not deleted:
            raise NotFoundException(message="Category not found", error_code="CATEGORY_NOT_FOUND")


category_service = CategoryService()
