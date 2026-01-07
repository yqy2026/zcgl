"""
配置管理模块
集中管理所有配置项

整合说明:
- 保留原有 Pydantic Settings 配置
- 添加 get_config() 和 initialize_config() 兼容函数
- 合并自 config_manager.py, unified_config.py, enhanced_config.py 的功能
@lastModified 2025-12-24
"""

import logging
import os
from typing import Any

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """应用配置"""

    model_config = ConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # 应用基本信息
    APP_NAME: str = "土地物业资产管理系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, json_schema_extra={"env": "DEBUG"})
    API_V1_STR: str = "/api/v1"

    # 服务器配置
    HOST: str = Field(default="0.0.0.0", json_schema_extra={"env": "HOST"})  # nosec - B104: Dev default, override in prod
    PORT: int = Field(default=8002, json_schema_extra={"env": "PORT"})
    RELOAD: bool = Field(default=True, json_schema_extra={"env": "RELOAD"})

    # 数据库配置
    DATABASE_URL: str = Field(
        default="sqlite:///./land_property.db",
        json_schema_extra={"env": "DATABASE_URL"},
    )
    DATABASE_ECHO: bool = Field(default=False, json_schema_extra={"env": "DATABASE_ECHO"})

    # Redis缓存配置
    REDIS_HOST: str | None = Field(default=None, json_schema_extra={"env": "REDIS_HOST"})
    REDIS_PORT: int = Field(default=6379, json_schema_extra={"env": "REDIS_PORT"})
    REDIS_DB: int = Field(default=0, json_schema_extra={"env": "REDIS_DB"})
    REDIS_PASSWORD: str | None = Field(default=None, json_schema_extra={"env": "REDIS_PASSWORD"})
    REDIS_ENABLED: bool = Field(default=False, json_schema_extra={"env": "REDIS_ENABLED"})

    # CORS配置
    CORS_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
        ],
        json_schema_extra={"env": "CORS_ORIGINS"},
    )

    # JWT配置 - 生产环境必须设置环境变量
    SECRET_KEY: str = Field(
        default="EMERGENCY-ONLY-REPLACE-WITH-ENV-SECRET-KEY-NOW",
        description="JWT密钥 - 生产环境必须通过环境变量设置强密钥",
        json_schema_extra={"env": "SECRET_KEY"},
    )
    ALGORITHM: str = Field(default="HS256", json_schema_extra={"env": "ALGORITHM"})
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=120, json_schema_extra={"env": "ACCESS_TOKEN_EXPIRE_MINUTES"}
    )  # 设置为120分钟以确保用户体验
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, json_schema_extra={"env": "REFRESH_TOKEN_EXPIRE_DAYS"}
    )

    # JWT安全强化配置
    JWT_ISSUER: str = Field(default="zcgl-system", json_schema_extra={"env": "JWT_ISSUER"})
    JWT_AUDIENCE: str = Field(default="zcgl-users", json_schema_extra={"env": "JWT_AUDIENCE"})
    ENABLE_JTI_CLAIM: bool = Field(default=True, json_schema_extra={"env": "ENABLE_JTI_CLAIM"})
    TOKEN_BLACKLIST_ENABLED: bool = Field(
        default=True, json_schema_extra={"env": "TOKEN_BLACKLIST_ENABLED"}
    )

    # 文件上传配置
    MAX_FILE_SIZE: int = Field(
        default=50 * 1024 * 1024, json_schema_extra={"env": "MAX_FILE_SIZE"}
    )  # 50MB
    UPLOAD_DIR: str = Field(default="./uploads", json_schema_extra={"env": "UPLOAD_DIR"})

    # 分页配置
    DEFAULT_PAGE_SIZE: int = Field(default=20, json_schema_extra={"env": "DEFAULT_PAGE_SIZE"})
    MAX_PAGE_SIZE: int = Field(default=100, json_schema_extra={"env": "MAX_PAGE_SIZE"})

    # 缓存配置
    CACHE_TTL: int = Field(default=3600, json_schema_extra={"env": "CACHE_TTL"})  # 1小时
    CACHE_PREFIX: str = Field(default="zcgl", json_schema_extra={"env": "CACHE_PREFIX"})

    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", json_schema_extra={"env": "LOG_LEVEL"})
    LOG_FILE: str | None = Field(default=None, json_schema_extra={"env": "LOG_FILE"})

    def validate_security_config(self) -> list[str]:
        """
        验证安全配置
        返回安全警告列表
        """
        warnings = []

        # 检查JWT密钥安全性
        if self.SECRET_KEY in [
            "EMERGENCY-ONLY-REPLACE-WITH-ENV-SECRET-KEY-NOW",
            "dev-secret-key-DO-NOT-USE-IN-PRODUCTION-REPLACE-WITH-ENV-VAR",
            "dev-secret-key-change-in-production",
        ]:
            warnings.append(
                "严重安全风险: 使用了默认或不安全的JWT密钥！"
                "请立即设置环境变量SECRET_KEY为强随机密钥。"
            )

        if len(self.SECRET_KEY) < 32:
            warnings.append("警告: JWT密钥长度不足32字符，建议使用更长的密钥。")

        # 检查是否在调试模式运行
        if self.DEBUG:
            warnings.append("警告: 当前在调试模式运行，生产环境必须设置DEBUG=false。")

        # 检查数据库是否为SQLite（生产环境推荐PostgreSQL）
        if self.DATABASE_URL.startswith("sqlite:///./land_property.db"):
            warnings.append("提醒: 使用默认SQLite数据库路径，生产环境建议使用PostgreSQL。")

        return warnings

    def log_security_status(self) -> None:
        """记录安全配置状态"""
        import logging

        logger = logging.getLogger(__name__)
        warnings = self.validate_security_config()

        if warnings:
            logger.warning("=" * 60)
            logger.warning("安全配置检查发现以下问题:")
            for warning in warnings:
                logger.warning(f"  {warning}")
            logger.warning("=" * 60)
        else:
            logger.info("安全配置检查通过")

    # 性能监控
    ENABLE_METRICS: bool = Field(default=True, json_schema_extra={"env": "ENABLE_METRICS"})
    SLOW_QUERY_THRESHOLD: float = Field(
        default=1.0, json_schema_extra={"env": "SLOW_QUERY_THRESHOLD"}
    )

    # 认证配置
    MIN_PASSWORD_LENGTH: int = Field(default=8, json_schema_extra={"env": "MIN_PASSWORD_LENGTH"})
    SESSION_EXPIRE_DAYS: int = Field(default=30, json_schema_extra={"env": "SESSION_EXPIRE_DAYS"})
    MAX_FAILED_ATTEMPTS: int = Field(default=5, json_schema_extra={"env": "MAX_FAILED_ATTEMPTS"})
    LOCKOUT_DURATION: int = Field(
        default=900, json_schema_extra={"env": "LOCKOUT_DURATION"}
    )  # 15分钟
    MAX_CONCURRENT_SESSIONS: int = Field(
        default=5, json_schema_extra={"env": "MAX_CONCURRENT_SESSIONS"}
    )
    AUDIT_LOG_RETENTION_DAYS: int = Field(
        default=90, json_schema_extra={"env": "AUDIT_LOG_RETENTION_DAYS"}
    )

    # LLM/ChatGLM3 配置（可选）
    CHATGLM3_API_URL: str | None = Field(
        default=None, json_schema_extra={"env": "CHATGLM3_API_URL"}
    )
    CHATGLM3_MAX_TOKENS: int = Field(default=1500, json_schema_extra={"env": "CHATGLM3_MAX_TOKENS"})
    CHATGLM3_TEMPERATURE: float = Field(
        default=0.2, json_schema_extra={"env": "CHATGLM3_TEMPERATURE"}
    )
    CHATGLM3_TIMEOUT: int = Field(default=30, json_schema_extra={"env": "CHATGLM3_TIMEOUT"})
    CHATGLM3_MODEL_ID: str = Field(
        default="THUDM/chatglm3-6b", json_schema_extra={"env": "CHATGLM3_MODEL_ID"}
    )
    CHATGLM3_DEVICE: str = Field(default="cpu", json_schema_extra={"env": "CHATGLM3_DEVICE"})
    LLM_TRIGGER_THRESHOLD: float = Field(
        default=0.65, json_schema_extra={"env": "LLM_TRIGGER_THRESHOLD"}
    )

    # 创建全局配置实例


