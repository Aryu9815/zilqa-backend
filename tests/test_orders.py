from decimal import Decimal
from uuid import uuid4
import pytest
from pydantic import ValidationError

from app.core.razorpay import razorpay_service
from app.schemas.order import (
    OrderCreate,
    OrderItemResponse,
    OrderResponse,
    OrderStatus,
    OrderStatusUpdate,
    PaymentStatus,
    PaymentStatusUpdate,
    RazorpayOrderCreateRequest,
    RazorpayOrderResponse,
    RazorpayPaymentVerifyRequest,
)
from app.services.order_service import VALID_STATUS_TRANSITIONS


def test_order_status_enums():
    assert OrderStatus.PENDING.value == "pending"
    assert OrderStatus.CONFIRMED.value == "confirmed"
    assert OrderStatus.PROCESSING.value == "processing"
    assert OrderStatus.SHIPPED.value == "shipped"
    assert OrderStatus.DELIVERED.value == "delivered"
    assert OrderStatus.CANCELLED.value == "cancelled"
    assert OrderStatus.RETURNED.value == "returned"


def test_payment_status_enums():
    assert PaymentStatus.PENDING.value == "pending"
    assert PaymentStatus.PAID.value == "paid"
    assert PaymentStatus.FAILED.value == "failed"
    assert PaymentStatus.REFUNDED.value == "refunded"
    assert PaymentStatus.PARTIALLY_REFUNDED.value == "partially_refunded"


def test_valid_status_transitions_rules():
    assert "confirmed" in VALID_STATUS_TRANSITIONS["pending"]
    assert "cancelled" in VALID_STATUS_TRANSITIONS["pending"]
    assert "processing" in VALID_STATUS_TRANSITIONS["confirmed"]
    assert "shipped" in VALID_STATUS_TRANSITIONS["processing"]
    assert "delivered" in VALID_STATUS_TRANSITIONS["shipped"]
    assert "returned" in VALID_STATUS_TRANSITIONS["delivered"]
    assert len(VALID_STATUS_TRANSITIONS["cancelled"]) == 0
    assert len(VALID_STATUS_TRANSITIONS["returned"]) == 0


def test_order_create_schema():
    address_id = uuid4()
    order_in = OrderCreate(
        address_id=address_id,
        payment_method="razorpay",
        coupon_code="ZELQA10",
        razorpay_order_id="order_12345",
        razorpay_payment_id="pay_12345",
        razorpay_signature="sig_12345"
    )
    assert order_in.address_id == address_id
    assert order_in.payment_method == "razorpay"
    assert order_in.coupon_code == "ZELQA10"
    assert order_in.razorpay_order_id == "order_12345"


def test_razorpay_schemas():
    address_id = uuid4()
    create_req = RazorpayOrderCreateRequest(address_id=address_id, coupon_code="SAVE10")
    assert create_req.address_id == address_id
    assert create_req.coupon_code == "SAVE10"

    resp = RazorpayOrderResponse(
        razorpay_order_id="order_rzp_123",
        amount=199900,
        currency="INR",
        key_id="rzp_test_key",
        subtotal=Decimal("2499.00"),
        discount_amount=Decimal("500.00"),
        shipping_amount=Decimal("0.00"),
        total_amount=Decimal("1999.00"),
        coupon_code="SAVE10"
    )
    assert resp.amount == 199900
    assert resp.total_amount == Decimal("1999.00")

    verify_req = RazorpayPaymentVerifyRequest(
        razorpay_order_id="order_rzp_123",
        razorpay_payment_id="pay_rzp_456",
        razorpay_signature="sig_abc123456789"
    )
    assert verify_req.razorpay_payment_id == "pay_rzp_456"


def test_order_item_response_with_offer_fields():
    item_id = uuid4()
    prod_id = uuid4()
    item = OrderItemResponse(
        id=item_id,
        product_id=prod_id,
        product_name="India Flag Ring",
        product_image_url="https://example.com/ring.jpg",
        price=Decimal("1000.00"),
        quantity=2,
        unit_price=Decimal("1000.00"),
        discount_type="percentage",
        discount_value=Decimal("20.00"),
        discount_amount=Decimal("200.00"),
        final_unit_price=Decimal("800.00"),
        total_price=Decimal("1600.00")
    )
    assert item.product_name == "India Flag Ring"
    assert item.price == Decimal("1000.00")
    assert item.discount_amount == Decimal("200.00")
    assert item.final_unit_price == Decimal("800.00")
    assert item.total_price == Decimal("1600.00")
    assert item.subtotal == Decimal("1600.00")  # Populated alias


