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


def test_cart_response_includes_country_and_currency():
    cart = CartResponse(
        id=uuid4(),
        currency="INR",
        country_code="IN",
        total_items=1,
        subtotal=Decimal("1000.00"),
        total_amount=Decimal("1000.00")
    )
    assert cart.currency == "INR"
    assert cart.country_code == "IN"


def test_live_bill_response_includes_country_and_currency():
    bill = LiveBillResponse(
        currency="INR",
        country_code="IN",
        country_name="India",
        exchange_rate=Decimal("83.50"),
        exchange_available=True,
        total_amount=Decimal("5000.00")
    )
    assert bill.currency == "INR"
    assert bill.country_code == "IN"
    assert bill.country_name == "India"
    assert bill.exchange_rate == Decimal("83.50")
    assert bill.exchange_available is True


@pytest.mark.asyncio
async def test_calculate_live_bill_uses_user_country(monkeypatch):
    from unittest.mock import AsyncMock
    from app.services.cart_service import cart_service
    from app.repositories.user_repository import user_repository
    from app.repositories.offer_repository import offer_repository
    from app.repositories.product_repository import product_repository
    from app.repositories.country_repository import country_repository
    from app.schemas.cart import LiveBillRequest, BillCartItemInput

    mock_user_id = uuid4()
    mock_prod_id = uuid4()
    mock_user = {
        "id": mock_user_id,
        "name": "Test User",
        "email": "test@example.com",
        "country_code": "IN"
    }

    mock_country = {
        "code": "IN",
        "name": "India",
        "rate_from_usd": Decimal("83.50"),
        "exchange_available": True
    }

    mock_product = {
        "id": mock_prod_id,
        "name": "Solitaire Ring",
        "price": Decimal("100.00"),
        "main_image_url": "https://example.com/ring.jpg",
        "is_active": True,
        "is_deleted": False
    }

    monkeypatch.setattr(user_repository, "get_by_id", AsyncMock(return_value=mock_user))
    monkeypatch.setattr(country_repository, "get_by_code", AsyncMock(return_value=mock_country))
    monkeypatch.setattr(product_repository, "get_by_ids", AsyncMock(return_value=[mock_product]))
    monkeypatch.setattr(offer_repository, "get_active_offers", AsyncMock(return_value=[]))

    mock_db = AsyncMock()
    req = LiveBillRequest(items=[BillCartItemInput(product_id=mock_prod_id, quantity=1)])
    bill = await cart_service.calculate_live_bill(db=mock_db, user_id=mock_user_id, req=req)

    assert bill.country_code == "IN"
    assert bill.country_name == "India"
    assert bill.currency == "INR"
    assert bill.exchange_available is True
    assert bill.exchange_rate == Decimal("83.50")
    # Subtotal in INR: 100 * 83.50 = 8350.00
    assert bill.subtotal_amount == Decimal("8350.00")
    assert bill.items[0].original_unit_price == Decimal("8350.00")


@pytest.mark.asyncio
async def test_order_pricing_calculated_in_user_currency(monkeypatch):
    from unittest.mock import AsyncMock
    from app.services.order_service import order_service
    from app.repositories.user_repository import user_repository
    from app.repositories.cart_repository import cart_repository
    from app.repositories.product_repository import product_repository
    from app.repositories.country_repository import country_repository
    from app.repositories.offer_repository import offer_repository

    mock_user_id = uuid4()
    mock_cart_id = uuid4()
    mock_prod_id = uuid4()

    mock_user = {
        "id": mock_user_id,
        "name": "Test User",
        "email": "test@example.com",
        "country_code": "IN"
    }

    mock_country = {
        "code": "IN",
        "name": "India",
        "rate_from_usd": Decimal("83.50"),
        "exchange_available": True
    }

    mock_cart = {
        "id": mock_cart_id,
        "user_id": mock_user_id,
        "coupon_code": None
    }

    mock_cart_item = {
        "id": uuid4(),
        "cart_id": mock_cart_id,
        "product_id": mock_prod_id,
        "quantity": 2,
        "product_name": "Diamond Ring"
    }

    mock_product = {
        "id": mock_prod_id,
        "name": "Diamond Ring",
        "price": Decimal("50.00"),
        "main_image_url": "https://example.com/ring.jpg",
        "is_active": True,
        "is_deleted": False
    }

    monkeypatch.setattr(user_repository, "get_by_id", AsyncMock(return_value=mock_user))
    monkeypatch.setattr(country_repository, "get_by_code", AsyncMock(return_value=mock_country))
    monkeypatch.setattr(cart_repository, "get_or_create_cart", AsyncMock(return_value=mock_cart))
    monkeypatch.setattr(cart_repository, "get_cart_items_with_products", AsyncMock(return_value=[mock_cart_item]))
    monkeypatch.setattr(product_repository, "get_by_id", AsyncMock(return_value=mock_product))
    monkeypatch.setattr(offer_repository, "get_active_offers", AsyncMock(return_value=[]))

    mock_db = AsyncMock()
    pricing = await order_service._calculate_cart_pricing(mock_db, mock_user_id)

    assert pricing["currency"] == "INR"
    assert pricing["country_code"] == "IN"
    # Price in USD: $50 * 2 = $100. In INR: 100 * 83.50 = 8350.00
    assert pricing["subtotal"] == Decimal("8350.00")



