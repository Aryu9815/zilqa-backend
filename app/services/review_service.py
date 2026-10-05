from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.repositories.product_repository import product_repository
from app.repositories.review_repository import review_repository
from app.schemas.common import PaginatedResponse
from app.schemas.review import (
    ReviewCreate,
    ReviewResponse,
    ReviewSortBy,
    ReviewStatusUpdate,
    ReviewSummaryResponse,
    ReviewUpdate,
)
from app.utils.helpers import calculate_pagination


class ReviewService:

    async def create_review(
        self,
        db: AsyncSession,
        review_in: ReviewCreate,
        user_id: Optional[UUID] = None
    ) -> ReviewResponse:
        assert review_in.product_id is not None, "product_id is required"
        product = await product_repository.get_by_id(db, review_in.product_id)
        if not product:
            raise NotFoundException(message="Product not found", error_code="PRODUCT_NOT_FOUND")

        # Automatically determine verified purchase status
        is_verified = False
        if user_id:
            is_verified = await review_repository.check_user_purchased_product(
                user_id=user_id,
                product_id=review_in.product_id
            )

        created_record = await review_repository.create(
            review_in=review_in,
            user_id=user_id,
            is_verified=is_verified
        )

        full_record = await review_repository.get_by_id(created_record["id"])
        assert full_record is not None
        return ReviewResponse.model_validate(dict(full_record))

    async def get_review(self, review_id: UUID, is_active_only: bool = False) -> ReviewResponse:
        record = await review_repository.get_by_id(review_id, is_active_only=is_active_only)
        if not record:
            raise NotFoundException(message="Review not found", error_code="REVIEW_NOT_FOUND")
        return ReviewResponse.model_validate(dict(record))

    async def list_product_reviews(
        self,
        db: AsyncSession,
        product_id: UUID,
        page: int = 1,
        limit: int = 20,
        rating: Optional[int] = None,
        sort_by: Optional[ReviewSortBy] = ReviewSortBy.NEWEST
    ) -> PaginatedResponse[ReviewResponse]:
        product = await product_repository.get_by_id(db, product_id)
        if not product:
            raise NotFoundException(message="Product not found", error_code="PRODUCT_NOT_FOUND")

        records, total = await review_repository.list_reviews(
            page=page,
            limit=limit,
            product_id=product_id,
            rating=rating,
            is_active_only=True,
            include_deleted=False,
            sort_by=sort_by
        )
        items = [ReviewResponse.model_validate(dict(r)) for r in records]
        pagination = calculate_pagination(total=total, page=page, limit=limit)
        return PaginatedResponse(data=items, pagination=pagination)

    async def get_product_summary(self, db: AsyncSession, product_id: UUID) -> ReviewSummaryResponse:
        product = await product_repository.get_by_id(db, product_id)
        if not product:
            raise NotFoundException(message="Product not found", error_code="PRODUCT_NOT_FOUND")

        summary_data = await review_repository.get_product_summary(product_id)
        return ReviewSummaryResponse.model_validate(summary_data)

    async def list_general_reviews(
        self,
        page: int = 1,
        limit: int = 20,
        rating: Optional[int] = None,
        sort_by: Optional[ReviewSortBy] = ReviewSortBy.NEWEST
    ) -> PaginatedResponse[ReviewResponse]:
        records, total = await review_repository.list_reviews(
            page=page,
            limit=limit,
            rating=rating,
            is_general=True,
            is_active_only=True,
            include_deleted=False,
            sort_by=sort_by
        )
        items = [ReviewResponse.model_validate(dict(r)) for r in records]
        pagination = calculate_pagination(total=total, page=page, limit=limit)
        return PaginatedResponse(data=items, pagination=pagination)

    async def list_user_reviews(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[ReviewResponse]:
        records, total = await review_repository.list_reviews(
            page=page,
            limit=limit,
            user_id=user_id,
            is_active_only=False,
            include_deleted=False,
            sort_by=ReviewSortBy.NEWEST
        )
        items = [ReviewResponse.model_validate(dict(r)) for r in records]
        pagination = calculate_pagination(total=total, page=page, limit=limit)
        return PaginatedResponse(data=items, pagination=pagination)

    async def update_user_review(
        self,
        review_id: UUID,
        user_id: UUID,
        review_in: ReviewUpdate
    ) -> ReviewResponse:
        existing = await review_repository.get_by_id(review_id)
        if not existing:
            raise NotFoundException(message="Review not found", error_code="REVIEW_NOT_FOUND")

        if existing["user_id"] != user_id:
            raise ForbiddenException(
                message="You do not have permission to modify this review",
                error_code="NOT_REVIEW_OWNER"
            )

        updated_record = await review_repository.update(review_id, review_in)
        assert updated_record is not None
        full_record = await review_repository.get_by_id(review_id)
        assert full_record is not None
        return ReviewResponse.model_validate(dict(full_record))

    async def delete_user_review(self, review_id: UUID, user_id: UUID) -> None:
        existing = await review_repository.get_by_id(review_id)
        if not existing:
            raise NotFoundException(message="Review not found", error_code="REVIEW_NOT_FOUND")

        if existing["user_id"] != user_id:
            raise ForbiddenException(
                message="You do not have permission to delete this review",
                error_code="NOT_REVIEW_OWNER"
            )

        await review_repository.delete(review_id, soft=True)

    async def list_admin_reviews(
        self,
        page: int = 1,
        limit: int = 20,
        product_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        rating: Optional[int] = None,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        is_general: Optional[bool] = None,
        include_deleted: bool = False,
        sort_by: Optional[ReviewSortBy] = ReviewSortBy.NEWEST
    ) -> PaginatedResponse[ReviewResponse]:
        records, total = await review_repository.list_reviews(
            page=page,
            limit=limit,
            product_id=product_id,
            user_id=user_id,
            rating=rating,
            is_general=is_general,
            is_verified=is_verified,
            is_active_only=False if is_active is None else is_active,
            include_deleted=include_deleted,
            sort_by=sort_by
        )
        items = [ReviewResponse.model_validate(dict(r)) for r in records]
        pagination = calculate_pagination(total=total, page=page, limit=limit)
        return PaginatedResponse(data=items, pagination=pagination)

    async def update_admin_review_status(
        self,
        review_id: UUID,
        status_in: ReviewStatusUpdate
    ) -> ReviewResponse:
        existing = await review_repository.get_by_id(review_id)
        if not existing:
            raise NotFoundException(message="Review not found", error_code="REVIEW_NOT_FOUND")

        await review_repository.update_status(
            review_id=review_id,
            is_active=status_in.is_active,
            is_verified=status_in.is_verified
        )

        full_record = await review_repository.get_by_id(review_id)
        assert full_record is not None
        return ReviewResponse.model_validate(dict(full_record))

    async def delete_admin_review(self, review_id: UUID, soft: bool = True) -> None:
        deleted = await review_repository.delete(review_id, soft=soft)
        if not deleted:
            raise NotFoundException(message="Review not found", error_code="REVIEW_NOT_FOUND")


review_service = ReviewService()
