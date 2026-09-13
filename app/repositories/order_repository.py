from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional, Sequence, Tuple
from uuid import UUID
import asyncpg

from app.repositories.base_repository import BaseRepository
from app.schemas.order import OrderStatus, PaymentStatus


class OrderRepository(BaseRepository):

    async def create_order(
        self,
        user_id: UUID,
        address_id: Optional[UUID],
        status: str,
        payment_status: str,
        payment_method: str,
        subtotal: Decimal,
        discount: Decimal,
        shipping_fee: Decimal,
        total_amount: Decimal,
        connection: Optional[asyncpg.Connection] = None
    ) -> asyncpg.Record:
        query = """
            INSERT INTO orders (
                user_id, address_id, status, payment_status, payment_method,
                subtotal, discount, shipping_fee, total_amount, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, user_id, address_id, status, payment_status, payment_method,
                      subtotal, discount, shipping_fee, total_amount, created_at, updated_at
        """
        record = await self.fetch_one(
            query,
            user_id,
            address_id,
            status,
            payment_status,
            payment_method,
            subtotal,
            discount,
            shipping_fee,
            total_amount,
            connection=connection
        )
        assert record is not None
        return record

    async def create_order_items(
        self,
        items_data: Sequence[Tuple[UUID, Optional[UUID], str, Optional[str], int, Decimal, Decimal]],
        connection: Optional[asyncpg.Connection] = None
    ) -> None:
        query = """
            INSERT INTO order_items (
                order_id, product_id, product_name, product_image_url,
                quantity, unit_price, subtotal
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        await self.executemany(query, items_data, connection=connection)

    async def get_by_id(
        self,
        order_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            SELECT o.id, o.user_id, o.address_id, o.status, o.payment_status, o.payment_method,
                   o.subtotal, o.discount, o.shipping_fee, o.total_amount, o.created_at, o.updated_at,
                   u.name AS customer_name, u.email AS customer_email,
                   a.full_name AS addr_full_name, a.phone AS addr_phone,
                   a.address_line_1 AS addr_line1, a.address_line_2 AS addr_line2,
                   a.city AS addr_city, a.state AS addr_state, a.postal_code AS addr_postal_code,
                   a.country AS addr_country, a.is_default AS addr_is_default,
                   a.created_at AS addr_created_at, a.updated_at AS addr_updated_at
            FROM orders o
            JOIN users u ON o.user_id = u.id
            LEFT JOIN user_addresses a ON o.address_id = a.id
            WHERE o.id = $1
        """
        return await self.fetch_one(query, order_id, connection=connection)

    async def get_items_by_order_id(
        self,
        order_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> List[asyncpg.Record]:
        query = """
            SELECT id, order_id, product_id, product_name, product_image_url,
                   quantity, unit_price, subtotal
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
        count_query = "SELECT COUNT(*) FROM orders WHERE user_id = $1"
        total = await self.fetch_val(count_query, user_id, connection=connection) or 0

        offset = (page - 1) * limit
        query = """
            SELECT o.id, o.user_id, o.address_id, o.status, o.payment_status, o.payment_method,
                   o.subtotal, o.discount, o.shipping_fee, o.total_amount, o.created_at, o.updated_at,
                   u.name AS customer_name, u.email AS customer_email,
                   a.full_name AS addr_full_name, a.phone AS addr_phone,
                   a.address_line_1 AS addr_line1, a.address_line_2 AS addr_line2,
                   a.city AS addr_city, a.state AS addr_state, a.postal_code AS addr_postal_code,
                   a.country AS addr_country, a.is_default AS addr_is_default,
                   a.created_at AS addr_created_at, a.updated_at AS addr_updated_at
            FROM orders o
            JOIN users u ON o.user_id = u.id
            LEFT JOIN user_addresses a ON o.address_id = a.id
            WHERE o.user_id = $1
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
        conditions = []
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
                OR u.name ILIKE ${idx}
                OR u.email ILIKE ${idx}
            )""")
            params.append(search_pattern)
            idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

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
            SELECT o.id, o.user_id, o.address_id, o.status, o.payment_status, o.payment_method,
                   o.subtotal, o.discount, o.shipping_fee, o.total_amount, o.created_at, o.updated_at,
                   u.name AS customer_name, u.email AS customer_email,
                   a.full_name AS addr_full_name, a.phone AS addr_phone,
                   a.address_line_1 AS addr_line1, a.address_line_2 AS addr_line2,
                   a.city AS addr_city, a.state AS addr_state, a.postal_code AS addr_postal_code,
                   a.country AS addr_country, a.is_default AS addr_is_default,
                   a.created_at AS addr_created_at, a.updated_at AS addr_updated_at
            FROM orders o
            JOIN users u ON o.user_id = u.id
            LEFT JOIN user_addresses a ON o.address_id = a.id
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
            WHERE id = $1
            RETURNING id, user_id, address_id, status, payment_status, payment_method,
                      subtotal, discount, shipping_fee, total_amount, created_at, updated_at
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
            WHERE id = $1
            RETURNING id, user_id, address_id, status, payment_status, payment_method,
                      subtotal, discount, shipping_fee, total_amount, created_at, updated_at
        """
        return await self.fetch_one(query, order_id, payment_status, connection=connection)


order_repository = OrderRepository()
