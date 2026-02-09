"""
配置管理模块
集中管理所有配置项，基于 Pydantic Settings
@lastModified 2026-01-29
"""

import logging
import os
from json import JSONDecodeError, loads
from typing import Any

from pydantic import model_validator
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


def _parse_cors_origins(raw_value: str) -> list[str]:
    """解析 CORS_ORIGINS，兼容 JSON 数组与逗号分隔格式。"""
    value = raw_value.strip()
    if value == "":
        return []

    loaded: Any
    try:
        loaded = loads(value)
    except JSONDecodeError:
        loaded = value

    if isinstance(loaded, list):
        origins = [str(origin).strip() for origin in loaded if str(origin).strip()]
    elif isinstance(loaded, str):
        origins = [origin.strip() for origin in loaded.split(",") if origin.strip()]
    else:
        raise ConfigurationError(
            "CORS_ORIGINS 格式无效，应为 JSON 数组或逗号分隔字符串",
            config_key="CORS_ORIGINS",
        )

    if any(origin == "*" for origin in origins):
        raise ConfigurationError(
            "CORS_ORIGINS 禁止使用 '*'，请配置明确域名列表",
            config_key="CORS_ORIGINS",
        )

    return origins


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

    @model_validator(mode="after")
    def apply_environment_overrides(self) -> "Settings":
        """按环境调整配置，避免运行时二次覆盖"""
        environment = self.ENVIRONMENT.lower()
        if environment == "production":  # pragma: no cover
            self.DEBUG = False  # pragma: no cover
            self.DATABASE_ECHO = False  # pragma: no cover
            # 从环境变量读取生产域名（兼容 JSON 数组与逗号分隔），如未设置则使用当前值并记录警告
            prod_origins = os.getenv("CORS_ORIGINS", "")  # pragma: no cover
            if prod_origins:  # pragma: no cover
                self.CORS_ORIGINS = _parse_cors_origins(prod_origins)  # pragma: no cover
            else:  # pragma: no cover
                logger.warning(  # pragma: no cover
                    "CORS_ORIGINS not set for production. Set CORS_ORIGINS env var."
                )
        elif environment == "development":  # pragma: no cover
            self.DEBUG = True  # pragma: no cover
            self.RELOAD = True  # pragma: no cover

        return self


settings = Settings()  # type: ignore[call-arg]


# 验证必要配置
def validate_config() -> None:
    """验证配置是否正确"""
    required_fields = ["DATABASE_URL"]

    missing_fields = []
    for field in required_fields:
        if not getattr(settings, field):
            missing_fields.append(field)

    if missing_fields:
        raise ConfigurationError(
            f"缺少必要配置: {', '.join(missing_fields)}",
            config_key=",".join(missing_fields),
        )

    logger.info(
        f"配置验证完成 - 应用: {settings.APP_NAME}, 版本: {settings.APP_VERSION}"
    )


# 导出配置实例
__all__ = ["settings", "validate_config", "Settings"]
