from typing import Any, Dict, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin, require_authenticated_user
from app.db.database import get_db
from app.schemas.common import PaginatedResponse, ResponseEnvelope
from app.schemas.review import (
    ReviewCreate,
    ReviewResponse,
    ReviewSortBy,
    ReviewStatusUpdate,
    ReviewSummaryResponse,
    ReviewUpdate,
)
from app.services.review_service import review_service


public_router = APIRouter(tags=["Reviews"])
user_router = APIRouter(prefix="/reviews", tags=["Reviews"])
admin_router = APIRouter(prefix="/admin/reviews", tags=["Admin Reviews"])


# =============================================================================
# PUBLIC REVIEW ENDPOINTS
# =============================================================================

@public_router.get(
    "/products/{product_id}/reviews",
    response_model=PaginatedResponse[ReviewResponse],
    summary="List product reviews with pagination, star filtering & sorting (Public)"
)
async def list_product_reviews(
    product_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    rating: Optional[int] = Query(None, ge=1, le=5, description="Filter by star rating (1-5)"),
    sort_by: Optional[ReviewSortBy] = Query(ReviewSortBy.NEWEST, description="Sort criteria"),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[ReviewResponse]:
    return await review_service.list_product_reviews(
        db=db,
        product_id=product_id,
        page=page,
        limit=limit,
        rating=rating,
        sort_by=sort_by
    )


@public_router.get(
    "/products/{product_id}/reviews/summary",
    response_model=ResponseEnvelope[ReviewSummaryResponse],
    summary="Get product review summary & rating breakdown (Public)"
)
async def get_product_review_summary(
    product_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> ResponseEnvelope[ReviewSummaryResponse]:
    summary = await review_service.get_product_summary(db=db, product_id=product_id)
    return ResponseEnvelope(
        success=True,
        message="Product review summary retrieved successfully",
        data=summary
    )


@public_router.get(
    "/reviews",
    response_model=PaginatedResponse[ReviewResponse],
    summary="List general reviews (Public, is_general=true only)"
)
async def list_reviews(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    rating: Optional[int] = Query(None, ge=1, le=5, description="Filter by star rating (1-5)"),
    sort_by: Optional[ReviewSortBy] = Query(ReviewSortBy.NEWEST, description="Sort criteria")
) -> PaginatedResponse[ReviewResponse]:
    """List general store testimonial reviews (strictly returns reviews where is_general is true)."""
    return await review_service.list_general_reviews(
        page=page,
        limit=limit,
        rating=rating,
        sort_by=sort_by
    )


@public_router.get(
    "/reviews/general",
    response_model=PaginatedResponse[ReviewResponse],
    summary="List general / testimonial reviews (Public, is_general=true only)"
)
async def list_general_reviews(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    rating: Optional[int] = Query(None, ge=1, le=5, description="Filter by star rating (1-5)"),
    sort_by: Optional[ReviewSortBy] = Query(ReviewSortBy.NEWEST, description="Sort criteria")
) -> PaginatedResponse[ReviewResponse]:
    """List general store testimonial reviews (strictly returns reviews where is_general is true)."""
    return await review_service.list_general_reviews(
        page=page,
        limit=limit,
        rating=rating,
        sort_by=sort_by
    )


@public_router.get(
    "/reviews/{review_id}",
    response_model=ResponseEnvelope[ReviewResponse],
    summary="Get single review details (Public)"
)
async def get_review(
    review_id: UUID
) -> ResponseEnvelope[ReviewResponse]:
    review = await review_service.get_review(review_id, is_active_only=True)
    return ResponseEnvelope(
        success=True,
        message="Review retrieved successfully",
        data=review
    )


# =============================================================================
# AUTHENTICATED CUSTOMER REVIEW ENDPOINTS
# =============================================================================

@public_router.post(
    "/products/{product_id}/reviews",
    response_model=ResponseEnvelope[ReviewResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit a review for a specific product (Authenticated)"
)
async def create_product_review(
    product_id: UUID,
    review_in: ReviewCreate,
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db)
) -> ResponseEnvelope[ReviewResponse]:
    # Ensure route path product_id takes precedence
    review_in.product_id = product_id
    review = await review_service.create_review(
        db=db,
        review_in=review_in,
        user_id=current_user["id"]
    )
    return ResponseEnvelope(
        success=True,
        message="Review submitted successfully",
        data=review
    )


@user_router.post(
    "",
    response_model=ResponseEnvelope[ReviewResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit a review with product_id in payload (Authenticated)"
)
async def create_review_standalone(
    review_in: ReviewCreate,
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db)
) -> ResponseEnvelope[ReviewResponse]:
    review = await review_service.create_review(
        db=db,
        review_in=review_in,
        user_id=current_user["id"]
    )
    return ResponseEnvelope(
        success=True,
        message="Review submitted successfully",
        data=review
    )


@user_router.get(
    "/me",
    response_model=PaginatedResponse[ReviewResponse],
    summary="List authenticated user's submitted reviews"
)
async def list_my_reviews(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> PaginatedResponse[ReviewResponse]:
    return await review_service.list_user_reviews(
        user_id=current_user["id"],
        page=page,
        limit=limit
    )


@user_router.put(
    "/{review_id}",
    response_model=ResponseEnvelope[ReviewResponse],
    summary="Update customer's own review"
)
async def update_my_review(
    review_id: UUID,
    review_in: ReviewUpdate,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[ReviewResponse]:
    updated_review = await review_service.update_user_review(
        review_id=review_id,
        user_id=current_user["id"],
        review_in=review_in
    )
    return ResponseEnvelope(
        success=True,
        message="Review updated successfully",
        data=updated_review
    )


@user_router.delete(
    "/{review_id}",
    response_model=ResponseEnvelope[None],
    summary="Delete customer's own review"
)
async def delete_my_review(
    review_id: UUID,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[None]:
    await review_service.delete_user_review(
        review_id=review_id,
        user_id=current_user["id"]
    )
    return ResponseEnvelope(
        success=True,
        message="Review deleted successfully"
    )


# =============================================================================
# ADMIN REVIEW ENDPOINTS
# =============================================================================

@admin_router.get(
    "",
    response_model=PaginatedResponse[ReviewResponse],
    summary="List all reviews with filtering for admin moderation (Admin only)"
)
async def list_admin_reviews(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    product_id: Optional[UUID] = Query(None, description="Filter by product UUID"),
    user_id: Optional[UUID] = Query(None, description="Filter by user UUID"),
    rating: Optional[int] = Query(None, ge=1, le=5, description="Filter by star rating"),
    is_active: Optional[bool] = Query(None, description="Filter by active visibility status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verified purchase status"),
    is_general: Optional[bool] = Query(None, description="Filter by general review status"),
    include_deleted: bool = Query(False, description="Include soft-deleted reviews"),
    sort_by: Optional[ReviewSortBy] = Query(ReviewSortBy.NEWEST, description="Sort criteria"),
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> PaginatedResponse[ReviewResponse]:
    return await review_service.list_admin_reviews(
        page=page,
        limit=limit,
        product_id=product_id,
        user_id=user_id,
        rating=rating,
        is_active=is_active,
        is_verified=is_verified,
        is_general=is_general,
        include_deleted=include_deleted,
        sort_by=sort_by
    )


@admin_router.put(
    "/{review_id}/status",
    response_model=ResponseEnvelope[ReviewResponse],
    summary="Update review visibility or verified status (Admin only)"
)
async def update_review_status(
    review_id: UUID,
    status_in: ReviewStatusUpdate,
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[ReviewResponse]:
    updated_review = await review_service.update_admin_review_status(
        review_id=review_id,
        status_in=status_in
    )
    return ResponseEnvelope(
        success=True,
        message="Review status updated successfully",
        data=updated_review
    )


@admin_router.delete(
    "/{review_id}",
    response_model=ResponseEnvelope[None],
    summary="Delete review (Admin only)"
)
async def delete_review_admin(
    review_id: UUID,
    soft: bool = Query(True, description="Whether to soft delete (default) or hard delete"),
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[None]:
    await review_service.delete_admin_review(review_id=review_id, soft=soft)
    return ResponseEnvelope(
        success=True,
        message="Review deleted successfully by administrator"
    )
