from typing import Any, Dict
from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.config import settings
from app.core.exceptions import UnauthorizedException


class GoogleAuthHelper:
    """Helper to verify Google OAuth2 ID tokens using Google's official auth library."""

    def verify_token(self, credential: str) -> Dict[str, Any]:
        """
        Verify Google ID token and extract verified user details.
        
        Raises UnauthorizedException if the token is invalid, expired, or has unverified email.
        """
        if not settings.GOOGLE_CLIENT_ID:
            raise UnauthorizedException(
                message="Google authentication is not configured on the server.",
                error_code="GOOGLE_AUTH_NOT_CONFIGURED"
            )

        try:
            request = requests.Request()
            payload = id_token.verify_oauth2_token(
                credential,
                request,
                settings.GOOGLE_CLIENT_ID
            )
        except ValueError:
            # Catches token expired, wrong recipient/audience, invalid signature, or malformed token
            raise UnauthorizedException(
                message="Invalid or expired Google authentication credential.",
                error_code="GOOGLE_AUTH_FAILED"
            )
        except Exception:
            raise UnauthorizedException(
                message="Google authentication verification failed.",
                error_code="GOOGLE_AUTH_FAILED"
            )

        sub = payload.get("sub")
        email = payload.get("email")
        email_verified = payload.get("email_verified")

        if not sub:
            raise UnauthorizedException(
                message="Google token missing subject identifier.",
                error_code="GOOGLE_AUTH_FAILED"
            )

        # email_verified can be boolean True or string "true"
        is_verified = (email_verified is True or email_verified == "true")
        if not email or not is_verified:
            raise UnauthorizedException(
                message="Google account email is unverified or missing.",
                error_code="GOOGLE_EMAIL_UNVERIFIED"
            )

        # Derive user name
        name = payload.get("name")
        if not name or not name.strip():
            given_name = payload.get("given_name", "")
            family_name = payload.get("family_name", "")
            name = f"{given_name} {family_name}".strip()
            if not name:
                name = email.split("@")[0]

        return {
            "sub": str(sub),
            "email": str(email).lower(),
            "email_verified": True,
            "name": str(name).strip(),
            "picture": payload.get("picture"),
            "given_name": payload.get("given_name"),
            "family_name": payload.get("family_name"),
        }


google_auth_helper = GoogleAuthHelper()
