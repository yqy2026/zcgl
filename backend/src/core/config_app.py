"""
Application-level settings.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

logger = logging.getLogger(__name__)


class AppSettings(BaseModel):
    """应用基础配置"""

    # 应用基本信息
    APP_NAME: str = "土地物业资产管理系统"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(
        default="development", json_schema_extra={"env": "ENVIRONMENT"}
    )
    DEBUG: bool = Field(default=False, json_schema_extra={"env": "DEBUG"})
    API_V1_STR: str = "/api/v1"
    ALLOW_MOCK_REGISTRY: bool = Field(
        default=False, json_schema_extra={"env": "ALLOW_MOCK_REGISTRY"}
    )

    # 服务器配置
    HOST: str = Field(default="0.0.0.0", json_schema_extra={"env": "HOST"})  # nosec - B104: Dev default, override in prod
    PORT: int = Field(default=8002, json_schema_extra={"env": "PORT"})
    RELOAD: bool = Field(default=True, json_schema_extra={"env": "RELOAD"})

    # CORS配置
    CORS_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "http://localhost:5175",
        ],
        json_schema_extra={"env": "CORS_ORIGINS"},
    )

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: list[str]) -> list[str]:
        """验证 CORS 域名配置，禁止使用通配符。"""
        normalized_origins = [
            origin.strip()
            for origin in v
            if isinstance(origin, str) and origin.strip() != ""
        ]
        if any(origin == "*" for origin in normalized_origins):
            raise PydanticCustomError(
                "invalid_cors_origins",
                "CORS_ORIGINS 禁止使用 '*'，请配置明确域名列表",
                {},
            )
        return normalized_origins

    @field_validator("PORT")
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
