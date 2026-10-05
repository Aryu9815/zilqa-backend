from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_optional_current_user, require_admin
from app.db.database import get_db
from app.schemas.common import PaginatedResponse, ResponseEnvelope
from app.schemas.offer import (
    CouponValidateRequest,
    CouponValidateResponse,
    OfferCreate,
    OfferResponse,
    OfferUpdate,
)
from app.services.offer_service import offer_service

public_router = APIRouter(prefix="/offers", tags=["Offers"])
admin_router = APIRouter(prefix="/admin/offers", tags=["Offers"])


# =============================================================================
# PUBLIC OFFER ENDPOINTS
# =============================================================================

@public_router.get(
    "",
    response_model=PaginatedResponse[OfferResponse],
    summary="List active offers and promotions (Public)"
)
async def list_public_offers(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term in name or description"),
    offer_type: Optional[str] = Query(None, description="Filter by offer type")
) -> PaginatedResponse[OfferResponse]:
    """Retrieve all currently active offers, promotions, and deals."""
    return await offer_service.list_offers(
        page=page,
        limit=limit,
        search=search,
        offer_type=offer_type,
        is_active=True
    )


@public_router.get(
    "/{offer_id}",
    response_model=ResponseEnvelope[OfferResponse],
    summary="Get details of a single active offer (Public)"
)
async def get_public_offer(offer_id: UUID) -> ResponseEnvelope[OfferResponse]:
    """Retrieve details of a single active offer by ID."""
    offer = await offer_service.get_offer(offer_id, is_active_only=True)
    return ResponseEnvelope(
        success=True,
        message="Offer retrieved successfully",
        data=offer
    )


@public_router.post(
    "/validate-coupon",
    response_model=ResponseEnvelope[CouponValidateResponse],
    summary="Validate coupon code and calculate savings (Public/Customer)"
)
async def validate_coupon(
    payload: CouponValidateRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> ResponseEnvelope[CouponValidateResponse]:
    """Validate a coupon code against current user order history, cart subtotal, dates, and limits."""
    user_id = current_user["id"] if current_user else None
    result = await offer_service.validate_and_calculate_coupon(
        coupon_code=payload.coupon_code,
        user_id=user_id,
        cart_subtotal=payload.cart_subtotal
    )
    return ResponseEnvelope(
        success=result.is_valid,
        message=result.message,
        data=result
    )


# =============================================================================
# ADMIN OFFER ENDPOINTS
# =============================================================================

@admin_router.post(
    "",
    response_model=ResponseEnvelope[OfferResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create offer (Admin only)"
)
async def create_offer(
    offer_in: OfferCreate,
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> ResponseEnvelope[OfferResponse]:
    """Create a new offer with strict validation of the 11 allowed offer types."""
    offer = await offer_service.create_offer(db, offer_in)
    return ResponseEnvelope(
        success=True,
        message="Offer created successfully",
        data=offer
    )


@admin_router.get(
    "",
    response_model=PaginatedResponse[OfferResponse],
    summary="List all offers with filters and pagination (Admin only)"
)
async def admin_list_offers(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term in name, description, or coupon code"),
    offer_type: Optional[str] = Query(None, description="Filter by offer type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> PaginatedResponse[OfferResponse]:
    """Admin endpoint to list all offers including inactive or scheduled ones."""
    return await offer_service.list_offers(
        page=page,
        limit=limit,
        search=search,
        offer_type=offer_type,
        is_active=is_active
    )


@admin_router.get(
    "/{offer_id}",
    response_model=ResponseEnvelope[OfferResponse],
    summary="Get offer details by ID (Admin only)"
)
async def admin_get_offer(
    offer_id: UUID,
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[OfferResponse]:
    """Admin endpoint to retrieve full offer details including target products and categories."""
    offer = await offer_service.get_offer(offer_id, is_active_only=False)
    return ResponseEnvelope(
        success=True,
        message="Offer retrieved successfully",
        data=offer
    )


@admin_router.put(
    "/{offer_id}",
    response_model=ResponseEnvelope[OfferResponse],
    summary="Update offer (Admin only)"
)
async def update_offer(
    offer_id: UUID,
    offer_in: OfferUpdate,
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> ResponseEnvelope[OfferResponse]:
    """Update offer attributes, discount terms, or linked products/categories."""
    updated = await offer_service.update_offer(db, offer_id, offer_in)
    return ResponseEnvelope(
        success=True,
        message="Offer updated successfully",
        data=updated
    )


@admin_router.delete(
    "/{offer_id}",
    response_model=ResponseEnvelope[None],
    summary="Delete/deactivate offer (Admin only)"
)
async def delete_offer(
    offer_id: UUID,
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[None]:
    """Soft-delete an offer by setting is_deleted=TRUE and is_active=FALSE."""
    await offer_service.delete_offer(offer_id)
    return ResponseEnvelope(
        success=True,
        message="Offer deactivated successfully"
    )
