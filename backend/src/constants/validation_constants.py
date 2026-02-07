"""
Validation constants.

Consolidated from:
- validation/lengths.py
- validation/ranges.py
- validation/sizes.py
- auth/fields.py

This module provides all validation-related constants including
field lengths, value ranges, file sizes, and auth field names.
"""

from typing import Final


class AuthFields:
    """
    Authentication and authorization field names.

    These constants define the standard names used for auth-related
    fields in models and schemas.
    """

    USERNAME: Final[str] = "username"
    EMAIL: Final[str] = "email"
    PASSWORD: Final[str] = "password"
    PHONE: Final[str] = "phone"
    TOKEN: Final[str] = "token"
    REFRESH_TOKEN: Final[str] = "refresh_token"
    ACCESS_TOKEN: Final[str] = "access_token"
    RESET_TOKEN: Final[str] = "reset_token"
    USER_ID: Final[str] = "user_id"
    USER: Final[str] = "user"
    ROLE: Final[str] = "role"
    ROLE_ID: Final[str] = "role_id"
    PERMISSIONS: Final[str] = "permissions"
    SCOPES: Final[str] = "scopes"
    IS_ACTIVE: Final[str] = "is_active"
    IS_VERIFIED: Final[str] = "is_verified"
    IS_AUTHENTICATED: Final[str] = "is_authenticated"
    LAST_LOGIN: Final[str] = "last_login"
    LAST_LOGIN_AT: Final[str] = "last_login_at"
    LOGIN_COUNT: Final[str] = "login_count"
    SESSION_ID: Final[str] = "session_id"
    SESSION_TOKEN: Final[str] = "session_token"

    @classmethod
    def get_credential_fields(cls) -> list[str]:
        """
        Get list of user credential field names.

        Returns:
            List of credential-related field names.
        """
        return [cls.USERNAME, cls.EMAIL, cls.PASSWORD, cls.PHONE]

    @classmethod
    def get_token_fields(cls) -> list[str]:
        """
        Get list of authentication token field names.

        Returns:
            List of token-related field names.
        """
        return [cls.TOKEN, cls.REFRESH_TOKEN, cls.ACCESS_TOKEN, cls.RESET_TOKEN]

    @classmethod
    def get_status_fields(cls) -> list[str]:
        """
        Get list of user status field names.

        Returns:
            List of status-related field names.
        """
        return [cls.IS_ACTIVE, cls.IS_VERIFIED, cls.IS_AUTHENTICATED]


class FieldLengthLimits:
    """
    Maximum field lengths for validation.

    These constants are used in Pydantic schemas and validation
    logic to enforce consistent field length limits.
    """

    SHORT_TEXT_MAX: Final[int] = 200
    MEDIUM_TEXT_MAX: Final[int] = 500
    LONG_TEXT_MAX: Final[int] = 2000
    TEXT_FIELD_MAX: Final[int] = 10000
    ID_MAX: Final[int] = 100
    CODE_MAX: Final[int] = 100
    PHONE_MAX: Final[int] = 20
    EMAIL_MAX: Final[int] = 255
    PROPERTY_NAME_MAX: Final[int] = 200
    ADDRESS_MAX: Final[int] = 500
    FILENAME_MAX: Final[int] = 255
    FILEPATH_MAX: Final[int] = 1000
    URL_MAX: Final[int] = 2048
    USER_AGENT_MIN: Final[int] = 10


class ValueRanges:
    """
    Numeric value range constants for validation.

    These constants define the acceptable ranges for various numeric
    fields used throughout the application.
    """

    LAND_AREA_MAX: Final[float] = 999999.99
    PROPERTY_AREA_MAX: Final[float] = 999999.99
    RENTABLE_AREA_MAX: Final[float] = 999999.99
    RENTED_AREA_MAX: Final[float] = 999999.99
    MIN_AREA: Final[float] = 0.0
    MONTHLY_RENT_MAX: Final[float] = 99999999.99
    DEPOSIT_MAX: Final[float] = 99999999.99
    AMOUNT_MIN: Final[float] = 0.0
    PERCENTAGE_MIN: Final[float] = 0.0
    PERCENTAGE_MAX: Final[float] = 100.0
    OCCUPANCY_RATE_MIN: Final[float] = 0.0
    OCCUPANCY_RATE_MAX: Final[float] = 100.0
    MAX_COUNT: Final[int] = 999999
    MIN_COUNT: Final[int] = 0
    PAGE_SIZE_MIN: Final[int] = 1
    PAGE_SIZE_MAX: Final[int] = 10000
    PAGE_SIZE_DEFAULT: Final[int] = 20

    @classmethod
    def validate_area(cls, area: float) -> bool:
        """
        Validate an area value.

        Args:
            area: The area value in square meters.

        Returns:
            True if the area is within acceptable range, False otherwise.
        """
        return cls.MIN_AREA <= area <= cls.PROPERTY_AREA_MAX

    @classmethod
    def validate_percentage(cls, value: float) -> bool:
        """
        Validate a percentage value.

        Args:
            value: The percentage value.

        Returns:
            True if the value is between 0 and 100, False otherwise.
        """
        return cls.PERCENTAGE_MIN <= value <= cls.PERCENTAGE_MAX

    @classmethod
    def validate_positive_number(cls, value: float) -> bool:
        """
        Validate that a number is positive.

        Args:
            value: The numeric value.

        Returns:
            True if the value is positive, False otherwise.
        """
        return value > cls.AMOUNT_MIN


