from typing import List
from uuid import UUID

from app.core.exceptions import NotFoundException
from app.repositories.product_repository import product_repository
from app.repositories.wishlist_repository import wishlist_repository
from app.schemas.wishlist import WishlistItemResponse, WishlistProductSnapshot, WishlistResponse


class WishlistService:

    async def get_user_wishlist(self, user_id: UUID) -> WishlistResponse:
        records = await wishlist_repository.list_by_user(user_id)
        items: List[WishlistItemResponse] = []

        for r in records:
            product_snapshot = WishlistProductSnapshot(
                id=r["product_id"],
                name=r["product_name"],
                main_image_url=r["main_image_url"],
                price=r["product_price"],
                is_active=r["product_is_active"],
                category_ids=r.get("category_ids") or []
            )
            items.append(
                WishlistItemResponse(
                    id=r["id"],
                    product=product_snapshot,
                    created_at=r["created_at"]
                )
            )

        return WishlistResponse(items=items, total_items=len(items))

    async def add_to_wishlist(self, user_id: UUID, product_id: UUID) -> WishlistResponse:
        product = await product_repository.get_by_id(product_id)
        if not product:
            raise NotFoundException(message="Product not found", error_code="PRODUCT_NOT_FOUND")

        await wishlist_repository.add_item(user_id, product_id)
        return await self.get_user_wishlist(user_id)

    async def remove_from_wishlist(self, user_id: UUID, product_id: UUID) -> WishlistResponse:
        await wishlist_repository.remove_item(user_id, product_id)
        return await self.get_user_wishlist(user_id)


wishlist_service = WishlistService()
