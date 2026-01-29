"""
Error messages and string constants.

Consolidated from:
- strings/empty.py
- errors/error_ids.py
- errors/messages.py

This module provides all message-related constants including
error IDs, error messages, and common string values.
"""

from typing import Final


class ErrorIDs:
    """Centralized error ID registry for structured logging"""

    class Database:
        """Database-related error IDs"""

        CONNECTION_FAILED: Final[str] = "DB_CONNECTION_FAILED"
        CONNECTION_TIMEOUT: Final[str] = "DB_CONNECTION_TIMEOUT"
        CONNECTION_REFUSED: Final[str] = "DB_CONNECTION_REFUSED"
        AUTHENTICATION_FAILED: Final[str] = "DB_AUTHENTICATION_FAILED"
        DATABASE_NOT_FOUND: Final[str] = "DB_DATABASE_NOT_FOUND"
        URL_MALFORMED: Final[str] = "DB_URL_MALFORMED"
        URL_MISSING_HOSTNAME: Final[str] = "DB_URL_MISSING_HOSTNAME"
        URL_MISSING_USERNAME: Final[str] = "DB_URL_MISSING_USERNAME"
        URL_MISSING_PASSWORD: Final[str] = "DB_URL_MISSING_PASSWORD"
        URL_MISSING_DATABASE: Final[str] = "DB_URL_MISSING_DATABASE"
        URL_INVALID_PORT: Final[str] = "DB_URL_INVALID_PORT"
        HEALTH_CHECK_FAILED: Final[str] = "DB_HEALTH_CHECK_FAILED"
        HEALTH_CHECK_UNKNOWN_ERROR: Final[str] = "DB_HEALTH_CHECK_UNKNOWN_ERROR"
        SESSION_ERROR: Final[str] = "DB_SESSION_ERROR"
        ROLLBACK_FAILED: Final[str] = "DB_ROLLBACK_FAILED"
        MISSING_DATABASE_URL: Final[str] = "MISSING_DATABASE_URL"
        MISSING_DATABASE_URL_DEV: Final[str] = "MISSING_DATABASE_URL_DEV"
        MISSING_DATABASE_URL_STAGING: Final[str] = "MISSING_DATABASE_URL_STAGING"
        POOL_EXHAUSTED: Final[str] = "DB_POOL_EXHAUSTED"
        POOL_TIMEOUT: Final[str] = "DB_POOL_TIMEOUT"

    class AuditLog:
        """Audit log related error IDs"""

        CREATION_FAILED: Final[str] = "AUDIT_LOG_FAILED"
        FALLBACK_FILE_WRITE_FAILED: Final[str] = "AUDIT_LOG_FALLBACK_FAILED"
        DB_WRITE_FAILED: Final[str] = "AUDIT_LOG_DB_WRITE_FAILED"
        VALIDATION_FAILED: Final[str] = "AUDIT_LOG_VALIDATION_FAILED"
        SERIALIZATION_FAILED: Final[str] = "AUDIT_LOG_SERIALIZATION_FAILED"
        FALLBACK_TO_FILE: Final[str] = "AUDIT_LOG_FALLBACK_TO_FILE"
        FALLBACK_TO_SYSLOG: Final[str] = "AUDIT_LOG_FALLBACK_TO_SYSLOG"
        FALLBACK_TO_WIN_EVENTLOG: Final[str] = "AUDIT_LOG_FALLBACK_TO_WIN_EVENTLOG"
        ALL_FALLBACKS_FAILED: Final[str] = "AUDIT_LOG_ALL_FALLBACKS_FAILED"
        STATUS_UNKNOWN: Final[str] = "AUDIT_LOG_STATUS_UNKNOWN"

    class SystemSettings:
        """System settings related error IDs"""

        VALIDATION_ERROR: Final[str] = "SYSTEM_SETTINGS_VALIDATION_ERROR"
        UPDATE_FAILED: Final[str] = "SYSTEM_SETTINGS_UPDATE_FAILED"
        UNEXPECTED_ERROR: Final[str] = "SYSTEM_SETTINGS_UNEXPECTED_ERROR"
        BACKUP_FAILED: Final[str] = "SYSTEM_SETTINGS_BACKUP_FAILED"
        RESTORE_FAILED: Final[str] = "SYSTEM_SETTINGS_RESTORE_FAILED"

    class Auth:
        """Authentication related error IDs"""

        LOGIN_FAILED: Final[str] = "AUTH_LOGIN_FAILED"
        TOKEN_INVALID: Final[str] = "AUTH_TOKEN_INVALID"
        TOKEN_EXPIRED: Final[str] = "AUTH_TOKEN_EXPIRED"
        PERMISSION_DENIED: Final[str] = "AUTH_PERMISSION_DENIED"
        USER_NOT_FOUND: Final[str] = "AUTH_USER_NOT_FOUND"
        INVALID_CREDENTIALS: Final[str] = "AUTH_INVALID_CREDENTIALS"

    class API:
        """API-related error IDs"""

        REQUEST_VALIDATION_FAILED: Final[str] = "API_REQUEST_VALIDATION_FAILED"
        RESPONSE_SERIALIZATION_FAILED: Final[str] = "API_RESPONSE_SERIALIZATION_FAILED"
        RATE_LIMIT_EXCEEDED: Final[str] = "API_RATE_LIMIT_EXCEEDED"
        ENDPOINT_NOT_FOUND: Final[str] = "API_ENDPOINT_NOT_FOUND"
        METHOD_NOT_ALLOWED: Final[str] = "API_METHOD_NOT_ALLOWED"

    class File:
        """File operation related error IDs"""

        NOT_FOUND: Final[str] = "FILE_NOT_FOUND"
        PERMISSION_DENIED: Final[str] = "FILE_PERMISSION_DENIED"
        DISK_FULL: Final[str] = "FILE_DISK_FULL"
        INVALID_PATH: Final[str] = "FILE_INVALID_PATH"
        UPLOAD_FAILED: Final[str] = "FILE_UPLOAD_FAILED"
        DELETE_FAILED: Final[str] = "FILE_DELETE_FAILED"

    class Migration:
        """Database migration related error IDs"""

        ALEMBIC_ERROR: Final[str] = "MIGRATION_ALEMBIC_ERROR"
        MODEL_IMPORT_FAILED: Final[str] = "MIGRATION_MODEL_IMPORT_FAILED"
        UPGRADE_FAILED: Final[str] = "MIGRATION_UPGRADE_FAILED"
        DOWNGRADE_FAILED: Final[str] = "MIGRATION_DOWNGRADE_FAILED"
        VERSION_CONFLICT: Final[str] = "MIGRATION_VERSION_CONFLICT"

    class Cache:
        """Cache-related error IDs"""

        HEALTH_CHECK_FAILED: Final[str] = "CACHE_HEALTH_CHECK_FAILED"
        CONNECTION_FAILED: Final[str] = "CACHE_CONNECTION_FAILED"
        MISS: Final[str] = "CACHE_MISS"
        INVALIDATION_FAILED: Final[str] = "CACHE_INVALIDATION_FAILED"

    class Filesystem:
        """Filesystem-related error IDs"""

        HEALTH_CHECK_FAILED: Final[str] = "FILESYSTEM_HEALTH_CHECK_FAILED"
        DISK_FULL: Final[str] = "FILESYSTEM_DISK_FULL"
        PERMISSION_DENIED: Final[str] = "FILESYSTEM_PERMISSION_DENIED"
        IO_ERROR: Final[str] = "FILESYSTEM_IO_ERROR"

    class System:
        """System-related error IDs"""

        MEMORY_CHECK_FAILED: Final[str] = "SYSTEM_MEMORY_CHECK_FAILED"
        CPU_OVERLOAD: Final[str] = "SYSTEM_CPU_OVERLOAD"
        RESOURCE_EXHAUSTED: Final[str] = "SYSTEM_RESOURCE_EXHAUSTED"

    class Security:
        """Security-related error IDs"""

        ENCRYPTION_KEY_MISSING: Final[str] = "SECURITY_ENCRYPTION_KEY_MISSING"
        ENCRYPTION_FAILED: Final[str] = "SECURITY_ENCRYPTION_FAILED"
        DECRYPTION_FAILED: Final[str] = "SECURITY_DECRYPTION_FAILED"
        SQL_INJECTION_ATTEMPT: Final[str] = "SECURITY_SQL_INJECTION_ATTEMPT"
        XSS_ATTEMPT: Final[str] = "SECURITY_XSS_ATTEMPT"
        TOKEN_BLACKLIST_FAILED: Final[str] = "SECURITY_TOKEN_BLACKLIST_FAILED"

    class Task:
        """Background task related error IDs"""

        EXPORT_FAILED: Final[str] = "TASK_EXPORT_FAILED"
        IMPORT_FAILED: Final[str] = "TASK_IMPORT_FAILED"
        STATUS_UPDATE_FAILED: Final[str] = "TASK_STATUS_UPDATE_FAILED"

    class Excel:
        """Excel operation related error IDs"""

        EXPORT_FAILED: Final[str] = "EXCEL_EXPORT_FAILED"
        IMPORT_FAILED: Final[str] = "EXCEL_IMPORT_FAILED"
        TEMPLATE_DOWNLOAD_ERROR: Final[str] = "EXCEL_TEMPLATE_DOWNLOAD_ERROR"


