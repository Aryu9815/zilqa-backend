from uuid import uuid4
import pytest
from pydantic import ValidationError

from app.schemas.product_size import (
    ProductSizeCreate,
    ProductSizeUpdate,
    ProductSizeResponse,
    ProductSizesFlowResponse,
)
from app.schemas.cart import (
    CartItemCreate,
    CartItemUpdate,
    CartItemResponse,
    CartProductSnapshot,
)
from decimal import Decimal


def test_product_size_create_schema():
    cat_id = uuid4()
    size_in = ProductSizeCreate(
        name="M",
        category_id=cat_id,
        display_order=2,
        is_active=True
    )
    assert size_in.name == "M"
    assert size_in.category_id == cat_id
    assert size_in.display_order == 2
    assert size_in.is_active is True


def test_product_size_empty_name_rejected():
    with pytest.raises(ValidationError):
        ProductSizeCreate(name="")


def test_product_size_update_schema():
    size_update = ProductSizeUpdate(
        name="L",
        display_order=3,
        is_active=False
    )
    assert size_update.name == "L"
    assert size_update.display_order == 3
    assert size_update.is_active is False
    assert size_update.category_id is None


def test_cart_item_create_with_size():
    prod_id = uuid4()
    item_in = CartItemCreate(
        product_id=prod_id,
        quantity=2,
        size="18mm"
    )
    assert item_in.product_id == prod_id
    assert item_in.quantity == 2
    assert item_in.size == "18mm"


def test_cart_item_update_with_size():
    item_update = CartItemUpdate(
        quantity=3,
        size="20mm"
    )
    assert item_update.quantity == 3
    assert item_update.size == "20mm"


def test_cart_item_response_includes_size():
    item_res = CartItemResponse(
        id=uuid4(),
        product=CartProductSnapshot(
            id=uuid4(),
            name="Classic Pearl Ring",
            main_image_url="https://example.com/ring.jpg",
            price=Decimal("150.00")
        ),
        quantity=1,
        size="16mm",
        subtotal=Decimal("150.00")
    )
    assert item_res.size == "16mm"
    assert item_res.quantity == 1


def test_product_size_country_code_normalization():
    # Whitespace and lowercase should be stripped and uppercased
    s1 = ProductSizeCreate(name="7", country_code=" in ")
    assert s1.country_code == "IN"

    # Blank strings should become None
    s2 = ProductSizeCreate(name="8", country_code="")
    assert s2.country_code is None

    s3 = ProductSizeCreate(name="9", country_code="   ")
    assert s3.country_code is None

    # None should remain None
    s4 = ProductSizeCreate(name="10", country_code=None)
    assert s4.country_code is None

    # Update schema normalization
    u1 = ProductSizeUpdate(country_code="us")
    assert u1.country_code == "US"

    u2 = ProductSizeUpdate(country_code="  ")
    assert u2.country_code is None


def test_product_sizes_flow_schema():
    flow = ProductSizesFlowResponse(
        has_country_codes=True,
        available_countries=["IN", "US", "UK"],
        selected_country_code="IN",
        sizes=[]
    )
    assert flow.has_country_codes is True
    assert flow.available_countries == ["IN", "US", "UK"]
    assert flow.selected_country_code == "IN"
    assert flow.sizes == []


@pytest.mark.asyncio
async def test_product_size_service_flow_with_country_codes(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock
    from datetime import datetime, timezone
    from app.services.product_size_service import product_size_service
    from app.repositories.product_size_repository import product_size_repository

    cat_id = uuid4()
    mock_db = AsyncMock()

    # Mock available countries returning ["IN", "US"]
    monkeypatch.setattr(
        product_size_repository,
        "get_available_countries",
        AsyncMock(return_value=["IN", "US"])
    )

    # Mock size record
    mock_record = MagicMock()
    mock_record.id = uuid4()
    mock_record.name = "18"
    mock_record.category_id = cat_id
    mock_record.country_code = "IN"
    mock_record.display_order = 1
    mock_record.is_active = True
    mock_record.is_deleted = False
    mock_record.created_at = datetime.now(timezone.utc)
    mock_record.updated_at = datetime.now(timezone.utc)
    mock_record.category = None

    list_sizes_mock = AsyncMock(return_value=([mock_record], 1))
    monkeypatch.setattr(product_size_repository, "list_sizes", list_sizes_mock)

    # 1. Flow when no country_code is provided -> should pick first available ("IN")
    res1 = await product_size_service.get_sizes_flow(
        db=mock_db,
        category_id=cat_id,
        country_code=None,
        is_active=True
    )
    assert res1.has_country_codes is True
    assert res1.available_countries == ["IN", "US"]
    assert res1.selected_country_code == "IN"
    assert len(res1.sizes) == 1
    assert res1.sizes[0].country_code == "IN"
    list_sizes_mock.assert_called_with(
        db=mock_db,
        category_id=cat_id,
        country_code="IN",
        is_active_only=True,
        include_deleted=False,
        page=1,
        limit=100
    )

    # 2. Flow when specific country_code is requested ("us") -> normalized to "US"
    res2 = await product_size_service.get_sizes_flow(
        db=mock_db,
        category_id=cat_id,
        country_code="us",
        is_active=True
    )
    assert res2.has_country_codes is True
    assert res2.selected_country_code == "US"
    list_sizes_mock.assert_called_with(
        db=mock_db,
        category_id=cat_id,
        country_code="US",
        is_active_only=True,
        include_deleted=False,
        page=1,
        limit=100
    )


@pytest.mark.asyncio
async def test_product_size_service_flow_without_country_codes(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock
    from datetime import datetime, timezone
    from app.services.product_size_service import product_size_service
    from app.repositories.product_size_repository import product_size_repository

    cat_id = uuid4()
    mock_db = AsyncMock()

    # Category has no country codes
    monkeypatch.setattr(
        product_size_repository,
        "get_available_countries",
        AsyncMock(return_value=[])
    )

    mock_record = MagicMock()
    mock_record.id = uuid4()
    mock_record.name = "Free Size"
    mock_record.category_id = cat_id
    mock_record.country_code = None
    mock_record.display_order = 0
    mock_record.is_active = True
    mock_record.is_deleted = False
    mock_record.created_at = datetime.now(timezone.utc)
    mock_record.updated_at = datetime.now(timezone.utc)
    mock_record.category = None

    list_sizes_mock = AsyncMock(return_value=([mock_record], 1))
    monkeypatch.setattr(product_size_repository, "list_sizes", list_sizes_mock)

    res = await product_size_service.get_sizes_flow(
        db=mock_db,
        category_id=cat_id,
        country_code=None,
        is_active=True
    )

    assert res.has_country_codes is False
    assert res.available_countries == []
    assert res.selected_country_code is None
    assert len(res.sizes) == 1
    assert res.sizes[0].name == "Free Size"
    list_sizes_mock.assert_called_with(
        db=mock_db,
        category_id=cat_id,
        country_code=None,
        is_active_only=True,
        include_deleted=False,
        page=1,
        limit=100
    )

