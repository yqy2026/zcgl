#!/usr/bin/env python3
from typing import Any

"""
错误恢复配置
定义错误恢复策略和配置参数
"""

from ..services.error_recovery_service import (
    ErrorCategory,
    ErrorSeverity,
    RecoveryStrategy,
)

# 错误恢复策略配置
RECOVERY_STRATEGIES = {
    ErrorCategory.NETWORK: RecoveryStrategy(
        name="网络错误恢复",
        category=ErrorCategory.NETWORK,
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        backoff_multiplier=2.0,
        retry_conditions=["timeout", "connection_error", "dns_error", "http_error"],
        fallback_enabled=True,
        auto_recovery=True,
    ),
    ErrorCategory.DATABASE: RecoveryStrategy(
        name="数据库错误恢复",
        category=ErrorCategory.DATABASE,
        max_attempts=2,
        base_delay=0.5,
        max_delay=10.0,
        backoff_multiplier=1.5,
        retry_conditions=["connection_lost", "deadlock", "timeout"],
        fallback_enabled=True,
        auto_recovery=True,
    ),
    ErrorCategory.VALIDATION: RecoveryStrategy(
        name="验证错误恢复",
        category=ErrorCategory.VALIDATION,
        max_attempts=1,
        base_delay=0.1,
        max_delay=1.0,
        backoff_multiplier=1.0,
        auto_recovery=True,
        fallback_enabled=False,
    ),
    ErrorCategory.AUTHENTICATION: RecoveryStrategy(
        name="认证错误恢复",
        category=ErrorCategory.AUTHENTICATION,
        max_attempts=2,
        base_delay=0.5,
        max_delay=5.0,
        backoff_multiplier=1.5,
        retry_conditions=["token_expired", "invalid_token"],
        fallback_enabled=False,
        auto_recovery=True,
        requires_manual_intervention=False,
    ),
    ErrorCategory.AUTHORIZATION: RecoveryStrategy(
        name="权限错误恢复",
        category=ErrorCategory.AUTHORIZATION,
        max_attempts=1,
        base_delay=0.1,
        max_delay=1.0,
        backoff_multiplier=1.0,
        fallback_enabled=False,
        auto_recovery=False,
        requires_manual_intervention=True,
    ),
    ErrorCategory.FILE_SYSTEM: RecoveryStrategy(
        name="文件系统错误恢复",
        category=ErrorCategory.FILE_SYSTEM,
        max_attempts=2,
        base_delay=0.5,
        max_delay=10.0,
        backoff_multiplier=2.0,
        retry_conditions=["file_not_found", "permission_denied", "disk_full"],
        fallback_enabled=True,
        auto_recovery=True,
    ),
    ErrorCategory.MEMORY: RecoveryStrategy(
        name="内存错误恢复",
        category=ErrorCategory.MEMORY,
        max_attempts=1,
        base_delay=1.0,
        max_delay=5.0,
        backoff_multiplier=1.0,
        fallback_enabled=True,
        auto_recovery=False,
        requires_manual_intervention=True,
    ),
    ErrorCategory.EXTERNAL_API: RecoveryStrategy(
        name="外部API错误恢复",
        category=ErrorCategory.EXTERNAL_API,
        max_attempts=3,
        base_delay=2.0,
        max_delay=60.0,
        backoff_multiplier=2.5,
        retry_conditions=["rate_limit", "service_unavailable", "timeout"],
        fallback_enabled=True,
        auto_recovery=True,
    ),
    ErrorCategory.PROCESSING: RecoveryStrategy(
        name="处理错误恢复",
        category=ErrorCategory.PROCESSING,
        max_attempts=2,
        base_delay=1.0,
        max_delay=15.0,
        backoff_multiplier=2.0,
        retry_conditions=["processing_error", "parsing_error"],
        fallback_enabled=True,
        auto_recovery=True,
    ),
    ErrorCategory.BUSINESS_LOGIC: RecoveryStrategy(
        name="业务逻辑错误恢复",
        category=ErrorCategory.BUSINESS_LOGIC,
        max_attempts=1,
        base_delay=0.1,
        max_delay=1.0,
        backoff_multiplier=1.0,
        fallback_enabled=False,
        auto_recovery=False,
        requires_manual_intervention=True,
    ),
    ErrorCategory.SYSTEM: RecoveryStrategy(
        name="系统错误恢复",
        category=ErrorCategory.SYSTEM,
        max_attempts=2,
        base_delay=2.0,
        max_delay=30.0,
        backoff_multiplier=1.5,
        retry_conditions=["system_error", "resource_error"],
        fallback_enabled=True,
        auto_recovery=False,
        requires_manual_intervention=True,
    ),
}

