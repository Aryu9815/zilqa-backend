from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
import pytest
from pydantic import ValidationError

from app.schemas.offer import (
    CouponValidateRequest,
    CouponValidateResponse,
    DiscountType,
    OfferBriefResponse,
    OfferCreate,
    OfferResponse,
    OfferType,
    OfferUpdate,
    normalize_offer_type,
)
from app.schemas.product import ProductResponse
from app.schemas.cart import CartProductSnapshot, CartResponse, CartItemResponse
from app.services.offer_service import offer_service


# =============================================================================
# 1. TEST STRICT VALIDATION OF THE 11 ALLOWED OFFER TYPES
# =============================================================================

ALLOWED_TYPES = [
    "Product Discount",
    "Category Discount",
    "Coupon Code",
    "Cart Discount",
    "Flash Sale",
    "First Order Discount",
    "Free Shipping",
    "Minimum Order Discount",
    "Limited-Time Offer",
    "Percentage Discount",
    "Fixed Amount Discount",
]


def test_all_11_allowed_offer_types_are_accepted():
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=7)

    for offer_type_str in ALLOWED_TYPES:
        coupon = "TESTCODE" if offer_type_str == "Coupon Code" else None
        disc_type = "percentage" if offer_type_str == "Percentage Discount" else "fixed"

        offer_in = OfferCreate(
            name=f"Test {offer_type_str}",
            offer_type=offer_type_str,  # type: ignore
            discount_type=disc_type,  # type: ignore
            discount_value=Decimal("10.00"),
            coupon_code=coupon,
            start_date=now,
            end_date=future,
        )
        assert offer_in.name == f"Test {offer_type_str}"
        assert offer_in.offer_type in list(OfferType)


def test_snake_case_offer_type_normalization():
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=7)

    test_cases = [
        ("product_discount", OfferType.PRODUCT_DISCOUNT),
        ("category_discount", OfferType.CATEGORY_DISCOUNT),
        ("coupon_code", OfferType.COUPON_CODE),
        ("cart_discount", OfferType.CART_DISCOUNT),
        ("flash_sale", OfferType.FLASH_SALE),
        ("first_order_discount", OfferType.FIRST_ORDER_DISCOUNT),
        ("free_shipping", OfferType.FREE_SHIPPING),
        ("minimum_order_discount", OfferType.MINIMUM_ORDER_DISCOUNT),
        ("limited_time_offer", OfferType.LIMITED_TIME_OFFER),
        ("percentage_discount", OfferType.PERCENTAGE_DISCOUNT),
        ("fixed_amount_discount", OfferType.FIXED_AMOUNT_DISCOUNT),
    ]

    for snake_str, expected_enum in test_cases:
        coupon = "SAVE10" if expected_enum == OfferType.COUPON_CODE else None
        disc_type = "percentage" if expected_enum == OfferType.PERCENTAGE_DISCOUNT else "fixed"

        offer_in = OfferCreate(
            name=f"Test {snake_str}",
            offer_type=snake_str,  # type: ignore
            discount_type=disc_type,  # type: ignore
            discount_value=Decimal("15.00"),
            coupon_code=coupon,
            start_date=now,
            end_date=future,
        )
        assert offer_in.offer_type == expected_enum


def test_invalid_offer_types_are_strictly_rejected():
    invalid_types = [
        "BOGO",
        "Buy 1 Get 1 Free",
        "Student Discount",
        "Employee Discount",
        "Summer Sale",
        "Volume Discount",
        "VIP Deal",
        "Random Discount",
        "",
        "unknown",
    ]

    now = datetime.now(timezone.utc)
    future = now + timedelta(days=7)

    for invalid in invalid_types:
        with pytest.raises(ValidationError) as exc_info:
            OfferCreate(
                name="Invalid Offer",
                offer_type=invalid,  # type: ignore
                discount_type=DiscountType.PERCENTAGE,
                discount_value=Decimal("10.00"),
                start_date=now,
                end_date=future,
            )
        assert "Only the following offer types are allowed" in str(exc_info.value)


