import uuid
from typing import Any, Dict, Optional, Union
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import fetch_one
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.db.database import get_db
from app.models.admin import Admin
from app.repositories.admin_repository import admin_repository

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


async def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: AsyncSession = Depends(get_db)
) -> Admin:
    """Dependency to extract, decode, and fetch the authenticated admin from admins table."""
    if not credentials or not credentials.credentials:
        raise UnauthorizedException(message="Authentication token is required", error_code="MISSING_TOKEN")

    token = credentials.credentials
    payload = decode_token(token)
    
    if payload.get("type") != "access":
        raise UnauthorizedException(message="Invalid token type", error_code="INVALID_TOKEN_TYPE")
        
    if not payload.get("is_admin") and payload.get("role") != "admin":
        raise ForbiddenException(message="Administrator privileges required", error_code="ADMIN_REQUIRED")

    admin_id_str = payload.get("sub")
    if not admin_id_str:
        raise UnauthorizedException(message="Invalid token subject", error_code="INVALID_TOKEN_SUBJECT")

    try:
        admin_uuid = uuid.UUID(admin_id_str)
    except ValueError:
        raise UnauthorizedException(message="Invalid admin identifier in token", error_code="INVALID_USER_ID")

    admin = await admin_repository.get_by_id(db, admin_uuid)
    
    if not admin:
        raise UnauthorizedException(message="Admin not found", error_code="ADMIN_NOT_FOUND")

    if not admin.is_active:
        raise ForbiddenException(message="Admin account is deactivated", error_code="ADMIN_INACTIVE")

    return admin


async def require_admin(
    current_admin: Admin = Depends(get_current_admin)
) -> Admin:
    """Dependency ensuring the authenticated admin is active (checked via admins table)."""
    return current_admin


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
