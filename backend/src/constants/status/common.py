"""
Status constants for common application states.

This module provides centralized status value constants to avoid
magic strings throughout the codebase.
"""

from typing import Final


class CommonStatusValues:
    """
    Common status string values.

    These constants define the actual string values used in the database
    for common status fields. These are kept for backward compatibility
    during the migration to enums.
    """

    # Active lifecycle statuses
    ACTIVE: Final[str] = "active"
    INACTIVE: Final[str] = "inactive"
    DELETED: Final[str] = "deleted"
    ARCHIVED: Final[str] = "archived"

    # Task/operation statuses
    PENDING: Final[str] = "pending"
    IN_PROGRESS: Final[str] = "in_progress"
    PROCESSING: Final[str] = "processing"
    COMPLETED: Final[str] = "completed"
    FAILED: Final[str] = "failed"
    CANCELLED: Final[str] = "cancelled"

    # Draft/publish workflow
    DRAFT: Final[str] = "draft"
    PUBLISHED: Final[str] = "published"

    # Verification states
    VERIFIED: Final[str] = "verified"
    UNVERIFIED: Final[str] = "unverified"

    # Suspension states
    SUSPENDED: Final[str] = "suspended"
    BLOCKED: Final[str] = "blocked"

    # Error states
    ERROR: Final[str] = "error"
    TIMEOUT: Final[str] = "timeout"

    @classmethod
    def get_active_statuses(cls) -> list[str]:
        """Get list of statuses considered active (not deleted/archived)."""
        return [cls.ACTIVE, cls.INACTIVE, cls.PENDING]

    @classmethod
    def get_terminal_statuses(cls) -> list[str]:
        """Get list of terminal statuses (no further state changes)."""
        return [cls.COMPLETED, cls.FAILED, cls.CANCELLED, cls.DELETED, cls.ARCHIVED]

    @classmethod
    def is_active(cls, status: str) -> bool:
        """Check if a status is considered active."""
        return status in [cls.ACTIVE, cls.INACTIVE, cls.VERIFIED]

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        """Check if a status is terminal."""
        return status in cls.get_terminal_statuses()


# Legacy compatibility aliases (deprecated, will be removed in v2.0)
STATUS_ACTIVE = CommonStatusValues.ACTIVE
STATUS_INACTIVE = CommonStatusValues.INACTIVE
STATUS_PENDING = CommonStatusValues.PENDING
STATUS_COMPLETED = CommonStatusValues.COMPLETED
STATUS_FAILED = CommonStatusValues.FAILED