# =============================================================================
# 2. TEST OFFER SCHEMA VALIDATION RULES
# =============================================================================

def test_offer_date_range_validation():
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=1)

    # end_date before start_date must fail
    with pytest.raises(ValidationError) as exc_info:
        OfferCreate(
            name="Invalid Dates",
            offer_type=OfferType.FLASH_SALE,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            start_date=now,
            end_date=past,
        )
    assert "end_date must be strictly after start_date" in str(exc_info.value)


def test_percentage_discount_cannot_exceed_100():
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=1)

    with pytest.raises(ValidationError) as exc_info:
        OfferCreate(
            name="Over 100 Percent",
            offer_type=OfferType.PERCENTAGE_DISCOUNT,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("105.00"),
            start_date=now,
            end_date=future,
        )
    assert "Percentage discount_value cannot exceed 100%" in str(exc_info.value)


def test_coupon_code_required_for_coupon_code_offer_type():
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=1)

    with pytest.raises(ValidationError) as exc_info:
        OfferCreate(
            name="Missing Code",
            offer_type=OfferType.COUPON_CODE,
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("50.00"),
            coupon_code=None,
            start_date=now,
            end_date=future,
        )
    assert "coupon_code is mandatory for 'Coupon Code' offer type" in str(exc_info.value)


# =============================================================================
# 3. TEST DISCOUNT CALCULATION ENGINE
# =============================================================================

def test_calculate_single_product_percentage_offer():
    prod_id = uuid4()
    price = Decimal("1000.00")

    mock_offer = {
        "id": uuid4(),
        "name": "20% Off Ring",
        "description": "Flash sale 20%",
        "offer_type": OfferType.FLASH_SALE.value,
        "discount_type": "percentage",
        "discount_value": Decimal("20.00"),
        "coupon_code": None,
        "minimum_order_amount": Decimal("0.00"),
        "maximum_discount_amount": None,
        "start_date": datetime.now(),
        "end_date": datetime.now() + timedelta(days=1),
        "product_ids": [prod_id],
    }

    offer_id, offer_data, disc_amt, disc_price, final_price = offer_service.calculate_single_product_offer(
        product_id=prod_id,
        price=price,
        active_offers=[mock_offer]
    )

    assert offer_id == mock_offer["id"]
    assert disc_amt == Decimal("200.00")
    assert disc_price == Decimal("800.00")
    assert final_price == Decimal("800.00")
    assert offer_data is not None
    assert offer_data.name == "20% Off Ring"


def test_calculate_percentage_offer_with_maximum_discount_cap():
    prod_id = uuid4()
    price = Decimal("5000.00")

    # 50% discount would be 2500, but capped at 500
    mock_offer = {
        "id": uuid4(),
        "name": "50% Off (Max 500)",
        "description": "Capped promo",
        "offer_type": OfferType.PRODUCT_DISCOUNT.value,
        "discount_type": "percentage",
        "discount_value": Decimal("50.00"),
        "coupon_code": None,
        "minimum_order_amount": Decimal("0.00"),
        "maximum_discount_amount": Decimal("500.00"),
        "start_date": datetime.now(),
        "end_date": datetime.now() + timedelta(days=1),
        "product_ids": [prod_id],
    }

    offer_id, _, disc_amt, disc_price, final_price = offer_service.calculate_single_product_offer(
        product_id=prod_id,
        price=price,
        active_offers=[mock_offer]
    )

    assert disc_amt == Decimal("500.00")
    assert final_price == Decimal("4500.00")


