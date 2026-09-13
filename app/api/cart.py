from typing import Any, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, status

from app.core.dependencies import require_authenticated_user
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartResponse
from app.schemas.common import ResponseEnvelope
from app.services.cart_service import cart_service

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get(
    "",
    response_model=ResponseEnvelope[CartResponse],
    summary="Get current user shopping cart"
)
async def get_cart(
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[CartResponse]:
    cart = await cart_service.get_user_cart(current_user["id"])
    return ResponseEnvelope(
        success=True,
        message="Cart retrieved successfully",
        data=cart
    )


@router.post(
    "/items",
    response_model=ResponseEnvelope[CartResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add product item to cart"
)
async def add_item_to_cart(
    item_in: CartItemCreate,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[CartResponse]:
    cart = await cart_service.add_item_to_cart(
        user_id=current_user["id"],
        product_id=item_in.product_id,
        quantity=item_in.quantity
    )
    return ResponseEnvelope(
        success=True,
        message="Item added to cart successfully",
        data=cart
    )


@router.put(
    "/items/{item_id}",
    response_model=ResponseEnvelope[CartResponse],
    summary="Update cart item quantity"
)
async def update_cart_item(
    item_id: UUID,
    item_in: CartItemUpdate,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[CartResponse]:
    cart = await cart_service.update_cart_item(
        user_id=current_user["id"],
        item_id=item_id,
        quantity=item_in.quantity
    )
    return ResponseEnvelope(
        success=True,
        message="Cart item quantity updated successfully",
        data=cart
    )


@router.delete(
    "/items/{item_id}",
    response_model=ResponseEnvelope[CartResponse],
    summary="Remove item from cart"
)
async def remove_cart_item(
    item_id: UUID,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[CartResponse]:
    cart = await cart_service.remove_cart_item(
        user_id=current_user["id"],
        item_id=item_id
    )
    return ResponseEnvelope(
        success=True,
        message="Item removed from cart successfully",
        data=cart
    )


@router.delete(
    "",
    response_model=ResponseEnvelope[CartResponse],
    summary="Clear entire cart"
)
async def clear_cart(
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[CartResponse]:
    cart = await cart_service.clear_cart(current_user["id"])
    return ResponseEnvelope(
        success=True,
        message="Cart cleared successfully",
        data=cart
    )
