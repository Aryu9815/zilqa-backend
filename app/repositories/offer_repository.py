from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional, Tuple
from uuid import UUID
import asyncpg

from app.core.database import get_transaction
from app.repositories.base_repository import BaseRepository
from app.schemas.offer import OfferCreate, OfferType, OfferUpdate


class OfferRepository(BaseRepository):

    async def get_by_id(
        self,
        offer_id: UUID,
        include_deleted: bool = False,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        conditions = ["o.id = $1"]
        if not include_deleted:
            conditions.append("o.is_deleted = FALSE")

        query = f"""
            SELECT o.id, o.name, o.description, o.offer_type, o.discount_type, o.discount_value,
                   o.coupon_code, o.minimum_order_amount, o.maximum_discount_amount,
                   o.start_date, o.end_date, o.usage_limit, o.used_count,
                   o.is_active, o.is_deleted, o.created_at, o.updated_at,
                   COALESCE(
                       ARRAY(
                           SELECT op.product_id 
                           FROM offer_products op 
                           WHERE op.offer_id = o.id
                       ),
                       '{{}}'::uuid[]
                   ) AS product_ids
            FROM offers o
            WHERE {" AND ".join(conditions)}
        """
        return await self.fetch_one(query, offer_id, connection=connection)

    async def get_by_coupon_code(
        self,
        coupon_code: str,
        is_active_only: bool = True,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        conditions = ["LOWER(o.coupon_code) = LOWER($1)", "o.is_deleted = FALSE"]
        if is_active_only:
            conditions.append("o.is_active = TRUE")

        query = f"""
            SELECT o.id, o.name, o.description, o.offer_type, o.discount_type, o.discount_value,
                   o.coupon_code, o.minimum_order_amount, o.maximum_discount_amount,
                   o.start_date, o.end_date, o.usage_limit, o.used_count,
                   o.is_active, o.is_deleted, o.created_at, o.updated_at,
                   COALESCE(
                       ARRAY(
                           SELECT op.product_id 
                           FROM offer_products op 
                           WHERE op.offer_id = o.id
                       ),
                       '{{}}'::uuid[]
                   ) AS product_ids
            FROM offers o
            WHERE {" AND ".join(conditions)}
        """
        return await self.fetch_one(query, coupon_code.strip(), connection=connection)

    async def list_offers(
        self,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        offer_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        include_deleted: bool = False,
        connection: Optional[asyncpg.Connection] = None
    ) -> Tuple[List[asyncpg.Record], int]:
        conditions = []
        params: List[Any] = []
        idx = 1

        if not include_deleted:
            conditions.append("o.is_deleted = FALSE")

        if is_active is not None:
            conditions.append(f"o.is_active = ${idx}")
            params.append(is_active)
            idx += 1

        if offer_type is not None:
            conditions.append(f"o.offer_type ILIKE ${idx}")
            params.append(offer_type.strip())
            idx += 1

        if search:
            search_pattern = f"%{search.strip()}%"
            conditions.append(f"(o.name ILIKE ${idx} OR o.description ILIKE ${idx} OR o.coupon_code ILIKE ${idx})")
            params.append(search_pattern)
            idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Count total
        count_query = f"SELECT COUNT(*) FROM offers o {where_clause}"
        total = await self.fetch_val(count_query, *params, connection=connection) or 0

        offset = (page - 1) * limit
        params.extend([limit, offset])

        query = f"""
            SELECT o.id, o.name, o.description, o.offer_type, o.discount_type, o.discount_value,
                   o.coupon_code, o.minimum_order_amount, o.maximum_discount_amount,
                   o.start_date, o.end_date, o.usage_limit, o.used_count,
                   o.is_active, o.is_deleted, o.created_at, o.updated_at,
                   COALESCE(
                       ARRAY(
                           SELECT op.product_id 
                           FROM offer_products op 
                           WHERE op.offer_id = o.id
                       ),
                       '{{}}'::uuid[]
                   ) AS product_ids
            FROM offers o
            {where_clause}
            ORDER BY o.created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        records = await self.fetch_all(query, *params, connection=connection)
        return records, total

    async def get_active_offers(
        self,
        now: Optional[datetime] = None,
        connection: Optional[asyncpg.Connection] = None
    ) -> List[asyncpg.Record]:
        """Fetch all currently active, non-deleted offers within validity window."""
        current_time = now or datetime.now(timezone.utc).replace(tzinfo=None)
        query = """
            SELECT o.id, o.name, o.description, o.offer_type, o.discount_type, o.discount_value,
                   o.coupon_code, o.minimum_order_amount, o.maximum_discount_amount,
                   o.start_date, o.end_date, o.usage_limit, o.used_count,
                   o.is_active, o.is_deleted, o.created_at, o.updated_at,
                   COALESCE(
                       ARRAY(
                           SELECT op.product_id 
                           FROM offer_products op 
                           WHERE op.offer_id = o.id
                       ),
                       '{{}}'::uuid[]
                   ) AS product_ids
            FROM offers o
            WHERE o.is_active = TRUE
              AND o.is_deleted = FALSE
              AND o.start_date <= $1
              AND o.end_date >= $1
              AND (o.usage_limit IS NULL OR o.used_count < o.usage_limit)
            ORDER BY o.created_at DESC
        """
        return await self.fetch_all(query, current_time, connection=connection)

    async def create(
        self,
        offer_in: OfferCreate,
        connection: Optional[asyncpg.Connection] = None
    ) -> asyncpg.Record:
        start_date_naive = offer_in.start_date.replace(tzinfo=None) if offer_in.start_date.tzinfo else offer_in.start_date
        end_date_naive = offer_in.end_date.replace(tzinfo=None) if offer_in.end_date.tzinfo else offer_in.end_date

        async def _execute_create(conn: asyncpg.Connection) -> asyncpg.Record:
            query = """
                INSERT INTO offers (
                    name, description, offer_type, discount_type, discount_value,
                    coupon_code, minimum_order_amount, maximum_discount_amount,
                    start_date, end_date, usage_limit, is_active, is_deleted,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id, name, description, offer_type, discount_type, discount_value,
                          coupon_code, minimum_order_amount, maximum_discount_amount,
                          start_date, end_date, usage_limit, used_count,
                          is_active, is_deleted, created_at, updated_at
            """
            record = await self.fetch_one(
                query,
                offer_in.name,
                offer_in.description,
                offer_in.offer_type.value if hasattr(offer_in.offer_type, "value") else str(offer_in.offer_type),
                offer_in.discount_type.value if hasattr(offer_in.discount_type, "value") else str(offer_in.discount_type),
                offer_in.discount_value,
                offer_in.coupon_code,
                offer_in.minimum_order_amount,
                offer_in.maximum_discount_amount,
                start_date_naive,
                end_date_naive,
                offer_in.usage_limit,
                offer_in.is_active,
                connection=conn
            )
            assert record is not None
            offer_id = record["id"]

            # Insert linked products
            if offer_in.product_ids:
                prod_tuples = [(offer_id, pid) for pid in set(offer_in.product_ids)]
                await self.executemany(
                    "INSERT INTO offer_products (offer_id, product_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    prod_tuples,
                    connection=conn
                )

            full_record = await self.get_by_id(offer_id, connection=conn)
            assert full_record is not None
            return full_record


        if connection is not None:
            return await _execute_create(connection)
        else:
            async with get_transaction() as conn:
                return await _execute_create(conn)

    async def update(
        self,
        offer_id: UUID,
        offer_in: OfferUpdate,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        async def _execute_update(conn: asyncpg.Connection) -> Optional[asyncpg.Record]:
            updates = []
            params: List[Any] = []
            idx = 1

            fields = [
                ("name", offer_in.name),
                ("description", offer_in.description),
                ("offer_type", offer_in.offer_type.value if offer_in.offer_type and hasattr(offer_in.offer_type, "value") else offer_in.offer_type),
                ("discount_type", offer_in.discount_type.value if offer_in.discount_type and hasattr(offer_in.discount_type, "value") else offer_in.discount_type),
                ("discount_value", offer_in.discount_value),
                ("coupon_code", offer_in.coupon_code),
                ("minimum_order_amount", offer_in.minimum_order_amount),
                ("maximum_discount_amount", offer_in.maximum_discount_amount),
                ("usage_limit", offer_in.usage_limit),
                ("is_active", offer_in.is_active),
            ]

            for col, val in fields:
                if val is not None:
                    updates.append(f"{col} = ${idx}")
                    params.append(val)
                    idx += 1

            if offer_in.start_date is not None:
                st = offer_in.start_date.replace(tzinfo=None) if offer_in.start_date.tzinfo else offer_in.start_date
                updates.append(f"start_date = ${idx}")
                params.append(st)
                idx += 1

            if offer_in.end_date is not None:
                et = offer_in.end_date.replace(tzinfo=None) if offer_in.end_date.tzinfo else offer_in.end_date
                updates.append(f"end_date = ${idx}")
                params.append(et)
                idx += 1

            if updates:
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(offer_id)
                query = f"""
                    UPDATE offers
                    SET {", ".join(updates)}
                    WHERE id = ${idx} AND is_deleted = FALSE
                """
                await self.execute(query, *params, connection=conn)

            # Sync products if provided
            if offer_in.product_ids is not None:
                await self.execute("DELETE FROM offer_products WHERE offer_id = $1", offer_id, connection=conn)
                if offer_in.product_ids:
                    prod_tuples = [(offer_id, pid) for pid in set(offer_in.product_ids)]
                    await self.executemany(
                        "INSERT INTO offer_products (offer_id, product_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                        prod_tuples,
                        connection=conn
                    )


            return await self.get_by_id(offer_id, connection=conn)

        if connection is not None:
            return await _execute_update(connection)
        else:
            async with get_transaction() as conn:
                return await _execute_update(conn)

    async def delete(
        self,
        offer_id: UUID,
        soft: bool = True,
        connection: Optional[asyncpg.Connection] = None
    ) -> bool:
        if soft:
            query = """
                UPDATE offers
                SET is_deleted = TRUE, is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1 AND is_deleted = FALSE
                RETURNING id
            """
        else:
            query = "DELETE FROM offers WHERE id = $1 RETURNING id"
        res = await self.fetch_one(query, offer_id, connection=connection)
        return res is not None

    async def increment_used_count(
        self,
        offer_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> None:
        query = """
            UPDATE offers
            SET used_count = used_count + 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """
        await self.execute(query, offer_id, connection=connection)

    async def count_user_orders(
        self,
        user_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> int:
        """Count non-cancelled orders for checking First Order Discount eligibility."""
        query = """
            SELECT COUNT(*) 
            FROM orders 
            WHERE user_id = $1 AND status != 'cancelled'
        """
        return await self.fetch_val(query, user_id, connection=connection) or 0


offer_repository = OfferRepository()
