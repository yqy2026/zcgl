"""
Performance monitoring thresholds.

All timing values are in milliseconds unless otherwise specified.
"""

from typing import Final


class PerformanceThresholds:
    """
    Performance monitoring thresholds.

    These constants define the thresholds for classifying query and API
    performance as fast, normal, or slow.
    """

    # Query performance thresholds (milliseconds)
    FAST_QUERY_MS: Final[float] = 200.0  # Fast queries
    NORMAL_QUERY_MS: Final[float] = 300.0  # Normal queries
    SLOW_QUERY_MS: Final[float] = 500.0  # Slow queries (logged for optimization)

    # Batch update thresholds
    BATCH_UPDATE_THRESHOLD_MS: Final[float] = 500.0

    # List query thresholds
    LIST_QUERY_THRESHOLD_MS: Final[float] = 300.0

    # Statistics query thresholds
    STATISTICS_QUERY_THRESHOLD_MS: Final[float] = 200.0

    # API response times (milliseconds)
    FAST_RESPONSE_MS: Final[int] = 200
    ACCEPTABLE_RESPONSE_MS: Final[int] = 500
    SLOW_RESPONSE_MS: Final[int] = 1000

    # Cache performance metrics
    GOOD_CACHE_HIT_PERCENT: Final[int] = 80  # Target cache hit rate
    MINIMUM_CACHE_HIT_PERCENT: Final[int] = 50  # Minimum acceptable cache hit rate

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
        elif duration_ms <= cls.NORMAL_QUERY_MS:
            return "normal"
        else:
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


# Legacy compatibility aliases (deprecated, will be removed in v2.0)
SLOW_QUERY_THRESHOLD = SLOW_QUERY_MS
FAST_RESPONSE_THRESHOLD = FAST_RESPONSE_MS
