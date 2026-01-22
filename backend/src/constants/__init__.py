"""
Centralized constants for the backend application.

This module provides organized, domain-specific constants to eliminate
magic numbers and strings throughout the codebase.

RECOMMENDED USAGE (Consolidated imports):
    from src.constants.api_constants import HTTPMethods, PaginationLimits, BasePaths
    from src.constants.validation_constants import FieldLengthLimits, AuthFields
    from src.constants.business_constants import CommonStatusValues, DateTimeFields
    from src.constants.storage_constants import FileTypes, DatabasePoolConfig
    from src.constants.message_constants import ErrorMessages, ErrorIDs
    from src.constants.performance_constants import CacheTTL, PerformanceThresholds
"""

# New consolidated imports (recommended)
from src.constants.api_constants import (
    API_PATHS,
    PREFIX_MAPPING,
    BasePaths,
    HTTPMethods,
    PaginationLimits,
    dynamic_path,
)
from src.constants.business_constants import (
    CommonStatusValues,
    DataStatusValues,
    DateTimeFields,
)
from src.constants.message_constants import EMPTY_STRING, ErrorIDs, ErrorMessages
from src.constants.performance_constants import (
    CacheLimits,
    CacheTTL,
    PerformanceThresholds,
)
from src.constants.storage_constants import (
    DatabasePoolConfig,
    FileLimits,
    FileTypes,
)
from src.constants.validation_constants import (
    AuthFields,
    FieldLengthLimits,
    FileSizeLimits,
    ValueRanges,
)

__all__: list[str] = [
    # API & HTTP
    "HTTPMethods",
    "PaginationLimits",
    "BasePaths",
    "API_PATHS",
    "dynamic_path",
    "PREFIX_MAPPING",
    # Business Logic
    "CommonStatusValues",
    "DataStatusValues",
    "DateTimeFields",
    # Validation
    "FieldLengthLimits",
    "ValueRanges",
    "FileSizeLimits",
    "AuthFields",
    # Storage
    "FileTypes",
    "FileLimits",
    "DatabasePoolConfig",
    # Messages
    "ErrorIDs",
    "ErrorMessages",
    "EMPTY_STRING",
    # Performance
    "CacheLimits",
    "CacheTTL",
    "PerformanceThresholds",
]
