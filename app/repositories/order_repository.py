import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from uuid import UUID
import asyncpg

from app.repositories.base_repository import BaseRepository


class OrderRepository(BaseRepository):

    async def create_order(
        self,
        user_id: UUID,
        status: str,
        payment_status: str,
        subtotal: Decimal,
        discount_amount: Decimal,
        shipping_amount: Decimal,
        total_amount: Decimal,
        shipping_address: Union[Dict[str, Any], str],
        currency: str = "INR",
        coupon_code: Optional[str] = None,
        razorpay_order_id: Optional[str] = None,
        razorpay_payment_id: Optional[str] = None,
        razorpay_signature: Optional[str] = None,
        connection: Optional[asyncpg.Connection] = None
    ) -> asyncpg.Record:
        address_json = shipping_address if isinstance(shipping_address, str) else json.dumps(shipping_address)

        query = """
            INSERT INTO orders (
                user_id, status, payment_status,
                razorpay_order_id, razorpay_payment_id, razorpay_signature,
                subtotal, discount_amount, shipping_amount, total_amount,
                currency, coupon_code, shipping_address,
                is_active, is_deleted, created_at, updated_at
            )
            VALUES (
                $1, $2, $3,
                $4, $5, $6,
                $7, $8, $9, $10,
                $11, $12, $13::jsonb,
                TRUE, FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            RETURNING id, user_id, status, payment_status,
                      razorpay_order_id, razorpay_payment_id, razorpay_signature,
                      subtotal, discount_amount, shipping_amount, total_amount,
                      currency, coupon_code, shipping_address,
                      is_active, is_deleted, created_at, updated_at
        """
        record = await self.fetch_one(
            query,
            user_id,
            status,
            payment_status,
            razorpay_order_id,
            razorpay_payment_id,
            razorpay_signature,
            subtotal,
            discount_amount,
            shipping_amount,
            total_amount,
            currency,
            coupon_code,
            address_json,
            connection=connection
        )
        assert record is not None
        return record

    async def create_order_items(
        self,
        items_data: Sequence[Tuple[
            UUID,           # order_id
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
        ]],
        connection: Optional[asyncpg.Connection] = None
    ) -> None:
        query = """
            INSERT INTO order_items (
                order_id, product_id, product_name, product_image_url,
                price, quantity, unit_price,
                discount_type, discount_value, discount_amount,
                final_unit_price, total_price,
                is_active, is_deleted, created_at, updated_at
            )
            VALUES (
                $1, $2, $3, $4,
                $5, $6, $7,
                $8, $9, $10,
                $11, $12,
                TRUE, FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
        """
        await self.executemany(query, items_data, connection=connection)

    async def get_by_id(
        self,
        order_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            SELECT o.id, o.user_id, o.status, o.payment_status,
                   o.razorpay_order_id, o.razorpay_payment_id, o.razorpay_signature,
                   o.subtotal, o.discount_amount, o.shipping_amount, o.total_amount,
                   o.currency, o.coupon_code, o.shipping_address,
                   o.is_active, o.is_deleted, o.created_at, o.updated_at,
                   u.name AS customer_name, u.email AS customer_email
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE o.id = $1
        """
        return await self.fetch_one(query, order_id, connection=connection)

    async def get_by_razorpay_order_id(
        self,
        razorpay_order_id: str,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            SELECT o.id, o.user_id, o.status, o.payment_status,
                   o.razorpay_order_id, o.razorpay_payment_id, o.razorpay_signature,
                   o.subtotal, o.discount_amount, o.shipping_amount, o.total_amount,
                   o.currency, o.coupon_code, o.shipping_address,
                   o.is_active, o.is_deleted, o.created_at, o.updated_at,
                   u.name AS customer_name, u.email AS customer_email
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE o.razorpay_order_id = $1
        """
        return await self.fetch_one(query, razorpay_order_id, connection=connection)

    async def get_items_by_order_id(
        self,
        order_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> List[asyncpg.Record]:
        query = """
            SELECT id, order_id, product_id, product_name, product_image_url,
                   price, quantity, unit_price,
                   discount_type, discount_value, discount_amount,
                   final_unit_price, total_price,
                   is_active, is_deleted, created_at, updated_at
            FROM order_items
            WHERE order_id = $1
            ORDER BY id ASC
        """
        return await self.fetch_all(query, order_id, connection=connection)

    async def list_by_user(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 20,
        connection: Optional[asyncpg.Connection] = None
    ) -> Tuple[List[asyncpg.Record], int]:
        count_query = "SELECT COUNT(*) FROM orders WHERE user_id = $1 AND is_deleted = FALSE"
        total = await self.fetch_val(count_query, user_id, connection=connection) or 0

        offset = (page - 1) * limit
        query = """
            SELECT o.id, o.user_id, o.status, o.payment_status,
                   o.razorpay_order_id, o.razorpay_payment_id, o.razorpay_signature,
                   o.subtotal, o.discount_amount, o.shipping_amount, o.total_amount,
                   o.currency, o.coupon_code, o.shipping_address,
                   o.is_active, o.is_deleted, o.created_at, o.updated_at,
                   u.name AS customer_name, u.email AS customer_email
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE o.user_id = $1 AND o.is_deleted = FALSE
            ORDER BY o.created_at DESC
            LIMIT $2 OFFSET $3
        """
        records = await self.fetch_all(query, user_id, limit, offset, connection=connection)
        return records, total

    async def list_admin(
        self,
        status: Optional[str] = None,
        payment_status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        connection: Optional[asyncpg.Connection] = None
    ) -> Tuple[List[asyncpg.Record], int]:
        conditions = ["o.is_deleted = FALSE"]
        params: List[Any] = []
        idx = 1

        if status:
            conditions.append(f"o.status = ${idx}")
            params.append(status)
            idx += 1

        if payment_status:
            conditions.append(f"o.payment_status = ${idx}")
            params.append(payment_status)
            idx += 1

        if date_from:
            conditions.append(f"o.created_at >= ${idx}")
            params.append(date_from)
            idx += 1

        if date_to:
            conditions.append(f"o.created_at <= ${idx}")
            params.append(date_to)
            idx += 1

        if search:
            search_pattern = f"%{search.strip()}%"
            conditions.append(f"""(
                CAST(o.id AS TEXT) ILIKE ${idx}
                OR o.razorpay_order_id ILIKE ${idx}
                OR u.name ILIKE ${idx}
                OR u.email ILIKE ${idx}
            )""")
            params.append(search_pattern)
            idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}"

        count_query = f"""
            SELECT COUNT(*)
            FROM orders o
            JOIN users u ON o.user_id = u.id
            {where_clause}
        """
        total = await self.fetch_val(count_query, *params, connection=connection) or 0

        offset = (page - 1) * limit
        params.extend([limit, offset])

        query = f"""
            SELECT o.id, o.user_id, o.status, o.payment_status,
                   o.razorpay_order_id, o.razorpay_payment_id, o.razorpay_signature,
                   o.subtotal, o.discount_amount, o.shipping_amount, o.total_amount,
                   o.currency, o.coupon_code, o.shipping_address,
                   o.is_active, o.is_deleted, o.created_at, o.updated_at,
                   u.name AS customer_name, u.email AS customer_email
            FROM orders o
            JOIN users u ON o.user_id = u.id
            {where_clause}
            ORDER BY o.created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        records = await self.fetch_all(query, *params, connection=connection)
        return records, total

    async def update_status(
        self,
        order_id: UUID,
        status: str,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            UPDATE orders
            SET status = $2, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1 AND is_deleted = FALSE
            RETURNING id, user_id, status, payment_status,
                      razorpay_order_id, razorpay_payment_id, razorpay_signature,
                      subtotal, discount_amount, shipping_amount, total_amount,
                      currency, coupon_code, shipping_address,
                      is_active, is_deleted, created_at, updated_at
        """
        return await self.fetch_one(query, order_id, status, connection=connection)

    async def update_payment_status(
        self,
        order_id: UUID,
        payment_status: str,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            UPDATE orders
            SET payment_status = $2, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1 AND is_deleted = FALSE
            RETURNING id, user_id, status, payment_status,
                      razorpay_order_id, razorpay_payment_id, razorpay_signature,
                      subtotal, discount_amount, shipping_amount, total_amount,
                      currency, coupon_code, shipping_address,
                      is_active, is_deleted, created_at, updated_at
        """
        return await self.fetch_one(query, order_id, payment_status, connection=connection)

    async def update_razorpay_payment(
        self,
        order_id: UUID,
        razorpay_payment_id: str,
        razorpay_signature: str,
        payment_status: str = "paid",
        status: str = "confirmed",
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            UPDATE orders
            SET razorpay_payment_id = $2,
                razorpay_signature = $3,
                payment_status = $4,
                status = $5,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1 AND is_deleted = FALSE
            RETURNING id, user_id, status, payment_status,
                      razorpay_order_id, razorpay_payment_id, razorpay_signature,
                      subtotal, discount_amount, shipping_amount, total_amount,
                      currency, coupon_code, shipping_address,
                      is_active, is_deleted, created_at, updated_at
        """
        return await self.fetch_one(
            query,
            order_id,
            razorpay_payment_id,
            razorpay_signature,
            payment_status,
            status,
            connection=connection
        )


order_repository = OrderRepository()
