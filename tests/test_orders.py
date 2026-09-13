from decimal import Decimal
from uuid import uuid4
import pytest
from pydantic import ValidationError

from app.schemas.order import (
    OrderCreate,
    OrderItemResponse,
    OrderStatus,
    OrderStatusUpdate,
    PaymentStatus,
    PaymentStatusUpdate,
)
from app.services.order_service import VALID_STATUS_TRANSITIONS


def test_order_status_enums():
    assert OrderStatus.PENDING.value == "pending"
    assert OrderStatus.CONFIRMED.value == "confirmed"
    assert OrderStatus.PROCESSING.value == "processing"
    assert OrderStatus.SHIPPED.value == "shipped"
    assert OrderStatus.DELIVERED.value == "delivered"
    assert OrderStatus.CANCELLED.value == "cancelled"


def test_payment_status_enums():
    assert PaymentStatus.PENDING.value == "pending"
    assert PaymentStatus.PAID.value == "paid"
    assert PaymentStatus.FAILED.value == "failed"
    assert PaymentStatus.REFUNDED.value == "refunded"


def test_valid_status_transitions_rules():
    assert "confirmed" in VALID_STATUS_TRANSITIONS["pending"]
    assert "cancelled" in VALID_STATUS_TRANSITIONS["pending"]
    assert "processing" in VALID_STATUS_TRANSITIONS["confirmed"]
    assert "shipped" in VALID_STATUS_TRANSITIONS["processing"]
    assert "delivered" in VALID_STATUS_TRANSITIONS["shipped"]
    assert len(VALID_STATUS_TRANSITIONS["delivered"]) == 0
    assert len(VALID_STATUS_TRANSITIONS["cancelled"]) == 0


def test_order_create_schema():
    address_id = uuid4()
    order_in = OrderCreate(address_id=address_id, payment_method="credit_card")
    assert order_in.address_id == address_id
    assert order_in.payment_method == "credit_card"


def test_order_item_response():
    item_id = uuid4()
    prod_id = uuid4()
    item = OrderItemResponse(
        id=item_id,
        product_id=prod_id,
        product_name="India Flag Ring",
        product_image_url="https://example.com/ring.jpg",
        quantity=2,
        unit_price=Decimal("999.00"),
        subtotal=Decimal("1998.00")
    )
    assert item.product_name == "India Flag Ring"
    assert item.subtotal == Decimal("1998.00")