settings = Settings()

# 根据环境变量覆盖配置
if os.getenv("ENVIRONMENT") == "production":  # pragma: no cover
    settings.DEBUG = False  # pragma: no cover
    settings.DATABASE_ECHO = False  # pragma: no cover
    settings.CORS_ORIGINS = ["https://your-production-domain.com"]  # pragma: no cover
elif os.getenv("ENVIRONMENT") == "development":  # pragma: no cover
    settings.DEBUG = True  # pragma: no cover
    settings.RELOAD = True  # pragma: no cover


# 验证必要配置
def validate_config():
    """验证配置是否正确"""
    import os

    # 检查是否为测试模式
    is_testing = os.getenv("TESTING_MODE", "false").lower() == "true"

    required_fields = [
        "DATABASE_URL",
        "SECRET_KEY",
    ]

    missing_fields = []
    for field in required_fields:
        if not getattr(settings, field):
            missing_fields.append(field)

    if missing_fields:
        raise ValueError(f"缺少必要配置: {', '.join(missing_fields)}")

    # 非测试模式下强制检查SECRET_KEY安全性
    if not is_testing:  # pragma: no cover
        insecure_keys = [  # pragma: no cover
            "EMERGENCY-ONLY-REPLACE-WITH-ENV-SECRET-KEY-NOW",  # pragma: no cover
            "dev-secret-key-DO-NOT-USE-IN-PRODUCTION-REPLACE-WITH-ENV-VAR",  # pragma: no cover
            "dev-secret-key-change-in-production",  # pragma: no cover
            "your-secret-key-change-in-production",  # pragma: no cover
            "secret-key",  # pragma: no cover
            "",  # pragma: no cover
        ]  # pragma: no cover

        if settings.SECRET_KEY in insecure_keys:  # pragma: no cover
            raise ValueError(  # pragma: no cover
                "致命安全错误: SECRET_KEY 使用了不安全的默认值！\n"  # pragma: no cover
                "请设置环境变量: export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"  # pragma: no cover
            )  # pragma: no cover

        if len(settings.SECRET_KEY) < 32:  # pragma: no cover
            raise ValueError(  # pragma: no cover
                f"致命安全错误: SECRET_KEY 长度不足 ({len(settings.SECRET_KEY)}字符)，最少需要32字符！"  # pragma: no cover
            )  # pragma: no cover

        logger.info("SECRET_KEY 安全检查通过")  # pragma: no cover

    # 检查Redis配置
    if settings.REDIS_ENABLED and not settings.REDIS_HOST:
        raise ValueError("启用Redis时需要配置REDIS_HOST")

    logger.info(f"配置验证完成 - 应用: {settings.APP_NAME}, 版本: {settings.APP_VERSION}")


