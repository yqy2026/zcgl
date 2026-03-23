"""
Database and Redis settings.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseModel):
    """数据库与Redis配置"""

    # 数据库配置
    DATABASE_URL: str = Field(
        default="",
        json_schema_extra={"env": "DATABASE_URL"},
    )
    DATABASE_ECHO: bool = Field(
        default=False, json_schema_extra={"env": "DATABASE_ECHO"}
    )
    DATABASE_POOL_SIZE: int = Field(
        default=20, json_schema_extra={"env": "DATABASE_POOL_SIZE"}
    )
    DATABASE_MAX_OVERFLOW: int = Field(
        default=30, json_schema_extra={"env": "DATABASE_MAX_OVERFLOW"}
    )
    DATABASE_POOL_TIMEOUT: int = Field(
        default=30, json_schema_extra={"env": "DATABASE_POOL_TIMEOUT"}
    )
    DATABASE_POOL_RECYCLE: int = Field(
        default=3600, json_schema_extra={"env": "DATABASE_POOL_RECYCLE"}
    )
    DATABASE_POOL_PRE_PING: bool = Field(
        default=True, json_schema_extra={"env": "DATABASE_POOL_PRE_PING"}
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

    @field_validator("REDIS_PORT")
    @classmethod
    def validate_port_range(cls, v: int) -> int:
        """验证端口号在有效范围内 (1-65535)"""
        if not 1 <= v <= 65535:
            raise PydanticCustomError(
                "invalid_port",
                "端口号必须在 1-65535 范围内，当前值: {port}",
                {"port": v},
            )
        return v

    @field_validator("REDIS_PORT")
    @classmethod
    def validate_redis_port(cls, v: int) -> int:
        """验证 Redis 端口 - 推荐使用标准端口或高位端口"""
        # 允许标准 Redis 端口或高位端口 (1024+)
        if v != 6379 and v < 1024:
            logger.warning(f"Redis 端口 {v} 小于 1024，可能需要管理员权限")
        return v

    @model_validator(mode="after")
    def validate_redis_configuration(self) -> DatabaseSettings:
        """验证 Redis 配置一致性"""
        if self.REDIS_ENABLED:
            if not self.REDIS_HOST:
                raise PydanticCustomError(
                    "missing_redis_host",
                    "启用 Redis 时必须设置 REDIS_HOST",
                    {},
                )
            if not self.REDIS_PASSWORD:
                environment = str(getattr(self, "ENVIRONMENT", "development")).lower()
                if environment == "production":
                    raise PydanticCustomError(
                        "missing_redis_password",
                        "生产环境启用 Redis 时必须设置 REDIS_PASSWORD",
                        {"environment": environment},
                    )
                logger.warning("Redis 已启用但未设置密码，建议配置 REDIS_PASSWORD")
        return self
