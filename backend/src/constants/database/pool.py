"""
Database connection pool configuration constants.

All values are in seconds unless otherwise specified.
"""

from typing import Final


class DatabasePoolConfig:
    """
    Database connection pool settings.

    These constants control the behavior of SQLAlchemy's connection pool
    for both SQLite (development) and PostgreSQL (production).
    """

    # Pool size settings
    SIZE_DEFAULT: Final[int] = 20
    MAX_OVERFLOW: Final[int] = 30
    TIMEOUT_SECONDS: Final[int] = 30
    RECYCLE_SECONDS: Final[int] = 3600  # 1 hour - recycle connections to prevent stale connections

    # Pool behavior
    PRE_PING_ENABLED: Final[bool] = True  # Verify connections before use
    ECHO_ENABLED: Final[bool] = False  # Log all SQL statements (debug only)

    # SQLite-specific settings
    SQLITE_TIMEOUT_SECONDS: Final[int] = 20
    SQLITE_CACHE_SIZE: Final[int] = 10000  # PRAGMA cache_size
    SQLITE_WAL_AUTOCHECKPOINT: Final[int] = 1000  # PRAGMA wal_autocheckpoint

    # Query monitoring
    SLOW_QUERY_THRESHOLD_MS: Final[float] = 100.0  # milliseconds - queries slower than this are logged
    ENABLE_QUERY_LOGGING: Final[bool] = False

    # Queue management
    QUERY_HISTORY_QUEUE_SIZE: Final[int] = 1000

    @classmethod
    def validate(cls) -> None:
        """
        Validate pool configuration consistency.

        Raises:
            ValueError: If configuration values are inconsistent.
        """
        if cls.MAX_OVERFLOW < 0:
            raise ValueError("MAX_OVERFLOW must be non-negative")
        if cls.SIZE_DEFAULT <= 0:
            raise ValueError("SIZE_DEFAULT must be positive")
        if cls.TIMEOUT_SECONDS <= 0:
            raise ValueError("TIMEOUT_SECONDS must be positive")


# Legacy compatibility aliases (deprecated, will be removed in v2.0)
POOL_SIZE = DatabasePoolConfig.SIZE_DEFAULT
MAX_OVERFLOW = DatabasePoolConfig.MAX_OVERFLOW
POOL_TIMEOUT = DatabasePoolConfig.TIMEOUT_SECONDS
