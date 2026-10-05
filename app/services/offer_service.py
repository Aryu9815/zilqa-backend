from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.repositories.offer_repository import offer_repository
from app.repositories.product_repository import product_repository
from app.schemas.common import PaginatedResponse
from app.schemas.offer import (
    CouponValidateResponse,
    DiscountType,
    OfferBriefResponse,
    OfferCreate,
    OfferResponse,
    OfferType,
    OfferUpdate,
)
from app.utils.helpers import calculate_pagination


def round_money(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class OfferService:

    # =========================================================================
    # ADMIN CRUD OPERATIONS
    # =========================================================================

    async def create_offer(self, db: AsyncSession, offer_in: OfferCreate) -> OfferResponse:
        # 1. Validate coupon code uniqueness if provided
        if offer_in.coupon_code:
            existing = await offer_repository.get_by_coupon_code(offer_in.coupon_code, is_active_only=False)
            if existing:
                raise ConflictException(
                    message=f"Coupon code '{offer_in.coupon_code}' already exists.",
                    error_code="COUPON_ALREADY_EXISTS"
                )

        # 2. Validate product IDs exist
        if offer_in.product_ids:
            found_prods = await product_repository.get_by_ids(
                db,
                offer_in.product_ids,
                is_active_only=False,
                include_deleted=False
            )
            found_ids = {r["id"] for r in found_prods}
            missing = [str(pid) for pid in offer_in.product_ids if pid not in found_ids]
            if missing:
                raise BadRequestException(
                    message=f"Specified product(s) do not exist: {', '.join(missing)}",
                    error_code="PRODUCT_NOT_FOUND"
                )


        record = await offer_repository.create(offer_in)
        return OfferResponse.model_validate(dict(record))

    async def get_offer(self, offer_id: UUID, is_active_only: bool = False) -> OfferResponse:
        record = await offer_repository.get_by_id(offer_id, include_deleted=False)
        if not record:
            raise NotFoundException(message="Offer not found", error_code="OFFER_NOT_FOUND")

        if is_active_only and not record["is_active"]:
            raise NotFoundException(message="Offer not found or inactive", error_code="OFFER_INACTIVE")

        return OfferResponse.model_validate(dict(record))

    async def list_offers(
        self,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        offer_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[OfferResponse]:
        records, total = await offer_repository.list_offers(
            page=page,
            limit=limit,
            search=search,
            offer_type=offer_type,
            is_active=is_active,
            include_deleted=False
        )
        items = [OfferResponse.model_validate(dict(r)) for r in records]
        pagination = calculate_pagination(total=total, page=page, limit=limit)
        return PaginatedResponse(data=items, pagination=pagination)

    async def update_offer(self, db: AsyncSession, offer_id: UUID, offer_in: OfferUpdate) -> OfferResponse:
        existing = await offer_repository.get_by_id(offer_id, include_deleted=False)
        if not existing:
            raise NotFoundException(message="Offer not found", error_code="OFFER_NOT_FOUND")

        # Check coupon uniqueness if changing
        if offer_in.coupon_code is not None and offer_in.coupon_code != existing["coupon_code"]:
            dup = await offer_repository.get_by_coupon_code(offer_in.coupon_code, is_active_only=False)
            if dup and dup["id"] != offer_id:
                raise ConflictException(
                    message=f"Coupon code '{offer_in.coupon_code}' already in use by another offer.",
                    error_code="COUPON_ALREADY_EXISTS"
                )

        # Validate product IDs if changing
        if offer_in.product_ids is not None and offer_in.product_ids:
            found_prods = await product_repository.get_by_ids(
                db,
                offer_in.product_ids,
                is_active_only=False,
                include_deleted=False
            )
            found_ids = {r["id"] for r in found_prods}
            missing = [str(pid) for pid in offer_in.product_ids if pid not in found_ids]
            if missing:
                raise BadRequestException(
                    message=f"Specified product(s) do not exist: {', '.join(missing)}",
                    error_code="PRODUCT_NOT_FOUND"
                )


        updated = await offer_repository.update(offer_id, offer_in)
        assert updated is not None
        return OfferResponse.model_validate(dict(updated))

    async def delete_offer(self, offer_id: UUID) -> None:
        existing = await offer_repository.get_by_id(offer_id, include_deleted=False)
        if not existing:
            raise NotFoundException(message="Offer not found", error_code="OFFER_NOT_FOUND")

        await offer_repository.delete(offer_id, soft=True)

    # =========================================================================
    # DISCOUNT CALCULATION ENGINE
    # =========================================================================

    def calculate_single_product_offer(
        self,
        product_id: UUID,
        price: Decimal,
        active_offers: List[asyncpg.Record]
    ) -> Tuple[Optional[UUID], Optional[OfferBriefResponse], Decimal, Decimal, Decimal]:
        """
        Calculates the best applicable discount for a product among all active offers.
        Returns (offer_id, offer_data, discount_amount, discounted_price, final_price).
        """
        if not active_offers or price <= Decimal("0.00"):
            return None, None, Decimal("0.00"), price, price

        best_offer_record: Optional[asyncpg.Record] = None
        best_discount_amount: Decimal = Decimal("0.00")

        # Filter offers that can apply automatically to products
        # (Coupon Code, First Order Discount, Free Shipping, Cart Discount, Minimum Order Discount are cart/checkout level)
        auto_offer_types = {
            OfferType.PRODUCT_DISCOUNT.value,
            OfferType.CATEGORY_DISCOUNT.value,
            OfferType.FLASH_SALE.value,
            OfferType.LIMITED_TIME_OFFER.value,
            OfferType.PERCENTAGE_DISCOUNT.value,
            OfferType.FIXED_AMOUNT_DISCOUNT.value,
        }

        for offer in active_offers:
            o_type = offer["offer_type"]
            if o_type not in auto_offer_types:
                continue

            # Check applicability: if product_ids are specified, must match; otherwise applies storewide
            offer_prod_ids = offer.get("product_ids") or []
            if offer_prod_ids and product_id not in offer_prod_ids:
                continue

            # Calculate discount value
            disc_type = offer["discount_type"].lower()
            val = Decimal(str(offer["discount_value"]))
            max_disc = Decimal(str(offer["maximum_discount_amount"])) if offer.get("maximum_discount_amount") else None

            if disc_type in ("percentage", "percent", "%"):
                calc_discount = (price * val) / Decimal("100.00")
                if max_disc is not None and calc_discount > max_disc:
                    calc_discount = max_disc
            else:
                # Fixed
                calc_discount = min(val, price)

            calc_discount = min(calc_discount, price)
            calc_discount = round_money(calc_discount)

            if calc_discount > best_discount_amount:
                best_discount_amount = calc_discount
                best_offer_record = offer

        if best_offer_record and best_discount_amount > Decimal("0.00"):
            final_price = round_money(max(Decimal("0.00"), price - best_discount_amount))
            offer_data = OfferBriefResponse(
                id=best_offer_record["id"],
                name=best_offer_record["name"],
                description=best_offer_record.get("description"),
                offer_type=best_offer_record["offer_type"],
                discount_type=best_offer_record["discount_type"],
                discount_value=Decimal(str(best_offer_record["discount_value"])),
                coupon_code=best_offer_record.get("coupon_code"),
                start_date=best_offer_record["start_date"],
                end_date=best_offer_record["end_date"],
                minimum_order_amount=Decimal(str(best_offer_record.get("minimum_order_amount") or 0)),
                maximum_discount_amount=Decimal(str(best_offer_record["maximum_discount_amount"])) if best_offer_record.get("maximum_discount_amount") else None,
            )
            return best_offer_record["id"], offer_data, best_discount_amount, final_price, final_price

        return None, None, Decimal("0.00"), price, price

    async def enrich_product_records(self, db, records: List[Any]) -> List[Dict[str, Any]]:
        """Enriches product records with offer data, final price, discounted price, and offer id in batch."""
        if not records:
            return []

        from sqlalchemy import select, or_
        from sqlalchemy.orm import selectinload
        from app.models.offer import Offer
        
        current_time = datetime.now(timezone.utc).replace(tzinfo=None)
        
        stmt = (
            select(Offer)
            .options(selectinload(Offer.offer_products))
            .where(
                Offer.is_active == True,
                Offer.is_deleted == False,
                Offer.start_date <= current_time,
                Offer.end_date >= current_time,
                or_(Offer.usage_limit.is_(None), Offer.used_count < Offer.usage_limit)
            )
            .order_by(Offer.created_at.desc())
        )
        result = await db.execute(stmt)
        orm_offers = result.scalars().all()
        
        active_offers = []
        for o in orm_offers:
            active_offers.append({
                "id": o.id,
                "name": o.name,
                "description": o.description,
                "offer_type": o.offer_type,
                "discount_type": o.discount_type,
                "discount_value": o.discount_value,
                "coupon_code": o.coupon_code,
                "minimum_order_amount": o.minimum_order_amount,
                "maximum_discount_amount": o.maximum_discount_amount,
                "start_date": o.start_date,
                "end_date": o.end_date,
                "usage_limit": o.usage_limit,
                "used_count": o.used_count,
                "is_active": o.is_active,
                "is_deleted": o.is_deleted,
                "created_at": o.created_at,
                "updated_at": o.updated_at,
                "product_ids": [op.product_id for op in o.offer_products]
            })

        enriched: List[Dict[str, Any]] = []

        for r in records:
            d = dict(r) if hasattr(r, "keys") else (r.__dict__ if hasattr(r, "__dict__") else dict(r))
            if not isinstance(d, dict) and hasattr(r, "_asdict"):
                d = dict(r._asdict())
            elif not isinstance(d, dict) and hasattr(r, "__table__"):
                d = {c.name: getattr(r, c.name) for c in r.__table__.columns}

            price = Decimal(str(d["price"]))
            pid = d["id"]

            offer_id, offer_data, discount_amt, discounted_p, final_p = self.calculate_single_product_offer(
                product_id=pid,
                price=price,
                active_offers=active_offers
            )

            d["offer_id"] = offer_id
            d["offer_data"] = offer_data
            d["discount_amount"] = discount_amt
            d["discounted_price"] = discounted_p
            d["final_price"] = final_p
            enriched.append(d)

        return enriched

    async def enrich_single_product_record(self, db, record: Any) -> Dict[str, Any]:
        """Enriches a single product record with offer details."""
        enriched = await self.enrich_product_records(db, [record])
        return enriched[0]

    # =========================================================================
    # COUPON VALIDATION & CART/CHECKOUT CALCULATIONS
    # =========================================================================

    async def validate_and_calculate_coupon(
        self,
        coupon_code: str,
        user_id: Optional[UUID] = None,
        cart_subtotal: Optional[Decimal] = None
    ) -> CouponValidateResponse:
        offer_record = await offer_repository.get_by_coupon_code(coupon_code, is_active_only=True)
        if not offer_record:
            return CouponValidateResponse(
                is_valid=False,
                message=f"Coupon code '{coupon_code}' is invalid or expired.",
                coupon_code=coupon_code,
                discount_amount=Decimal("0.00"),
                final_amount=cart_subtotal,
                offer=None
            )

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Check date range
        if offer_record["start_date"] > now:
            return CouponValidateResponse(
                is_valid=False,
                message=f"Coupon code '{coupon_code}' is not active yet.",
                coupon_code=coupon_code,
                discount_amount=Decimal("0.00"),
                final_amount=cart_subtotal,
                offer=None
            )

        if offer_record["end_date"] < now:
            return CouponValidateResponse(
                is_valid=False,
                message=f"Coupon code '{coupon_code}' has expired.",
                coupon_code=coupon_code,
                discount_amount=Decimal("0.00"),
                final_amount=cart_subtotal,
                offer=None
            )

        # Check usage limit
        if offer_record["usage_limit"] is not None and offer_record["used_count"] >= offer_record["usage_limit"]:
            return CouponValidateResponse(
                is_valid=False,
                message=f"Coupon code '{coupon_code}' has reached its maximum redemption limit.",
                coupon_code=coupon_code,
                discount_amount=Decimal("0.00"),
                final_amount=cart_subtotal,
                offer=None
            )

        # Check First Order Discount
        if offer_record["offer_type"] == OfferType.FIRST_ORDER_DISCOUNT.value:
            if user_id:
                prev_orders = await offer_repository.count_user_orders(user_id)
                if prev_orders > 0:
                    return CouponValidateResponse(
                        is_valid=False,
                        message="This coupon is valid only for your first order.",
                        coupon_code=coupon_code,
                        discount_amount=Decimal("0.00"),
                        final_amount=cart_subtotal,
                        offer=None
                    )

        # Check minimum order amount if cart subtotal is available
        min_order = Decimal(str(offer_record.get("minimum_order_amount") or 0))
        if cart_subtotal is not None and min_order > Decimal("0.00"):
            if cart_subtotal < min_order:
                return CouponValidateResponse(
                    is_valid=False,
                    message=f"Coupon requires a minimum order amount of ₹{min_order:.2f}.",
                    coupon_code=coupon_code,
                    discount_amount=Decimal("0.00"),
                    final_amount=cart_subtotal,
                    offer=None
                )

        # Calculate discount amount
        discount_amount = Decimal("0.00")
        if cart_subtotal is not None and cart_subtotal > Decimal("0.00"):
            val = Decimal(str(offer_record["discount_value"]))
            disc_type = offer_record["discount_type"].lower()
            max_disc = Decimal(str(offer_record["maximum_discount_amount"])) if offer_record.get("maximum_discount_amount") else None

            if disc_type in ("percentage", "percent", "%"):
                discount_amount = (cart_subtotal * val) / Decimal("100.00")
                if max_disc is not None and discount_amount > max_disc:
                    discount_amount = max_disc
            else:
                discount_amount = min(val, cart_subtotal)

            discount_amount = min(discount_amount, cart_subtotal)
            discount_amount = round_money(discount_amount)

        final_amount = round_money(max(Decimal("0.00"), cart_subtotal - discount_amount)) if cart_subtotal is not None else None

        brief = OfferBriefResponse(
            id=offer_record["id"],
            name=offer_record["name"],
            description=offer_record.get("description"),
            offer_type=offer_record["offer_type"],
            discount_type=offer_record["discount_type"],
            discount_value=Decimal(str(offer_record["discount_value"])),
            coupon_code=offer_record.get("coupon_code"),
            start_date=offer_record["start_date"],
            end_date=offer_record["end_date"],
            minimum_order_amount=min_order,
            maximum_discount_amount=Decimal(str(offer_record["maximum_discount_amount"])) if offer_record.get("maximum_discount_amount") else None,
        )

        return CouponValidateResponse(
            is_valid=True,
            message="Coupon applied successfully!",
            coupon_code=coupon_code,
            discount_amount=discount_amount,
            final_amount=final_amount,
            offer=brief
        )


offer_service = OfferService()
