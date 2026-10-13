from decimal import Decimal
from uuid import uuid4
import pytest
from pydantic import ValidationError

from app.schemas.product import (
    ProductCreate,
    ProductMaterial,
    ProductResponse,
    ProductSortBy,
    ProductUpdate,
)


def test_product_create_validation_with_category_ids():
    cat1 = uuid4()
    cat2 = uuid4()
    product_in = ProductCreate(
        name="India Flag Ring",
        slug="india-flag-ring",
        seo_title="India Flag Ring | Zelqa",
        price=Decimal("999.00"),
        category_ids=[cat1, cat2],
        description="Sterling Silver ring",
        is_active=True,
    )
    assert product_in.name == "India Flag Ring"
    assert product_in.price == Decimal("999.00")
    assert product_in.category_ids == [cat1, cat2]
    assert len(product_in.category_ids) == 2


def test_product_create_legacy_category_id_supported():
    cat = uuid4()
    product_in = ProductCreate(
        name="Single Category Product",
        slug="single-category-product",
        seo_title="Single Category Product | Zelqa",
        price=Decimal("499.00"),
        category_id=cat,
    )
    assert product_in.category_ids == [cat]


def test_product_materials_validation():
    product_in = ProductCreate(
        name="Material Product",
        slug="material-product",
        seo_title="Material Product | Zelqa",
        price=Decimal("299.00"),
        materials=[
            {"title": "Metal", "note": "925 Sterling Silver with Rhodium Plating"},
            {"title": "Gemstone", "note": "AAAAA Grade Cubic Zirconia"},
        ],
    )
    assert len(product_in.materials) == 2
    assert product_in.materials[0].title == "Metal"
    assert product_in.materials[0].note == "925 Sterling Silver with Rhodium Plating"
    assert product_in.materials[1].title == "Gemstone"
    assert product_in.materials[1].note == "AAAAA Grade Cubic Zirconia"


def test_product_materials_json_string_parsing():
    import json
    raw_materials = json.dumps([
        {"title": "Base", "note": "Recycled silver"},
    ])
    product_in = ProductCreate(
        name="JSON Material Product",
        slug="json-material-product",
        seo_title="JSON Material Product | Zelqa",
        price=Decimal("199.00"),
        materials=raw_materials,
    )
    assert len(product_in.materials) == 1
    assert product_in.materials[0].title == "Base"
    assert product_in.materials[0].note == "Recycled silver"


def test_product_negative_price_rejected():
    category_id = uuid4()
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Invalid Product",
            slug="invalid-product",
            seo_title="Invalid Product",
            price=Decimal("-10.00"),
            category_ids=[category_id],
        )


def test_product_sort_by_values():
    assert ProductSortBy.PRICE_ASC.value == "price_asc"
    assert ProductSortBy.PRICE_DESC.value == "price_desc"
    assert ProductSortBy.NEWEST.value == "newest"
    assert ProductSortBy.OLDEST.value == "oldest"
    assert ProductSortBy.NAME_ASC.value == "name_asc"
    assert ProductSortBy.NAME_DESC.value == "name_desc"
