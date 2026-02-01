"""
HttpOnly Cookie Management for Authentication

This module provides secure cookie-based authentication to eliminate
XSS vulnerabilities from localStorage token storage.

Security Features:
- HttpOnly: Prevents JavaScript access to cookies (XSS protection)
- Secure: Only sends cookies over HTTPS
- SameSite: CSRF protection (configurable, Strict by default)
- Max-Age: Automatic expiration
"""

from datetime import UTC, datetime, timedelta
import secrets

from fastapi import Response

from ..core.config import settings
from ..core.environment import is_production


class CookieManager:
    """Manage httpOnly authentication cookies"""

    def __init__(self) -> None:
        # Cookie configuration
        self.cookie_name = "auth_token"
        self.cookie_max_age = timedelta(hours=1)  # 1 hour default
        self.refresh_cookie_name = "refresh_token"
        self.refresh_cookie_max_age = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        self.csrf_cookie_name = settings.CSRF_COOKIE_NAME
        self.cookie_path = "/"
        self.cookie_domain = None  # Current domain only
        self.secure_cookie = is_production()
        self.cookie_samesite = settings.CSRF_SAMESITE

    def set_auth_cookie(
        self,
        response: Response,
        token: str,
        max_age: timedelta | None = None,
    ) -> None:
        """
        Set httpOnly authentication cookie

        Args:
            response: FastAPI Response object
            token: JWT access token
            max_age: Optional custom expiration time (defaults to 1 hour)
        """
        max_age = max_age or self.cookie_max_age

        response.set_cookie(
            key=self.cookie_name,
            value=token,
            max_age=int(max_age.total_seconds()),
            expires=datetime.now(UTC) + max_age,
            path=self.cookie_path,
            domain=self.cookie_domain,
            secure=self.secure_cookie,
            httponly=True,
            samesite=self.cookie_samesite,
        )

    def clear_auth_cookie(self, response: Response) -> None:
        """
        Clear authentication cookie

        Args:
            response: FastAPI Response object
        """
        response.delete_cookie(
            key=self.cookie_name,
            path=self.cookie_path,
            domain=self.cookie_domain,
            secure=self.secure_cookie,
            httponly=True,
            samesite=self.cookie_samesite,
        )

    def set_refresh_cookie(
        self,
        response: Response,
        token: str,
        max_age: timedelta | None = None,
    ) -> None:
        max_age = max_age or self.refresh_cookie_max_age

        response.set_cookie(
            key=self.refresh_cookie_name,
            value=token,
            max_age=int(max_age.total_seconds()),
            expires=datetime.now(UTC) + max_age,
            path=self.cookie_path,
            domain=self.cookie_domain,
            secure=self.secure_cookie,
            httponly=True,
            samesite=self.cookie_samesite,
        )

    def clear_refresh_cookie(self, response: Response) -> None:
        response.delete_cookie(
            key=self.refresh_cookie_name,
            path=self.cookie_path,
            domain=self.cookie_domain,
            secure=self.secure_cookie,
            httponly=True,
            samesite=self.cookie_samesite,
        )

    def create_csrf_token(self) -> str:
        """Generate CSRF token for double-submit protection."""
        return secrets.token_urlsafe(32)

    def set_csrf_cookie(
        self, response: Response, token: str, max_age: timedelta | None = None
    ) -> None:
        """Set CSRF token cookie (non-HttpOnly)."""
        if not settings.CSRF_ENABLED:
            return

        max_age = max_age or self.cookie_max_age
        response.set_cookie(
            key=self.csrf_cookie_name,
            value=token,
            max_age=int(max_age.total_seconds()),
            expires=datetime.now(UTC) + max_age,
            path=self.cookie_path,
            domain=self.cookie_domain,
            secure=self.secure_cookie,
            httponly=False,
            samesite=self.cookie_samesite,
        )

    def clear_csrf_cookie(self, response: Response) -> None:
        """Clear CSRF token cookie."""
        if not settings.CSRF_ENABLED:
            return

        response.delete_cookie(
            key=self.csrf_cookie_name,
            path=self.cookie_path,
            domain=self.cookie_domain,
            secure=self.secure_cookie,
            httponly=False,
            samesite=self.cookie_samesite,
        )

    def get_token_from_cookie(
        self, cookie_header: str, cookie_name: str | None = None
    ) -> str | None:
        """
        Extract token from cookie header

        Args:
            cookie_header: Raw Cookie header value

        Returns:
            Token string if found, None otherwise
        """
        if not cookie_header:
            return None

        # Parse cookie header
        cookies = {}
        for item in cookie_header.split(";"):
            if "=" in item:
                key, value = item.strip().split("=", 1)
                cookies[key] = value

        cookie_key = cookie_name or self.cookie_name
        return cookies.get(cookie_key)


# Singleton instance
cookie_manager = CookieManager()
