"""
HTTP method constants.

Provides standardized HTTP method names to avoid magic strings
in API route definitions and middleware.
"""

from typing import Final


class HTTPMethods:
    """
    HTTP method constants.

    These constants provide type-safe references to HTTP methods
    used throughout the application.
    """

    GET: Final[str] = "GET"
    POST: Final[str] = "POST"
    PUT: Final[str] = "PUT"
    PATCH: Final[str] = "PATCH"
    DELETE: Final[str] = "DELETE"
    OPTIONS: Final[str] = "OPTIONS"
    HEAD: Final[str] = "HEAD"
    TRACE: Final[str] = "TRACE"
    CONNECT: Final[str] = "CONNECT"

    @classmethod
    def get_common_methods(cls) -> list[str]:
        """
        Get list of commonly used HTTP methods.

        Returns:
            List of common HTTP method names.
        """
        return [cls.GET, cls.POST, cls.PUT, cls.PATCH, cls.DELETE]

    @classmethod
    def get_data_modifying_methods(cls) -> list[str]:
        """
        Get list of HTTP methods that modify data.

        Returns:
            List of HTTP methods that change server state.
        """
        return [cls.POST, cls.PUT, cls.PATCH, cls.DELETE]

    @classmethod
    def get_safe_methods(cls) -> list[str]:
        """
        Get list of HTTP methods that are safe (idempotent).

        Returns:
            List of HTTP methods that don't modify server state.
        """
        return [cls.GET, cls.HEAD, cls.OPTIONS]

    @classmethod
    def is_safe_method(cls, method: str) -> bool:
        """
        Check if an HTTP method is safe (doesn't modify state).

        Args:
            method: The HTTP method to check.

        Returns:
            True if the method is safe, False otherwise.
        """
        return method.upper() in cls.get_safe_methods()


# Legacy compatibility aliases (deprecated, will be removed in v2.0)
GET = HTTPMethods.GET
POST = HTTPMethods.POST
PUT = HTTPMethods.PUT
DELETE = HTTPMethods.DELETE
PATCH = HTTPMethods.PATCH
OPTIONS = HTTPMethods.OPTIONS
