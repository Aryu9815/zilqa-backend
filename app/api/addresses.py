from typing import Any, Dict, List
from uuid import UUID
from fastapi import APIRouter, Depends, status

from app.core.dependencies import require_authenticated_user
from app.schemas.address import AddressCreate, AddressResponse, AddressUpdate
from app.schemas.common import ResponseEnvelope
from app.services.user_service import user_service

router = APIRouter(prefix="/users/me/addresses", tags=["Addresses"])


@router.get(
    "",
    response_model=ResponseEnvelope[List[AddressResponse]],
    summary="List all shipping addresses for current user"
)
async def list_addresses(
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[List[AddressResponse]]:
    addresses = await user_service.list_addresses(current_user["id"])
    return ResponseEnvelope(
        success=True,
        message="Addresses retrieved successfully",
        data=addresses
    )


@router.post(
    "",
    response_model=ResponseEnvelope[AddressResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add a new shipping address"
)
async def create_address(
    address_in: AddressCreate,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[AddressResponse]:
    address = await user_service.create_address(current_user["id"], address_in)
    return ResponseEnvelope(
        success=True,
        message="Address created successfully",
        data=address
    )


@router.get(
    "/{address_id}",
    response_model=ResponseEnvelope[AddressResponse],
    summary="Get single address details"
)
async def get_address(
    address_id: UUID,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[AddressResponse]:
    address = await user_service.get_address(address_id, current_user["id"])
    return ResponseEnvelope(
        success=True,
        message="Address retrieved successfully",
        data=address
    )


@router.put(
    "/{address_id}",
    response_model=ResponseEnvelope[AddressResponse],
    summary="Update shipping address"
)
async def update_address(
    address_id: UUID,
    address_in: AddressUpdate,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[AddressResponse]:
    address = await user_service.update_address(address_id, current_user["id"], address_in)
    return ResponseEnvelope(
        success=True,
        message="Address updated successfully",
        data=address
    )


@router.delete(
    "/{address_id}",
    response_model=ResponseEnvelope[None],
    summary="Delete shipping address"
)
async def delete_address(
    address_id: UUID,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[None]:
    await user_service.delete_address(address_id, current_user["id"])
    return ResponseEnvelope(
        success=True,
        message="Address deleted successfully"
    )


@router.patch(
    "/{address_id}/default",
    response_model=ResponseEnvelope[AddressResponse],
    summary="Set address as default shipping address"
)
async def set_default_address(
    address_id: UUID,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[AddressResponse]:
    address = await user_service.set_default_address(address_id, current_user["id"])
    return ResponseEnvelope(
        success=True,
        message="Default address updated successfully",
        data=address
    )
