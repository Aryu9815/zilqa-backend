from typing import Any, Dict
from fastapi import APIRouter, Depends

from app.core.dependencies import require_authenticated_user
from app.schemas.common import ResponseEnvelope
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=ResponseEnvelope[UserResponse],
    summary="Get authenticated user profile"
)
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[UserResponse]:
    profile = await user_service.get_profile(current_user["id"])
    return ResponseEnvelope(
        success=True,
        message="User profile retrieved successfully",
        data=profile
    )


@router.put(
    "/me",
    response_model=ResponseEnvelope[UserResponse],
    summary="Update authenticated user profile"
)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[UserResponse]:
    updated_profile = await user_service.update_profile(current_user["id"], user_update)
    return ResponseEnvelope(
        success=True,
        message="Profile updated successfully",
        data=updated_profile
    )
