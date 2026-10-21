from uuid import uuid4
import pytest
from pydantic import ValidationError

from app.schemas.product_size import (
    ProductSizeCreate,
    ProductSizeUpdate,
    ProductSizeResponse,
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
