"""
Error ID Constants for Logging and Monitoring

This module contains centralized error ID constants used throughout the application.
These constants provide:
- Type safety through autocomplete
- Consistency across log aggregation tools (Sentry, ELK, etc.)
- Easy tracking of error patterns in production

Usage:
    from src.constants.errors.error_ids import ErrorIDs
    import logging

    logger.error(
        "Database connection failed",
        extra={"error_id": ErrorIDs.DB_CONNECTION_FAILED}
    )

Error ID Format:
- UPPERCASE with underscores
- Descriptive but concise
- Grouped by subsystem
"""

from typing import Final


class ErrorIDs:
    """Centralized error ID registry for structured logging"""

    # ========================================================================
    # Database Error IDs
    # ========================================================================

    class Database:
        """Database-related error IDs"""

        # Connection errors
        CONNECTION_FAILED: Final[str] = "DB_CONNECTION_FAILED"
        CONNECTION_TIMEOUT: Final[str] = "DB_CONNECTION_TIMEOUT"
        CONNECTION_REFUSED: Final[str] = "DB_CONNECTION_REFUSED"
        AUTHENTICATION_FAILED: Final[str] = "DB_AUTHENTICATION_FAILED"
        DATABASE_NOT_FOUND: Final[str] = "DB_DATABASE_NOT_FOUND"

        # URL validation errors
        URL_MALFORMED: Final[str] = "DB_URL_MALFORMED"
        URL_MISSING_HOSTNAME: Final[str] = "DB_URL_MISSING_HOSTNAME"
        URL_MISSING_USERNAME: Final[str] = "DB_URL_MISSING_USERNAME"
        URL_MISSING_PASSWORD: Final[str] = "DB_URL_MISSING_PASSWORD"
        URL_MISSING_DATABASE: Final[str] = "DB_URL_MISSING_DATABASE"
        URL_INVALID_PORT: Final[str] = "DB_URL_INVALID_PORT"

        # Health check errors
        HEALTH_CHECK_FAILED: Final[str] = "DB_HEALTH_CHECK_FAILED"
        HEALTH_CHECK_UNKNOWN_ERROR: Final[str] = "DB_HEALTH_CHECK_UNKNOWN_ERROR"

        # Session errors
        SESSION_ERROR: Final[str] = "DB_SESSION_ERROR"
        ROLLBACK_FAILED: Final[str] = "DB_ROLLBACK_FAILED"

        # Configuration errors
        MISSING_DATABASE_URL: Final[str] = "MISSING_DATABASE_URL"
        MISSING_DATABASE_URL_DEV: Final[str] = "MISSING_DATABASE_URL_DEV"
        MISSING_DATABASE_URL_STAGING: Final[str] = "MISSING_DATABASE_URL_STAGING"
        USING_DEFAULT_SQLITE: Final[str] = "USING_DEFAULT_SQLITE"
        SQLITE_FALLBACK_EXPLICIT: Final[str] = "SQLITE_FALLBACK_EXPLICIT"
        SQLITE_IN_PRODUCTION: Final[str] = "SQLITE_IN_PRODUCTION"

        # Pool errors
        POOL_EXHAUSTED: Final[str] = "DB_POOL_EXHAUSTED"
        POOL_TIMEOUT: Final[str] = "DB_POOL_TIMEOUT"

    # ========================================================================
    # Audit Log Error IDs
    # ========================================================================

    class AuditLog:
        """Audit log related error IDs"""

        CREATION_FAILED: Final[str] = "AUDIT_LOG_FAILED"
        FALLBACK_FILE_WRITE_FAILED: Final[str] = "AUDIT_LOG_FALLBACK_FAILED"
        DB_WRITE_FAILED: Final[str] = "AUDIT_LOG_DB_WRITE_FAILED"
        VALIDATION_FAILED: Final[str] = "AUDIT_LOG_VALIDATION_FAILED"
        SERIALIZATION_FAILED: Final[str] = "AUDIT_LOG_SERIALIZATION_FAILED"

        # 🔒 安全修复: 添加审计日志回退机制错误ID
        FALLBACK_TO_FILE: Final[str] = "AUDIT_LOG_FALLBACK_TO_FILE"
        FALLBACK_TO_SYSLOG: Final[str] = "AUDIT_LOG_FALLBACK_TO_SYSLOG"
        FALLBACK_TO_WIN_EVENTLOG: Final[str] = "AUDIT_LOG_FALLBACK_TO_WIN_EVENTLOG"
        ALL_FALLBACKS_FAILED: Final[str] = "AUDIT_LOG_ALL_FALLBACKS_FAILED"
        STATUS_UNKNOWN: Final[str] = "AUDIT_LOG_STATUS_UNKNOWN"

    # ========================================================================
    # System Settings Error IDs
    # ========================================================================

    class SystemSettings:
        """System settings related error IDs"""

        VALIDATION_ERROR: Final[str] = "SYSTEM_SETTINGS_VALIDATION_ERROR"
        UPDATE_FAILED: Final[str] = "SYSTEM_SETTINGS_UPDATE_FAILED"
        UNEXPECTED_ERROR: Final[str] = "SYSTEM_SETTINGS_UNEXPECTED_ERROR"
        BACKUP_FAILED: Final[str] = "SYSTEM_SETTINGS_BACKUP_FAILED"
        RESTORE_FAILED: Final[str] = "SYSTEM_SETTINGS_RESTORE_FAILED"

    # ========================================================================
    # Authentication Error IDs
    # ========================================================================

    class Auth:
        """Authentication related error IDs"""

        LOGIN_FAILED: Final[str] = "AUTH_LOGIN_FAILED"
        TOKEN_INVALID: Final[str] = "AUTH_TOKEN_INVALID"
        TOKEN_EXPIRED: Final[str] = "AUTH_TOKEN_EXPIRED"
        PERMISSION_DENIED: Final[str] = "AUTH_PERMISSION_DENIED"
        USER_NOT_FOUND: Final[str] = "AUTH_USER_NOT_FOUND"
        INVALID_CREDENTIALS: Final[str] = "AUTH_INVALID_CREDENTIALS"

    # ========================================================================
    # API Error IDs
    # ========================================================================

    class API:
        """API-related error IDs"""

        REQUEST_VALIDATION_FAILED: Final[str] = "API_REQUEST_VALIDATION_FAILED"
        RESPONSE_SERIALIZATION_FAILED: Final[str] = "API_RESPONSE_SERIALIZATION_FAILED"
        RATE_LIMIT_EXCEEDED: Final[str] = "API_RATE_LIMIT_EXCEEDED"
        ENDPOINT_NOT_FOUND: Final[str] = "API_ENDPOINT_NOT_FOUND"
        METHOD_NOT_ALLOWED: Final[str] = "API_METHOD_NOT_ALLOWED"

    # ========================================================================
    # File Operation Error IDs
    # ========================================================================

    class File:
        """File operation related error IDs"""

        NOT_FOUND: Final[str] = "FILE_NOT_FOUND"
        PERMISSION_DENIED: Final[str] = "FILE_PERMISSION_DENIED"
        DISK_FULL: Final[str] = "FILE_DISK_FULL"
        INVALID_PATH: Final[str] = "FILE_INVALID_PATH"
        UPLOAD_FAILED: Final[str] = "FILE_UPLOAD_FAILED"
        DELETE_FAILED: Final[str] = "FILE_DELETE_FAILED"

    # ========================================================================
    # Migration Error IDs
    # ========================================================================

    class Migration:
        """Database migration related error IDs"""

        ALEMBIC_ERROR: Final[str] = "MIGRATION_ALEMBIC_ERROR"
        MODEL_IMPORT_FAILED: Final[str] = "MIGRATION_MODEL_IMPORT_FAILED"
        UPGRADE_FAILED: Final[str] = "MIGRATION_UPGRADE_FAILED"
        DOWNGRADE_FAILED: Final[str] = "MIGRATION_DOWNGRADE_FAILED"
        VERSION_CONFLICT: Final[str] = "MIGRATION_VERSION_CONFLICT"

    # ========================================================================
    # Cache Error IDs
    # ========================================================================

    class Cache:
        """Cache-related error IDs"""

        HEALTH_CHECK_FAILED: Final[str] = "CACHE_HEALTH_CHECK_FAILED"
        CONNECTION_FAILED: Final[str] = "CACHE_CONNECTION_FAILED"
        MISS: Final[str] = "CACHE_MISS"
        INVALIDATION_FAILED: Final[str] = "CACHE_INVALIDATION_FAILED"

    # ========================================================================
    # Filesystem Error IDs
    # ========================================================================

    class Filesystem:
        """Filesystem-related error IDs"""

        HEALTH_CHECK_FAILED: Final[str] = "FILESYSTEM_HEALTH_CHECK_FAILED"
        DISK_FULL: Final[str] = "FILESYSTEM_DISK_FULL"
        PERMISSION_DENIED: Final[str] = "FILESYSTEM_PERMISSION_DENIED"
        IO_ERROR: Final[str] = "FILESYSTEM_IO_ERROR"

    # ========================================================================
    # System Error IDs
    # ========================================================================

    class System:
        """System-related error IDs"""

        MEMORY_CHECK_FAILED: Final[str] = "SYSTEM_MEMORY_CHECK_FAILED"
        CPU_OVERLOAD: Final[str] = "SYSTEM_CPU_OVERLOAD"
        RESOURCE_EXHAUSTED: Final[str] = "SYSTEM_RESOURCE_EXHAUSTED"

    # ========================================================================
    # Security Error IDs
    # ========================================================================

    class Security:
        """Security-related error IDs"""

        ENCRYPTION_KEY_MISSING: Final[str] = "SECURITY_ENCRYPTION_KEY_MISSING"
        ENCRYPTION_FAILED: Final[str] = "SECURITY_ENCRYPTION_FAILED"
        DECRYPTION_FAILED: Final[str] = "SECURITY_DECRYPTION_FAILED"
        SQL_INJECTION_ATTEMPT: Final[str] = "SECURITY_SQL_INJECTION_ATTEMPT"
        XSS_ATTEMPT: Final[str] = "SECURITY_XSS_ATTEMPT"
        TOKEN_BLACKLIST_FAILED: Final[str] = "SECURITY_TOKEN_BLACKLIST_FAILED"

    # ========================================================================
    # Task Error IDs
    # ========================================================================

    class Task:
        """Background task related error IDs"""

        EXPORT_FAILED: Final[str] = "TASK_EXPORT_FAILED"
        IMPORT_FAILED: Final[str] = "TASK_IMPORT_FAILED"
        STATUS_UPDATE_FAILED: Final[str] = "TASK_STATUS_UPDATE_FAILED"

    # ========================================================================
    # Excel Error IDs
    # ========================================================================

    class Excel:
        """Excel operation related error IDs"""

        EXPORT_FAILED: Final[str] = "EXCEL_EXPORT_FAILED"
        IMPORT_FAILED: Final[str] = "EXCEL_IMPORT_FAILED"
        TEMPLATE_DOWNLOAD_ERROR: Final[str] = "EXCEL_TEMPLATE_DOWNLOAD_ERROR"


