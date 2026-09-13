import pytest
from httpx import AsyncClient

from app.core.exceptions import UnauthorizedException
from app.core.security import (
    create_access_token,
    decode_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.schemas.auth import LoginRequest, RegisterRequest


def test_password_hashing_and_verification():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_lifecycle():
    user_id = "a0000000-0000-0000-0000-000000000001"
    role = "admin"
    token = create_access_token(subject=user_id, role=role)
    
    payload = decode_token(token)
    assert payload["sub"] == user_id
    assert payload["role"] == role
    assert payload["type"] == "access"


def test_invalid_token_decoding():
    with pytest.raises(UnauthorizedException):
        decode_token("invalid.token.signature")


def test_refresh_token_generation_and_hashing():
    raw_token = generate_refresh_token()
    assert len(raw_token) > 30
    hashed_1 = hash_token(raw_token)
    hashed_2 = hash_token(raw_token)
    assert hashed_1 == hashed_2
    assert hashed_1 != raw_token


def test_auth_schemas_validation():
    valid_register = RegisterRequest(
        name="Test User",
        email="test@example.com",
        password="ValidPassword123!"
    )
    assert valid_register.email == "test@example.com"

    valid_login = LoginRequest(
        email="test@example.com",
        password="ValidPassword123!"
    )
    assert valid_login.email == "test@example.com"


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
