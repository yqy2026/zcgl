"""
Value range constants.

Provides standardized numeric ranges for validation throughout
the application to avoid magic numbers in schemas and validators.
"""

from typing import Final


class ValueRanges:
    """
    Numeric value range constants for validation.

    These constants define the acceptable ranges for various numeric
    fields used throughout the application.
    """

    # Area values (in square meters)
    LAND_AREA_MAX: Final[float] = 999999.99
    PROPERTY_AREA_MAX: Final[float] = 999999.99
    RENTABLE_AREA_MAX: Final[float] = 999999.99
    RENTED_AREA_MAX: Final[float] = 999999.99
    MIN_AREA: Final[float] = 0.0

    # Financial values (currency)
    MONTHLY_RENT_MAX: Final[float] = 99999999.99
    DEPOSIT_MAX: Final[float] = 99999999.99
    AMOUNT_MIN: Final[float] = 0.0

    # Percentages (0-100)
    PERCENTAGE_MIN: Final[float] = 0.0
    PERCENTAGE_MAX: Final[float] = 100.0

    # Rates and ratios
    OCCUPANCY_RATE_MIN: Final[float] = 0.0
    OCCUPANCY_RATE_MAX: Final[float] = 100.0

    # Count values
    MAX_COUNT: Final[int] = 999999
    MIN_COUNT: Final[int] = 0

    # Page sizes and limits
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


# Legacy compatibility aliases (deprecated, will be removed in v2.0)
MAX_PROPERTY_VALUE = ValueRanges.PROPERTY_AREA_MAX
MAX_LAND_AREA = ValueRanges.LAND_AREA_MAX
MAX_RENTABLE_AREA = ValueRanges.RENTABLE_AREA_MAX
MAX_RENTED_AREA = ValueRanges.RENTED_AREA_MAX
MAX_MONTHLY_RENT = ValueRanges.MONTHLY_RENT_MAX
