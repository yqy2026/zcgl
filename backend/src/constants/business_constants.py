"""
Business logic constants.

Consolidated from:
- status/common.py
- status/data.py
- datetime/fields.py

This module provides all business-related constants including
status values and datetime field names.
"""

from typing import Final


class CommonStatusValues:
    """
    Common status string values.

    These constants define the actual string values used in the database
    for common status fields. These are kept for backward compatibility
    during the migration to enums.
    """

    ACTIVE: Final[str] = "active"
    INACTIVE: Final[str] = "inactive"
    DELETED: Final[str] = "deleted"
    ARCHIVED: Final[str] = "archived"
    PENDING: Final[str] = "pending"
    IN_PROGRESS: Final[str] = "in_progress"
    PROCESSING: Final[str] = "processing"
    COMPLETED: Final[str] = "completed"
    FAILED: Final[str] = "failed"
    CANCELLED: Final[str] = "cancelled"
    DRAFT: Final[str] = "draft"
    PUBLISHED: Final[str] = "published"
    VERIFIED: Final[str] = "verified"
    UNVERIFIED: Final[str] = "unverified"
    SUSPENDED: Final[str] = "suspended"
    BLOCKED: Final[str] = "blocked"
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


class DataStatusValues:
    """
    Data lifecycle status values.

    These constants define the status values for data entities throughout
    their lifecycle (normal, abnormal, deleted, etc.).
    """

    ASSET_NORMAL: Final[str] = "正常"
    ASSET_ABNORMAL: Final[str] = "异常"
    ASSET_DELETED: Final[str] = "已删除"
    ASSET_ARCHIVED: Final[str] = "已归档"
    OWNERSHIP_CONFIRMED: Final[str] = "已确权"
    OWNERSHIP_UNCONFIRMED: Final[str] = "未确权"
    OWNERSHIP_PARTIAL: Final[str] = "部分确权"
    PROPERTY_OPERATIONAL: Final[str] = "经营性"
    PROPERTY_NON_OPERATIONAL: Final[str] = "非经营性"
    USAGE_RENTED: Final[str] = "出租"
    USAGE_SELF_USE: Final[str] = "自用"
    USAGE_VACANT: Final[str] = "空置"
    USAGE_OTHER: Final[str] = "其他"
    CONTRACT_ACTIVE: Final[str] = "生效"
    CONTRACT_EXPIRED: Final[str] = "过期"
    CONTRACT_TERMINATED: Final[str] = "终止"
    CONTRACT_PENDING: Final[str] = "待生效"

    @classmethod
    def get_active_asset_statuses(cls) -> list[str]:
        """Get list of active asset statuses (not deleted or archived)."""
        return [cls.ASSET_NORMAL, cls.ASSET_ABNORMAL]

    @classmethod
    def is_asset_active(cls, status: str) -> bool:
        """Check if an asset status is active."""
        return status in cls.get_active_asset_statuses()

    @classmethod
    def get_ownership_statuses(cls) -> list[str]:
        """Get all ownership status values."""
        return [
            cls.OWNERSHIP_CONFIRMED,
            cls.OWNERSHIP_UNCONFIRMED,
            cls.OWNERSHIP_PARTIAL,
        ]


class DateTimeFields:
    """
    Common datetime field names.

    These constants define the standard names used for timestamp fields
    throughout the application models.
    """

    CREATED_AT: Final[str] = "created_at"
    UPDATED_AT: Final[str] = "updated_at"
    DELETED_AT: Final[str] = "deleted_at"
    LAST_ACCESSED_AT: Final[str] = "last_accessed_at"
    EXPIRES_AT: Final[str] = "expires_at"
    VERIFIED_AT: Final[str] = "verified_at"
    ARCHIVED_AT: Final[str] = "archived_at"
    PUBLISHED_AT: Final[str] = "published_at"
    LAST_LOGIN_AT: Final[str] = "last_login_at"
    LAST_MODIFIED_AT: Final[str] = "last_modified_at"
    LAST_SYNCED_AT: Final[str] = "last_synced_at"

    @classmethod
    def get_timestamp_fields(cls) -> list[str]:
        """
        Get list of standard timestamp fields for whitelisting.

        Returns:
            List of common timestamp field names.
        """
        return [cls.CREATED_AT, cls.UPDATED_AT, cls.DELETED_AT]

    @classmethod
    def get_auditing_fields(cls) -> list[str]:
        """
        Get list of audit-related timestamp fields.

        Returns:
            List of audit field names used for tracking changes.
        """
        return [
            cls.CREATED_AT,
            cls.UPDATED_AT,
            cls.DELETED_AT,
            cls.LAST_ACCESSED_AT,
            cls.LAST_MODIFIED_AT,
        ]

    @classmethod
    def is_timestamp_field(cls, field_name: str) -> bool:
        """
        Check if a field name is a timestamp field.

        Args:
            field_name: The field name to check.

        Returns:
            True if the field is a timestamp field, False otherwise.
        """
        return field_name in cls.get_timestamp_fields()


STATUS_ACTIVE = CommonStatusValues.ACTIVE
STATUS_INACTIVE = CommonStatusValues.INACTIVE
STATUS_PENDING = CommonStatusValues.PENDING
STATUS_COMPLETED = CommonStatusValues.COMPLETED
STATUS_FAILED = CommonStatusValues.FAILED
ASSET_STATUS_NORMAL = DataStatusValues.ASSET_NORMAL
ASSET_STATUS_ABNORMAL = DataStatusValues.ASSET_ABNORMAL
OWNERSHIP_STATUS_CONFIRMED = DataStatusValues.OWNERSHIP_CONFIRMED
CREATED_AT = DateTimeFields.CREATED_AT
UPDATED_AT = DateTimeFields.UPDATED_AT
DELETED_AT = DateTimeFields.DELETED_AT

__all__ = [
    "CommonStatusValues",
    "DataStatusValues",
    "DateTimeFields",
]
