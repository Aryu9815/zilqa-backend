from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID
import asyncpg
from app.core.config import settings
from app.core.exceptions import ConflictException, ForbiddenException, UnauthorizedException
from app.core.google_auth import google_auth_helper
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.repositories.user_repository import user_repository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserSummaryResponse


DEFAULT_COUNTRY_CODE = "US"


class AuthService:

    async def _generate_auth_tokens(self, user_record: Any, country_code: Optional[str] = None) -> TokenResponse:
        """Helper to generate JWT access token, store hashed refresh token, set country_code, and return TokenResponse."""
        user_id = user_record["id"]
        role = "customer"
        mobile_number = user_record.get("mobile_number") if hasattr(user_record, "get") else user_record["mobile_number"] if "mobile_number" in user_record else None

        existing_country_code = user_record.get("country_code") if hasattr(user_record, "get") else user_record["country_code"] if "country_code" in user_record else None

        # Determine country code to set if not already present
        incoming_cc = country_code.strip().upper() if country_code and country_code.strip() else DEFAULT_COUNTRY_CODE

        if not existing_country_code:
            effective_country_code = incoming_cc
            updated_record = await user_repository.update_country_code(
                user_id=user_id,
                country_code=effective_country_code
            )
            if updated_record:
                user_record = updated_record
        else:
            effective_country_code = existing_country_code

        access_token = create_access_token(
            subject=user_id,
            role=role,
            additional_claims={"country_code": effective_country_code}
        )
        raw_refresh_token = generate_refresh_token()
        hashed_rf_token = hash_token(raw_refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await user_repository.save_refresh_token(
            user_id=user_id,
            token_hash=hashed_rf_token,
            expires_at=expires_at
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            refresh_token=raw_refresh_token,
            country_code=effective_country_code,
            user=UserSummaryResponse(
                id=user_id,
                name=user_record["name"],
                email=user_record["email"],
                mobile_number=mobile_number,
                role=role,
                country_code=effective_country_code
            )
        )

    async def register(self, register_in: RegisterRequest, country_code: Optional[str] = None) -> TokenResponse:
        # Check if email is already in use
        existing_user = await user_repository.get_by_email(register_in.email)
        if existing_user:
            raise ConflictException(
                message="An account with this email address already exists",
                error_code="EMAIL_ALREADY_EXISTS"
            )

        effective_cc = (country_code or DEFAULT_COUNTRY_CODE).strip().upper()

        hashed_pwd = hash_password(register_in.password)
        user_record = await user_repository.create(
            name=register_in.name,
            email=register_in.email,
            password_hash=hashed_pwd,
            role="customer",
            country_code=effective_cc
        )

        return await self._generate_auth_tokens(user_record, country_code=effective_cc)

    async def login(self, login_in: LoginRequest, country_code: Optional[str] = None) -> TokenResponse:
        user_record = await user_repository.get_by_email(login_in.email)
        if not user_record:
            raise UnauthorizedException(
                message="Invalid email or password",
                error_code="INVALID_CREDENTIALS"
            )

        # Reject password login for Google-only users without password_hash
        if not user_record.get("password_hash"):
            raise UnauthorizedException(
                message="This account was created using Google Sign-In. Please log in with Google or set a password.",
                error_code="GOOGLE_AUTH_REQUIRED"
            )

        if not verify_password(login_in.password, user_record["password_hash"]):
            raise UnauthorizedException(
                message="Invalid email or password",
                error_code="INVALID_CREDENTIALS"
            )

        if not user_record["is_active"]:
            raise ForbiddenException(
                message="Account has been deactivated. Please contact support.",
                error_code="ACCOUNT_DEACTIVATED"
            )

        effective_cc = (country_code or DEFAULT_COUNTRY_CODE).strip().upper()
        return await self._generate_auth_tokens(user_record, country_code=effective_cc)

    async def google_login(self, credential: str, country_code: Optional[str] = None) -> TokenResponse:
        """
        Authenticate with a verified Google ID token.
        Follows lookup order:
        1. Find by google_id -> authenticate
        2. Find by verified email -> link google_id -> authenticate
        3. Create new user with role='customer', password_hash=None -> authenticate
        """
        effective_cc = (country_code or DEFAULT_COUNTRY_CODE).strip().upper()

        # Verify credential using Google official library
        google_data = google_auth_helper.verify_token(credential)
        google_id = google_data["sub"]
        email = google_data["email"]
        name = google_data["name"]

        # STEP 1: Find the user by google_id
        user_record = await user_repository.get_by_google_id(google_id)
        if user_record:
            if not user_record["is_active"]:
                raise ForbiddenException(
                    message="Account has been deactivated. Please contact support.",
                    error_code="ACCOUNT_DEACTIVATED"
                )
            return await self._generate_auth_tokens(user_record, country_code=effective_cc)

        # STEP 2: If google_id is not found, find the user by verified email
        user_record = await user_repository.get_by_email(email)
        if user_record:
            if not user_record["is_active"]:
                raise ForbiddenException(
                    message="Account has been deactivated. Please contact support.",
                    error_code="ACCOUNT_DEACTIVATED"
                )

            # Link the verified Google ID to that existing user
            try:
                updated_record = await user_repository.link_google_id(
                    user_id=user_record["id"],
                    google_id=google_id
                )
                if updated_record:
                    user_record = updated_record
            except asyncpg.UniqueViolationError:
                raise ConflictException(
                    message="Google account is already associated with another user.",
                    error_code="GOOGLE_ACCOUNT_CONFLICT"
                )

            return await self._generate_auth_tokens(user_record, country_code=effective_cc)

        # STEP 3: If no user exists with the verified email, create a new user
        try:
            new_user = await user_repository.create(
                name=name,
                email=email,
                password_hash=None,
                role="customer",
                google_id=google_id,
                mobile_number=None,
                country_code=effective_cc
            )
        except asyncpg.UniqueViolationError:
            raise ConflictException(
                message="An account with this email or Google account already exists.",
                error_code="ACCOUNT_CONFLICT"
            )

        return await self._generate_auth_tokens(new_user, country_code=effective_cc)

    async def refresh_token(self, refresh_token_str: str, country_code: Optional[str] = None) -> TokenResponse:
        hashed_rf_token = hash_token(refresh_token_str)
        token_record = await user_repository.get_refresh_token(hashed_rf_token)

        if not token_record:
            raise UnauthorizedException(
                message="Invalid refresh token",
                error_code="INVALID_REFRESH_TOKEN"
            )

        if token_record["revoked"]:
            # Potential token compromise: Revoke all tokens for this user
            await user_repository.revoke_all_user_tokens(token_record["user_id"])
            raise UnauthorizedException(
                message="Refresh token has been revoked",
                error_code="REVOKED_REFRESH_TOKEN"
            )

        expires_at = token_record["expires_at"]
        if isinstance(expires_at, datetime) and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < datetime.now(timezone.utc):
            raise UnauthorizedException(
                message="Refresh token has expired",
                error_code="EXPIRED_REFRESH_TOKEN"
            )

        # Rotate token: Revoke current refresh token
        await user_repository.revoke_refresh_token(hashed_rf_token)

        user_id = token_record["user_id"]
        user_record = await user_repository.get_by_id(user_id)
        if not user_record or not user_record["is_active"]:
            raise UnauthorizedException(
                message="User not found or inactive",
                error_code="USER_INACTIVE"
            )

        effective_cc = (country_code or user_record.get("country_code") or DEFAULT_COUNTRY_CODE).strip().upper()
        return await self._generate_auth_tokens(user_record, country_code=effective_cc)

    async def logout(self, refresh_token_str: Optional[str], user_id: Optional[UUID] = None) -> None:
        if refresh_token_str:
            hashed_rf_token = hash_token(refresh_token_str)
            await user_repository.revoke_refresh_token(hashed_rf_token)
        elif user_id:
            await user_repository.revoke_all_user_tokens(user_id)


auth_service = AuthService()
