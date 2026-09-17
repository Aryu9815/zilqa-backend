from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
import asyncpg
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.exceptions import ConflictException, ForbiddenException, UnauthorizedException
from app.core.google_auth import GoogleAuthHelper, google_auth_helper
from app.core.security import decode_token, hash_token
from app.schemas.auth import GoogleLoginRequest, LoginRequest
from app.services.auth_service import auth_service


# =============================================================================
# 1. GOOGLE CREDENTIAL VERIFICATION HELPER TESTS
# =============================================================================

def test_google_auth_helper_success():
    """Verify that a valid token correctly extracts verified user profile data."""
    helper = GoogleAuthHelper()
    mock_payload = {
        "sub": "google-user-12345",
        "email": "Jane.Doe@gmail.com",
        "email_verified": True,
        "name": "Jane Doe",
        "given_name": "Jane",
        "family_name": "Doe",
        "picture": "https://lh3.googleusercontent.com/a/photo.jpg"
    }

    with patch.object(settings, "GOOGLE_CLIENT_ID", "mock-client-id"), \
         patch("app.core.google_auth.id_token.verify_oauth2_token", return_value=mock_payload):
        result = helper.verify_token("valid_token_credential")

        assert result["sub"] == "google-user-12345"
        assert result["email"] == "jane.doe@gmail.com"
        assert result["email_verified"] is True
        assert result["name"] == "Jane Doe"
        assert result["picture"] == "https://lh3.googleusercontent.com/a/photo.jpg"


def test_google_auth_helper_invalid_credential():
    """Verify that an invalid Google token raises UnauthorizedException (GOOGLE_AUTH_FAILED)."""
    helper = GoogleAuthHelper()

    with patch.object(settings, "GOOGLE_CLIENT_ID", "mock-client-id"), \
         patch("app.core.google_auth.id_token.verify_oauth2_token", side_effect=ValueError("Invalid signature")):
        with pytest.raises(UnauthorizedException) as exc_info:
            helper.verify_token("invalid_credential")
        assert exc_info.value.error_code == "GOOGLE_AUTH_FAILED"
        assert "Invalid or expired" in exc_info.value.message


def test_google_auth_helper_expired_credential():
    """Verify that an expired Google token raises UnauthorizedException (GOOGLE_AUTH_FAILED)."""
    helper = GoogleAuthHelper()

    with patch.object(settings, "GOOGLE_CLIENT_ID", "mock-client-id"), \
         patch("app.core.google_auth.id_token.verify_oauth2_token", side_effect=ValueError("Token expired")):
        with pytest.raises(UnauthorizedException) as exc_info:
            helper.verify_token("expired_credential")
        assert exc_info.value.error_code == "GOOGLE_AUTH_FAILED"


def test_google_auth_helper_unverified_email():
    """Verify that an unverified email (email_verified=False) is rejected with GOOGLE_EMAIL_UNVERIFIED."""
    helper = GoogleAuthHelper()
    mock_payload = {
        "sub": "google-user-12345",
        "email": "unverified@example.com",
        "email_verified": False,
        "name": "Unverified User"
    }

    with patch.object(settings, "GOOGLE_CLIENT_ID", "mock-client-id"), \
         patch("app.core.google_auth.id_token.verify_oauth2_token", return_value=mock_payload):
        with pytest.raises(UnauthorizedException) as exc_info:
            helper.verify_token("unverified_credential")
        assert exc_info.value.error_code == "GOOGLE_EMAIL_UNVERIFIED"


def test_google_auth_helper_missing_email():
    """Verify that a token with no email field is rejected."""
    helper = GoogleAuthHelper()
    mock_payload = {
        "sub": "google-user-12345",
        "email_verified": True,
        "name": "No Email User"
    }

    with patch.object(settings, "GOOGLE_CLIENT_ID", "mock-client-id"), \
         patch("app.core.google_auth.id_token.verify_oauth2_token", return_value=mock_payload):
        with pytest.raises(UnauthorizedException) as exc_info:
            helper.verify_token("missing_email_credential")
        assert exc_info.value.error_code == "GOOGLE_EMAIL_UNVERIFIED"


def test_google_auth_helper_missing_sub():
    """Verify that a token with no subject ID is rejected."""
    helper = GoogleAuthHelper()
    mock_payload = {
        "email": "user@gmail.com",
        "email_verified": True,
        "name": "No Sub User"
    }

    with patch.object(settings, "GOOGLE_CLIENT_ID", "mock-client-id"), \
         patch("app.core.google_auth.id_token.verify_oauth2_token", return_value=mock_payload):
        with pytest.raises(UnauthorizedException) as exc_info:
            helper.verify_token("missing_sub_credential")
        assert exc_info.value.error_code == "GOOGLE_AUTH_FAILED"


