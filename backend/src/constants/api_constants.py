"""
API and HTTP constants.

Consolidated from:
- http/methods.py
- pagination/limits.py
- api_paths.py

This module provides all API-related constants including HTTP methods,
pagination limits, and API route paths.
"""

from typing import Final

from src.constants.api_paths import (
    API_PATHS,
    PREFIX_MAPPING,
    AnalyticsPaths,
    AssetPaths,
    AuthPaths,
    BackupPaths,
    BasePaths,
    CustomFieldPaths,
    ExcelPaths,
    HistoryPaths,
    OrganizationPaths,
    OwnershipPaths,
    PDFImportPaths,
    ProjectPaths,
    RentalPaths,
    RolePaths,
    StatisticsPaths,
    SystemPaths,
    UserPaths,
    dynamic_path,
)


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


class PaginationLimits:
    """
    Pagination configuration constants.

    These constants define the default and maximum pagination limits
    used throughout the application.
    """

    DEFAULT_PAGE: Final[int] = 1
    DEFAULT_SKIP: Final[int] = 0
    DEFAULT_PAGE_SIZE: Final[int] = 20
    MIN_PAGE_SIZE: Final[int] = 1
    MAX_PAGE_SIZE: Final[int] = 100
    LARGE_PAGE_SIZE: Final[int] = 50
    MAX_LARGE_PAGE_SIZE: Final[int] = 500
    SMALL_PAGE_SIZE: Final[int] = 10
    API_DEFAULT_PAGE_SIZE: Final[int] = 20
    API_MAX_PAGE_SIZE: Final[int] = 1000

    @classmethod
    def validate_page_size(cls, page_size: int) -> int:
        """
        Validate and clamp page size to acceptable range.

        Args:
            page_size: Requested page size.

        Returns:
            Validated page size within acceptable range.
        """
        if page_size < cls.MIN_PAGE_SIZE:
            return cls.DEFAULT_PAGE_SIZE
        if page_size > cls.MAX_PAGE_SIZE:
            return cls.MAX_PAGE_SIZE
        return page_size

    @classmethod
    def validate_page(cls, page: int) -> int:
        """
        Validate and clamp page number.

        Args:
            page: Requested page number.

        Returns:
            Validated page number (>= 1).
        """
        return max(page, cls.DEFAULT_PAGE)

    @classmethod
    def calculate_skip(cls, page: int, page_size: int) -> int:
        """
        Calculate skip offset for pagination.

        Args:
            page: Page number (1-indexed).
            page_size: Records per page.

        Returns:
            Number of records to skip.
        """
        validated_page = cls.validate_page(page)
        return (validated_page - 1) * page_size


GET = HTTPMethods.GET
POST = HTTPMethods.POST
PUT = HTTPMethods.PUT
DELETE = HTTPMethods.DELETE
PATCH = HTTPMethods.PATCH
OPTIONS = HTTPMethods.OPTIONS

DEFAULT_PAGE_SIZE = PaginationLimits.DEFAULT_PAGE_SIZE
MAX_PAGE_SIZE = PaginationLimits.MAX_PAGE_SIZE
DEFAULT_PAGE = PaginationLimits.DEFAULT_PAGE

__all__ = [
    # HTTP Methods
    "HTTPMethods",
    # Pagination
    "PaginationLimits",
    # API Paths
    "BasePaths",
    "AssetPaths",
    "PDFImportPaths",
    "AuthPaths",
    "UserPaths",
    "RolePaths",
    "OrganizationPaths",
    "RentalPaths",
    "OwnershipPaths",
    "ProjectPaths",
    "AnalyticsPaths",
    "StatisticsPaths",
    "ExcelPaths",
    "BackupPaths",
    "SystemPaths",
    "HistoryPaths",
    "CustomFieldPaths",
    "API_PATHS",
    "dynamic_path",
    "PREFIX_MAPPING",
]
