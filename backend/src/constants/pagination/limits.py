"""
Pagination limit constants.

Provides standardized pagination defaults and limits to avoid
magic numbers in list endpoints and queries.
"""

from typing import Final


class PaginationLimits:
    """
    Pagination configuration constants.

    These constants define the default and maximum pagination limits
    used throughout the application.
    """

    # Page settings
    DEFAULT_PAGE: Final[int] = 1  # Default page number (1-indexed)
    DEFAULT_SKIP: Final[int] = 0  # Default number of records to skip

    # Page size settings
    DEFAULT_PAGE_SIZE: Final[int] = 20  # Default records per page
    MIN_PAGE_SIZE: Final[int] = 1  # Minimum records per page
    MAX_PAGE_SIZE: Final[int] = 100  # Maximum records per page

    # Large result set limits
    LARGE_PAGE_SIZE: Final[int] = 50  # For admin/export endpoints
    MAX_LARGE_PAGE_SIZE: Final[int] = 500  # Maximum for large queries

    # Small result set limits
    SMALL_PAGE_SIZE: Final[int] = 10  # For mobile/limited UI

    # API-specific limits
    API_DEFAULT_PAGE_SIZE: Final[int] = 20  # Default for API endpoints
    API_MAX_PAGE_SIZE: Final[int] = 1000  # Maximum for API endpoints

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


# Legacy compatibility aliases (deprecated, will be removed in v2.0)
DEFAULT_PAGE_SIZE = PaginationLimits.DEFAULT_PAGE_SIZE
MAX_PAGE_SIZE = PaginationLimits.MAX_PAGE_SIZE
DEFAULT_PAGE = PaginationLimits.DEFAULT_PAGE