def test_calculate_product_discount_targeting_and_storewide():
    prod_1 = uuid4()
    prod_2 = uuid4()
    price = Decimal("1200.00")

    # Targeted offer only for prod_1
    mock_targeted_offer = {
        "id": uuid4(),
        "name": "Prod 1 25% Off",
        "description": "Product discount",
        "offer_type": OfferType.PRODUCT_DISCOUNT.value,
        "discount_type": "percentage",
        "discount_value": Decimal("25.00"),
        "coupon_code": None,
        "minimum_order_amount": Decimal("0.00"),
        "maximum_discount_amount": None,
        "start_date": datetime.now(),
        "end_date": datetime.now() + timedelta(days=1),
        "product_ids": [prod_1],
    }

    # Should match prod_1
    offer_id, _, disc_amt, _, final_price = offer_service.calculate_single_product_offer(
        product_id=prod_1,
        price=price,
        active_offers=[mock_targeted_offer]
    )
    assert offer_id == mock_targeted_offer["id"]
    assert disc_amt == Decimal("300.00")
    assert final_price == Decimal("900.00")

    # Should NOT match prod_2
    offer_id_none, _, disc_none, _, final_orig = offer_service.calculate_single_product_offer(
        product_id=prod_2,
        price=price,
        active_offers=[mock_targeted_offer]
    )
    assert offer_id_none is None
    assert disc_none == Decimal("0.00")
    assert final_orig == price

    # Storewide offer (product_ids is empty)
    mock_storewide_offer = {
        "id": uuid4(),
        "name": "Storewide 10% Off",
        "description": "Storewide discount",
        "offer_type": OfferType.PRODUCT_DISCOUNT.value,
        "discount_type": "percentage",
        "discount_value": Decimal("10.00"),
        "coupon_code": None,
        "minimum_order_amount": Decimal("0.00"),
        "maximum_discount_amount": None,
        "start_date": datetime.now(),
        "end_date": datetime.now() + timedelta(days=1),
        "product_ids": [],
    }

    offer_id_sw, _, disc_sw, _, final_sw = offer_service.calculate_single_product_offer(
        product_id=prod_2,
        price=price,
        active_offers=[mock_storewide_offer]
    )
    assert offer_id_sw == mock_storewide_offer["id"]
    assert disc_sw == Decimal("120.00")
    assert final_sw == Decimal("1080.00")


def test_highest_savings_offer_is_selected():
    prod_id = uuid4()
    price = Decimal("1000.00")

    offer_10_percent = {
        "id": uuid4(),
        "name": "10% Off",
        "offer_type": OfferType.LIMITED_TIME_OFFER.value,
        "discount_type": "percentage",
        "discount_value": Decimal("10.00"),
        "coupon_code": None,
        "minimum_order_amount": Decimal("0.00"),
        "maximum_discount_amount": None,
        "start_date": datetime.now(),
        "end_date": datetime.now() + timedelta(days=1),
        "product_ids": [prod_id],
    }

    offer_300_fixed = {
        "id": uuid4(),
        "name": "₹300 Flat Off",
        "offer_type": OfferType.FIXED_AMOUNT_DISCOUNT.value,
        "discount_type": "fixed",
        "discount_value": Decimal("300.00"),
        "coupon_code": None,
        "minimum_order_amount": Decimal("0.00"),
        "maximum_discount_amount": None,
        "start_date": datetime.now(),
        "end_date": datetime.now() + timedelta(days=1),
        "product_ids": [prod_id],
    }

    # 10% = 100 savings, 300 flat = 300 savings -> 300 flat should win
    offer_id, offer_data, disc_amt, _, final_price = offer_service.calculate_single_product_offer(
        product_id=prod_id,
        price=price,
        active_offers=[offer_10_percent, offer_300_fixed]
    )

    assert offer_id == offer_300_fixed["id"]
    assert disc_amt == Decimal("300.00")
    assert final_price == Decimal("700.00")


# =============================================================================
# 4. TEST PRODUCT RESPONSE OFFER ENRICHMENT
# =============================================================================

