"""
配置管理模块
集中管理所有配置项，基于 Pydantic Settings
@lastModified 2026-01-29
"""

import logging
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

from .config_app import AppSettings
from .config_cache import CacheSettings
from .config_database import DatabaseSettings
from .config_files import FileUploadSettings
from .config_llm import LlmSettings
from .config_logging import LoggingSettings
from .config_metrics import MetricsSettings
from .config_pagination import PaginationSettings
from .config_security import SecuritySettings
from .exception_handler import ConfigurationError

logger = logging.getLogger(__name__)


class Settings(
    BaseSettings,
    AppSettings,
    DatabaseSettings,
    SecuritySettings,
    FileUploadSettings,
    PaginationSettings,
    CacheSettings,
    LoggingSettings,
    MetricsSettings,
    LlmSettings,
):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


settings = Settings()  # type: ignore[call-arg]

# 根据环境变量覆盖配置
if settings.ENVIRONMENT == "production":  # pragma: no cover
    settings.DEBUG = False  # pragma: no cover
    settings.DATABASE_ECHO = False  # pragma: no cover
    # 从环境变量读取生产域名，如未设置则使用默认值并记录警告
    prod_origins = os.getenv("CORS_ORIGINS", "")  # pragma: no cover
    if prod_origins:  # pragma: no cover
        settings.CORS_ORIGINS = [
            o.strip() for o in prod_origins.split(",")
        ]  # pragma: no cover
    else:  # pragma: no cover
        import logging  # pragma: no cover

        logging.getLogger(__name__).warning(  # pragma: no cover
            "CORS_ORIGINS not set for production. Set CORS_ORIGINS env var."
        )  # pragma: no cover
elif settings.ENVIRONMENT == "development":  # pragma: no cover
    settings.DEBUG = True  # pragma: no cover
    settings.RELOAD = True  # pragma: no cover


# 验证必要配置
def validate_config() -> None:
    """验证配置是否正确"""
    # 检查是否为测试模式
    is_testing = settings.ENVIRONMENT == "testing" or (
        os.getenv("TESTING_MODE", "false").lower() == "true"
    )

    required_fields = [
        "DATABASE_URL",
        "SECRET_KEY",
    ]

    missing_fields = []
    for field in required_fields:
        if not getattr(settings, field):
            missing_fields.append(field)

    if missing_fields:
        raise ConfigurationError(
            f"缺少必要配置: {', '.join(missing_fields)}",
            config_key=",".join(missing_fields),
        )

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
            raise ConfigurationError(  # pragma: no cover
                "致命安全错误: SECRET_KEY 使用了不安全的默认值！\n"  # pragma: no cover
                "请设置环境变量: export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"  # pragma: no cover
            )  # pragma: no cover

        if len(settings.SECRET_KEY) < 32:  # pragma: no cover
            raise ConfigurationError(  # pragma: no cover
                f"致命安全错误: SECRET_KEY 长度不足 ({len(settings.SECRET_KEY)}字符)，最少需要32字符！"  # pragma: no cover
            )  # pragma: no cover

        logger.info("SECRET_KEY 安全检查通过")  # pragma: no cover

    # 检查Redis配置
    if settings.REDIS_ENABLED and not settings.REDIS_HOST:
        raise ConfigurationError(
            "启用Redis时需要配置REDIS_HOST",
            config_key="REDIS_HOST",
        )

    logger.info(
        f"配置验证完成 - 应用: {settings.APP_NAME}, 版本: {settings.APP_VERSION}"
    )


# 导出配置实例
__all__ = ["settings", "validate_config", "Settings"]
