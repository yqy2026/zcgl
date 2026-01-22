"""
Performance and caching constants.

Consolidated from:
- performance/cache.py
- performance/monitoring.py

This module provides all performance-related constants including
cache TTL and performance thresholds.
"""

from typing import Final


class CacheTTL:
    """
    Cache expiration time constants.

    These constants define how long different types of data should
    be cached before being refreshed.
    """

    SHORT_SECONDS: Final[int] = 300
    MEDIUM_SECONDS: Final[int] = 600
    LONG_SECONDS: Final[int] = 1800
    EXTENDED_SECONDS: Final[int] = 3600
    VERY_LONG_SECONDS: Final[int] = 7200


class CacheLimits:
    """
    Cache size and behavior limits.

    These constants define the maximum size and behavior constraints
    for in-memory caches.
    """

    MAX_CRUD_ENTRIES: Final[int] = 100
    MAX_QUERY_RESULTS: Final[int] = 500
    MAX_STATS_ENTRIES: Final[int] = 50


class PerformanceThresholds:
    """
    Performance monitoring thresholds.

    These constants define the thresholds for classifying query and API
    performance as fast, normal, or slow.
    """

    FAST_QUERY_MS: Final[float] = 200.0
    NORMAL_QUERY_MS: Final[float] = 300.0
    SLOW_QUERY_MS: Final[float] = 500.0
    BATCH_UPDATE_THRESHOLD_MS: Final[float] = 500.0
    LIST_QUERY_THRESHOLD_MS: Final[float] = 300.0
    STATISTICS_QUERY_THRESHOLD_MS: Final[float] = 200.0
    FAST_RESPONSE_MS: Final[int] = 200
    ACCEPTABLE_RESPONSE_MS: Final[int] = 500
    SLOW_RESPONSE_MS: Final[int] = 1000
    GOOD_CACHE_HIT_PERCENT: Final[int] = 80
    MINIMUM_CACHE_HIT_PERCENT: Final[int] = 50

    @classmethod
    def classify_query(cls, duration_ms: float) -> str:
        """
        Classify a query based on its execution time.

        Args:
            duration_ms: Query execution time in milliseconds.

        Returns:
            Classification: "fast", "normal", or "slow".
        """
        if duration_ms <= cls.FAST_QUERY_MS:
            return "fast"
        if duration_ms <= cls.NORMAL_QUERY_MS:
            return "normal"
        return "slow"

    @classmethod
    def is_slow_query(cls, duration_ms: float) -> bool:
        """
        Determine if a query is considered slow.

        Args:
            duration_ms: Query execution time in milliseconds.

        Returns:
            True if the query is slow, False otherwise.
        """
        return duration_ms > cls.SLOW_QUERY_MS


CACHE_TTL_DEFAULT = CacheTTL.SHORT_SECONDS
CACHE_TIMEOUT = CacheTTL.SHORT_SECONDS
MAX_CACHE_SIZE = CacheLimits.MAX_CRUD_ENTRIES
SLOW_QUERY_THRESHOLD = PerformanceThresholds.SLOW_QUERY_MS
FAST_RESPONSE_THRESHOLD = PerformanceThresholds.FAST_RESPONSE_MS

__all__ = [
    "CacheLimits",
    "CacheTTL",
    "PerformanceThresholds",
]