def test_google_auth_helper_unconfigured():
    """Verify that unconfigured GOOGLE_CLIENT_ID raises GOOGLE_AUTH_NOT_CONFIGURED."""
    helper = GoogleAuthHelper()

    with patch.object(settings, "GOOGLE_CLIENT_ID", ""):
        with pytest.raises(UnauthorizedException) as exc_info:
            helper.verify_token("any_credential")
        assert exc_info.value.error_code == "GOOGLE_AUTH_NOT_CONFIGURED"


# =============================================================================
# 2. AUTH SERVICE GOOGLE LOGIN LOGIC & EDGE CASES
# =============================================================================

@pytest.mark.asyncio
async def test_google_login_existing_google_id():
    """Step 1: User found by google_id -> authenticate directly without creating or linking."""
    user_id = uuid4()
    existing_record = {
        "id": user_id,
        "name": "Existing Google User",
        "email": "existing@gmail.com",
        "mobile_number": None,
        "password_hash": None,
        "google_id": "google-sub-100",
        "role": "customer",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    mock_google_data = {
        "sub": "google-sub-100",
        "email": "existing@gmail.com",
        "email_verified": True,
        "name": "Existing Google User",
    }

    with patch.object(google_auth_helper, "verify_token", return_value=mock_google_data), \
         patch("app.services.auth_service.user_repository.get_by_google_id", new_callable=AsyncMock) as mock_get_gid, \
         patch("app.services.auth_service.user_repository.get_by_email", new_callable=AsyncMock) as mock_get_email, \
         patch("app.services.auth_service.user_repository.create", new_callable=AsyncMock) as mock_create, \
         patch("app.services.auth_service.user_repository.save_refresh_token", new_callable=AsyncMock) as mock_save_rf:

        mock_get_gid.return_value = existing_record

        token_response = await auth_service.google_login("dummy_credential")

        mock_get_gid.assert_awaited_once_with("google-sub-100")
        mock_get_email.assert_not_called()
        mock_create.assert_not_called()
        mock_save_rf.assert_awaited_once()

        assert token_response.user.id == user_id
        assert token_response.user.email == "existing@gmail.com"
        assert token_response.user.role == "customer"
        assert token_response.access_token is not None
        assert token_response.refresh_token is not None


@pytest.mark.asyncio
async def test_google_login_existing_email_links_google_id():
    """Step 2: User not found by google_id, but found by email -> link google_id to existing user."""
    user_id = uuid4()
    existing_user_without_gid = {
        "id": user_id,
        "name": "Password User",
        "email": "user@gmail.com",
        "mobile_number": "9876543210",
        "password_hash": "existing_hash",
        "google_id": None,
        "role": "customer",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    linked_user = dict(existing_user_without_gid)
    linked_user["google_id"] = "google-sub-200"

    mock_google_data = {
        "sub": "google-sub-200",
        "email": "user@gmail.com",
        "email_verified": True,
        "name": "User Name",
    }

    with patch.object(google_auth_helper, "verify_token", return_value=mock_google_data), \
         patch("app.services.auth_service.user_repository.get_by_google_id", new_callable=AsyncMock) as mock_get_gid, \
         patch("app.services.auth_service.user_repository.get_by_email", new_callable=AsyncMock) as mock_get_email, \
         patch("app.services.auth_service.user_repository.link_google_id", new_callable=AsyncMock) as mock_link, \
         patch("app.services.auth_service.user_repository.create", new_callable=AsyncMock) as mock_create, \
         patch("app.services.auth_service.user_repository.save_refresh_token", new_callable=AsyncMock) as mock_save_rf:

        mock_get_gid.return_value = None
        mock_get_email.return_value = existing_user_without_gid
        mock_link.return_value = linked_user

        token_response = await auth_service.google_login("dummy_credential")

        mock_get_gid.assert_awaited_once_with("google-sub-200")
        mock_get_email.assert_awaited_once_with("user@gmail.com")
        mock_link.assert_awaited_once_with(user_id=user_id, google_id="google-sub-200")
        mock_create.assert_not_called()
        mock_save_rf.assert_awaited_once()

        assert token_response.user.id == user_id
        assert token_response.user.email == "user@gmail.com"


@pytest.mark.asyncio
async def test_google_login_new_user_creation():
    """Step 3: Neither google_id nor email found -> creates new user with role='customer' and password_hash=NULL."""
    new_user_id = uuid4()
    created_user = {
        "id": new_user_id,
        "name": "Brand New User",
        "email": "newuser@gmail.com",
        "mobile_number": None,
        "password_hash": None,
        "google_id": "google-sub-300",
        "role": "customer",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    mock_google_data = {
        "sub": "google-sub-300",
        "email": "newuser@gmail.com",
        "email_verified": True,
        "name": "Brand New User",
    }

    with patch.object(google_auth_helper, "verify_token", return_value=mock_google_data), \
         patch("app.services.auth_service.user_repository.get_by_google_id", new_callable=AsyncMock) as mock_get_gid, \
         patch("app.services.auth_service.user_repository.get_by_email", new_callable=AsyncMock) as mock_get_email, \
         patch("app.services.auth_service.user_repository.create", new_callable=AsyncMock) as mock_create, \
         patch("app.services.auth_service.user_repository.save_refresh_token", new_callable=AsyncMock) as mock_save_rf:

        mock_get_gid.return_value = None
        mock_get_email.return_value = None
        mock_create.return_value = created_user

        token_response = await auth_service.google_login("dummy_credential")

        mock_create.assert_awaited_once_with(
            name="Brand New User",
            email="newuser@gmail.com",
            password_hash=None,
            role="customer",
            google_id="google-sub-300",
            mobile_number=None
        )
        assert token_response.user.id == new_user_id
        assert token_response.user.role == "customer"


@pytest.mark.asyncio
async def test_google_login_inactive_user_rejected():
    """Inactive accounts are rejected with ForbiddenException (ACCOUNT_DEACTIVATED)."""
    user_id = uuid4()
    inactive_user = {
        "id": user_id,
        "name": "Inactive User",
        "email": "inactive@gmail.com",
        "google_id": "google-sub-inactive",
        "role": "customer",
        "is_active": False,
    }

    mock_google_data = {
        "sub": "google-sub-inactive",
        "email": "inactive@gmail.com",
        "email_verified": True,
        "name": "Inactive User",
    }

    with patch.object(google_auth_helper, "verify_token", return_value=mock_google_data), \
         patch("app.services.auth_service.user_repository.get_by_google_id", new_callable=AsyncMock) as mock_get_gid:

        mock_get_gid.return_value = inactive_user

        with pytest.raises(ForbiddenException) as exc_info:
            await auth_service.google_login("dummy_credential")
        assert exc_info.value.error_code == "ACCOUNT_DEACTIVATED"


@pytest.mark.asyncio
async def test_google_login_duplicate_google_id_protection():
    """Ensure unique constraint violation on google_id raises ConflictException (GOOGLE_ACCOUNT_CONFLICT)."""
    user_id = uuid4()
    existing_user = {
        "id": user_id,
        "name": "Existing User",
        "email": "existing@gmail.com",
        "google_id": None,
        "role": "customer",
        "is_active": True,
    }

    mock_google_data = {
        "sub": "google-sub-conflict",
        "email": "existing@gmail.com",
        "email_verified": True,
        "name": "Existing User",
    }

    with patch.object(google_auth_helper, "verify_token", return_value=mock_google_data), \
         patch("app.services.auth_service.user_repository.get_by_google_id", new_callable=AsyncMock) as mock_get_gid, \
         patch("app.services.auth_service.user_repository.get_by_email", new_callable=AsyncMock) as mock_get_email, \
         patch("app.services.auth_service.user_repository.link_google_id", new_callable=AsyncMock) as mock_link:

        mock_get_gid.return_value = None
        mock_get_email.return_value = existing_user
        mock_link.side_effect = asyncpg.UniqueViolationError()

        with pytest.raises(ConflictException) as exc_info:
            await auth_service.google_login("dummy_credential")
        assert exc_info.value.error_code == "GOOGLE_ACCOUNT_CONFLICT"


@pytest.mark.asyncio
async def test_google_login_jwt_claims_and_validity():
    """Verify generated JWT access token contains valid sub, role, type, and expiration claims."""
    user_id = uuid4()
    user_record = {
        "id": user_id,
        "name": "JWT User",
        "email": "jwt@gmail.com",
        "google_id": "google-sub-jwt",
        "role": "customer",
        "is_active": True,
    }

    mock_google_data = {
        "sub": "google-sub-jwt",
        "email": "jwt@gmail.com",
        "email_verified": True,
        "name": "JWT User",
    }

    with patch.object(google_auth_helper, "verify_token", return_value=mock_google_data), \
         patch("app.services.auth_service.user_repository.get_by_google_id", new_callable=AsyncMock, return_value=user_record), \
         patch("app.services.auth_service.user_repository.save_refresh_token", new_callable=AsyncMock):

        response = await auth_service.google_login("dummy_credential")

        payload = decode_token(response.access_token)
        assert payload["sub"] == str(user_id)
        assert "role" not in payload
        assert response.user.role == "customer"
        assert payload["type"] == "access"
        assert "exp" in payload


@pytest.mark.asyncio
async def test_google_login_refresh_token_creation_and_hashing():
    """Verify raw refresh token is returned to client, while database receives SHA-256 hash."""
    user_id = uuid4()
    user_record = {
        "id": user_id,
        "name": "Refresh User",
        "email": "refresh@gmail.com",
        "google_id": "google-sub-refresh",
        "role": "customer",
        "is_active": True,
    }

    mock_google_data = {
        "sub": "google-sub-refresh",
        "email": "refresh@gmail.com",
        "email_verified": True,
        "name": "Refresh User",
    }

    with patch.object(google_auth_helper, "verify_token", return_value=mock_google_data), \
         patch("app.services.auth_service.user_repository.get_by_google_id", new_callable=AsyncMock, return_value=user_record), \
         patch("app.services.auth_service.user_repository.save_refresh_token", new_callable=AsyncMock) as mock_save_rf:

        response = await auth_service.google_login("dummy_credential")

        raw_refresh_token = response.refresh_token
        assert raw_refresh_token is not None
        assert len(raw_refresh_token) > 20

        # Check call arguments to user_repository.save_refresh_token
        mock_save_rf.assert_awaited_once()
        call_kwargs = mock_save_rf.call_args.kwargs
        stored_hash = call_kwargs["token_hash"]

        # Raw token MUST NOT be stored
        assert stored_hash != raw_refresh_token
        # Must match SHA-256 hash of raw token
        assert stored_hash == hash_token(raw_refresh_token)
        assert call_kwargs["user_id"] == user_id


@pytest.mark.asyncio
async def test_password_login_rejects_google_only_user():
    """Verify that email/password login on a Google-only user (password_hash=NULL) raises GOOGLE_AUTH_REQUIRED."""
    user_record = {
        "id": uuid4(),
        "name": "Google Only",
        "email": "googleonly@gmail.com",
        "password_hash": None,
        "role": "customer",
        "is_active": True,
    }

    with patch("app.services.auth_service.user_repository.get_by_email", new_callable=AsyncMock, return_value=user_record):
        login_req = LoginRequest(email="googleonly@gmail.com", password="AttemptedPassword123!")
        with pytest.raises(UnauthorizedException) as exc_info:
            await auth_service.login(login_req)
        assert exc_info.value.error_code == "GOOGLE_AUTH_REQUIRED"
        assert "Google Sign-In" in exc_info.value.message


# =============================================================================
# 3. FASTAPI API ROUTE ENDPOINT INTEGRATION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_api_google_login_endpoint_success(client: AsyncClient):
    """POST /api/v1/auth/google returns standard ResponseEnvelope[TokenResponse]."""
    user_id = uuid4()
    user_record = {
        "id": user_id,
        "name": "API User",
        "email": "apiuser@gmail.com",
        "mobile_number": None,
        "password_hash": None,
        "google_id": "google-sub-api",
        "role": "customer",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    mock_google_data = {
        "sub": "google-sub-api",
        "email": "apiuser@gmail.com",
        "email_verified": True,
        "name": "API User",
    }

    with patch.object(google_auth_helper, "verify_token", return_value=mock_google_data), \
         patch("app.services.auth_service.user_repository.get_by_google_id", new_callable=AsyncMock, return_value=user_record), \
         patch("app.services.auth_service.user_repository.save_refresh_token", new_callable=AsyncMock):

        response = await client.post(
            "/api/v1/auth/google",
            json={"credential": "valid.google.credential"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Google login successful"
        assert "access_token" in body["data"]
        assert "refresh_token" in body["data"]
        assert body["data"]["token_type"] == "bearer"
        assert body["data"]["user"]["id"] == str(user_id)
        assert body["data"]["user"]["email"] == "apiuser@gmail.com"
        assert body["data"]["user"]["role"] == "customer"


@pytest.mark.asyncio
async def test_api_google_login_endpoint_invalid_credential(client: AsyncClient):
    """POST /api/v1/auth/google with invalid credential returns 401 with standard ErrorResponse."""
    with patch.object(google_auth_helper, "verify_token", side_effect=UnauthorizedException("Invalid credential", error_code="GOOGLE_AUTH_FAILED")):
        response = await client.post(
            "/api/v1/auth/google",
            json={"credential": "invalid.credential"}
        )

        assert response.status_code == 401
        body = response.json()
        assert body["success"] is False
        assert body["error_code"] == "GOOGLE_AUTH_FAILED"


@pytest.mark.asyncio
async def test_api_google_login_endpoint_validation_error(client: AsyncClient):
    """POST /api/v1/auth/google missing credential field returns 422 VALIDATION_ERROR."""
    response = await client.post(
        "/api/v1/auth/google",
        json={}
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error_code"] == "VALIDATION_ERROR"
