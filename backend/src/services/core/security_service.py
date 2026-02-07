"""
Security Service - Stub Implementation (SAFEGUARDED)

This file previously contained insecure stub implementations.
It has been modified to prevent accidental usage in production.

DO NOT USE THIS SERVICE. Use `src.services.core.password_service.PasswordService` instead.
"""

from typing import Any

from ...exceptions import BusinessLogicError


class SecurityService:
    """
    Security service stub - DEPRECATED / UNSAFE

    This class exists only for backward compatibility with tests that might import it.
    All methods now raise errors to prevent usage in production code.
    """

    def __init__(self) -> None:
        """Initialize security service"""
        pass

    def validate_password(self, password: str) -> bool:
        """Validate password strength"""
        raise BusinessLogicError(
            "SecurityService.validate_password is deprecated and unsafe. "
            "Use PasswordService.validate_password_strength() instead."
        )

    def hash_password(self, password: str) -> str:
        """Hash password"""
        raise BusinessLogicError(
            "SecurityService.hash_password is deprecated and unsafe. "
            "Use PasswordService.get_password_hash() instead."
        )

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        raise BusinessLogicError(
            "SecurityService.verify_password is deprecated and unsafe. "
            "Use PasswordService.verify_password() instead."
        )

    def generate_token(self, user_id: str) -> str:
        """Generate authentication token"""
        raise BusinessLogicError(
            "SecurityService.generate_token is deprecated. "
            "Use AsyncAuthenticationService or jwt_security module instead."
        )

    def validate_token(self, token: str) -> dict[str, Any]:
        """Validate and decode token"""
        raise BusinessLogicError(
            "SecurityService.validate_token is deprecated. "
            "Use AsyncAuthenticationService or jwt_security module instead."
        )


# Singleton instance
security_service = SecurityService()

__all__ = ["SecurityService", "security_service"]
