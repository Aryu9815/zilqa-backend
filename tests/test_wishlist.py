from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.schemas.wishlist import WishlistItemResponse, WishlistProductSnapshot, WishlistResponse


def test_wishlist_schemas():
    prod_id = uuid4()
    item_id = uuid4()

    snapshot = WishlistProductSnapshot(
        id=prod_id,
        name="Silver Pendant",
        main_image_url="https://example.com/pendant.jpg",
        price=Decimal("1499.00"),
        is_active=True
    )

    wishlist_item = WishlistItemResponse(
        id=item_id,
        product=snapshot,
        created_at=datetime.now(timezone.utc)
    )

    wishlist = WishlistResponse(
        items=[wishlist_item],
        total_items=1
    )

    assert wishlist.total_items == 1
    assert wishlist.items[0].product.name == "Silver Pendant"
