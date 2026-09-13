from typing import Any, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, status

from app.core.dependencies import require_authenticated_user
from app.schemas.common import ResponseEnvelope
from app.schemas.wishlist import WishlistResponse
from app.services.wishlist_service import wishlist_service

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


@router.get(
    "",
    response_model=ResponseEnvelope[WishlistResponse],
    summary="Get authenticated user wishlist"
)
async def get_wishlist(
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[WishlistResponse]:
    wishlist = await wishlist_service.get_user_wishlist(current_user["id"])
    return ResponseEnvelope(
        success=True,
        message="Wishlist retrieved successfully",
        data=wishlist
    )


@router.post(
    "/{product_id}",
    response_model=ResponseEnvelope[WishlistResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add product to wishlist"
)
async def add_to_wishlist(
    product_id: UUID,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[WishlistResponse]:
    wishlist = await wishlist_service.add_to_wishlist(current_user["id"], product_id)
    return ResponseEnvelope(
        success=True,
        message="Product added to wishlist successfully",
        data=wishlist
    )


@router.delete(
    "/{product_id}",
    response_model=ResponseEnvelope[WishlistResponse],
    summary="Remove product from wishlist"
)
async def remove_from_wishlist(
    product_id: UUID,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[WishlistResponse]:
    wishlist = await wishlist_service.remove_from_wishlist(current_user["id"], product_id)
    return ResponseEnvelope(
        success=True,
        message="Product removed from wishlist successfully",
        data=wishlist
    )
