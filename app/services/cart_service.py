from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.repositories.cart_repository import cart_repository
from app.repositories.offer_repository import offer_repository
from app.repositories.product_repository import product_repository
from app.schemas.cart import (
    BillCartItemInput,
    BillItemDetail,
    CartItemResponse,
    CartProductSnapshot,
    CartResponse,
    LiveBillRequest,
    LiveBillResponse,
)
from app.schemas.offer import OfferBriefResponse, OfferType
from app.services.offer_service import offer_service, round_money
from app.repositories.user_repository import user_repository
from app.repositories.country_repository import country_repository
from app.services.country_service import country_service
from app.utils.helpers import (
    get_currency_for_country,
    get_country_name_for_code,
    get_user_currency_and_rate,
)


class CartService:

    async def _refresh_and_persist_cart_state(
        self,
        cart_id: UUID,
        user_id: UUID
    ) -> Any:
        """
        Evaluates active offers on all cart items, synchronizes offer details and total_price
        into cart_items, validates/calculates coupon code if present, calculates delivery charges
        and grand totals, and persists them into the carts table.
        """
        currency, rate, country_code, country_name, exchange_available = await get_user_currency_and_rate(
            user_id, user_repository, country_repository
        )
        active_offers = await offer_repository.get_active_offers()
        items_records = await cart_repository.get_cart_items_with_products(cart_id)

        gross_subtotal = Decimal("0.00")
        product_discount_total = Decimal("0.00")

        for r in items_records:
            base_price = Decimal(str(r["product_price"]))
            original_price = round_money(base_price * rate)
            qty = int(r["quantity"])

            offer_id, offer_data, disc_unit, discounted_unit_p, final_unit_p = (
                offer_service.calculate_single_product_offer(
                    product_id=r["product_id"],
                    price=original_price,
                    active_offers=active_offers
                )
            )

            disc_type = offer_data.discount_type if offer_data else None
            disc_val = Decimal(str(offer_data.discount_value)) if offer_data else None
            item_total = round_money(final_unit_p * qty)

            # Persist item offer and pricing to cart_items table in user's currency
            await cart_repository.update_item_offer_and_pricing(
                item_id=r["id"],
                offer_id=offer_id,
                unit_price=original_price,
                discount_type=disc_type,
                discount_value=disc_val,
                discount_amount=disc_unit,
                final_unit_price=final_unit_p,
                total_price=item_total
            )

            gross_subtotal += round_money(original_price * qty)
            product_discount_total += round_money(disc_unit * qty)

        net_items_amount = round_money(max(Decimal("0.00"), gross_subtotal - product_discount_total))

        # Check existing coupon on cart
        cart_record = await cart_repository.get_cart_by_user(user_id)
        current_coupon_code = cart_record.get("coupon_code") if cart_record else None

        coupon_discount_amount = Decimal("0.00")
        coupon_discount_type: Optional[str] = None
        coupon_discount_value: Optional[Decimal] = None
        coupon_code_to_save: Optional[str] = None
        applied_coupon_obj: Optional[OfferBriefResponse] = None

        if current_coupon_code and net_items_amount > Decimal("0.00"):
            coupon_res = await offer_service.validate_and_calculate_coupon(
                coupon_code=current_coupon_code,
                user_id=user_id,
                cart_subtotal=net_items_amount
            )
            if coupon_res.is_valid:
                coupon_code_to_save = current_coupon_code
                coupon_discount_amount = coupon_res.discount_amount
                if coupon_res.offer:
                    applied_coupon_obj = coupon_res.offer
                    coupon_discount_type = coupon_res.offer.discount_type
                    coupon_discount_value = coupon_res.offer.discount_value
            else:
                # Coupon became invalid due to cart changes
                coupon_code_to_save = None
        else:
            coupon_code_to_save = None

        # Delivery & shipping calculation in user's currency
        free_delivery_threshold = round_money(Decimal("150.00") * rate)
        standard_delivery_fee = round_money(Decimal("15.00") * rate)

        if net_items_amount == Decimal("0.00"):
            shipping_amount = Decimal("0.00")
        elif applied_coupon_obj and applied_coupon_obj.offer_type == OfferType.FREE_SHIPPING.value:
            shipping_amount = Decimal("0.00")
        elif net_items_amount >= free_delivery_threshold:
            shipping_amount = Decimal("0.00")
        else:
            shipping_amount = standard_delivery_fee

        total_discount = round_money(min(gross_subtotal, product_discount_total + coupon_discount_amount))
        total_amount = round_money(max(Decimal("0.00"), gross_subtotal - total_discount + shipping_amount))

        # Persist updated cart summary and coupon details into carts table
        updated_cart = await cart_repository.update_cart_totals_and_coupon(
            cart_id=cart_id,
            coupon_code=coupon_code_to_save,
            coupon_discount_type=coupon_discount_type,
            coupon_discount_value=coupon_discount_value,
            coupon_discount_amount=coupon_discount_amount,
            subtotal=gross_subtotal,
            total_discount=total_discount,
            shipping_amount=shipping_amount,
            total_amount=total_amount
        )
        return updated_cart

    async def get_user_cart(self, user_id: UUID) -> CartResponse:
        cart_record = await cart_repository.get_or_create_cart(user_id)
        cart_id = cart_record["id"]

        # Refresh state and persist calculations to both carts and cart_items
        cart_record = await self._refresh_and_persist_cart_state(cart_id, user_id)
        items_records = await cart_repository.get_cart_items_with_products(cart_id)

        cart_items: List[CartItemResponse] = []
        total_items_count = 0

        for r in items_records:
            qty = int(r["quantity"])
            unit_price = Decimal(str(r["unit_price"] or r["product_price"]))
            disc_amount = Decimal(str(r["discount_amount"] or "0.00"))
            final_unit_p = Decimal(str(r["final_unit_price"] or r["product_price"]))
            item_total = Decimal(str(r["total_price"] or (final_unit_p * qty)))

            product_snapshot = CartProductSnapshot(
                id=r["product_id"],
                name=r["product_name"],
                main_image_url=r["main_image_url"],
                price=unit_price,
                is_active=r["product_is_active"],
                original_price=unit_price,
                discount_amount=disc_amount,
                discounted_price=final_unit_p,
                final_price=final_unit_p,
                offer_id=r["offer_id"]
            )

            cart_items.append(
                CartItemResponse(
                    id=r["id"],
                    product=product_snapshot,
                    quantity=qty,
                    subtotal=item_total,
                    offer_id=r["offer_id"],
                    unit_price=unit_price,
                    discount_type=r["discount_type"],
                    discount_value=Decimal(str(r["discount_value"])) if r["discount_value"] is not None else None,
                    discount_amount=disc_amount,
                    final_unit_price=final_unit_p,
                    total_price=item_total
                )
            )
            total_items_count += qty

        # Load applied coupon offer info if coupon is present
        applied_offer: Optional[OfferBriefResponse] = None
        if cart_record.get("coupon_code"):
            offer_rec = await offer_repository.get_by_coupon_code(cart_record["coupon_code"], is_active_only=False)
            if offer_rec:
                applied_offer = OfferBriefResponse(
                    id=offer_rec["id"],
                    name=offer_rec["name"],
                    description=offer_rec.get("description"),
                    offer_type=offer_rec["offer_type"],
                    discount_type=offer_rec["discount_type"],
                    discount_value=Decimal(str(offer_rec["discount_value"])),
                    coupon_code=offer_rec.get("coupon_code"),
                    start_date=offer_rec["start_date"],
                    end_date=offer_rec["end_date"],
                    minimum_order_amount=Decimal(str(offer_rec.get("minimum_order_amount") or 0)),
                    maximum_discount_amount=Decimal(str(offer_rec["maximum_discount_amount"])) if offer_rec.get("maximum_discount_amount") else None,
                )

        subtotal = Decimal(str(cart_record["subtotal"] or "0.00"))
        total_discount = Decimal(str(cart_record["total_discount"] or "0.00"))
        shipping_amount = Decimal(str(cart_record["shipping_amount"] or "0.00"))
        total_amount = Decimal(str(cart_record["total_amount"] or "0.00"))

        user = await user_repository.get_by_id(user_id)
        user_country_code = user["country_code"].strip().upper() if user and user.get("country_code") else None
        currency = get_currency_for_country(user_country_code)

        return CartResponse(
            id=cart_id,
            items=cart_items,
            total_items=total_items_count,
            coupon_code=cart_record.get("coupon_code"),
            coupon_discount_type=cart_record.get("coupon_discount_type"),
            coupon_discount_value=Decimal(str(cart_record["coupon_discount_value"])) if cart_record.get("coupon_discount_value") is not None else None,
            coupon_discount_amount=Decimal(str(cart_record["coupon_discount_amount"] or "0.00")),
            subtotal=subtotal,
            total_discount=total_discount,
            shipping_amount=shipping_amount,
            total_amount=total_amount,
            final_amount=total_amount,
            applied_offer=applied_offer,
            currency=currency,
            country_code=user_country_code,
        )

    async def add_item_to_cart(self, db: AsyncSession, user_id: UUID, product_id: UUID, quantity: int) -> CartResponse:
        product = await product_repository.get_by_id(db, product_id)
        if not product:
            raise NotFoundException(message="Product not found", error_code="PRODUCT_NOT_FOUND")

        is_act = getattr(product, "is_active", None) if hasattr(product, "is_active") else product.get("is_active")
        is_del = getattr(product, "is_deleted", False) if hasattr(product, "is_deleted") else product.get("is_deleted", False)
        if not is_act or is_del:
            raise BadRequestException(
                message="This product is currently inactive and cannot be added to cart",
                error_code="PRODUCT_INACTIVE"
            )

        raw_price = getattr(product, "price", None) if hasattr(product, "price") else product.get("price")
        orig_price = Decimal(str(raw_price))
        active_offers = await offer_repository.get_active_offers()
        offer_id, offer_data, disc_unit, _, final_unit_p = (
            offer_service.calculate_single_product_offer(
                product_id=product_id,
                price=orig_price,
                active_offers=active_offers
            )
        )
        disc_type = offer_data.discount_type if offer_data else None
        disc_val = Decimal(str(offer_data.discount_value)) if offer_data else None
        item_total = round_money(final_unit_p * quantity)

        cart_record = await cart_repository.get_or_create_cart(user_id)
        cart_id = cart_record["id"]

        # Insert or update cart item with active offer details
        await cart_repository.add_or_increment_item(
            cart_id=cart_id,
            product_id=product_id,
            quantity=quantity,
            offer_id=offer_id,
            unit_price=orig_price,
            discount_type=disc_type,
            discount_value=disc_val,
            discount_amount=disc_unit,
            final_unit_price=final_unit_p,
            total_price=item_total
        )

        # Recalculate totals and persist to carts table
        await self._refresh_and_persist_cart_state(cart_id, user_id)
        return await self.get_user_cart(user_id)

    async def update_cart_item(self, db: AsyncSession, user_id: UUID, item_id: UUID, quantity: int) -> CartResponse:
        cart_record = await cart_repository.get_cart_by_user(user_id)
        if not cart_record:
            raise NotFoundException(message="Cart not found", error_code="CART_NOT_FOUND")

        cart_id = cart_record["id"]
        item = await cart_repository.get_item_by_id(item_id)
        if not item or item["cart_id"] != cart_id:
            raise NotFoundException(message="Cart item not found", error_code="CART_ITEM_NOT_FOUND")

        # Check product status
        product = await product_repository.get_by_id(db, item["product_id"])
        if not product or not product["is_active"] or product.get("is_deleted", False):
            raise BadRequestException(
                message="Product is no longer active",
                error_code="PRODUCT_INACTIVE"
            )

        orig_price = Decimal(str(product["price"]))
        active_offers = await offer_repository.get_active_offers()
        offer_id, offer_data, disc_unit, _, final_unit_p = (
            offer_service.calculate_single_product_offer(
                product_id=item["product_id"],
                price=orig_price,
                active_offers=active_offers
            )
        )
        disc_type = offer_data.discount_type if offer_data else None
        disc_val = Decimal(str(offer_data.discount_value)) if offer_data else None
        item_total = round_money(final_unit_p * quantity)

        # Update quantity and refreshed offer pricing
        await cart_repository.update_item_offer_and_pricing(
            item_id=item_id,
            offer_id=offer_id,
            unit_price=orig_price,
            discount_type=disc_type,
            discount_value=disc_val,
            discount_amount=disc_unit,
            final_unit_price=final_unit_p,
            total_price=item_total
        )
        await cart_repository.update_item_quantity(item_id, quantity, total_price=item_total)

        await self._refresh_and_persist_cart_state(cart_id, user_id)
        return await self.get_user_cart(user_id)

    async def remove_cart_item(self, user_id: UUID, item_id: UUID) -> CartResponse:
        cart_record = await cart_repository.get_cart_by_user(user_id)
        if not cart_record:
            raise NotFoundException(message="Cart not found", error_code="CART_NOT_FOUND")

        cart_id = cart_record["id"]
        deleted = await cart_repository.delete_item(item_id, cart_id)
        if not deleted:
            raise NotFoundException(message="Cart item not found", error_code="CART_ITEM_NOT_FOUND")

        await self._refresh_and_persist_cart_state(cart_id, user_id)
        return await self.get_user_cart(user_id)

    async def clear_cart(self, user_id: UUID) -> CartResponse:
        cart_record = await cart_repository.get_or_create_cart(user_id)
        await cart_repository.clear_cart(cart_record["id"])
        return await self.get_user_cart(user_id)

    async def apply_coupon(self, user_id: UUID, coupon_code: str) -> CartResponse:
        """
        Validates coupon code, persists it to the carts table, and recomputes all totals.
        """
        code = coupon_code.strip().upper()
        cart_record = await cart_repository.get_or_create_cart(user_id)
        cart_id = cart_record["id"]

        items_records = await cart_repository.get_cart_items_with_products(cart_id)
        if not items_records:
            raise BadRequestException(
                message="Cannot apply coupon to an empty cart",
                error_code="EMPTY_CART"
            )

        # Refresh item offers to get accurate current net items amount
        await self._refresh_and_persist_cart_state(cart_id, user_id)
        items_records = await cart_repository.get_cart_items_with_products(cart_id)
        net_items_amount = sum(Decimal(str(r["total_price"])) for r in items_records)

        coupon_res = await offer_service.validate_and_calculate_coupon(
            coupon_code=code,
            user_id=user_id,
            cart_subtotal=net_items_amount
        )
        if not coupon_res.is_valid:
            raise BadRequestException(
                message=coupon_res.message,
                error_code="INVALID_COUPON"
            )

        # Set coupon on cart and run recalculation
        coupon_disc_type = coupon_res.offer.discount_type if coupon_res.offer else None
        coupon_disc_val = coupon_res.offer.discount_value if coupon_res.offer else None
        await cart_repository.update_cart_totals_and_coupon(
            cart_id=cart_id,
            coupon_code=code,
            coupon_discount_type=coupon_disc_type,
            coupon_discount_value=coupon_disc_val,
            coupon_discount_amount=coupon_res.discount_amount
        )

        await self._refresh_and_persist_cart_state(cart_id, user_id)
        return await self.get_user_cart(user_id)

    async def remove_coupon(self, user_id: UUID) -> CartResponse:
        """
        Removes applied coupon from the cart and recomputes totals.
        """
        cart_record = await cart_repository.get_cart_by_user(user_id)
        if not cart_record:
            raise NotFoundException(message="Cart not found", error_code="CART_NOT_FOUND")

        cart_id = cart_record["id"]
        await cart_repository.update_cart_totals_and_coupon(
            cart_id=cart_id,
            coupon_code=None,
            coupon_discount_type=None,
            coupon_discount_value=None,
            coupon_discount_amount=Decimal("0.00")
        )

        await self._refresh_and_persist_cart_state(cart_id, user_id)
        return await self.get_user_cart(user_id)

    async def calculate_live_bill(
        self,
        db: AsyncSession,
        user_id: Optional[UUID],
        req: LiveBillRequest,
    ) -> LiveBillResponse:
        """
        Calculates live bill for cart checkout.
        Uses persisted cart items and persisted coupon if user is authenticated and items not explicitly passed.
        """
        active_offers = await offer_repository.get_active_offers()
        bill_items: List[BillItemDetail] = []
        subtotal_amount = Decimal("0.00")
        product_discount_amount = Decimal("0.00")
        net_items_amount = Decimal("0.00")
        total_items_count = 0

        # Determine user country data and exchange rate from user table if user_id is provided
        currency, rate, user_country_code, user_country_name, exchange_available = await get_user_currency_and_rate(
            user_id, user_repository, country_repository
        )

        # Determine coupon code to evaluate
        requested_coupon = req.coupon_code.strip().upper() if req.coupon_code and req.coupon_code.strip() else None

        if req.items is not None:
            # Dynamic calculation from explicit items (e.g. guest cart or preview)
            if req.items:
                prod_ids = [it.product_id for it in req.items if it.quantity > 0]
                found_prods = await product_repository.get_by_ids(db, prod_ids, is_active_only=True, include_deleted=False)
                prod_map = {getattr(r, "id", None) or (r["id"] if isinstance(r, dict) or hasattr(r, "__getitem__") else None): r for r in found_prods}

                for it in req.items:
                    if it.quantity <= 0:
                        continue
                    product = prod_map.get(it.product_id)
                    if not product:
                        continue

                    raw_price = getattr(product, "price", None) or (product["price"] if isinstance(product, dict) or hasattr(product, "__getitem__") else 0)
                    base_price = Decimal(str(raw_price))
                    orig_price = round_money(base_price * rate)
                    qty = it.quantity
                    offer_id, offer_data, disc_unit, discounted_unit_p, final_unit_p = (
                        offer_service.calculate_single_product_offer(
                            product_id=it.product_id,
                            price=orig_price,
                            active_offers=active_offers
                        )
                    )

                    gross_sub = round_money(orig_price * qty)
                    disc_sub = round_money(disc_unit * qty)
                    net_sub = round_money(final_unit_p * qty)

                    subtotal_amount += gross_sub
                    product_discount_amount += disc_sub
                    net_items_amount += net_sub
                    total_items_count += qty

                    prod_name = getattr(product, "name", None) or (product["name"] if isinstance(product, dict) or hasattr(product, "__getitem__") else "")
                    prod_img = getattr(product, "main_image_url", None) or (product.get("main_image_url") if isinstance(product, dict) or hasattr(product, "get") else None)

                    bill_items.append(
                        BillItemDetail(
                            product_id=it.product_id,
                            product_name=prod_name,
                            product_image_url=prod_img,
                            quantity=qty,
                            original_unit_price=orig_price,
                            product_discount_unit=disc_unit,
                            final_unit_price=final_unit_p,
                            gross_subtotal=gross_sub,
                            product_discount_total=disc_sub,
                            net_subtotal=net_sub,
                            applied_offer=offer_data
                        )
                    )
            coupon_to_check = requested_coupon
        elif user_id is not None:
            # Pull from user's database cart with persisted item offers
            cart_record = await cart_repository.get_or_create_cart(user_id)
            cart_id = cart_record["id"]

            # Refresh and persist latest state
            cart_record = await self._refresh_and_persist_cart_state(cart_id, user_id)
            items_records = await cart_repository.get_cart_items_with_products(cart_id)

            for r in items_records:
                qty = int(r["quantity"])
                unit_price = Decimal(str(r["unit_price"] or r["product_price"]))
                disc_unit = Decimal(str(r["discount_amount"] or "0.00"))
                final_unit_p = Decimal(str(r["final_unit_price"] or r["product_price"]))
                item_total = Decimal(str(r["total_price"] or (final_unit_p * qty)))
                gross_sub = round_money(unit_price * qty)
                disc_sub = round_money(disc_unit * qty)

                subtotal_amount += gross_sub
                product_discount_amount += disc_sub
                net_items_amount += item_total
                total_items_count += qty

                # Construct applied offer snapshot if offer_id present
                item_offer_data: Optional[OfferBriefResponse] = None
                if r["offer_id"]:
                    for off in active_offers:
                        if off["id"] == r["offer_id"]:
                            item_offer_data = OfferBriefResponse(
                                id=off["id"],
                                name=off["name"],
                                description=off.get("description"),
                                offer_type=off["offer_type"],
                                discount_type=off["discount_type"],
                                discount_value=Decimal(str(off["discount_value"])),
                                coupon_code=off.get("coupon_code"),
                                start_date=off["start_date"],
                                end_date=off["end_date"],
                                minimum_order_amount=Decimal(str(off.get("minimum_order_amount") or 0)),
                                maximum_discount_amount=Decimal(str(off["maximum_discount_amount"])) if off.get("maximum_discount_amount") else None,
                            )
                            break

                bill_items.append(
                    BillItemDetail(
                        product_id=r["product_id"],
                        product_name=r["product_name"],
                        product_image_url=r["main_image_url"],
                        quantity=qty,
                        original_unit_price=unit_price,
                        product_discount_unit=disc_unit,
                        final_unit_price=final_unit_p,
                        gross_subtotal=gross_sub,
                        product_discount_total=disc_sub,
                        net_subtotal=item_total,
                        applied_offer=item_offer_data
                    )
                )

            # Use requested coupon if provided; otherwise fall back to persisted cart coupon
            coupon_to_check = requested_coupon if requested_coupon else cart_record.get("coupon_code")
        else:
            coupon_to_check = requested_coupon

        # Coupon evaluation
        coupon_discount_amount = Decimal("0.00")
        is_coupon_applied = False
        coupon_message: Optional[str] = None
        applied_coupon: Optional[OfferBriefResponse] = None

        if coupon_to_check and net_items_amount > Decimal("0.00"):
            coupon_res = await offer_service.validate_and_calculate_coupon(
                coupon_code=coupon_to_check,
                user_id=user_id,
                cart_subtotal=net_items_amount
            )
            is_coupon_applied = coupon_res.is_valid
            coupon_message = coupon_res.message
            if coupon_res.is_valid:
                coupon_discount_amount = coupon_res.discount_amount
                applied_coupon = coupon_res.offer
            else:
                coupon_discount_amount = Decimal("0.00")
        elif coupon_to_check and net_items_amount == Decimal("0.00"):
            coupon_message = "Cart is empty"

        # Delivery charges calculation in user's currency
        free_delivery_threshold = round_money(Decimal("150.00") * rate)
        standard_delivery_fee = round_money(Decimal("15.00") * rate)

        if net_items_amount == Decimal("0.00"):
            delivery_charge = Decimal("0.00")
            is_free_delivery = True
            amount_needed = Decimal("0.00")
        elif applied_coupon and applied_coupon.offer_type == OfferType.FREE_SHIPPING.value:
            delivery_charge = Decimal("0.00")
            is_free_delivery = True
            amount_needed = Decimal("0.00")
        elif net_items_amount >= free_delivery_threshold:
            delivery_charge = Decimal("0.00")
            is_free_delivery = True
            amount_needed = Decimal("0.00")
        else:
            delivery_charge = standard_delivery_fee
            is_free_delivery = False
            amount_needed = round_money(free_delivery_threshold - net_items_amount)

        total_discount_amount = round_money(product_discount_amount + coupon_discount_amount)
        total_savings_amount = total_discount_amount
        total_savings_pct = (
            round_money((total_savings_amount / subtotal_amount) * Decimal("100.00"))
            if subtotal_amount > Decimal("0.00")
            else Decimal("0.00")
        )

        total_payable = round_money(
            max(Decimal("0.00"), net_items_amount - coupon_discount_amount + delivery_charge)
        )

        return LiveBillResponse(
            items=bill_items,
            total_items=total_items_count,
            items_count=len(bill_items),
            subtotal_amount=round_money(subtotal_amount),
            product_discount_amount=round_money(product_discount_amount),
            net_items_amount=round_money(net_items_amount),
            coupon_code=coupon_to_check if is_coupon_applied else req.coupon_code,
            is_coupon_applied=is_coupon_applied,
            coupon_discount_amount=round_money(coupon_discount_amount),
            coupon_message=coupon_message,
            applied_coupon=applied_coupon,
            delivery_charge=round_money(delivery_charge),
            is_free_delivery=is_free_delivery,
            free_delivery_threshold=free_delivery_threshold,
            amount_needed_for_free_delivery=amount_needed,
            delivery_title="Insured Luxury Express Delivery",
            estimated_delivery_days="3-5 Business Days",
            gift_packaging_charge=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            is_tax_included=True,
            tax_description="Inclusive of all luxury taxes and GST",
            total_discount_amount=total_discount_amount,
            total_savings_amount=total_savings_amount,
            total_savings_percentage=total_savings_pct,
            total_amount=total_payable,
            currency=currency,
            country_code=user_country_code,
            country_name=user_country_name,
            exchange_rate=rate,
            exchange_available=exchange_available,
        )


cart_service = CartService()
