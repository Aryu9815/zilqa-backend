from decimal import Decimal
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
            INSERT INTO carts (user_id, is_deleted, is_active, created_at, updated_at)
            VALUES ($1, FALSE, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE
            SET is_deleted = FALSE, is_active = TRUE, updated_at = CURRENT_TIMESTAMP
            RETURNING id, user_id, coupon_code, coupon_discount_type, coupon_discount_value,
                      coupon_discount_amount, subtotal, total_discount, shipping_amount, total_amount,
                      is_active, is_deleted, created_at, updated_at
        """
        record = await self.fetch_one(query, user_id, connection=connection)
        assert record is not None
        return record

    async def get_cart_by_user(
        self,
        user_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            SELECT id, user_id, coupon_code, coupon_discount_type, coupon_discount_value,
                   coupon_discount_amount, subtotal, total_discount, shipping_amount, total_amount,
                   is_active, is_deleted, created_at, updated_at
            FROM carts
            WHERE user_id = $1 AND is_deleted = FALSE
        """
        return await self.fetch_one(query, user_id, connection=connection)

    async def get_cart_items_with_products(
        self,
        cart_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> List[asyncpg.Record]:
        query = """
            SELECT ci.id, ci.cart_id, ci.product_id, ci.quantity,
                   ci.offer_id, ci.unit_price, ci.discount_type, ci.discount_value,
                   ci.discount_amount, ci.final_unit_price, ci.total_price,
                   ci.is_active, ci.is_deleted, ci.created_at, ci.updated_at,
                   p.name AS product_name, p.main_image_url, p.price AS product_price,
                   p.category_ids AS product_category_ids,
                   p.is_active AS product_is_active
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.id
            WHERE ci.cart_id = $1 AND ci.is_deleted = FALSE AND ci.is_active = TRUE AND p.is_active = TRUE AND p.is_deleted = FALSE
            ORDER BY ci.created_at ASC
        """
        return await self.fetch_all(query, cart_id, connection=connection)

    async def get_item_by_id(
        self,
        item_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            SELECT id, cart_id, product_id, quantity,
                   offer_id, unit_price, discount_type, discount_value,
                   discount_amount, final_unit_price, total_price,
                   is_active, is_deleted, created_at, updated_at
            FROM cart_items
            WHERE id = $1 AND is_deleted = FALSE
        """
        return await self.fetch_one(query, item_id, connection=connection)

    async def get_item_by_cart_and_product(
        self,
        cart_id: UUID,
        product_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            SELECT id, cart_id, product_id, quantity,
                   offer_id, unit_price, discount_type, discount_value,
                   discount_amount, final_unit_price, total_price,
                   is_active, is_deleted, created_at, updated_at
            FROM cart_items
            WHERE cart_id = $1 AND product_id = $2 AND is_deleted = FALSE
        """
        return await self.fetch_one(query, cart_id, product_id, connection=connection)

    async def add_or_increment_item(
        self,
        cart_id: UUID,
        product_id: UUID,
        quantity: int,
        offer_id: Optional[UUID] = None,
        unit_price: Decimal = Decimal("0.00"),
        discount_type: Optional[str] = None,
        discount_value: Optional[Decimal] = None,
        discount_amount: Decimal = Decimal("0.00"),
        final_unit_price: Decimal = Decimal("0.00"),
        total_price: Decimal = Decimal("0.00"),
        connection: Optional[asyncpg.Connection] = None
    ) -> asyncpg.Record:
        query = """
            INSERT INTO cart_items (
                cart_id, product_id, quantity,
                offer_id, unit_price, discount_type, discount_value,
                discount_amount, final_unit_price, total_price,
                is_deleted, is_active, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, COALESCE($7, 0.00), COALESCE($8, 0.00), $9, $10, FALSE, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (cart_id, product_id) DO UPDATE
            SET quantity = cart_items.quantity + EXCLUDED.quantity,
                offer_id = EXCLUDED.offer_id,
                unit_price = EXCLUDED.unit_price,
                discount_type = EXCLUDED.discount_type,
                discount_value = EXCLUDED.discount_value,
                discount_amount = EXCLUDED.discount_amount,
                final_unit_price = EXCLUDED.final_unit_price,
                total_price = EXCLUDED.final_unit_price * (cart_items.quantity + EXCLUDED.quantity),
                is_deleted = FALSE,
                is_active = TRUE,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id, cart_id, product_id, quantity,
                      offer_id, unit_price, discount_type, discount_value,
                      discount_amount, final_unit_price, total_price,
                      is_active, is_deleted, created_at, updated_at
        """
        record = await self.fetch_one(
            query,
            cart_id,
            product_id,
            quantity,
            offer_id,
            unit_price,
            discount_type,
            discount_value if discount_value is not None else Decimal("0.00"),
            discount_amount,
            final_unit_price,
            total_price,
            connection=connection
        )
        assert record is not None
        return record

    async def update_item_quantity(
        self,
        item_id: UUID,
        quantity: int,
        total_price: Optional[Decimal] = None,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        if total_price is not None:
            query = """
                UPDATE cart_items
                SET quantity = $2, total_price = $3, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1 AND is_deleted = FALSE
                RETURNING id, cart_id, product_id, quantity,
                          offer_id, unit_price, discount_type, discount_value,
                          discount_amount, final_unit_price, total_price,
                          is_active, is_deleted, created_at, updated_at
            """
            return await self.fetch_one(query, item_id, quantity, total_price, connection=connection)
        else:
            query = """
                UPDATE cart_items
                SET quantity = $2, total_price = final_unit_price * $2, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1 AND is_deleted = FALSE
                RETURNING id, cart_id, product_id, quantity,
                          offer_id, unit_price, discount_type, discount_value,
                          discount_amount, final_unit_price, total_price,
                          is_active, is_deleted, created_at, updated_at
            """
            return await self.fetch_one(query, item_id, quantity, connection=connection)

    async def update_item_offer_and_pricing(
        self,
        item_id: UUID,
        offer_id: Optional[UUID],
        unit_price: Decimal,
        discount_type: Optional[str],
        discount_value: Optional[Decimal],
        discount_amount: Decimal,
        final_unit_price: Decimal,
        total_price: Decimal,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            UPDATE cart_items
            SET offer_id = $2,
                unit_price = $3,
                discount_type = $4,
                discount_value = COALESCE($5, 0.00),
                discount_amount = COALESCE($6, 0.00),
                final_unit_price = $7,
                total_price = $8,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1 AND is_deleted = FALSE
            RETURNING id, cart_id, product_id, quantity,
                      offer_id, unit_price, discount_type, discount_value,
                      discount_amount, final_unit_price, total_price,
                      is_active, is_deleted, created_at, updated_at
        """
        return await self.fetch_one(
            query,
            item_id,
            offer_id,
            unit_price,
            discount_type,
            discount_value if discount_value is not None else Decimal("0.00"),
            discount_amount,
            final_unit_price,
            total_price,
            connection=connection
        )

    async def update_cart_totals_and_coupon(
        self,
        cart_id: UUID,
        coupon_code: Optional[str] = None,
        coupon_discount_type: Optional[str] = None,
        coupon_discount_value: Optional[Decimal] = None,
        coupon_discount_amount: Decimal = Decimal("0.00"),
        subtotal: Decimal = Decimal("0.00"),
        total_discount: Decimal = Decimal("0.00"),
        shipping_amount: Decimal = Decimal("0.00"),
        total_amount: Decimal = Decimal("0.00"),
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            UPDATE carts
            SET coupon_code = $2,
                coupon_discount_type = $3,
                coupon_discount_value = COALESCE($4, 0.00),
                coupon_discount_amount = COALESCE($5, 0.00),
                subtotal = COALESCE($6, 0.00),
                total_discount = COALESCE($7, 0.00),
                shipping_amount = COALESCE($8, 0.00),
                total_amount = COALESCE($9, 0.00),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1 AND is_deleted = FALSE
            RETURNING id, user_id, coupon_code, coupon_discount_type, coupon_discount_value,
                      coupon_discount_amount, subtotal, total_discount, shipping_amount, total_amount,
                      is_active, is_deleted, created_at, updated_at
        """
        return await self.fetch_one(
            query,
            cart_id,
            coupon_code,
            coupon_discount_type,
            coupon_discount_value if coupon_discount_value is not None else Decimal("0.00"),
            coupon_discount_amount,
            subtotal,
            total_discount,
            shipping_amount,
            total_amount,
            connection=connection
        )

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
        """Hard delete all cart items for the specified cart and reset totals."""
        query = "DELETE FROM cart_items WHERE cart_id = $1"
        await self.execute(query, cart_id, connection=connection)

        reset_cart_query = """
            UPDATE carts
            SET coupon_code = NULL,
                coupon_discount_type = NULL,
                coupon_discount_value = 0,
                coupon_discount_amount = 0,
                subtotal = 0,
                total_discount = 0,
                shipping_amount = 0,
                total_amount = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """
        await self.execute(reset_cart_query, cart_id, connection=connection)


cart_repository = CartRepository()
