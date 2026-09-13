from decimal import Decimal
from uuid import uuid4
import pytest
from pydantic import ValidationError

from app.schemas.product import ProductCreate, ProductResponse, ProductSortBy, ProductUpdate


def test_product_create_validation_with_category_ids():
    cat1 = uuid4()
    cat2 = uuid4()
    product_in = ProductCreate(
        name="India Flag Ring",
        main_image_url="https://example.com/ring.jpg",
        other_image_urls=["https://example.com/ring2.jpg"],
        price=Decimal("999.00"),
        category_ids=[cat1, cat2],
        description="Sterling Silver ring",
        is_active=True
    )
    assert product_in.name == "India Flag Ring"
    assert product_in.price == Decimal("999.00")
    assert product_in.category_ids == [cat1, cat2]
    assert len(product_in.category_ids) == 2


def test_product_create_legacy_category_id_supported():
    cat = uuid4()
    product_in = ProductCreate(
        name="Single Category Product",
        main_image_url="https://example.com/img.jpg",
        price=Decimal("499.00"),
        category_id=cat
    )
    assert product_in.category_ids == [cat]


def test_product_negative_price_rejected():
    category_id = uuid4()
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Invalid Product",
            main_image_url="https://example.com/img.jpg",
            price=Decimal("-10.00"),
            category_ids=[category_id]
        )


def test_product_sort_by_values():
    assert ProductSortBy.PRICE_ASC.value == "price_asc"
    assert ProductSortBy.PRICE_DESC.value == "price_desc"
    assert ProductSortBy.NEWEST.value == "newest"
    assert ProductSortBy.OLDEST.value == "oldest"
    assert ProductSortBy.NAME_ASC.value == "name_asc"
    assert ProductSortBy.NAME_DESC.value == "name_desc"

