from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
import asyncpg

from app.core.database import get_transaction
from app.core.exceptions import BadRequestException, NotFoundException
from app.repositories.address_repository import address_repository
from app.repositories.cart_repository import cart_repository
from app.repositories.order_repository import order_repository
from app.repositories.product_repository import product_repository
from app.schemas.address import AddressResponse
from app.schemas.common import PaginatedResponse
from app.schemas.order import (
    OrderCreate,
    OrderCustomerInfo,
    OrderItemResponse,
    OrderResponse,
    OrderStatus,
    PaymentStatus,
)
from app.utils.helpers import calculate_pagination


VALID_STATUS_TRANSITIONS: Dict[str, List[str]] = {
    "pending": ["confirmed", "cancelled"],
    "confirmed": ["processing", "cancelled"],
    "processing": ["shipped", "cancelled"],
    "shipped": ["delivered"],
    "delivered": [],
    "cancelled": []
}


class OrderService:

    async def create_order(self, user_id: UUID, order_in: OrderCreate) -> OrderResponse:
        # 1. Validate shipping address belongs to user
        address_record = await address_repository.get_by_id_and_user(order_in.address_id, user_id)
        if not address_record:
            raise BadRequestException(
                message="Specified shipping address was not found or does not belong to you",
                error_code="INVALID_SHIPPING_ADDRESS"
            )

        # 2. Load user's cart
        cart_record = await cart_repository.get_or_create_cart(user_id)
        cart_id = cart_record["id"]
        cart_items_records = await cart_repository.get_cart_items_with_products(cart_id)

        if not cart_items_records:
            raise BadRequestException(
                message="Cannot create order because your shopping cart is empty",
                error_code="EMPTY_CART"
            )

        # 3. Validate each product is active and calculate live pricing from database
        calculated_items: List[Tuple[Optional[UUID], str, Optional[str], int, Decimal, Decimal]] = []
        subtotal = Decimal("0.00")

        for item in cart_items_records:
            product_id = item["product_id"]
            live_product = await product_repository.get_by_id(product_id)

            if not live_product or not live_product["is_active"]:
                raise BadRequestException(
                    message=f"Product '{item['product_name']}' is currently unavailable or deactivated",
                    error_code="PRODUCT_UNAVAILABLE"
                )

            unit_price = Decimal(str(live_product["price"]))
            quantity = int(item["quantity"])
            item_subtotal = unit_price * quantity
            subtotal += item_subtotal

            calculated_items.append((
                product_id,
                live_product["name"],
                live_product["main_image_url"],
                quantity,
                unit_price,
                item_subtotal
            ))

        discount = Decimal("0.00")
        shipping_fee = Decimal("0.00")  # Standard free shipping default
        total_amount = subtotal - discount + shipping_fee

        # 4. Atomically commit order, items, and clear cart in a single asyncpg transaction
        async with get_transaction() as conn:
            order_record = await order_repository.create_order(
                user_id=user_id,
                address_id=order_in.address_id,
                status=OrderStatus.PENDING.value,
                payment_status=PaymentStatus.PENDING.value,
                payment_method=order_in.payment_method,
                subtotal=subtotal,
                discount=discount,
                shipping_fee=shipping_fee,
                total_amount=total_amount,
                connection=conn
            )
            order_id = order_record["id"]

            # Prepare items tuples with generated order_id
            order_items_to_insert = [
                (order_id, p_id, p_name, p_img, qty, price, item_tot)
                for p_id, p_name, p_img, qty, price, item_tot in calculated_items
            ]
            await order_repository.create_order_items(order_items_to_insert, connection=conn)

            # Clear cart
            await cart_repository.clear_cart(cart_id, connection=conn)

        return await self.get_order_details(order_id)

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

        shipping_addr = None
        if order_record.get("address_id") and order_record.get("addr_full_name"):
            shipping_addr = AddressResponse(
                id=order_record["address_id"],
                user_id=order_record["user_id"],
                full_name=order_record["addr_full_name"],
                phone=order_record["addr_phone"],
                address_line_1=order_record["addr_line1"],
                address_line_2=order_record.get("addr_line2"),
                city=order_record["addr_city"],
                state=order_record["addr_state"],
                postal_code=order_record["addr_postal_code"],
                country=order_record["addr_country"],
                is_default=order_record["addr_is_default"],
                created_at=order_record["addr_created_at"],
                updated_at=order_record["addr_updated_at"]
            )

        return OrderResponse(
            id=order_record["id"],
            user_id=order_record["user_id"],
            customer=customer_info,
            address_id=order_record["address_id"],
            shipping_address=shipping_addr,
            status=order_record["status"],
            payment_status=order_record["payment_status"],
            payment_method=order_record["payment_method"],
            subtotal=Decimal(str(order_record["subtotal"])),
            discount=Decimal(str(order_record["discount"])),
            shipping_fee=Decimal(str(order_record["shipping_fee"])),
            total_amount=Decimal(str(order_record["total_amount"])),
            items=order_items,
            created_at=order_record["created_at"],
            updated_at=order_record["updated_at"]
        )

    async def list_user_orders(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[OrderResponse]:
        records, total = await order_repository.list_by_user(user_id, page=page, limit=limit)
        items: List[OrderResponse] = []
        for r in records:
            items_records = await order_repository.get_items_by_order_id(r["id"])
            order_items = [OrderItemResponse.model_validate(dict(i)) for i in items_records]

            shipping_addr = None
            if r.get("address_id") and r.get("addr_full_name"):
                shipping_addr = AddressResponse(
                    id=r["address_id"],
                    user_id=r["user_id"],
                    full_name=r["addr_full_name"],
                    phone=r["addr_phone"],
                    address_line_1=r["addr_line1"],
                    address_line_2=r.get("addr_line2"),
                    city=r["addr_city"],
                    state=r["addr_state"],
                    postal_code=r["addr_postal_code"],
                    country=r["addr_country"],
                    is_default=r["addr_is_default"],
                    created_at=r["addr_created_at"],
                    updated_at=r["addr_updated_at"]
                )

            items.append(
                OrderResponse(
                    id=r["id"],
                    user_id=r["user_id"],
                    customer=None,
                    address_id=r["address_id"],
                    shipping_address=shipping_addr,
                    status=r["status"],
                    payment_status=r["payment_status"],
                    payment_method=r["payment_method"],
                    subtotal=Decimal(str(r["subtotal"])),
                    discount=Decimal(str(r["discount"])),
                    shipping_fee=Decimal(str(r["shipping_fee"])),
                    total_amount=Decimal(str(r["total_amount"])),
                    items=order_items,
                    created_at=r["created_at"],
                    updated_at=r["updated_at"]
                )
            )

        pagination = calculate_pagination(total=total, page=page, limit=limit)
        return PaginatedResponse(data=items, pagination=pagination)

    async def get_user_order(self, order_id: UUID, user_id: UUID) -> OrderResponse:
        order = await self.get_order_details(order_id)
        if order.user_id != user_id:
            raise NotFoundException(message="Order not found", error_code="ORDER_NOT_FOUND")
        return order

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
        items: List[OrderResponse] = []
        for r in records:
            items_records = await order_repository.get_items_by_order_id(r["id"])
            order_items = [OrderItemResponse.model_validate(dict(i)) for i in items_records]

            customer_info = OrderCustomerInfo(
                id=r["user_id"],
                name=r["customer_name"],
                email=r["customer_email"]
            )

            shipping_addr = None
            if r.get("address_id") and r.get("addr_full_name"):
                shipping_addr = AddressResponse(
                    id=r["address_id"],
                    user_id=r["user_id"],
                    full_name=r["addr_full_name"],
                    phone=r["addr_phone"],
                    address_line_1=r["addr_line1"],
                    address_line_2=r.get("addr_line2"),
                    city=r["addr_city"],
                    state=r["addr_state"],
                    postal_code=r["addr_postal_code"],
                    country=r["addr_country"],
                    is_default=r["addr_is_default"],
                    created_at=r["addr_created_at"],
                    updated_at=r["addr_updated_at"]
                )

            items.append(
                OrderResponse(
                    id=r["id"],
                    user_id=r["user_id"],
                    customer=customer_info,
                    address_id=r["address_id"],
                    shipping_address=shipping_addr,
                    status=r["status"],
                    payment_status=r["payment_status"],
                    payment_method=r["payment_method"],
                    subtotal=Decimal(str(r["subtotal"])),
                    discount=Decimal(str(r["discount"])),
                    shipping_fee=Decimal(str(r["shipping_fee"])),
                    total_amount=Decimal(str(r["total_amount"])),
                    items=order_items,
                    created_at=r["created_at"],
                    updated_at=r["updated_at"]
                )
            )

        pagination = calculate_pagination(total=total, page=page, limit=limit)
        return PaginatedResponse(data=items, pagination=pagination)

    async def update_order_status(self, order_id: UUID, new_status: OrderStatus) -> OrderResponse:
        current = await order_repository.get_by_id(order_id)
        if not current:
            raise NotFoundException(message="Order not found", error_code="ORDER_NOT_FOUND")

        current_status = current["status"]
        allowed_transitions = VALID_STATUS_TRANSITIONS.get(current_status, [])

        if new_status.value != current_status and new_status.value not in allowed_transitions:
            raise BadRequestException(
                message=f"Invalid status transition from '{current_status}' to '{new_status.value}'. Allowed next states: {allowed_transitions}",
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
