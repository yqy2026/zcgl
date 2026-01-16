"""
Cache TTL (Time To Live) constants.

All values are in seconds unless otherwise specified.
"""

from typing import Final


class CacheTTL:
    """
    Cache expiration time constants.

    These constants define how long different types of data should
    be cached before being refreshed.
    """

    # Short-term cache (5 minutes)
    SHORT_SECONDS: Final[int] = 300

    # Medium-term cache (10 minutes)
    MEDIUM_SECONDS: Final[int] = 600

    # Long-term cache (30 minutes)
    LONG_SECONDS: Final[int] = 1800

    # Extended cache (1 hour)
    EXTENDED_SECONDS: Final[int] = 3600

    # Very long cache (2 hours)
    VERY_LONG_SECONDS: Final[int] = 7200


class CacheLimits:
    """
    Cache size and behavior limits.

    These constants define the maximum size and behavior constraints
    for in-memory caches.
    """

    # Maximum number of entries in CRUD cache
    MAX_CRUD_ENTRIES: Final[int] = 100

    # Maximum number of entries in query result cache
    MAX_QUERY_RESULTS: Final[int] = 500

    # Maximum number of entries in statistics cache
    MAX_STATS_ENTRIES: Final[int] = 50


# Legacy compatibility aliases (deprecated, will be removed in v2.0)
CACHE_TTL_DEFAULT = SHORT_SECONDS
CACHE_TIMEOUT = SHORT_SECONDS
MAX_CACHE_SIZE = MAX_CRUD_ENTRIES
