from typing import Any, Dict, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_optional_current_user, require_authenticated_user
from app.schemas.cart import (
    ApplyCouponRequest,
    CartItemCreate,
    CartItemUpdate,
    CartResponse,
    LiveBillRequest,
    LiveBillResponse,
)
from app.schemas.common import ResponseEnvelope
from app.services.cart_service import cart_service

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.post(
    "/calculate-bill",
    response_model=ResponseEnvelope[LiveBillResponse],
    summary="Calculate live dynamic bill with offers, coupons, and delivery charges"
)
async def calculate_bill(
    req: LiveBillRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> ResponseEnvelope[LiveBillResponse]:
    user_id = current_user["id"] if current_user else None
    bill = await cart_service.calculate_live_bill(user_id=user_id, req=req)
    return ResponseEnvelope(
        success=True,
        message="Live bill calculated successfully",
        data=bill
    )


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


@router.post(
    "/coupon",
    response_model=ResponseEnvelope[CartResponse],
    summary="Apply coupon code to cart"
)
async def apply_coupon(
    req: ApplyCouponRequest,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[CartResponse]:
    cart = await cart_service.apply_coupon(
        user_id=current_user["id"],
        coupon_code=req.coupon_code
    )
    return ResponseEnvelope(
        success=True,
        message=f"Coupon '{req.coupon_code.strip().upper()}' applied successfully",
        data=cart
    )


@router.post(
    "/apply-coupon",
    response_model=ResponseEnvelope[CartResponse],
    summary="Apply coupon code to cart (alias)"
)
async def apply_coupon_alias(
    req: ApplyCouponRequest,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[CartResponse]:
    return await apply_coupon(req=req, current_user=current_user)


@router.delete(
    "/coupon",
    response_model=ResponseEnvelope[CartResponse],
    summary="Remove applied coupon from cart"
)
async def remove_coupon(
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[CartResponse]:
    cart = await cart_service.remove_coupon(user_id=current_user["id"])
    return ResponseEnvelope(
        success=True,
        message="Coupon removed from cart successfully",
        data=cart
    )


@router.delete(
    "/remove-coupon",
    response_model=ResponseEnvelope[CartResponse],
    summary="Remove applied coupon from cart (alias)"
)
async def remove_coupon_alias(
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[CartResponse]:
    return await remove_coupon(current_user=current_user)
