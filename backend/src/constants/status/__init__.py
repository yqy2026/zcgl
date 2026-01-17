"""
Status constants module.

This module provides status-related constants for use throughout
the application to avoid magic status strings.
"""

from src.constants.status.common import CommonStatusValues
from src.constants.status.data import DataStatusValues

__all__ = ["CommonStatusValues", "DataStatusValues"]
