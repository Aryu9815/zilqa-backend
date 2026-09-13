from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import require_admin, require_authenticated_user
from app.schemas.common import PaginatedResponse, ResponseEnvelope
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderStatus,
    OrderStatusUpdate,
    PaymentStatus,
    PaymentStatusUpdate,
)
from app.services.order_service import order_service

user_router = APIRouter(prefix="/orders", tags=["Orders"])
admin_router = APIRouter(prefix="/admin/orders", tags=["Admin Orders"])


# =============================================================================
# USER ORDER ENDPOINTS
# =============================================================================

@user_router.post(
    "",
    response_model=ResponseEnvelope[OrderResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Place a new order from current shopping cart"
)
async def create_order(
    order_in: OrderCreate,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[OrderResponse]:
    order = await order_service.create_order(current_user["id"], order_in)
    return ResponseEnvelope(
        success=True,
        message="Order placed successfully",
        data=order
    )


@user_router.get(
    "",
    response_model=PaginatedResponse[OrderResponse],
    summary="List authenticated user's orders (Paginated)"
)
async def list_my_orders(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> PaginatedResponse[OrderResponse]:
    return await order_service.list_user_orders(current_user["id"], page=page, limit=limit)


@user_router.get(
    "/{order_id}",
    response_model=ResponseEnvelope[OrderResponse],
    summary="Get user's single order details"
)
async def get_my_order(
    order_id: UUID,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[OrderResponse]:
    order = await order_service.get_user_order(order_id, current_user["id"])
    return ResponseEnvelope(
        success=True,
        message="Order retrieved successfully",
        data=order
    )


# =============================================================================
# ADMIN ORDER ENDPOINTS
# =============================================================================

@admin_router.get(
    "",
    response_model=PaginatedResponse[OrderResponse],
    summary="List all customer orders with filters (Admin only)"
)
async def list_admin_orders(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status"),
    date_from: Optional[datetime] = Query(None, description="Filter orders created on or after"),
    date_to: Optional[datetime] = Query(None, description="Filter orders created on or before"),
    search: Optional[str] = Query(None, description="Search by Order ID, customer name, or customer email"),
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> PaginatedResponse[OrderResponse]:
    return await order_service.list_admin_orders(
        status=status,
        payment_status=payment_status,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        limit=limit
    )


@admin_router.get(
    "/{order_id}",
    response_model=ResponseEnvelope[OrderResponse],
    summary="Get single order details with customer and address information (Admin only)"
)
async def get_admin_order(
    order_id: UUID,
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[OrderResponse]:
    order = await order_service.get_order_details(order_id)
    return ResponseEnvelope(
        success=True,
        message="Order retrieved successfully",
        data=order
    )


@admin_router.patch(
    "/{order_id}/status",
    response_model=ResponseEnvelope[OrderResponse],
    summary="Update order fulfillment status (Admin only)"
)
async def update_order_status(
    order_id: UUID,
    status_in: OrderStatusUpdate,
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[OrderResponse]:
    updated_order = await order_service.update_order_status(order_id, status_in.status)
    return ResponseEnvelope(
        success=True,
        message=f"Order status updated to {status_in.status.value}",
        data=updated_order
    )


@admin_router.patch(
    "/{order_id}/payment-status",
    response_model=ResponseEnvelope[OrderResponse],
    summary="Update order payment status (Admin only)"
)
async def update_payment_status(
    order_id: UUID,
    status_in: PaymentStatusUpdate,
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[OrderResponse]:
    updated_order = await order_service.update_payment_status(order_id, status_in.payment_status)
    return ResponseEnvelope(
        success=True,
        message=f"Payment status updated to {status_in.payment_status.value}",
        data=updated_order
    )