# 导出配置实例
__all__ = ["settings", "validate_config", "get_config", "initialize_config"]


# ============================================================
# 兼容性函数 (合并自 config_manager.py)
# ============================================================


def get_config(key: str, default: Any = None) -> Any:
    """
    获取配置值的便捷函数

    支持点号分隔的配置键，如:
    - "cors_origins" -> settings.CORS_ORIGINS
    - "database.pool_size" -> settings.DATABASE_POOL_SIZE (需要添加)

    Args:
        key: 配置键名
        default: 默认值

    Returns:
        配置值或默认值
    """
    # 首先尝试直接从 settings 获取
    if hasattr(settings, key.upper()):
        return getattr(settings, key.upper())

    # 尝试带下划线的键名
    upper_key = key.upper().replace(".", "_")
    if hasattr(settings, upper_key):
        return getattr(settings, upper_key)

    # 特殊配置映射
    config_mappings = {
        "cors_origins": settings.CORS_ORIGINS,
        "database.url": settings.DATABASE_URL,
        "database.echo": settings.DATABASE_ECHO,
        "database.pool_size": 20,
        "database.max_overflow": 30,
        "database.pool_timeout": 30,
        "database.pool_recycle": 3600,
        "database.enable_query_logging": False,
        "rate_limit": {},
        "security": {},
        "slow_query_threshold_ms": int(settings.SLOW_QUERY_THRESHOLD * 1000),
        "performance_monitoring_enabled": settings.ENABLE_METRICS,
        "cache_enabled": settings.REDIS_ENABLED,
        "cache_ttl_seconds": settings.CACHE_TTL,
        "cache_max_size": 1000,
        "permission_cache_ttl": 300,
        "debug": settings.DEBUG,
        "log_level": settings.LOG_LEVEL,
        "log_file": settings.LOG_FILE,
        "security_log_file": "logs/security.log",
        "security_logging_enabled": True,
        "request_log_file": "logs/requests.log",
        "request_logging_enabled": True,
    }

    if key in config_mappings:
        return config_mappings[key]

    # 返回默认值
    logger.debug(f"Config key '{key}' not found, using default: {default}")
    return default


def initialize_config() -> None:
    """
    初始化配置的便捷函数

    验证配置并记录安全状态
    """
    logger.info("Initializing configuration...")

    # 验证必要配置
    try:
        validate_config()
    except ValueError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise

    # 记录安全状态
    settings.log_security_status()

    logger.info("Configuration initialized successfully")


def get_all_config() -> dict[str, Any]:
    """
    获取所有配置的便捷函数

    Returns:
        包含所有配置的字典
    """
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "api_v1_str": settings.API_V1_STR,
        "host": settings.HOST,
        "port": settings.PORT,
        "database_url": settings.DATABASE_URL,
        "redis_enabled": settings.REDIS_ENABLED,
        "cors_origins": settings.CORS_ORIGINS,
        "log_level": settings.LOG_LEVEL,
    }
