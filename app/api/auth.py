from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
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
from app.services.country_service import country_service
from app.utils.helpers import get_client_ip, get_country_from_ip

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=ResponseEnvelope[TokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new customer account"
)
async def register(
    register_in: RegisterRequest,
    request: Request
) -> ResponseEnvelope[TokenResponse]:
    """Register a new customer user and issue an initial access/refresh token pair."""
    ip = get_client_ip(request)
    country_code = await get_country_from_ip(ip)
    token_response = await auth_service.register(
        register_in,
        country_code=country_code
    )
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
async def login(
    login_in: LoginRequest,
    request: Request
) -> ResponseEnvelope[TokenResponse]:
    """Authenticate with email and password to receive access & refresh tokens."""
    ip = get_client_ip(request)
    country_code = await get_country_from_ip(ip)
    print('country code', country_code)
    token_response = await auth_service.login(
        login_in,
        country_code=country_code
    )
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
async def google_login(
    login_in: GoogleLoginRequest,
    request: Request
) -> ResponseEnvelope[TokenResponse]:
    """Authenticate or register with verified Google ID token credential to receive access & refresh tokens."""
    ip = get_client_ip(request)
    country_code = await get_country_from_ip(ip)
    token_response = await auth_service.google_login(
        login_in.credential,
        country_code=country_code
    )
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
async def refresh_token(
    request_in: RefreshTokenRequest,
    request: Request
) -> ResponseEnvelope[TokenResponse]:
    """Exchange a valid refresh token for a fresh token pair (rotating the refresh token)."""
    ip = get_client_ip(request)
    country_code = await get_country_from_ip(ip)
    token_response = await auth_service.refresh_token(
        request_in.refresh_token,
        country_code=country_code
    )
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


@router.get(
    "/location",
    summary="Get user location and exchange rate based on IP (No login required)"
)
async def get_location(
    request: Request,
    country_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Detect user's country from IP (defaults to US if not detected)
    and return exchange rate if available in countries table.
    Does not require login.
    """
    if not country_code:
        ip = get_client_ip(request)
        country_code = await get_country_from_ip(ip)

    if not country_code:
        country_code = "US"
    else:
        country_code = country_code.strip().upper()

    currency = await country_service.get_exchange_rate_for_country(db, country_code)
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