# Legacy aliases for backward compatibility
# Map old error IDs to new structured format
_LEGACY_ERROR_IDS = {
    "DB_CONNECTION_FAILED": ErrorIDs.Database.CONNECTION_FAILED,
    "AUDIT_LOG_FAILED": ErrorIDs.AuditLog.CREATION_FAILED,
    "DB_HEALTH_CHECK_FAILED": ErrorIDs.Database.HEALTH_CHECK_FAILED,
    "DB_HEALTH_CHECK_UNKNOWN_ERROR": ErrorIDs.Database.HEALTH_CHECK_UNKNOWN_ERROR,
    "MISSING_DATABASE_URL": ErrorIDs.Database.MISSING_DATABASE_URL,
    "USING_DEFAULT_SQLITE": ErrorIDs.Database.USING_DEFAULT_SQLITE,
    "SQLITE_IN_PRODUCTION": ErrorIDs.Database.SQLITE_IN_PRODUCTION,
}


def get_error_id(legacy_id: str) -> str:
    """
    Get error ID from legacy error ID string.

    This function provides backward compatibility with old error ID strings.
    New code should use ErrorIDs class directly.

    Args:
        legacy_id: Legacy error ID string

    Returns:
        New error ID string

    Example:
        >>> get_error_id("DB_CONNECTION_FAILED")
        "DB_CONNECTION_FAILED"
    """
    return _LEGACY_ERROR_IDS.get(legacy_id, legacy_id)
