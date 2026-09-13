from decimal import Decimal
from uuid import uuid4
import pytest
from pydantic import ValidationError

from app.schemas.cart import CartItemCreate, CartItemResponse, CartItemUpdate, CartProductSnapshot, CartResponse


def test_cart_item_quantity_validation():
    prod_id = uuid4()
    item = CartItemCreate(product_id=prod_id, quantity=2)
    assert item.quantity == 2

    # Zero or negative quantity should fail
    with pytest.raises(ValidationError):
        CartItemCreate(product_id=prod_id, quantity=0)

    with pytest.raises(ValidationError):
        CartItemCreate(product_id=prod_id, quantity=-5)


def test_cart_response_computation():
    prod_id = uuid4()
    item_id = uuid4()
    cart_id = uuid4()

    snapshot = CartProductSnapshot(
        id=prod_id,
        name="Test Ring",
        main_image_url="https://example.com/ring.jpg",
        price=Decimal("999.00"),
        is_active=True
    )

    cart_item = CartItemResponse(
        id=item_id,
        product=snapshot,
        quantity=2,
        subtotal=Decimal("1998.00")
    )

    cart = CartResponse(
        id=cart_id,
        items=[cart_item],
        total_items=2,
        subtotal=Decimal("1998.00")
    )

    assert cart.total_items == 2
    assert cart.subtotal == Decimal("1998.00")
    assert len(cart.items) == 1