@pytest.mark.asyncio
async def test_razorpay_service_mock_order_creation():
    order_data = await razorpay_service.create_order(
        amount=Decimal("1500.00"),
        currency="INR"
    )
    assert order_data["amount"] == 150000
    assert order_data["currency"] == "INR"
    assert "id" in order_data


def test_razorpay_service_signature_verification():
    # In mock/test sandbox mode without live keys:
    valid_mock = razorpay_service.verify_payment_signature(
        razorpay_order_id="order_mock_12345",
        razorpay_payment_id="pay_mock_12345",
        razorpay_signature="mock_sig_12345"
    )
    assert valid_mock is True

    # Empty signature fails
    invalid_empty = razorpay_service.verify_payment_signature(
        razorpay_order_id="order_123",
        razorpay_payment_id="pay_123",
        razorpay_signature=""
    )
    assert invalid_empty is False


from app.main import app
from app.core.dependencies import require_authenticated_user


@pytest.mark.asyncio
async def test_api_create_razorpay_order_endpoint(client, monkeypatch):
    test_uid = uuid4()
    app.dependency_overrides[require_authenticated_user] = lambda: {
        "id": test_uid, "role": "customer", "name": "Test User", "email": "test@example.com", "is_active": True
    }
    try:
        mock_rzp_resp = RazorpayOrderResponse(
            razorpay_order_id="order_rzp_mock_999",
            amount=250000,
            currency="INR",
            key_id="rzp_key_test",
            subtotal=Decimal("3000.00"),
            discount_amount=Decimal("500.00"),
            shipping_amount=Decimal("0.00"),
            total_amount=Decimal("2500.00"),
            coupon_code="SAVE500"
        )

        from app.services.order_service import order_service
        async def mock_create(uid, req):
            return mock_rzp_resp

        monkeypatch.setattr(order_service, "create_razorpay_order", mock_create)

        resp = await client.post(
            "/api/v1/orders/create-razorpay-order",
            headers={"Authorization": "Bearer dummy_token"},
            json={
                "shipping_address": {
                    "full_name": "Test User",
                    "phone": "+919876543210",
                    "address_line_1": "123 Main St",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "postal_code": "400001"
                },
                "coupon_code": "SAVE500"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["razorpay_order_id"] == "order_rzp_mock_999"
        assert data["data"]["amount"] == 250000
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_verify_payment_and_complete_order_endpoint(client, monkeypatch):
    test_uid = uuid4()
    app.dependency_overrides[require_authenticated_user] = lambda: {
        "id": test_uid, "role": "customer", "name": "Test User", "email": "test@example.com", "is_active": True
    }
    try:
        order_id = uuid4()
        item_id = uuid4()
        mock_order = OrderResponse(
            id=order_id,
            user_id=test_uid,
            status="confirmed",
            payment_status="paid",
            subtotal=Decimal("2000.00"),
            discount_amount=Decimal("400.00"),
            shipping_amount=Decimal("0.00"),
            total_amount=Decimal("1600.00"),
            currency="INR",
            coupon_code=None,
            shipping_address={
                "full_name": "Test User",
                "phone": "+919876543210",
                "address_line_1": "123 Main St",
                "city": "Mumbai",
                "state": "Maharashtra",
                "postal_code": "400001"
            },
            razorpay_order_id="order_rzp_mock_999",
            razorpay_payment_id="pay_rzp_mock_999",
            razorpay_signature="mock_sig_valid",
            items=[
                OrderItemResponse(
                    id=item_id,
                    product_name="Silver Ring",
                    price=Decimal("2000.00"),
                    quantity=1,
                    unit_price=Decimal("2000.00"),
                    discount_type="percentage",
                    discount_value=Decimal("20.00"),
                    discount_amount=Decimal("400.00"),
                    final_unit_price=Decimal("1600.00"),
                    total_price=Decimal("1600.00")
                )
            ],
            created_at=pytest.importorskip("datetime").datetime.now(),
            updated_at=pytest.importorskip("datetime").datetime.now()
        )

        from app.services.order_service import order_service
        async def mock_verify(uid, req):
            return mock_order

        monkeypatch.setattr(order_service, "verify_and_complete_order", mock_verify)

        resp = await client.post(
            "/api/v1/orders/verify-payment",
            headers={"Authorization": "Bearer dummy_token"},
            json={
                "razorpay_order_id": "order_rzp_mock_999",
                "razorpay_payment_id": "pay_rzp_mock_999",
                "razorpay_signature": "mock_sig_valid"
            }
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["status"] == "confirmed"
        assert data["data"]["payment_status"] == "paid"
        assert len(data["data"]["items"]) == 1
        assert data["data"]["items"][0]["discount_amount"] == "400.00"
    finally:
        app.dependency_overrides.clear()

