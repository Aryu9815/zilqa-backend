from typing import List, Optional
from uuid import UUID
import asyncpg

from app.repositories.base_repository import BaseRepository


class CartRepository(BaseRepository):

    async def get_or_create_cart(
        self,
        user_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> asyncpg.Record:
        query = """
            INSERT INTO carts (user_id, created_at, updated_at)
            VALUES ($1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE
            SET updated_at = CURRENT_TIMESTAMP
            RETURNING id, user_id, created_at, updated_at
        """
        record = await self.fetch_one(query, user_id, connection=connection)
        assert record is not None
        return record

    async def get_cart_by_user(
        self,
        user_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = "SELECT id, user_id, created_at, updated_at FROM carts WHERE user_id = $1"
        return await self.fetch_one(query, user_id, connection=connection)

    async def get_cart_items_with_products(
        self,
        cart_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> List[asyncpg.Record]:
        query = """
            SELECT ci.id, ci.cart_id, ci.product_id, ci.quantity, ci.created_at, ci.updated_at,
                   p.name AS product_name, p.main_image_url, p.price AS product_price,
                   p.is_active AS product_is_active
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.id
            WHERE ci.cart_id = $1 AND p.is_active = TRUE AND p.is_deleted = FALSE
            ORDER BY ci.created_at ASC
        """
        return await self.fetch_all(query, cart_id, connection=connection)

    async def get_item_by_id(
        self,
        item_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = "SELECT id, cart_id, product_id, quantity, created_at, updated_at FROM cart_items WHERE id = $1"
        return await self.fetch_one(query, item_id, connection=connection)

    async def get_item_by_cart_and_product(
        self,
        cart_id: UUID,
        product_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            SELECT id, cart_id, product_id, quantity, created_at, updated_at
            FROM cart_items
            WHERE cart_id = $1 AND product_id = $2
        """
        return await self.fetch_one(query, cart_id, product_id, connection=connection)

    async def add_or_increment_item(
        self,
        cart_id: UUID,
        product_id: UUID,
        quantity: int,
        connection: Optional[asyncpg.Connection] = None
    ) -> asyncpg.Record:
        query = """
            INSERT INTO cart_items (cart_id, product_id, quantity, created_at, updated_at)
            VALUES ($1, $2, $3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (cart_id, product_id) DO UPDATE
            SET quantity = cart_items.quantity + EXCLUDED.quantity,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id, cart_id, product_id, quantity, created_at, updated_at
        """
        record = await self.fetch_one(query, cart_id, product_id, quantity, connection=connection)
        assert record is not None
        return record

    async def update_item_quantity(
        self,
        item_id: UUID,
        quantity: int,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            UPDATE cart_items
            SET quantity = $2, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING id, cart_id, product_id, quantity, created_at, updated_at
        """
        return await self.fetch_one(query, item_id, quantity, connection=connection)

    async def delete_item(
        self,
        item_id: UUID,
        cart_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> bool:
        query = "DELETE FROM cart_items WHERE id = $1 AND cart_id = $2 RETURNING id"
        res = await self.fetch_one(query, item_id, cart_id, connection=connection)
        return res is not None

    async def clear_cart(
        self,
        cart_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> None:
        query = "DELETE FROM cart_items WHERE cart_id = $1"
        await self.execute(query, cart_id, connection=connection)


cart_repository = CartRepository()
