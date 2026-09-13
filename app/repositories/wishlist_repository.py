from typing import List, Optional
from uuid import UUID
import asyncpg

from app.repositories.base_repository import BaseRepository


class WishlistRepository(BaseRepository):

    async def list_by_user(
        self,
        user_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> List[asyncpg.Record]:
        query = """
            SELECT wi.id, wi.user_id, wi.product_id, wi.created_at,
                   p.name AS product_name, p.main_image_url, p.price AS product_price,
                   p.is_active AS product_is_active, p.category_ids
            FROM wishlist_items wi
            JOIN products p ON wi.product_id = p.id
            WHERE wi.user_id = $1 AND p.is_active = TRUE AND p.is_deleted = FALSE
            ORDER BY wi.created_at DESC
        """
        return await self.fetch_all(query, user_id, connection=connection)

    async def add_item(
        self,
        user_id: UUID,
        product_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> asyncpg.Record:
        query = """
            INSERT INTO wishlist_items (user_id, product_id, created_at)
            VALUES ($1, $2, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, product_id) DO NOTHING
            RETURNING id, user_id, product_id, created_at
        """
        record = await self.fetch_one(query, user_id, product_id, connection=connection)
        if not record:
            # Already existed, fetch existing
            get_query = """
                SELECT id, user_id, product_id, created_at
                FROM wishlist_items
                WHERE user_id = $1 AND product_id = $2
            """
            record = await self.fetch_one(get_query, user_id, product_id, connection=connection)
        assert record is not None
        return record

    async def remove_item(
        self,
        user_id: UUID,
        product_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> bool:
        query = "DELETE FROM wishlist_items WHERE user_id = $1 AND product_id = $2 RETURNING id"
        res = await self.fetch_one(query, user_id, product_id, connection=connection)
        return res is not None


wishlist_repository = WishlistRepository()