# 熔断器配置
CIRCUIT_BREAKER_CONFIG = {
    "failure_threshold": 5,  # 失败次数阈值
    "recovery_timeout": 60,  # 恢复超时时间（秒）
    "half_open_max_calls": 3,  # 半开状态最大调用次数
    "monitoring_window": 300,  # 监控窗口时间（秒）
}

# 错误分类规则
ERROR_CLASSIFICATION_RULES = {
    ErrorCategory.NETWORK: [
        "timeout",
        "connection",
        "network",
        "dns",
        "host",
        "socket",
        "connectionrefused",
        "connectionreset",
        "connectionaborted",
        "timedout",
        "networkunreachable",
        "hostunreachable",
    ],
    ErrorCategory.DATABASE: [
        "database",
        "sql",
        "connection",
        "deadlock",
        "lock",
        "transaction",
        "constraint",
        "duplicate",
        "foreign",
        "integrity",
        "operationalerror",
        "interfaceerror",
        "databaseerror",
    ],
    ErrorCategory.VALIDATION: [
        "validation",
        "invalid",
        "required",
        "format",
        "missing",
        "malformed",
        "badrequest",
        "schema",
        "value",
        "typeerror",
        "valueerror",
        "keyerror",
    ],
    ErrorCategory.AUTHENTICATION: [
        "auth",
        "token",
        "unauthorized",
        "credential",
        "login",
        "authentication",
        "permission",
        "access",
        "denied",
        "forbidden",
        "jwt",
        "session",
    ],
    ErrorCategory.AUTHORIZATION: [
        "permission",
        "access",
        "denied",
        "forbidden",
        "unauthorized",
        "role",
        "privilege",
        "authorization",
        "accessdenied",
    ],
    ErrorCategory.FILE_SYSTEM: [
        "file",
        "path",
        "directory",
        "disk",
        "filesystem",
        "notfound",
        "permission",
        "exists",
        "access",
        "filenotfound",
        "permissionerror",
        "isadirectoryerror",
    ],
    ErrorCategory.MEMORY: [
        "memory",
        "outof",
        "allocation",
        "heap",
        "stack",
        "memoryerror",
        "allocationerror",
        "resourceexhausted",
    ],
    ErrorCategory.EXTERNAL_API: [
        "api",
        "service",
        "external",
        "thirdparty",
        "rate",
        "limit",
        "unavailable",
        "down",
        "timeout",
        "ratelimit",
        "serviceunavailable",
        "apierror",
    ],
    ErrorCategory.PROCESSING: [
        "processing",
        "parse",
        "transform",
        "convert",
        "encode",
        "decode",
        "format",
        "syntax",
        "structure",
        "parsingerror",
        "formaterror",
        "encodingerror",
    ],
    ErrorCategory.BUSINESS_LOGIC: [
        "business",
        "logic",
        "rule",
        "constraint",
        "policy",
        "workflow",
        "process",
        "state",
        "condition",
        "businessexception",
        "ruleviolation",
    ],
    ErrorCategory.SYSTEM: [
        "system",
        "internal",
        "server",
        "critical",
        "fatal",
        "exception",
        "panic",
        "crash",
        "shutdown",
        "systemerror",
        "internalexception",
        "criticalerror",
    ],
}

# 错误严重程度配置
SEVERITY_CONFIG = {
    ErrorSeverity.CRITICAL: {
        "categories": [ErrorCategory.SYSTEM, ErrorCategory.MEMORY],
        "description": "系统级错误，需要立即处理",
        "alert_level": "critical",
    },
    ErrorSeverity.HIGH: {
        "categories": [ErrorCategory.DATABASE, ErrorCategory.SYSTEM],
        "description": "高级错误，影响核心功能",
        "alert_level": "warning",
    },
    ErrorSeverity.MEDIUM: {
        "categories": [
            ErrorCategory.NETWORK,
            ErrorCategory.AUTHENTICATION,
            ErrorCategory.EXTERNAL_API,
        ],
        "description": "中级错误，影响部分功能",
        "alert_level": "info",
    },
    ErrorSeverity.LOW: {
        "categories": [ErrorCategory.VALIDATION, ErrorCategory.FILE_SYSTEM],
        "description": "低级错误，用户体验影响",
        "alert_level": "debug",
    },
}

