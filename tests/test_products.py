from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import UUID, uuid4
import pytest
from pydantic import ValidationError

from app.core.exceptions import BadRequestException
from app.schemas.product import (
    ProductCreate,
    ProductMaterial,
    ProductResponse,
    ProductSortBy,
    ProductUpdate,
    ProductVariantBrief,
)
from app.services.product_service import product_service


def test_product_create_validation_with_category_ids():
    cat1 = uuid4()
    cat2 = uuid4()
    product_in = ProductCreate(
        name="India Flag Ring",
        variant_name="Silver",
        slug="india-flag-ring",
        seo_title="India Flag Ring | Zelqa",
        price=Decimal("999.00"),
        category_ids=[cat1, cat2],
        description="Sterling Silver ring",
        is_active=True,
    )
    assert product_in.name == "India Flag Ring"
    assert product_in.variant_name == "Silver"
    assert product_in.price == Decimal("999.00")
    assert product_in.category_ids == [cat1, cat2]
    assert len(product_in.category_ids) == 2
    assert product_in.variants == []


def test_product_create_legacy_category_id_supported():
    cat = uuid4()
    product_in = ProductCreate(
        name="Single Category Product",
        variant_name="Standard",
        slug="single-category-product",
        seo_title="Single Category Product | Zelqa",
        price=Decimal("499.00"),
        category_id=cat,
    )
    assert product_in.category_ids == [cat]
    assert product_in.variant_name == "Standard"


def test_product_variant_name_compulsory():
    # variant_name is missing
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Ring Without Variant Name",
            slug="ring-without-variant-name",
            seo_title="Ring | Zelqa",
            price=Decimal("499.00"),
        )

    # variant_name is empty string
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Ring With Empty Variant Name",
            variant_name="",
            slug="ring-with-empty-variant-name",
            seo_title="Ring | Zelqa",
            price=Decimal("499.00"),
        )


def test_product_variants_validation():
    var1 = uuid4()
    var2 = uuid4()
    product_in = ProductCreate(
        name="Gold Necklace",
        variant_name="18K Yellow Gold",
        slug="gold-necklace",
        seo_title="Gold Necklace | Zelqa",
        price=Decimal("1599.00"),
        variants=[var1, var2],
    )
    assert product_in.variants == [var1, var2]


def test_product_variants_json_string_parsing():
    import json
    var1 = uuid4()
    var2 = uuid4()
    raw_variants = json.dumps([str(var1), str(var2)])
    product_in = ProductCreate(
        name="JSON Variants Product",
        variant_name="Rose Gold",
        slug="json-variants-product",
        seo_title="JSON Variants Product | Zelqa",
        price=Decimal("199.00"),
        variants=raw_variants,
    )
    assert len(product_in.variants) == 2
    assert product_in.variants[0] == var1
    assert product_in.variants[1] == var2


def test_product_materials_validation():
    product_in = ProductCreate(
        name="Material Product",
        variant_name="Default",
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
        variant_name="Default",
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
            variant_name="Default",
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


@pytest.mark.asyncio
async def test_bidirectional_variant_sync():
    prod_a_id = uuid4()
    prod_b_id = uuid4()
    prod_c_id = uuid4()

    mock_db = AsyncMock()

    with patch("app.services.product_service.product_repository") as mock_repo:
        mock_repo.add_variant_to_product = AsyncMock()
        mock_repo.remove_variant_from_product = AsyncMock()

        # Sync: Product A adds variant B (A -> [B])
        await product_service._sync_bidirectional_variants(
            db=mock_db,
            product_id=prod_a_id,
            old_variant_ids=[],
            new_variant_ids=[prod_b_id]
        )
        # Should add A to B
        mock_repo.add_variant_to_product.assert_awaited_once_with(mock_db, prod_b_id, prod_a_id)

        mock_repo.add_variant_to_product.reset_mock()
        mock_repo.remove_variant_from_product.reset_mock()

        # Sync: Product A updates from [B] to [C]
        await product_service._sync_bidirectional_variants(
            db=mock_db,
            product_id=prod_a_id,
            old_variant_ids=[prod_b_id],
            new_variant_ids=[prod_c_id]
        )
        # Should remove A from B and add A to C
        mock_repo.remove_variant_from_product.assert_awaited_once_with(mock_db, prod_b_id, prod_a_id)
        mock_repo.add_variant_to_product.assert_awaited_once_with(mock_db, prod_c_id, prod_a_id)


@pytest.mark.asyncio
async def test_update_product_self_variant_rejected():
    prod_a_id = uuid4()
    mock_db = AsyncMock()

    with patch("app.services.product_service.product_repository") as mock_repo:
        mock_repo.get_by_id = AsyncMock(return_value=MagicMock(id=prod_a_id, variants=[]))
        update_in = ProductUpdate(variants=[prod_a_id])

        with pytest.raises(BadRequestException) as exc_info:
            await product_service.update_product(mock_db, prod_a_id, update_in)
        assert exc_info.value.error_code == "INVALID_VARIANT_PRODUCT"