def test_product_response_contains_offer_data():
    prod_id = uuid4()
    offer_id = uuid4()

    brief = OfferBriefResponse(
        id=offer_id,
        name="Flash 20",
        offer_type=OfferType.FLASH_SALE.value,
        discount_type="percentage",
        discount_value=Decimal("20.00"),
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=1),
    )

    prod = ProductResponse(
        id=prod_id,
        name="Silver Peacock Ring",
        main_image_url="https://example.com/ring.jpg",
        price=Decimal("1000.00"),
        offer_id=offer_id,
        offer_data=brief,
        discount_amount=Decimal("200.00"),
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    assert prod.price == Decimal("1000.00")
    assert prod.discount_amount == Decimal("200.00")
    assert prod.discounted_price == Decimal("800.00")
    assert prod.final_price == Decimal("800.00")
    assert prod.offer_id == offer_id
    assert prod.offer_data.name == "Flash 20"


def test_product_response_defaults_when_no_offer():
    prod_id = uuid4()
    prod = ProductResponse(
        id=prod_id,
        name="Plain Silver Chain",
        main_image_url="https://example.com/chain.jpg",
        price=Decimal("1500.00"),
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    assert prod.price == Decimal("1500.00")
    assert prod.discount_amount == Decimal("0.00")
    assert prod.discounted_price == Decimal("1500.00")
    assert prod.final_price == Decimal("1500.00")
    assert prod.offer_id is None
    assert prod.offer_data is None


# =============================================================================
# 5. TEST CART SCHEMA ENRICHMENT WITH OFFERS
# =============================================================================

def test_cart_item_and_response_with_discount():
    prod_id = uuid4()
    offer_id = uuid4()

    snapshot = CartProductSnapshot(
        id=prod_id,
        name="Silver Ring",
        main_image_url="https://example.com/ring.jpg",
        price=Decimal("1000.00"),
        original_price=Decimal("1000.00"),
        discount_amount=Decimal("200.00"),
        offer_id=offer_id,
        is_active=True
    )

    assert snapshot.price == Decimal("1000.00")
    assert snapshot.original_price == Decimal("1000.00")
    assert snapshot.discount_amount == Decimal("200.00")
    assert snapshot.final_price == Decimal("800.00")

    cart_item = CartItemResponse(
        id=uuid4(),
        product=snapshot,
        quantity=2,
        subtotal=Decimal("1600.00")  # 800 * 2
    )

    cart = CartResponse(
        id=uuid4(),
        items=[cart_item],
        total_items=2,
        subtotal=Decimal("2000.00"),     # 1000 * 2
        total_discount=Decimal("400.00"), # 200 * 2
        final_amount=Decimal("1600.00")
    )

    assert cart.subtotal == Decimal("2000.00")
    assert cart.total_discount == Decimal("400.00")
    assert cart.final_amount == Decimal("1600.00")


# =============================================================================
# 6. TEST COUPON VALIDATION ENGINE RULES
# =============================================================================

@pytest.mark.asyncio
async def test_coupon_validation_invalid_code(monkeypatch):
    async def mock_get_coupon(code, is_active_only=True, connection=None):
        return None

    from app.repositories.offer_repository import offer_repository
    monkeypatch.setattr(offer_repository, "get_by_coupon_code", mock_get_coupon)

    res = await offer_service.validate_and_calculate_coupon("NONEXISTENT")
    assert not res.is_valid
    assert "invalid or expired" in res.message


@pytest.mark.asyncio
async def test_coupon_validation_min_order_amount(monkeypatch):
    now = datetime.now()
    mock_offer = {
        "id": uuid4(),
        "name": "Flat 200 on 1000",
        "description": "Min order 1000",
        "offer_type": OfferType.MINIMUM_ORDER_DISCOUNT.value,
        "discount_type": "fixed",
        "discount_value": Decimal("200.00"),
        "coupon_code": "MIN1000",
        "minimum_order_amount": Decimal("1000.00"),
        "maximum_discount_amount": None,
        "start_date": now - timedelta(days=1),
        "end_date": now + timedelta(days=1),
        "usage_limit": None,
        "used_count": 0,
        "is_active": True,
        "is_deleted": False,
        "product_ids": [],
    }

    from app.repositories.offer_repository import offer_repository
    async def mock_get(code, is_active_only=True, connection=None):
        return mock_offer

    monkeypatch.setattr(offer_repository, "get_by_coupon_code", mock_get)

    # Subtotal 500 is below 1000 -> invalid
    res_fail = await offer_service.validate_and_calculate_coupon("MIN1000", cart_subtotal=Decimal("500.00"))
    assert not res_fail.is_valid
    assert "minimum order amount" in res_fail.message

    # Subtotal 1500 meets threshold -> valid
    res_pass = await offer_service.validate_and_calculate_coupon("MIN1000", cart_subtotal=Decimal("1500.00"))
    assert res_pass.is_valid
    assert res_pass.discount_amount == Decimal("200.00")
    assert res_pass.final_amount == Decimal("1300.00")


@pytest.mark.asyncio
async def test_coupon_validation_first_order_discount(monkeypatch):
    now = datetime.now()
    mock_offer = {
        "id": uuid4(),
        "name": "First Order 15% Off",
        "description": "Welcome bonus",
        "offer_type": OfferType.FIRST_ORDER_DISCOUNT.value,
        "discount_type": "percentage",
        "discount_value": Decimal("15.00"),
        "coupon_code": "WELCOME15",
        "minimum_order_amount": Decimal("0.00"),
        "maximum_discount_amount": None,
        "start_date": now - timedelta(days=1),
        "end_date": now + timedelta(days=1),
        "usage_limit": None,
        "used_count": 0,
        "is_active": True,
        "is_deleted": False,
        "product_ids": [],
    }

    user_id = uuid4()
    from app.repositories.offer_repository import offer_repository
    async def mock_get(code, is_active_only=True, connection=None):
        return mock_offer

    async def mock_count_existing(uid, connection=None):
        return 2

    async def mock_count_zero(uid, connection=None):
        return 0

    monkeypatch.setattr(offer_repository, "get_by_coupon_code", mock_get)

    # User with prior orders -> rejected
    monkeypatch.setattr(offer_repository, "count_user_orders", mock_count_existing)
    res_existing_user = await offer_service.validate_and_calculate_coupon("WELCOME15", user_id=user_id, cart_subtotal=Decimal("1000.00"))
    assert not res_existing_user.is_valid
    assert "first order" in res_existing_user.message

    # User with 0 prior orders -> allowed
    monkeypatch.setattr(offer_repository, "count_user_orders", mock_count_zero)
    res_new_user = await offer_service.validate_and_calculate_coupon("WELCOME15", user_id=user_id, cart_subtotal=Decimal("1000.00"))
    assert res_new_user.is_valid
    assert res_new_user.discount_amount == Decimal("150.00")
    assert res_new_user.final_amount == Decimal("850.00")


# =============================================================================
# 7. TEST FASTAPI ENDPOINTS (PUBLIC & ADMIN)
# =============================================================================

from app.schemas.common import PaginatedResponse, PaginationMeta


@pytest.mark.asyncio
async def test_api_list_public_offers(client, monkeypatch):
    mock_offer = OfferResponse(
        id=uuid4(),
        name="Summer Flash Sale",
        offer_type=OfferType.FLASH_SALE.value,
        discount_type="percentage",
        discount_value=Decimal("20.00"),
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=5),
        is_active=True,
    )

    async def mock_list(*args, **kwargs):
        return PaginatedResponse(
            data=[mock_offer],
            pagination=PaginationMeta(total=1, page=1, limit=20, total_pages=1, has_next=False, has_prev=False)
        )

    monkeypatch.setattr(offer_service, "list_offers", mock_list)

    resp = await client.get("/api/v1/offers")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["name"] == "Summer Flash Sale"
    assert data["data"][0]["offer_type"] == "Flash Sale"


@pytest.mark.asyncio
async def test_api_validate_coupon_endpoint(client, monkeypatch):
    async def mock_validate(*args, **kwargs):
        return CouponValidateResponse(
            is_valid=True,
            message="Coupon applied!",
            coupon_code="ZELQA10",
            discount_amount=Decimal("100.00"),
            final_amount=Decimal("900.00")
        )

    monkeypatch.setattr(offer_service, "validate_and_calculate_coupon", mock_validate)

    resp = await client.post("/api/v1/offers/validate-coupon", json={
        "coupon_code": "ZELQA10",
        "cart_subtotal": "1000.00"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["discount_amount"] == "100.00"
    assert data["data"]["final_amount"] == "900.00"


from app.main import app
from app.core.dependencies import require_admin
from app.core.exceptions import ForbiddenException


@pytest.mark.asyncio
async def test_api_admin_create_offer_non_admin_forbidden(client):
    app.dependency_overrides[require_admin] = lambda: (_ for _ in ()).throw(
        ForbiddenException(message="Administrator privileges required", error_code="ADMIN_REQUIRED")
    )
    try:
        now = datetime.now()
        payload = {
            "name": "Unauthorized Offer",
            "offer_type": "Product Discount",
            "discount_type": "percentage",
            "discount_value": "10.00",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=2)).isoformat(),
        }
        resp = await client.post("/api/v1/admin/offers", json=payload)
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_admin_create_offer_invalid_type_rejected(client):
    app.dependency_overrides[require_admin] = lambda: {"id": uuid4(), "role": "admin", "name": "Admin"}
    try:
        now = datetime.now()
        payload = {
            "name": "Invalid Offer Type",
            "offer_type": "Completely Disallowed Type",
            "discount_type": "percentage",
            "discount_value": "10.00",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=2)).isoformat(),
        }
        resp = await client.post("/api/v1/admin/offers", json=payload)
        assert resp.status_code in (400, 422)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_admin_create_offer_success(client, monkeypatch):
    app.dependency_overrides[require_admin] = lambda: {"id": uuid4(), "role": "admin", "name": "Admin"}
    try:
        now = datetime.now()
        created_id = uuid4()
        mock_resp = OfferResponse(
            id=created_id,
            name="Festive Product Discount",
            offer_type=OfferType.PRODUCT_DISCOUNT.value,
            discount_type="percentage",
            discount_value=Decimal("15.00"),
            start_date=now,
            end_date=now + timedelta(days=7),
            is_active=True,
        )

        async def mock_create(offer_in):
            return mock_resp

        monkeypatch.setattr(offer_service, "create_offer", mock_create)

        payload = {
            "name": "Festive Product Discount",
            "offer_type": "Product Discount",
            "discount_type": "percentage",
            "discount_value": "15.00",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=7)).isoformat(),
        }
        resp = await client.post("/api/v1/admin/offers", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["id"] == str(created_id)
        assert data["data"]["offer_type"] == "Product Discount"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_admin_get_and_delete_offer(client, monkeypatch):
    app.dependency_overrides[require_admin] = lambda: {"id": uuid4(), "role": "admin", "name": "Admin"}
    try:
        target_id = uuid4()
        now = datetime.now()
        mock_resp = OfferResponse(
            id=target_id,
            name="Target Offer",
            offer_type=OfferType.FREE_SHIPPING.value,
            discount_type="fixed",
            discount_value=Decimal("0.00"),
            start_date=now,
            end_date=now + timedelta(days=7),
            is_active=True,
        )

        async def mock_get(oid, is_active_only=False):
            return mock_resp

        async def mock_delete(oid):
            return None

        monkeypatch.setattr(offer_service, "get_offer", mock_get)
        monkeypatch.setattr(offer_service, "delete_offer", mock_delete)

        # GET
        get_resp = await client.get(f"/api/v1/admin/offers/{target_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["name"] == "Target Offer"

        # DELETE
        del_resp = await client.delete(f"/api/v1/admin/offers/{target_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["message"] == "Offer deactivated successfully"
    finally:
        app.dependency_overrides.clear()



