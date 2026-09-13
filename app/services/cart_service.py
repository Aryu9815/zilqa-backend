from decimal import Decimal
from typing import List
from uuid import UUID

from app.core.exceptions import BadRequestException, NotFoundException
from app.repositories.cart_repository import cart_repository
from app.repositories.product_repository import product_repository
from app.schemas.cart import CartItemResponse, CartProductSnapshot, CartResponse


class CartService:

    async def get_user_cart(self, user_id: UUID) -> CartResponse:
        cart_record = await cart_repository.get_or_create_cart(user_id)
        cart_id = cart_record["id"]

        items_records = await cart_repository.get_cart_items_with_products(cart_id)
        cart_items: List[CartItemResponse] = []
        grand_subtotal = Decimal("0.00")
        total_items_count = 0

        for r in items_records:
            price = Decimal(str(r["product_price"]))
            qty = int(r["quantity"])
            item_subtotal = price * qty
            grand_subtotal += item_subtotal
            total_items_count += qty

            product_snapshot = CartProductSnapshot(
                id=r["product_id"],
                name=r["product_name"],
                main_image_url=r["main_image_url"],
                price=price,
                is_active=r["product_is_active"]
            )

            cart_items.append(
                CartItemResponse(
                    id=r["id"],
                    product=product_snapshot,
                    quantity=qty,
                    subtotal=item_subtotal
                )
            )

        return CartResponse(
            id=cart_id,
            items=cart_items,
            total_items=total_items_count,
            subtotal=grand_subtotal
        )

    async def add_item_to_cart(self, user_id: UUID, product_id: UUID, quantity: int) -> CartResponse:
        product = await product_repository.get_by_id(product_id)
        if not product:
            raise NotFoundException(message="Product not found", error_code="PRODUCT_NOT_FOUND")

        if not product["is_active"]:
            raise BadRequestException(
                message="This product is currently inactive and cannot be added to cart",
                error_code="PRODUCT_INACTIVE"
            )

        cart_record = await cart_repository.get_or_create_cart(user_id)
        cart_id = cart_record["id"]

        await cart_repository.add_or_increment_item(cart_id, product_id, quantity)
        return await self.get_user_cart(user_id)

    async def update_cart_item(self, user_id: UUID, item_id: UUID, quantity: int) -> CartResponse:
        cart_record = await cart_repository.get_cart_by_user(user_id)
        if not cart_record:
            raise NotFoundException(message="Cart not found", error_code="CART_NOT_FOUND")

        cart_id = cart_record["id"]
        item = await cart_repository.get_item_by_id(item_id)
        if not item or item["cart_id"] != cart_id:
            raise NotFoundException(message="Cart item not found", error_code="CART_ITEM_NOT_FOUND")

        # Check product status
        product = await product_repository.get_by_id(item["product_id"])
        if not product or not product["is_active"]:
            raise BadRequestException(
                message="Product is no longer active",
                error_code="PRODUCT_INACTIVE"
            )

        await cart_repository.update_item_quantity(item_id, quantity)
        return await self.get_user_cart(user_id)

    async def remove_cart_item(self, user_id: UUID, item_id: UUID) -> CartResponse:
        cart_record = await cart_repository.get_cart_by_user(user_id)
        if not cart_record:
            raise NotFoundException(message="Cart not found", error_code="CART_NOT_FOUND")

        cart_id = cart_record["id"]
        deleted = await cart_repository.delete_item(item_id, cart_id)
        if not deleted:
            raise NotFoundException(message="Cart item not found", error_code="CART_ITEM_NOT_FOUND")

        return await self.get_user_cart(user_id)

    async def clear_cart(self, user_id: UUID) -> CartResponse:
        cart_record = await cart_repository.get_or_create_cart(user_id)
        await cart_repository.clear_cart(cart_record["id"])
        return await self.get_user_cart(user_id)


cart_service = CartService()
