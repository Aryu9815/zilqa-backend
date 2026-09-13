from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, status
from app.core.dependencies import get_current_user, require_authenticated_user
from app.schemas.auth import (
    GoogleLoginRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.common import ResponseEnvelope
from app.schemas.user import UserResponse
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=ResponseEnvelope[TokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new customer account"
)
async def register(register_in: RegisterRequest) -> ResponseEnvelope[TokenResponse]:
    """Register a new customer user and issue an initial access/refresh token pair."""
    token_response = await auth_service.register(register_in)
    return ResponseEnvelope(
        success=True,
        message="Account registered successfully",
        data=token_response
    )


@router.post(
    "/login",
    response_model=ResponseEnvelope[TokenResponse],
    summary="Authenticate user and get access token"
)
async def login(login_in: LoginRequest) -> ResponseEnvelope[TokenResponse]:
    """Authenticate with email and password to receive access & refresh tokens."""
    token_response = await auth_service.login(login_in)
    return ResponseEnvelope(
        success=True,
        message="Login successful",
        data=token_response
    )


@router.post(
    "/google",
    response_model=ResponseEnvelope[TokenResponse],
    summary="Authenticate user with Google Sign-In"
)
async def google_login(login_in: GoogleLoginRequest) -> ResponseEnvelope[TokenResponse]:
    """Authenticate or register with verified Google ID token credential to receive access & refresh tokens."""
    print("api received: ", login_in.credential)
    token_response = await auth_service.google_login(login_in.credential)
    return ResponseEnvelope(
        success=True,
        message="Google login successful",
        data=token_response
    )


@router.post(
    "/refresh",
    response_model=ResponseEnvelope[TokenResponse],
    summary="Rotate and refresh JWT access token"
)
async def refresh_token(request_in: RefreshTokenRequest) -> ResponseEnvelope[TokenResponse]:
    """Exchange a valid refresh token for a fresh token pair (rotating the refresh token)."""
    token_response = await auth_service.refresh_token(request_in.refresh_token)
    return ResponseEnvelope(
        success=True,
        message="Token refreshed successfully",
        data=token_response
    )


@router.post(
    "/logout",
    response_model=ResponseEnvelope[None],
    summary="Revoke refresh token and logout"
)
async def logout(
    request_in: Optional[RefreshTokenRequest] = None,
    current_user: Optional[Dict[str, Any]] = Depends(require_authenticated_user)
) -> ResponseEnvelope[None]:
    """Revoke the current refresh token or all user active tokens."""
    token_str = request_in.refresh_token if request_in else None
    user_id = current_user["id"] if current_user else None
    await auth_service.logout(refresh_token_str=token_str, user_id=user_id)
    return ResponseEnvelope(
        success=True,
        message="Logged out successfully"
    )


@router.get(
    "/me",
    response_model=ResponseEnvelope[UserResponse],
    summary="Get current authenticated user profile"
)
async def get_me(
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
) -> ResponseEnvelope[UserResponse]:
    """Retrieve full profile details for the currently logged in user."""
    return ResponseEnvelope(
        success=True,
        message="Profile fetched successfully",
        data=UserResponse.model_validate(current_user)
    )