class ErrorMessages:
    """Common error message constants"""

    RESOURCE_NOT_FOUND: Final[str] = "资源不存在"
    USER_NOT_FOUND: Final[str] = "用户不存在"
    ASSET_NOT_FOUND: Final[str] = "资产不存在"
    CONTRACT_NOT_FOUND: Final[str] = "合同不存在"
    ORGANIZATION_NOT_FOUND: Final[str] = "组织不存在"
    OWNERSHIP_NOT_FOUND: Final[str] = "权属方不存在"
    CONTACT_NOT_FOUND: Final[str] = "联系人不存在"
    PRIMARY_CONTACT_NOT_FOUND: Final[str] = "主要联系人不存在"
    ENUM_TYPE_NOT_FOUND: Final[str] = "枚举类型不存在"
    ENUM_VALUE_NOT_FOUND: Final[str] = "枚举值不存在"
    SESSION_NOT_FOUND: Final[str] = "会话不存在"
    ROLE_NOT_FOUND: Final[str] = "角色不存在"
    LEDGER_NOT_FOUND: Final[str] = "台账记录不存在"
    COLLECTION_RECORD_NOT_FOUND: Final[str] = "催缴记录不存在"
    PROJECT_NOT_FOUND: Final[str] = "项目不存在"
    NOTIFICATION_NOT_FOUND: Final[str] = "通知不存在"
    TASK_NOT_FOUND: Final[str] = "任务不存在"
    CONFIG_NOT_FOUND: Final[str] = "配置不存在"
    FILE_NOT_FOUND: Final[str] = "文件不存在"
    OPERATION_LOG_NOT_FOUND: Final[str] = "日志不存在"
    DATABASE_MANAGER_NOT_AVAILABLE: Final[str] = "数据库管理器不可用"
    OPERATION_FAILED: Final[str] = "操作失败"
    DATABASE_CONNECTION_FAILED: Final[str] = "数据库连接失败"
    DATABASE_NOT_INITIALIZED: Final[str] = "数据库引擎未初始化"
    DELETION_FAILED: Final[str] = "删除失败"
    SAVE_FAILED: Final[str] = "保存失败"
    PASSWORD_CHANGE_FAILED: Final[str] = "密码修改失败"
    SESSION_REVOKATION_FAILED: Final[str] = "撤销会话失败"
    PERFORMANCE_METRIC_SAVE_FAILED: Final[str] = "性能指标保存失败"
    SYSTEM_HEALTH_CHECK_FAILED: Final[str] = "获取系统健康状态失败"
    DASHBOARD_DATA_FETCH_FAILED: Final[str] = "获取仪表板数据失败"
    VALIDATION_FAILED: Final[str] = "数据验证失败"
    DATA_INTEGRITY_ERROR: Final[str] = "数据完整性错误"
    FILENAME_EMPTY: Final[str] = "文件名不能为空"
    FILENAME_TOO_LONG: Final[str] = "文件名过长"
    INVALID_DATA_PROVIDED: Final[str] = "提供的数据无效"
    MISSING_REQUIRED_FIELD: Final[str] = "缺少必填字段"
    INVALID_FILE_TYPE: Final[str] = "文件类型无效"
    INVALID_FILE_FORMAT: Final[str] = "文件格式错误"
    ONLY_PDF_SUPPORTED: Final[str] = "仅支持PDF文件"
    BACKUP_MUST_BE_JSON: Final[str] = "备份文件必须是JSON格式"
    NO_ASSET_IDS_PROVIDED: Final[str] = "未提供要删除的资产ID列表"
    PRODUCTION_DEPENDENCIES_MISSING: Final[str] = "生产环境关键依赖缺失"
    PERMISSION_DENIED: Final[str] = "权限不足"
    PERMISSION_CHECK_FAILED: Final[str] = "权限验证失败"
    ACCESS_DENIED: Final[str] = "访问被拒绝"
    UNAUTHORIZED_OPERATION: Final[str] = "未授权的操作"
    AUTHENTICATION_FAILED: Final[str] = "认证失败"
    INVALID_CREDENTIALS: Final[str] = "凭据无效"
    TOKEN_MISSING: Final[str] = "Token缺失"
    TOKEN_EXPIRED: Final[str] = "Token已过期"
    TOKEN_INVALID: Final[str] = "Token无效"
    TOKEN_VERIFICATION_FAILED: Final[str] = "Token验证失败"
    TOKEN_MISSING_EXPIRATION: Final[str] = "Token missing expiration time"
    TOKEN_MISSING_ISSUED_AT: Final[str] = "Token missing issued at time"
    RATE_LIMIT_EXCEEDED: Final[str] = "请求过于频繁，请稍后重试"
    IP_BLOCKED: Final[str] = "IP地址已被封禁"
    TOO_MANY_REQUESTS: Final[str] = "请求次数过多"
    DUPLICATE_RESOURCE: Final[str] = "资源已存在"
    RESOURCE_ALREADY_EXISTS: Final[str] = "资源已存在"
    PROPERTY_NAME_EXISTS: Final[str] = "物业名称已存在"
    INVALID_STATUS_TRANSITION: Final[str] = "状态转换无效"
    OPERATION_NOT_ALLOWED: Final[str] = "不允许此操作"
    FILE_TOO_LARGE: Final[str] = "文件过大"
    FILE_UPLOAD_VALIDATION_FAILED: Final[str] = "文件上传验证失败"
    FILE_SIZE_EXCEEDED: Final[str] = "请求过大"
    SECURITY_ERROR: Final[str] = "安全错误"
    IMPORT_FAILED: Final[str] = "导入失败"
    EXPORT_FAILED: Final[str] = "导出失败"
    EXPORT_FILE_NOT_FOUND: Final[str] = "导出文件不存在"
    DEFAULT_CONFIG_NOT_FOUND: Final[str] = "未找到默认配置"
    INTERNAL_SERVER_ERROR: Final[str] = "服务器内部错误"
    SERVICE_UNAVAILABLE: Final[str] = "服务暂时不可用"
    UNKNOWN_ERROR: Final[str] = "未知错误"