# 自动纠正规则
AUTO_CORRECTION_RULES = {
    "email": {
        "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z0-9.-]+$",
        "corrections": [
            {"condition": "missing_domain", "correction": "example.com"},
            {"condition": "missing_tld", "correction": "com"},
            {"condition": "invalid_chars", "correction": "clean_chars"},
        ],
    },
    "phone": {
        "pattern": r"^\+?[\d\s\-()]{10,}$",
        "corrections": [
            {"condition": "missing_country", "correction": "+86"},
            {"condition": "invalid_format", "correction": "clean_format"},
        ],
    },
    "date": {
        "pattern": r"^\d{4}-\d{2}-\d{2}$",
        "corrections": [
            {"condition": "wrong_separator", "correction": "use_dash"},
            {"condition": "invalid_format", "correction": "standard_format"},
        ],
    },
}

# Fallback响应配置
FALLBACK_RESPONSES = {
    ErrorCategory.NETWORK: {
        "success": False,
        "message": "网络服务暂时不可用，请稍后重试",
        "code": "NETWORK_FALLBACK",
    },
    ErrorCategory.DATABASE: {
        "success": False,
        "message": "数据库服务暂时不可用，请稍后重试",
        "code": "DATABASE_FALLBACK",
    },
    ErrorCategory.EXTERNAL_API: {
        "success": False,
        "message": "外部服务暂时不可用，请稍后重试",
        "code": "EXTERNAL_API_FALLBACK",
    },
    ErrorCategory.FILE_SYSTEM: {
        "success": False,
        "message": "文件服务暂时不可用，请稍后重试",
        "code": "FILE_SYSTEM_FALLBACK",
    },
}

# 监控和告警配置
MONITORING_CONFIG = {
    "enabled": True,
    "metrics_retention_hours": 24,
    "alert_thresholds": {
        "failure_rate": 0.1,  # 10%失败率
        "recovery_time": 10.0,  # 10秒平均恢复时间
        "consecutive_failures": 5,  # 连续5次失败
    },
    "alert_channels": ["log", "email", "webhook"],
    "health_check_interval": 60,  # 60秒健康检查间隔
}

# 性能配置
PERFORMANCE_CONFIG = {
    "max_concurrent_recoveries": 10,
    "recovery_timeout": 300,  # 5分钟恢复超时
    "max_recovery_history": 10000,
    "cleanup_interval": 3600,  # 1小时清理间隔
    "cache_size": 1000,  # 缓存大小
}

# 调试配置
DEBUG_CONFIG = {
    "enabled": False,
    "log_all_errors": True,
    "log_recovery_attempts": True,
    "log_stack_traces": True,
    "include_error_context": True,
    "save_recovery_history": True,
}

# 全局错误恢复配置
ERROR_RECOVERY_CONFIG = {
    "strategies": RECOVERY_STRATEGIES,
    "circuit_breaker": CIRCUIT_BREAKER_CONFIG,
    "classification_rules": ERROR_CLASSIFICATION_RULES,
    "severity_config": SEVERITY_CONFIG,
    "auto_correction_rules": AUTO_CORRECTION_RULES,
    "fallback_responses": FALLBACK_RESPONSES,
    "monitoring": MONITORING_CONFIG,
    "performance": PERFORMANCE_CONFIG,
    "debug": DEBUG_CONFIG,
}


def get_recovery_strategy(error_category: ErrorCategory) -> RecoveryStrategy:
    """获取错误恢复策略"""
    return RECOVERY_STRATEGIES.get(error_category)


def get_error_classification_rules() -> dict[str, Any][ErrorCategory, list[str]]:
    """获取错误分类规则"""
    return ERROR_CLASSIFICATION_RULES


def get_fallback_response(error_category: ErrorCategory) -> dict[str, Any]:
    """获取fallback响应"""
    return FALLBACK_RESPONSES.get(
        error_category,
        {
            "success": False,
            "message": "服务暂时不可用，请稍后重试",
            "code": "DEFAULT_FALLBACK",
        },
    )


def is_recovery_enabled() -> bool:
    """检查错误恢复是否启用"""
    return MONITORING_CONFIG.get("enabled", True)
