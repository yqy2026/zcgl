"""Database URL resolution and validation helpers."""

from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

from src.constants.message_constants import ErrorIDs

from .core.exception_handler import ConfigurationError

logger = logging.getLogger(__name__)


def _build_safe_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    return (
        f"{parsed.scheme}://{parsed.username}@{parsed.hostname}:{parsed.port or 5432}"
        f"{parsed.path}"
    )


def validate_postgresql_database_url(database_url: str) -> str:
    """Validate PostgreSQL URL format and return the original URL."""
    try:
        parsed = urlparse(database_url)

        if not parsed.hostname:
            raise ConfigurationError("缺少主机名 (hostname)", config_key="DATABASE_URL")
        if not parsed.username:
            raise ConfigurationError("缺少用户名 (username)", config_key="DATABASE_URL")
        if not parsed.password:
            logger.warning("DATABASE_URL缺少密码 (password)")
        if not parsed.path or len(parsed.path) <= 1:
            raise ConfigurationError(
                "缺少数据库名称 (database name)",
                config_key="DATABASE_URL",
            )
        if parsed.port and not (1 <= parsed.port <= 65535):
            raise ConfigurationError(
                f"无效端口号: {parsed.port}",
                config_key="DATABASE_URL",
            )

        logger.info(f"PostgreSQL URL验证通过: {_build_safe_url(database_url)}")
    except (ValueError, ConfigurationError) as error:
        logger.error(
            f"DATABASE_URL验证失败: {error}",
            extra={"error_id": "DATABASE_URL_INVALID"},
        )
        raise ConfigurationError(
            f"DATABASE_URL格式错误: {error}\n"
            "正确格式: postgresql+psycopg://user:password@host:port/database\n"
            "示例: postgresql+psycopg://postgres:password@localhost:5432/zcgl_db",
            config_key="DATABASE_URL",
        ) from error

    return database_url


def get_database_url() -> str:
    """Read and validate DATABASE_URL from environment."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        environment = os.getenv("ENVIRONMENT", "development")
        logger.critical(
            f"环境 '{environment}' 未设置DATABASE_URL",
            extra={"error_id": ErrorIDs.Database.MISSING_DATABASE_URL},
        )
        raise ConfigurationError(
            "必须设置DATABASE_URL环境变量。\n"
            "请在.env文件中配置:\n"
            "DATABASE_URL=postgresql+psycopg://user:password@host:port/database\n"
            "帮助文档: docs/POSTGRESQL_MIGRATION.md",
            config_key="DATABASE_URL",
        )

    if database_url.startswith("postgresql+psycopg://"):
        return validate_postgresql_database_url(database_url)

    logger.error(
        f"不支持的数据库类型: {database_url[:20]}...",
        extra={"error_id": "UNSUPPORTED_DATABASE_TYPE"},
    )
    raise ConfigurationError(
        "不支持的数据库类型。支持: postgresql+psycopg://\n"
        f"当前URL: {database_url[:50]}",
        config_key="DATABASE_URL",
    )


def get_async_database_url() -> str:
    """Convert sync psycopg URL to asyncpg URL."""
    return get_database_url().replace(
        "postgresql+psycopg://", "postgresql+asyncpg://", 1
    )