class FileSizeLimits:
    """
    File size limit constants.

    These constants define the maximum allowed file sizes for different
    file types and contexts. All values are in megabytes (MB) unless
    otherwise specified.
    """

    SMALL_FILE_MAX_MB: Final[int] = 1
    AVATAR_MAX_MB: Final[int] = 2
    MEDIUM_FILE_MAX_MB: Final[int] = 10
    IMAGE_MAX_MB: Final[int] = 5
    LARGE_FILE_MAX_MB: Final[int] = 50
    EXCEL_MAX_MB: Final[int] = 50
    PDF_MAX_MB: Final[int] = 100
    VERY_LARGE_FILE_MAX_MB: Final[int] = 500
    ARCHIVE_MAX_MB: Final[int] = 500
    CSV_MAX_MB: Final[int] = 10
    JSON_MAX_MB: Final[int] = 5
    TEXT_MAX_MB: Final[int] = 1
    MIN_FILE_SIZE_BYTES: Final[int] = 1024
    MIN_FILE_SIZE_MB: Final[float] = 0.001
    EXCEL_MAX_BYTES: Final[int] = EXCEL_MAX_MB * 1024 * 1024
    PDF_MAX_BYTES: Final[int] = PDF_MAX_MB * 1024 * 1024
    IMAGE_MAX_BYTES: Final[int] = IMAGE_MAX_MB * 1024 * 1024

    @classmethod
    def mb_to_bytes(cls, size_mb: int) -> int:
        """
        Convert megabytes to bytes.

        Args:
            size_mb: Size in megabytes.

        Returns:
            Size in bytes.
        """
        return size_mb * 1024 * 1024

    @classmethod
    def bytes_to_mb(cls, size_bytes: int) -> float:
        """
        Convert bytes to megabytes.

        Args:
            size_bytes: Size in bytes.

        Returns:
            Size in megabytes.
        """
        return size_bytes / (1024 * 1024)

    @classmethod
    def validate_file_size(cls, file_size_bytes: int, max_size_mb: int) -> bool:
        """
        Validate if a file size is within the allowed limit.

        Args:
            file_size_bytes: The file size in bytes.
            max_size_mb: The maximum allowed size in megabytes.

        Returns:
            True if the file size is acceptable, False otherwise.
        """
        max_size_bytes = cls.mb_to_bytes(max_size_mb)
        return cls.MIN_FILE_SIZE_BYTES <= file_size_bytes <= max_size_bytes


EMAIL = AuthFields.EMAIL
PASSWORD = AuthFields.PASSWORD
USERNAME = AuthFields.USERNAME
MAX_SHORT_TEXT_LENGTH = FieldLengthLimits.SHORT_TEXT_MAX
MAX_LONG_TEXT_LENGTH = FieldLengthLimits.MEDIUM_TEXT_MAX
MAX_FILENAME_LENGTH = FieldLengthLimits.FILENAME_MAX
MAX_PROPERTY_VALUE = ValueRanges.PROPERTY_AREA_MAX
MAX_LAND_AREA = ValueRanges.LAND_AREA_MAX
MAX_RENTABLE_AREA = ValueRanges.RENTABLE_AREA_MAX
MAX_RENTED_AREA = ValueRanges.RENTED_AREA_MAX
MAX_MONTHLY_RENT = ValueRanges.MONTHLY_RENT_MAX
MAX_EXCEL_SIZE = FileSizeLimits.EXCEL_MAX_MB
MAX_PDF_SIZE = FileSizeLimits.PDF_MAX_MB
MAX_IMAGE_SIZE = FileSizeLimits.IMAGE_MAX_MB

__all__ = [
    "FieldLengthLimits",
    "ValueRanges",
    "FileSizeLimits",
    "AuthFields",
]
