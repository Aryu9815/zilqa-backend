import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
import asyncpg

from app.core.config import settings
from app.core.database import get_transaction
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.razorpay import razorpay_service
from app.repositories.address_repository import address_repository
from app.repositories.cart_repository import cart_repository
from app.repositories.offer_repository import offer_repository
from app.repositories.order_repository import order_repository
from app.repositories.product_repository import product_repository
from app.schemas.common import PaginatedResponse
from app.schemas.offer import OfferType
from app.schemas.order import (
    OrderCreate,
    OrderCustomerInfo,
    OrderItemResponse,
    OrderResponse,
    OrderStatus,
    PaymentStatus,
    RazorpayOrderCreateRequest,
    RazorpayOrderResponse,
    RazorpayPaymentVerifyRequest,
)
from app.services.offer_service import offer_service, round_money
from app.utils.helpers import calculate_pagination


VALID_STATUS_TRANSITIONS: Dict[str, List[str]] = {
    "confirmed": ["processing", "cancelled"],
    "processing": ["shipped", "cancelled"],
    "shipped": ["delivered"],
    "delivered": ["returned"],
    "cancelled": [],
    "returned": []
}


class OrderService:

    async def _resolve_shipping_address(
        self,
        user_id: UUID,
        address_id: Optional[UUID] = None,
        shipping_address: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Resolves shipping address from either address_id or explicit shipping_address dict."""
        if address_id:
            addr_record = await address_repository.get_by_id_and_user(address_id, user_id)
            if not addr_record:
                raise BadRequestException(
                    message="Specified shipping address was not found or does not belong to you",
                    error_code="INVALID_SHIPPING_ADDRESS"
                )
            return {
                "id": str(addr_record["id"]),
                "full_name": addr_record["full_name"],
                "phone": addr_record["phone"],
                "address_line_1": addr_record["address_line_1"],
                "address_line_2": addr_record.get("address_line_2"),
                "city": addr_record["city"],
                "state": addr_record["state"],
                "postal_code": addr_record["postal_code"],
                "country": addr_record.get("country", "India"),
            }

        if shipping_address:
            required_fields = ["full_name", "phone", "address_line_1", "city", "state", "postal_code"]
            missing = [f for f in required_fields if not shipping_address.get(f)]
            if missing:
                raise BadRequestException(
                    message=f"Shipping address is missing required fields: {', '.join(missing)}",
                    error_code="INCOMPLETE_SHIPPING_ADDRESS"
                )
            return dict(shipping_address)

        raise BadRequestException(
            message="Shipping address is required to place an order",
            error_code="MISSING_SHIPPING_ADDRESS"
        )

    async def _calculate_cart_pricing(
        self,
        user_id: UUID,
        coupon_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Loads user cart items and evaluates all active product discounts, coupon codes, and shipping."""
        cart_record = await cart_repository.get_or_create_cart(user_id)
        cart_id = cart_record["id"]
        if not coupon_code and cart_record.get("coupon_code"):
            coupon_code = cart_record["coupon_code"]
        cart_items_records = await cart_repository.get_cart_items_with_products(cart_id)

        if not cart_items_records:
            raise BadRequestException(
                message="Cannot proceed because your shopping cart is empty",
                error_code="EMPTY_CART"
            )

        active_offers = await offer_repository.get_active_offers()

        calculated_items: List[Tuple[
            Optional[UUID], # product_id
            str,            # product_name
            Optional[str],  # product_image_url
            Decimal,        # price
            int,            # quantity
            Decimal,        # unit_price
            Optional[str],  # discount_type
            Decimal,        # discount_value
            Decimal,        # discount_amount
            Decimal,        # final_unit_price
            Decimal         # total_price
        ]] = []

        subtotal = Decimal("0.00")
        product_discount_total = Decimal("0.00")

        for item in cart_items_records:
            product_id = item["product_id"]
            live_product = await product_repository.get_by_id(product_id)

            if not live_product or not live_product["is_active"] or live_product.get("is_deleted", False):
                raise BadRequestException(
                    message=f"Product '{item['product_name']}' is currently unavailable or deactivated",
                    error_code="PRODUCT_UNAVAILABLE"
                )

            orig_price = Decimal(str(live_product["price"]))
            quantity = int(item["quantity"])

            offer_id, offer_data, disc_unit, _, final_unit_price = (
                offer_service.calculate_single_product_offer(
                    product_id=product_id,
                    price=orig_price,
                    active_offers=active_offers
                )
            )

            disc_type = str(offer_data.discount_type) if offer_data else None
            disc_val = Decimal(str(offer_data.discount_value)) if offer_data else Decimal("0.00")
            disc_amt = disc_unit
            total_item_price = round_money(final_unit_price * quantity)

            subtotal += round_money(orig_price * quantity)
            product_discount_total += round_money(disc_unit * quantity)

            calculated_items.append((
                product_id,
                live_product["name"],
                live_product.get("main_image_url"),
                orig_price,
                quantity,
                orig_price,
                disc_type,
                disc_val,
                disc_amt,
                final_unit_price,
                total_item_price
            ))

        # Handle coupon code if present
        coupon_discount = Decimal("0.00")
        applied_coupon_offer_id: Optional[UUID] = None
        shipping_amount = Decimal("0.00")

        coupon_offer_obj = None
        if coupon_code:
            eligible_base = max(Decimal("0.00"), subtotal - product_discount_total)
            coupon_res = await offer_service.validate_and_calculate_coupon(
                coupon_code=coupon_code,
                user_id=user_id,
                cart_subtotal=eligible_base
            )
            if not coupon_res.is_valid:
                raise BadRequestException(
                    message=coupon_res.message,
                    error_code="INVALID_COUPON"
                )
            coupon_discount = coupon_res.discount_amount
            if coupon_res.offer:
                applied_coupon_offer_id = coupon_res.offer.id
                coupon_offer_obj = coupon_res.offer

        free_delivery_threshold = Decimal("150.00")
        standard_delivery_fee = Decimal("15.00")
        net_after_prod_disc = max(Decimal("0.00"), subtotal - product_discount_total)

        if net_after_prod_disc >= free_delivery_threshold or (coupon_offer_obj and coupon_offer_obj.offer_type == OfferType.FREE_SHIPPING.value) or net_after_prod_disc == Decimal("0.00"):
            shipping_amount = Decimal("0.00")
        else:
            shipping_amount = standard_delivery_fee

        total_discount = min(subtotal, product_discount_total + coupon_discount)
        total_amount = round_money(max(Decimal("0.00"), subtotal - total_discount + shipping_amount))

        return {
            "cart_id": cart_id,
            "subtotal": subtotal,
            "product_discount_total": product_discount_total,
            "coupon_discount": coupon_discount,
            "total_discount": total_discount,
            "shipping_amount": shipping_amount,
            "total_amount": total_amount,
            "coupon_code": coupon_code,
            "applied_coupon_offer_id": applied_coupon_offer_id,
            "calculated_items": calculated_items
        }

    # =========================================================================
    # RAZORPAY CHECKOUT METHODS
    # =========================================================================

    async def create_razorpay_order(
        self,
        user_id: UUID,
        req: RazorpayOrderCreateRequest
    ) -> RazorpayOrderResponse:
        """
        Step 1 of Razorpay checkout: validates cart and address, calculates total with offers,
        and initializes a Razorpay order returning razorpay_order_id and amount in paise.
        """
        # Validate shipping address
        await self._resolve_shipping_address(user_id, req.address_id, req.shipping_address)

        # Calculate pricing
        pricing = await self._calculate_cart_pricing(user_id, req.coupon_code)

        # Create Razorpay order
        rzp_order = await razorpay_service.create_order(
            amount=pricing["total_amount"],
            currency="INR",
            notes={"user_id": str(user_id)}
        )

        return RazorpayOrderResponse(
            razorpay_order_id=rzp_order["id"],
            amount=rzp_order["amount"],
            currency=rzp_order.get("currency", "INR"),
            key_id=settings.RAZORPAY_KEY_ID,
            subtotal=pricing["subtotal"],
            discount_amount=pricing["total_discount"],
            shipping_amount=pricing["shipping_amount"],
            total_amount=pricing["total_amount"],
            coupon_code=req.coupon_code
        )

    async def verify_and_complete_order(
        self,
        user_id: UUID,
        req: RazorpayPaymentVerifyRequest
    ) -> OrderResponse:
        """
        Step 2 of Razorpay checkout: verifies the cryptographic signature from Razorpay,
        creates the order and order_items with offer details and calculations, increments coupon
        redemption, and hard-deletes the cart items from cart_items upon completion.
        """
        # 1. Verify Razorpay cryptographic signature
        is_valid = razorpay_service.verify_payment_signature(
            razorpay_order_id=req.razorpay_order_id,
            razorpay_payment_id=req.razorpay_payment_id,
            razorpay_signature=req.razorpay_signature
        )
        if not is_valid:
            raise BadRequestException(
                message="Razorpay payment signature verification failed",
                error_code="INVALID_PAYMENT_SIGNATURE"
            )

        # 2. Check for duplicate order creation by razorpay_order_id
        existing_order = await order_repository.get_by_razorpay_order_id(req.razorpay_order_id)
        if existing_order:
            return await self.get_order_details(existing_order["id"])

        # 3. Resolve shipping address
        resolved_addr = await self._resolve_shipping_address(user_id, req.address_id, req.shipping_address)

        # 4. Calculate live cart pricing with active offers
        pricing = await self._calculate_cart_pricing(user_id, req.coupon_code)
        cart_id = pricing["cart_id"]

        # 5. Atomically commit order and order_items with offer details, then hard-delete cart items
        async with get_transaction() as conn:
            order_record = await order_repository.create_order(
                user_id=user_id,
                status=OrderStatus.CONFIRMED.value,
                payment_status=PaymentStatus.PAID.value,
                subtotal=pricing["subtotal"],
                discount_amount=pricing["total_discount"],
                shipping_amount=pricing["shipping_amount"],
                total_amount=pricing["total_amount"],
                shipping_address=resolved_addr,
                currency="INR",
                coupon_code=req.coupon_code,
                razorpay_order_id=req.razorpay_order_id,
                razorpay_payment_id=req.razorpay_payment_id,
                razorpay_signature=req.razorpay_signature,
                connection=conn
            )
            order_id = order_record["id"]

            # Increment coupon usage count if coupon applied
            if pricing["applied_coupon_offer_id"]:
                await offer_repository.increment_used_count(pricing["applied_coupon_offer_id"], connection=conn)

            # Insert order items with offer details
            items_to_insert = [
                (
                    order_id,
                    p_id,
                    p_name,
                    p_img,
                    orig_p,
                    qty,
                    u_p,
                    d_type,
                    d_val,
                    d_amt,
                    f_unit_p,
                    t_p
                )
                for (p_id, p_name, p_img, orig_p, qty, u_p, d_type, d_val, d_amt, f_unit_p, t_p)
                in pricing["calculated_items"]
            ]
            await order_repository.create_order_items(items_to_insert, connection=conn)

            # Hard delete cart items from cart
            await cart_repository.clear_cart(cart_id, connection=conn)

        return await self.get_order_details(order_id)

    # =========================================================================
    # GENERAL ORDER CREATION (DIRECT / STANDARD / BACKWARD COMPATIBLE)
    # =========================================================================

    async def create_order(self, user_id: UUID, order_in: OrderCreate) -> OrderResponse:
        """
        Places a new order from current cart.
        If Razorpay payment details are included, verifies signature and marks order confirmed/paid.
        Otherwise creates order in confirmed status with pending payment.
        Creates order and order_items with offer details and hard-deletes cart items.
        """
        # If Razorpay payment details are provided, route to payment verification
        if order_in.razorpay_order_id and order_in.razorpay_payment_id and order_in.razorpay_signature:
            verify_req = RazorpayPaymentVerifyRequest(
                razorpay_order_id=order_in.razorpay_order_id,
                razorpay_payment_id=order_in.razorpay_payment_id,
                razorpay_signature=order_in.razorpay_signature,
                address_id=order_in.address_id,
                shipping_address=order_in.shipping_address,
                coupon_code=order_in.coupon_code
            )
            return await self.verify_and_complete_order(user_id, verify_req)

        # 1. Resolve shipping address
        resolved_addr = await self._resolve_shipping_address(
            user_id,
            order_in.address_id,
            order_in.shipping_address
        )

        # 2. Calculate cart pricing with offers
        pricing = await self._calculate_cart_pricing(user_id, order_in.coupon_code)
        cart_id = pricing["cart_id"]

        # Default statuses
        status_val = OrderStatus.CONFIRMED.value
        payment_status_val = PaymentStatus.PENDING.value

        # 3. Atomically commit order, items, and hard-delete cart items
        async with get_transaction() as conn:
            order_record = await order_repository.create_order(
                user_id=user_id,
                status=status_val,
                payment_status=payment_status_val,
                subtotal=pricing["subtotal"],
                discount_amount=pricing["total_discount"],
                shipping_amount=pricing["shipping_amount"],
                total_amount=pricing["total_amount"],
                shipping_address=resolved_addr,
                currency="INR",
                coupon_code=order_in.coupon_code,
                razorpay_order_id=order_in.razorpay_order_id,
                razorpay_payment_id=order_in.razorpay_payment_id,
                razorpay_signature=order_in.razorpay_signature,
                connection=conn
            )
            order_id = order_record["id"]

            if pricing["applied_coupon_offer_id"]:
                await offer_repository.increment_used_count(pricing["applied_coupon_offer_id"], connection=conn)

            items_to_insert = [
                (
                    order_id,
                    p_id,
                    p_name,
                    p_img,
                    orig_p,
                    qty,
                    u_p,
                    d_type,
                    d_val,
                    d_amt,
                    f_unit_p,
                    t_p
                )
                for (p_id, p_name, p_img, orig_p, qty, u_p, d_type, d_val, d_amt, f_unit_p, t_p)
                in pricing["calculated_items"]
            ]
            await order_repository.create_order_items(items_to_insert, connection=conn)

            # Hard delete cart items from cart
            await cart_repository.clear_cart(cart_id, connection=conn)

        return await self.get_order_details(order_id)

    # =========================================================================
    # ORDER DETAILS & LISTING
    # =========================================================================

    async def get_order_details(self, order_id: UUID) -> OrderResponse:
        order_record = await order_repository.get_by_id(order_id)
        if not order_record:
            raise NotFoundException(message="Order not found", error_code="ORDER_NOT_FOUND")

        items_records = await order_repository.get_items_by_order_id(order_id)
        order_items = [OrderItemResponse.model_validate(dict(i)) for i in items_records]

        customer_info = None
        if order_record.get("customer_name"):
            customer_info = OrderCustomerInfo(
                id=order_record["user_id"],
                name=order_record["customer_name"],
                email=order_record["customer_email"]
            )

        shipping_addr = order_record.get("shipping_address")
        if isinstance(shipping_addr, str):
            try:
                shipping_addr = json.loads(shipping_addr)
            except Exception:
                pass

        return OrderResponse(
            id=order_record["id"],
            user_id=order_record["user_id"],
            customer=customer_info,
            status=order_record["status"],
            payment_status=order_record["payment_status"],
            subtotal=Decimal(str(order_record["subtotal"])),
            discount_amount=Decimal(str(order_record["discount_amount"])),
            shipping_amount=Decimal(str(order_record["shipping_amount"])),
            total_amount=Decimal(str(order_record["total_amount"])),
            currency=order_record.get("currency") or "INR",
            coupon_code=order_record.get("coupon_code"),
            shipping_address=shipping_addr,
            razorpay_order_id=order_record.get("razorpay_order_id"),
            razorpay_payment_id=order_record.get("razorpay_payment_id"),
            razorpay_signature=order_record.get("razorpay_signature"),
            items=order_items,
            is_active=bool(order_record.get("is_active", True)),
            is_deleted=bool(order_record.get("is_deleted", False)),
            created_at=order_record["created_at"],
            updated_at=order_record["updated_at"]
        )

    async def get_user_order(self, order_id: UUID, user_id: UUID) -> OrderResponse:
        order = await self.get_order_details(order_id)
        if order.user_id != user_id:
            raise NotFoundException(message="Order not found", error_code="ORDER_NOT_FOUND")
        return order

    async def list_user_orders(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[OrderResponse]:
        records, total = await order_repository.list_by_user(user_id, page=page, limit=limit)
        orders: List[OrderResponse] = []
        for r in records:
            items_records = await order_repository.get_items_by_order_id(r["id"])
            order_items = [OrderItemResponse.model_validate(dict(i)) for i in items_records]

            shipping_addr = r.get("shipping_address")
            if isinstance(shipping_addr, str):
                try:
                    shipping_addr = json.loads(shipping_addr)
                except Exception:
                    pass

            orders.append(OrderResponse(
                id=r["id"],
                user_id=r["user_id"],
                customer=OrderCustomerInfo(id=r["user_id"], name=r["customer_name"], email=r["customer_email"]),
                status=r["status"],
                payment_status=r["payment_status"],
                subtotal=Decimal(str(r["subtotal"])),
                discount_amount=Decimal(str(r["discount_amount"])),
                shipping_amount=Decimal(str(r["shipping_amount"])),
                total_amount=Decimal(str(r["total_amount"])),
                currency=r.get("currency") or "INR",
                coupon_code=r.get("coupon_code"),
                shipping_address=shipping_addr,
                razorpay_order_id=r.get("razorpay_order_id"),
                razorpay_payment_id=r.get("razorpay_payment_id"),
                razorpay_signature=r.get("razorpay_signature"),
                items=order_items,
                is_active=bool(r.get("is_active", True)),
                is_deleted=bool(r.get("is_deleted", False)),
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            ))

        pagination = calculate_pagination(total, page, limit)
        return PaginatedResponse(data=orders, pagination=pagination)

    async def list_admin_orders(
        self,
        status: Optional[str] = None,
        payment_status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[OrderResponse]:
        records, total = await order_repository.list_admin(
            status=status,
            payment_status=payment_status,
            date_from=date_from,
            date_to=date_to,
            search=search,
            page=page,
            limit=limit
        )
        orders: List[OrderResponse] = []
        for r in records:
            items_records = await order_repository.get_items_by_order_id(r["id"])
            order_items = [OrderItemResponse.model_validate(dict(i)) for i in items_records]

            shipping_addr = r.get("shipping_address")
            if isinstance(shipping_addr, str):
                try:
                    shipping_addr = json.loads(shipping_addr)
                except Exception:
                    pass

            orders.append(OrderResponse(
                id=r["id"],
                user_id=r["user_id"],
                customer=OrderCustomerInfo(id=r["user_id"], name=r["customer_name"], email=r["customer_email"]),
                status=r["status"],
                payment_status=r["payment_status"],
                subtotal=Decimal(str(r["subtotal"])),
                discount_amount=Decimal(str(r["discount_amount"])),
                shipping_amount=Decimal(str(r["shipping_amount"])),
                total_amount=Decimal(str(r["total_amount"])),
                currency=r.get("currency") or "INR",
                coupon_code=r.get("coupon_code"),
                shipping_address=shipping_addr,
                razorpay_order_id=r.get("razorpay_order_id"),
                razorpay_payment_id=r.get("razorpay_payment_id"),
                razorpay_signature=r.get("razorpay_signature"),
                items=order_items,
                is_active=bool(r.get("is_active", True)),
                is_deleted=bool(r.get("is_deleted", False)),
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            ))

        pagination = calculate_pagination(total, page, limit)
        return PaginatedResponse(data=orders, pagination=pagination)

    async def update_order_status(self, order_id: UUID, new_status: OrderStatus) -> OrderResponse:
        current = await order_repository.get_by_id(order_id)
        if not current:
            raise NotFoundException(message="Order not found", error_code="ORDER_NOT_FOUND")

        current_status = current["status"]
        allowed_transitions = VALID_STATUS_TRANSITIONS.get(current_status, [])
        if current_status == "pending":
            allowed_transitions = ["confirmed", "cancelled"]
        if new_status.value not in allowed_transitions:
            raise BadRequestException(
                message=f"Cannot transition order status from '{current_status}' to '{new_status.value}'.",
                error_code="INVALID_STATUS_TRANSITION"
            )

        await order_repository.update_status(order_id, new_status.value)
        return await self.get_order_details(order_id)

    async def update_payment_status(self, order_id: UUID, new_payment_status: PaymentStatus) -> OrderResponse:
        current = await order_repository.get_by_id(order_id)
        if not current:
            raise NotFoundException(message="Order not found", error_code="ORDER_NOT_FOUND")

        await order_repository.update_payment_status(order_id, new_payment_status.value)
        return await self.get_order_details(order_id)


order_service = OrderService()
