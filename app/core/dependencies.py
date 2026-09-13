import uuid
from typing import Any, Dict, Optional
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import fetch_one
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token

# Reusable Bearer scheme that does not auto-error so optional auth works cleanly
http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)
) -> Dict[str, Any]:
    """Dependency to extract, decode, and fetch the authenticated active user."""
    if not credentials or not credentials.credentials:
        raise UnauthorizedException(message="Authentication token is required", error_code="MISSING_TOKEN")

    token = credentials.credentials
    payload = decode_token(token)
    
    if payload.get("type") != "access":
        raise UnauthorizedException(message="Invalid token type", error_code="INVALID_TOKEN_TYPE")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException(message="Invalid token subject", error_code="INVALID_TOKEN_SUBJECT")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException(message="Invalid user identifier in token", error_code="INVALID_USER_ID")

    query = """
        SELECT id, name, email, role, is_active, created_at, updated_at
        FROM users
        WHERE id = $1
    """
    user = await fetch_one(query, user_uuid)
    
    if not user:
        raise UnauthorizedException(message="User not found", error_code="USER_NOT_FOUND")

    if not user["is_active"]:
        raise ForbiddenException(message="User account is deactivated", error_code="USER_INACTIVE")

    return dict(user)


async def require_authenticated_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Dependency ensuring an authenticated user is active."""
    return current_user


async def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Dependency ensuring the authenticated user has 'admin' role."""
    if current_user.get("role") != "admin":
        raise ForbiddenException(message="Administrator privileges required", error_code="ADMIN_REQUIRED")
    return current_user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)
) -> Optional[Dict[str, Any]]:
    """Optional authentication dependency for routes allowing guest or authenticated access."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return await get_current_user(credentials)
    except Exception:
        return None