EMPTY_STRING: Final[str] = ""

RESOURCE_NOT_FOUND = ErrorMessages.RESOURCE_NOT_FOUND
USER_NOT_FOUND = ErrorMessages.USER_NOT_FOUND
ASSET_NOT_FOUND = ErrorMessages.ASSET_NOT_FOUND
OPERATION_FAILED = ErrorMessages.OPERATION_FAILED
VALIDATION_FAILED = ErrorMessages.VALIDATION_FAILED
PERMISSION_DENIED = ErrorMessages.PERMISSION_DENIED
AUTHENTICATION_FAILED = ErrorMessages.AUTHENTICATION_FAILED
DATABASE_CONNECTION_FAILED = ErrorMessages.DATABASE_CONNECTION_FAILED
TOKEN_EXPIRED = ErrorMessages.TOKEN_EXPIRED
RATE_LIMIT_EXCEEDED = ErrorMessages.RATE_LIMIT_EXCEEDED
EMPTY = EMPTY_STRING

_LEGACY_ERROR_IDS = {
    "DB_CONNECTION_FAILED": ErrorIDs.Database.CONNECTION_FAILED,
    "AUDIT_LOG_FAILED": ErrorIDs.AuditLog.CREATION_FAILED,
    "DB_HEALTH_CHECK_FAILED": ErrorIDs.Database.HEALTH_CHECK_FAILED,
    "DB_HEALTH_CHECK_UNKNOWN_ERROR": ErrorIDs.Database.HEALTH_CHECK_UNKNOWN_ERROR,
    "MISSING_DATABASE_URL": ErrorIDs.Database.MISSING_DATABASE_URL,
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


__all__ = [
    "ErrorIDs",
    "ErrorMessages",
    "EMPTY_STRING",
]
