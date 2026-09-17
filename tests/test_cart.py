from decimal import Decimal
from uuid import uuid4
import pytest
from pydantic import ValidationError

from app.schemas.cart import (
    ApplyCouponRequest,
    BillCartItemInput,
    BillItemDetail,
    CartItemCreate,
    CartItemResponse,
    CartItemUpdate,
    CartProductSnapshot,
    CartResponse,
    LiveBillRequest,
    LiveBillResponse,
)


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


def test_cart_item_response_with_persisted_offer_details():
    prod_id = uuid4()
    item_id = uuid4()
    offer_id = uuid4()

    snapshot = CartProductSnapshot(
        id=prod_id,
        name="Sapphire Necklace",
        main_image_url="https://example.com/necklace.jpg",
        price=Decimal("500.00"),
        is_active=True,
        original_price=Decimal("500.00"),
        discount_amount=Decimal("50.00"),
        discounted_price=Decimal("450.00"),
        final_price=Decimal("450.00"),
        offer_id=offer_id
    )

    cart_item = CartItemResponse(
        id=item_id,
        product=snapshot,
        quantity=2,
        subtotal=Decimal("900.00"),
        offer_id=offer_id,
        unit_price=Decimal("500.00"),
        discount_type="percentage",
        discount_value=Decimal("10.00"),
        discount_amount=Decimal("50.00"),
        final_unit_price=Decimal("450.00"),
        total_price=Decimal("900.00")
    )

    assert cart_item.offer_id == offer_id
    assert cart_item.unit_price == Decimal("500.00")
    assert cart_item.discount_type == "percentage"
    assert cart_item.discount_value == Decimal("10.00")
    assert cart_item.discount_amount == Decimal("50.00")
    assert cart_item.final_unit_price == Decimal("450.00")
    assert cart_item.total_price == Decimal("900.00")


def test_cart_response_with_persisted_coupon_and_totals():
    cart_id = uuid4()
    cart = CartResponse(
        id=cart_id,
        items=[],
        total_items=0,
        coupon_code="ZELQA10",
        coupon_discount_type="percentage",
        coupon_discount_value=Decimal("10.00"),
        coupon_discount_amount=Decimal("50.00"),
        subtotal=Decimal("500.00"),
        total_discount=Decimal("50.00"),
        shipping_amount=Decimal("0.00"),
        total_amount=Decimal("450.00")
    )

    assert cart.coupon_code == "ZELQA10"
    assert cart.coupon_discount_type == "percentage"
    assert cart.coupon_discount_value == Decimal("10.00")
    assert cart.coupon_discount_amount == Decimal("50.00")
    assert cart.subtotal == Decimal("500.00")
    assert cart.total_discount == Decimal("50.00")
    assert cart.shipping_amount == Decimal("0.00")
    assert cart.total_amount == Decimal("450.00")
    assert cart.final_amount == Decimal("450.00")


def test_apply_coupon_request_validation():
    req = ApplyCouponRequest(coupon_code="DISCOUNT20")
    assert req.coupon_code == "DISCOUNT20"

    with pytest.raises(ValidationError):
        ApplyCouponRequest(coupon_code="")


def test_live_bill_response_structure():
    item_detail = BillItemDetail(
        product_id=uuid4(),
        product_name="Silver Bracelet",
        product_image_url="https://example.com/bracelet.jpg",
        quantity=2,
        original_unit_price=Decimal("100.00"),
        product_discount_unit=Decimal("10.00"),
        final_unit_price=Decimal("90.00"),
        gross_subtotal=Decimal("200.00"),
        product_discount_total=Decimal("20.00"),
        net_subtotal=Decimal("180.00")
    )

    bill = LiveBillResponse(
        items=[item_detail],
        total_items=2,
        items_count=1,
        subtotal_amount=Decimal("200.00"),
        product_discount_amount=Decimal("20.00"),
        net_items_amount=Decimal("180.00"),
        coupon_code="SAVE10",
        is_coupon_applied=True,
        coupon_discount_amount=Decimal("18.00"),
        coupon_message="Coupon applied successfully",
        delivery_charge=Decimal("0.00"),
        is_free_delivery=True,
        total_discount_amount=Decimal("38.00"),
        total_savings_amount=Decimal("38.00"),
        total_savings_percentage=Decimal("19.00"),
        total_amount=Decimal("162.00"),
        currency="USD"
    )

    assert bill.total_items == 2
    assert bill.subtotal_amount == Decimal("200.00")
    assert bill.product_discount_amount == Decimal("20.00")
    assert bill.net_items_amount == Decimal("180.00")
    assert bill.coupon_discount_amount == Decimal("18.00")
    assert bill.total_amount == Decimal("162.00")
    assert bill.is_coupon_applied is True
