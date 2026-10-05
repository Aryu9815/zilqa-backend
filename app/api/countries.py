from typing import Any, Dict, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, status

from app.core.dependencies import require_admin
from app.schemas.common import PaginatedResponse, ResponseEnvelope
from app.schemas.country import CountryCreate, CountryResponse, CountryUpdate, LocationResponse
from app.services.country_service import country_service
from app.utils.helpers import get_client_ip, get_country_from_ip

public_router = APIRouter(prefix="/countries", tags=["Countries"])
admin_router = APIRouter(prefix="/admin/countries", tags=["Countries"])


# =============================================================================
# PUBLIC COUNTRY ENDPOINTS
# =============================================================================

@public_router.get(
    "/location",
    summary="Get user location and exchange rate from IP (No login required)"
)
async def get_location(
    request: Request,
    country_code: Optional[str] = Query(None, description="Optional override for testing")
) -> Dict[str, Any]:
    """
    Detect user's country from IP (defaults to US if not detected)
    and return exchange rate if available in countries table.
    """
    if not country_code:
        ip = get_client_ip(request)
        country_code = await get_country_from_ip(ip)

    if not country_code:
        country_code = "US"
    else:
        country_code = country_code.strip().upper()

    currency = await country_service.get_exchange_rate_for_country(country_code)
    exchange_rate = currency["exchange_rate"] if currency else None
    exchange_available = currency["exchange_available"] if currency else False

    return {
        "success": True,
        "message": "Location retrieved successfully",
        "country_code": country_code,
        "exchange_rate": exchange_rate,
        "exchange_available": exchange_available,
        "data": {
            "country_code": country_code,
            "exchange_rate": exchange_rate,
            "exchange_available": exchange_available,
        }
    }


@public_router.get(
    "",
    response_model=PaginatedResponse[CountryResponse],
    summary="List countries (Public, Paginated, Searchable)"
)
async def list_countries(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=250, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by country name or code")
) -> PaginatedResponse[CountryResponse]:
    """Retrieve countries available for shipping and address checkout (active only)."""
    return await country_service.list_countries(
        page=page,
        limit=limit,
        search=search,
        is_active=True,
        include_deleted=False
    )


@public_router.get(
    "/{country_id}",
    response_model=ResponseEnvelope[CountryResponse],
    summary="Get single country by ID (Public)"
)
async def get_country(country_id: UUID) -> ResponseEnvelope[CountryResponse]:
    """Retrieve details for a single active country."""
    country = await country_service.get_country(country_id, is_active_only=True, include_deleted=False)
    return ResponseEnvelope(
        success=True,
        message="Country retrieved successfully",
        data=country
    )


# =============================================================================
# ADMIN COUNTRY ENDPOINTS
# =============================================================================

@admin_router.get(
    "",
    response_model=PaginatedResponse[CountryResponse],
    summary="List all countries including inactive (Admin only)"
)
async def admin_list_countries(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by country name or code"),
    is_active: Optional[bool] = Query(None, description="Filter by active status (None = all)"),
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> PaginatedResponse[CountryResponse]:
    """Admin endpoint to list countries with full filtering."""
    return await country_service.list_countries(
        page=page,
        limit=limit,
        search=search,
        is_active=is_active,
        include_deleted=False
    )


@admin_router.post(
    "",
    response_model=ResponseEnvelope[CountryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create country (Admin only)"
)
async def create_country(
    country_in: CountryCreate,
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[CountryResponse]:
    """Create a new country with unique name and code."""
    created = await country_service.create_country(country_in)
    return ResponseEnvelope(
        success=True,
        message="Country created successfully",
        data=created
    )


@admin_router.get(
    "/{country_id}",
    response_model=ResponseEnvelope[CountryResponse],
    summary="Get country by ID (Admin only)"
)
async def admin_get_country(
    country_id: UUID,
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[CountryResponse]:
    """Admin endpoint to retrieve any non-deleted country by ID."""
    country = await country_service.get_country(country_id, include_deleted=False)
    return ResponseEnvelope(
        success=True,
        message="Country retrieved successfully",
        data=country
    )


@admin_router.put(
    "/{country_id}",
    response_model=ResponseEnvelope[CountryResponse],
    summary="Update country (Admin only)"
)
async def update_country(
    country_id: UUID,
    country_in: CountryUpdate,
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[CountryResponse]:
    """Update country details such as name, code, or active status."""
    updated = await country_service.update_country(country_id, country_in)
    return ResponseEnvelope(
        success=True,
        message="Country updated successfully",
        data=updated
    )


@admin_router.delete(
    "/{country_id}",
    response_model=ResponseEnvelope[None],
    summary="Delete country (Admin only)"
)
async def delete_country(
    country_id: UUID,
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[None]:
    """Soft-delete a country by ID."""
    await country_service.delete_country(country_id, soft=True)
    return ResponseEnvelope(
        success=True,
        message="Country deleted successfully"
    )
