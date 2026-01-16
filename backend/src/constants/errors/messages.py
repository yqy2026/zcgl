"""
Common Error Message Constants

This module contains standardized error messages used throughout the application.
These constants help eliminate magic strings and provide consistent error messaging.

Usage:
    from src.constants.errors.messages import ErrorMessages

    raise HTTPException(
        status_code=404,
        detail=ErrorMessages.RESOURCE_NOT_FOUND
    )
"""

from typing import Final

# Legacy aliases for backward compatibility
# TODO: Remove in v2.0


class ErrorMessages:
    """Common error message constants"""

    # Resource Not Found Errors (404)
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

    # Operation Failure Errors (500)
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

    # Validation Errors (400)
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

    # Permission Errors (403)
    PERMISSION_DENIED: Final[str] = "权限不足"
    PERMISSION_CHECK_FAILED: Final[str] = "权限验证失败"
    ACCESS_DENIED: Final[str] = "访问被拒绝"
    UNAUTHORIZED_OPERATION: Final[str] = "未授权的操作"

    # Authentication Errors (401)
    AUTHENTICATION_FAILED: Final[str] = "认证失败"
    INVALID_CREDENTIALS: Final[str] = "凭据无效"
    TOKEN_MISSING: Final[str] = "Token缺失"
    TOKEN_EXPIRED: Final[str] = "Token已过期"
    TOKEN_INVALID: Final[str] = "Token无效"
    TOKEN_VERIFICATION_FAILED: Final[str] = "Token验证失败"
    TOKEN_MISSING_EXPIRATION: Final[str] = "Token missing expiration time"
    TOKEN_MISSING_ISSUED_AT: Final[str] = "Token missing issued at time"

    # Rate Limiting Errors (429)
    RATE_LIMIT_EXCEEDED: Final[str] = "请求过于频繁，请稍后重试"
    IP_BLOCKED: Final[str] = "IP地址已被封禁"
    TOO_MANY_REQUESTS: Final[str] = "请求次数过多"

    # Business Logic Errors
    DUPLICATE_RESOURCE: Final[str] = "资源已存在"
    RESOURCE_ALREADY_EXISTS: Final[str] = "资源已存在"
    PROPERTY_NAME_EXISTS: Final[str] = "物业名称已存在"
    INVALID_STATUS_TRANSITION: Final[str] = "状态转换无效"
    OPERATION_NOT_ALLOWED: Final[str] = "不允许此操作"

    # File Upload Errors
    FILE_TOO_LARGE: Final[str] = "文件过大"
    FILE_UPLOAD_VALIDATION_FAILED: Final[str] = "文件上传验证失败"
    FILE_SIZE_EXCEEDED: Final[str] = "请求过大"
    SECURITY_ERROR: Final[str] = "安全错误"

    # Import/Export Errors
    IMPORT_FAILED: Final[str] = "导入失败"
    EXPORT_FAILED: Final[str] = "导出失败"
    EXPORT_FILE_NOT_FOUND: Final[str] = "导出文件不存在"
    DEFAULT_CONFIG_NOT_FOUND: Final[str] = "未找到默认配置"

    # Generic Errors
    INTERNAL_SERVER_ERROR: Final[str] = "服务器内部错误"
    SERVICE_UNAVAILABLE: Final[str] = "服务暂时不可用"
    UNKNOWN_ERROR: Final[str] = "未知错误"


# Legacy aliases for backward compatibility
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
