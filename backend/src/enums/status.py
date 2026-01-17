"""
Status enumeration constants.

This module provides type-safe enums for status values throughout the application,
replacing magic status strings with enum-based constants.
"""

from enum import Enum


class AssetStatus(str, Enum):
    """
    Asset data status values.

    Represents the lifecycle status of asset records in the system.
    """

    NORMAL = "正常"
    ABNORMAL = "异常"
    DELETED = "已删除"
    ARCHIVED = "已归档"

    @classmethod
    def get_active_statuses(cls) -> list["AssetStatus"]:
        """Get list of non-deleted/active statuses."""
        return [cls.NORMAL, cls.ABNORMAL]

    @classmethod
    def is_active(cls, status: str) -> bool:
        """
        Check if an asset status is considered active (not deleted or archived).

        Args:
            status: The status string to check.

        Returns:
            True if the status is active, False otherwise.
        """
        return status in [cls.NORMAL.value, cls.ABNORMAL.value]


class UserStatus(str, Enum):
    """
    User account status values.

    Represents the authentication and authorization status of user accounts.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"

    @classmethod
    def is_active(cls, status: str) -> bool:
        """
        Check if a user status is considered active.

        Args:
            status: The status string to check.

        Returns:
            True if the user is active, False otherwise.
        """
        return status == cls.ACTIVE.value

    @classmethod
    def can_login(cls, status: str) -> bool:
        """
        Check if a user with the given status can login.

        Args:
            status: The status string to check.

        Returns:
            True if the user can login, False otherwise.
        """
        return status == cls.ACTIVE.value


class TaskExecutionStatus(str, Enum):
    """
    Task execution status values.

    Represents the current state of background or async tasks.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        """
        Check if a task status is terminal (no further transitions possible).

        Args:
            status: The status string to check.

        Returns:
            True if the task is in a terminal state, False otherwise.
        """
        return status in [cls.COMPLETED.value, cls.FAILED.value, cls.CANCELLED.value]

    @classmethod
    def is_in_progress(cls, status: str) -> bool:
        """
        Check if a task is currently running.

        Args:
            status: The status string to check.

        Returns:
            True if the task is running, False otherwise.
        """
        return status == cls.RUNNING.value


class ContractStatus(str, Enum):
    """
    Contract lifecycle status values.

    Represents the current state of contracts in the system.
    """

    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    PENDING_RENEWAL = "pending_renewal"

    @classmethod
    def is_active(cls, status: str) -> bool:
        """
        Check if a contract is currently active.

        Args:
            status: The status string to check.

        Returns:
            True if the contract is active, False otherwise.
        """
        return status == cls.ACTIVE.value

    @classmethod
    def get_modifiable_statuses(cls) -> list["ContractStatus"]:
        """Get list of statuses that allow contract modification."""
        return [cls.DRAFT, cls.ACTIVE, cls.PENDING_RENEWAL]


class DocumentStatus(str, Enum):
    """
    Document processing status values.

    Represents the processing state of uploaded documents.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    @classmethod
    def is_complete(cls, status: str) -> bool:
        """
        Check if document processing is complete (success or failure).

        Args:
            status: The status string to check.

        Returns:
            True if processing is complete, False otherwise.
        """
        return status in [cls.COMPLETED.value, cls.FAILED.value]


class CommonStatus(str, Enum):
    """
    Common status values used across multiple entity types.

    Provides a standard set of statuses for entities that follow
    a simple active/inactive lifecycle.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"
    ARCHIVED = "archived"

    @classmethod
    def is_visible(cls, status: str) -> bool:
        """
        Check if an entity with the given status should be visible in listings.

        Args:
            status: The status string to check.

        Returns:
            True if visible, False otherwise.
        """
        return status in [cls.ACTIVE.value, cls.INACTIVE.value]
