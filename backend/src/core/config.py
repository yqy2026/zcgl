"""
配置管理模块
集中管理所有配置项
"""

import os

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


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
    HOST: str = Field(default="0.0.0.0", json_schema_extra={"env": "HOST"})
    PORT: int = Field(default=8002, json_schema_extra={"env": "PORT"})
    RELOAD: bool = Field(default=True, json_schema_extra={"env": "RELOAD"})

    # 数据库配置
    DATABASE_URL: str = Field(
        default="sqlite:///./land_property.db",
        json_schema_extra={"env": "DATABASE_URL"},
    )
    DATABASE_ECHO: bool = Field(
        default=False, json_schema_extra={"env": "DATABASE_ECHO"}
    )

    # Redis缓存配置
    REDIS_HOST: str | None = Field(
        default=None, json_schema_extra={"env": "REDIS_HOST"}
    )
    REDIS_PORT: int = Field(default=6379, json_schema_extra={"env": "REDIS_PORT"})
    REDIS_DB: int = Field(default=0, json_schema_extra={"env": "REDIS_DB"})
    REDIS_PASSWORD: str | None = Field(
        default=None, json_schema_extra={"env": "REDIS_PASSWORD"}
    )
    REDIS_ENABLED: bool = Field(
        default=False, json_schema_extra={"env": "REDIS_ENABLED"}
    )

    # CORS配置
    CORS_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
        ],
        json_schema_extra={"env": "CORS_ORIGINS"},
    )

    # JWT配置
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        json_schema_extra={"env": "SECRET_KEY"},
    )
    ALGORITHM: str = Field(default="HS256", json_schema_extra={"env": "ALGORITHM"})
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, json_schema_extra={"env": "ACCESS_TOKEN_EXPIRE_MINUTES"}
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, json_schema_extra={"env": "REFRESH_TOKEN_EXPIRE_DAYS"}
    )

    # 文件上传配置
    MAX_FILE_SIZE: int = Field(
        default=50 * 1024 * 1024, json_schema_extra={"env": "MAX_FILE_SIZE"}
    )  # 50MB
    UPLOAD_DIR: str = Field(
        default="./uploads", json_schema_extra={"env": "UPLOAD_DIR"}
    )

    # 分页配置
    DEFAULT_PAGE_SIZE: int = Field(
        default=20, json_schema_extra={"env": "DEFAULT_PAGE_SIZE"}
    )
    MAX_PAGE_SIZE: int = Field(default=100, json_schema_extra={"env": "MAX_PAGE_SIZE"})

    # 缓存配置
    CACHE_TTL: int = Field(
        default=3600, json_schema_extra={"env": "CACHE_TTL"}
    )  # 1小时
    CACHE_PREFIX: str = Field(default="zcgl", json_schema_extra={"env": "CACHE_PREFIX"})

    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", json_schema_extra={"env": "LOG_LEVEL"})
    LOG_FILE: str | None = Field(default=None, json_schema_extra={"env": "LOG_FILE"})

    # 性能监控
    ENABLE_METRICS: bool = Field(
        default=True, json_schema_extra={"env": "ENABLE_METRICS"}
    )
    SLOW_QUERY_THRESHOLD: float = Field(
        default=1.0, json_schema_extra={"env": "SLOW_QUERY_THRESHOLD"}
    )

    # 认证配置
    MIN_PASSWORD_LENGTH: int = Field(
        default=8, json_schema_extra={"env": "MIN_PASSWORD_LENGTH"}
    )
    SESSION_EXPIRE_DAYS: int = Field(
        default=30, json_schema_extra={"env": "SESSION_EXPIRE_DAYS"}
    )
    MAX_FAILED_ATTEMPTS: int = Field(
        default=5, json_schema_extra={"env": "MAX_FAILED_ATTEMPTS"}
    )
    LOCKOUT_DURATION: int = Field(
        default=900, json_schema_extra={"env": "LOCKOUT_DURATION"}
    )  # 15分钟
    MAX_CONCURRENT_SESSIONS: int = Field(
        default=5, json_schema_extra={"env": "MAX_CONCURRENT_SESSIONS"}
    )
    AUDIT_LOG_RETENTION_DAYS: int = Field(
        default=90, json_schema_extra={"env": "AUDIT_LOG_RETENTION_DAYS"}
    )

    # 创建全局配置实例


settings = Settings()

# 根据环境变量覆盖配置
if os.getenv("ENVIRONMENT") == "production":
    settings.DEBUG = False
    settings.DATABASE_ECHO = False
    settings.CORS_ORIGINS = ["https://your-production-domain.com"]
elif os.getenv("ENVIRONMENT") == "development":
    settings.DEBUG = True
    settings.RELOAD = True


# 验证必要配置
def validate_config():
    """验证配置是否正确"""
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

    # 检查Redis配置
    if settings.REDIS_ENABLED:
        if not settings.REDIS_HOST:
            raise ValueError("启用Redis时需要配置REDIS_HOST")

    print(f"配置验证完成 - 应用: {settings.APP_NAME}, 版本: {settings.APP_VERSION}")


# 导出配置实例
__all__ = ["settings", "validate_config"]
