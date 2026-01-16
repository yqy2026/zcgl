"""
DateTime field name constants.

Provides standardized field names for datetime fields across all models
to avoid magic strings and improve maintainability.
"""

from typing import Final


class DateTimeFields:
    """
    Common datetime field names.

    These constants define the standard names used for timestamp fields
    throughout the application models.
    """

    # Standard timestamp fields
    CREATED_AT: Final[str] = "created_at"
    UPDATED_AT: Final[str] = "updated_at"
    DELETED_AT: Final[str] = "deleted_at"

    # Additional tracking fields
    LAST_ACCESSED_AT: Final[str] = "last_accessed_at"
    EXPIRES_AT: Final[str] = "expires_at"
    VERIFIED_AT: Final[str] = "verified_at"
    ARCHIVED_AT: Final[str] = "archived_at"
    PUBLISHED_AT: Final[str] = "published_at"

    # Activity tracking
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


# Legacy compatibility aliases (deprecated, will be removed in v2.0)
CREATED_AT = DateTimeFields.CREATED_AT
UPDATED_AT = DateTimeFields.UPDATED_AT
DELETED_AT = DateTimeFields.DELETED_AT
