from uuid import uuid4
import pytest
from pydantic import ValidationError

from app.schemas.review import (
    ReviewCreate,
    ReviewResponse,
    ReviewSortBy,
    ReviewStatusUpdate,
    ReviewSummaryResponse,
    ReviewUpdate,
)


def test_review_create_validation():
    product_id = uuid4()
    review_in = ReviewCreate(
        product_id=product_id,
        rating=5,
        comment="Absolutely stunning craftsmanship and authentic sterling silver!",
        image_urls=["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"],
        is_general=False
    )
    assert review_in.product_id == product_id
    assert review_in.rating == 5
    assert len(review_in.image_urls) == 2
    assert review_in.is_general is False


def test_review_rating_lower_bound_rejected():
    product_id = uuid4()
    with pytest.raises(ValidationError):
        ReviewCreate(
            product_id=product_id,
            rating=0,
            comment="Too low rating"
        )


def test_review_rating_upper_bound_rejected():
    product_id = uuid4()
    with pytest.raises(ValidationError):
        ReviewCreate(
            product_id=product_id,
            rating=6,
            comment="Too high rating"
        )


def test_review_max_image_urls_rejected():
    product_id = uuid4()
    with pytest.raises(ValidationError):
        ReviewCreate(
            product_id=product_id,
            rating=4,
            image_urls=[f"https://example.com/photo_{i}.jpg" for i in range(6)]
        )


def test_review_update_validation():
    update_in = ReviewUpdate(
        rating=4,
        comment="Updated comment after wearing for 2 weeks"
    )
    assert update_in.rating == 4
    assert update_in.comment == "Updated comment after wearing for 2 weeks"
    assert update_in.image_urls is None


def test_review_status_update():
    status_in = ReviewStatusUpdate(is_active=False, is_verified=True)
    assert status_in.is_active is False
    assert status_in.is_verified is True


def test_review_summary_defaults():
    product_id = uuid4()
    summary = ReviewSummaryResponse(
        product_id=product_id,
        average_rating=4.5,
        total_reviews=10,
        rating_breakdown={1: 0, 2: 0, 3: 1, 4: 3, 5: 6}
    )
    assert summary.product_id == product_id
    assert summary.average_rating == 4.5
    assert summary.total_reviews == 10
    assert summary.rating_breakdown[5] == 6


def test_review_sort_by_enum_values():
    assert ReviewSortBy.NEWEST.value == "newest"
    assert ReviewSortBy.OLDEST.value == "oldest"
    assert ReviewSortBy.HIGHEST_RATING.value == "highest_rating"
    assert ReviewSortBy.LOWEST_RATING.value == "lowest_rating"


def test_review_routes_registered():
    from app.main import app
    openapi_paths = app.openapi()["paths"]
    assert "/api/v1/products/{product_id}/reviews" in openapi_paths
    assert "/api/v1/products/{product_id}/reviews/summary" in openapi_paths
    assert "/api/v1/reviews/general" in openapi_paths
    assert "/api/v1/reviews/{review_id}" in openapi_paths
    assert "/api/v1/reviews/me" in openapi_paths
    assert "/api/v1/admin/reviews" in openapi_paths
    assert "/api/v1/admin/reviews/{review_id}/status" in openapi_paths
