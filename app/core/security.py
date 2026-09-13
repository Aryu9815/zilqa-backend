import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings
from app.core.exceptions import UnauthorizedException

# Configure modern password hashing with Argon2 as primary, Bcrypt as secondary
password_hash = PasswordHash((
    Argon2Hasher(),
    BcryptHasher(),
))


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2/Bcrypt."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against the stored hash."""
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(
    subject: Union[str, Any],
    role: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """Create a short-lived JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    if additional_claims:
        to_encode.update(additional_claims)
        
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException(message="Token has expired", error_code="TOKEN_EXPIRED")
    except jwt.InvalidTokenError:
        raise UnauthorizedException(message="Invalid token", error_code="INVALID_TOKEN")


def generate_refresh_token() -> str:
    """Generate a secure cryptographic random string for refresh token."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Hash a token using SHA-256 for secure database lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
