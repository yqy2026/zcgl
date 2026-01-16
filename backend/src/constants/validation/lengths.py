"""
Field length validation constants.

These constants define maximum field lengths for validation throughout
the application.
"""

from typing import Final


class FieldLengthLimits:
    """
    Maximum field lengths for validation.

    These constants are used in Pydantic schemas and validation
    logic to enforce consistent field length limits.
    """

    # Text fields
    SHORT_TEXT_MAX: Final[int] = 200  # Names, titles
    MEDIUM_TEXT_MAX: Final[int] = 500  # Descriptions, addresses
    LONG_TEXT_MAX: Final[int] = 2000  # Extended text
    TEXT_FIELD_MAX: Final[int] = 10000  # Large text blocks

    # Identifier fields
    ID_MAX: Final[int] = 100
    CODE_MAX: Final[int] = 100
    PHONE_MAX: Final[int] = 20
    EMAIL_MAX: Final[int] = 255

    # Asset-specific fields
    PROPERTY_NAME_MAX: Final[int] = 200
    ADDRESS_MAX: Final[int] = 500

    # File-related
    FILENAME_MAX: Final[int] = 255  # Standard filesystem limit
    FILEPATH_MAX: Final[int] = 1000

    # URL fields
    URL_MAX: Final[int] = 2048

    # User agent
    USER_AGENT_MIN: Final[int] = 10  # Minimum reasonable user agent length


# Legacy compatibility aliases (deprecated, will be removed in v2.0)
MAX_SHORT_TEXT_LENGTH = FieldLengthLimits.SHORT_TEXT_MAX
MAX_LONG_TEXT_LENGTH = FieldLengthLimits.MEDIUM_TEXT_MAX
MAX_FILENAME_LENGTH = FieldLengthLimits.FILENAME_MAX
