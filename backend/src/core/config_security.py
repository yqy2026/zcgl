"""
Security and authentication settings.
"""

from __future__ import annotations

import logging
import os

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator
from pydantic_core import PydanticCustomError

logger = logging.getLogger(__name__)


class SecuritySettings(BaseModel):
    """安全与认证配置"""

    # JWT配置 - 必须通过环境变量设置
    SECRET_KEY: str = Field(
        ...,
        min_length=32,
        description="JWT密钥 - 必须32+字符的强随机字符串",
        json_schema_extra={"env": "SECRET_KEY"},
    )
    ALGORITHM: str = Field(default="HS256", json_schema_extra={"env": "ALGORITHM"})
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, json_schema_extra={"env": "ACCESS_TOKEN_EXPIRE_MINUTES"}
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, json_schema_extra={"env": "REFRESH_TOKEN_EXPIRE_DAYS"}
    )

    # JWT安全强化配置
    JWT_ISSUER: str = Field(
        default="zcgl-system", json_schema_extra={"env": "JWT_ISSUER"}
    )
    JWT_AUDIENCE: str = Field(
        default="zcgl-users", json_schema_extra={"env": "JWT_AUDIENCE"}
    )
    ENABLE_JTI_CLAIM: bool = Field(
        default=True, json_schema_extra={"env": "ENABLE_JTI_CLAIM"}
    )
    TOKEN_BLACKLIST_ENABLED: bool = Field(
        default=True, json_schema_extra={"env": "TOKEN_BLACKLIST_ENABLED"}
    )

    # 数据加密配置
    DATA_ENCRYPTION_KEY: str | None = Field(
        default=None,
        description="Encryption key for PII fields (format: base64:key:version, supports multiple keys: key1:1,key2:2)",
        json_schema_extra={"env": "DATA_ENCRYPTION_KEY"},
    )
    REQUIRE_ENCRYPTION: bool = Field(
        default=False,
        description="强制要求 DATA_ENCRYPTION_KEY（生产环境默认启用）",
        json_schema_extra={"env": "REQUIRE_ENCRYPTION"},
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

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        """验证 SECRET_KEY 强度，生产环境必须使用强密钥"""
        # 定义弱密钥模式（不应在生产环境使用）
        # 包括硬编码默认值、示例值、常见弱密钥等
        weak_patterns = [
            "EMERGENCY-ONLY",
            "REPLACE-WITH",
            "REPLACE_WITH",
            "dev-secret-key",
            "your-secret-key",
            "secret-key",
            "test-key",
            "example",
            "default",
            "changeme",
            "change-this",
            "minimum-32-characters",
        ]

        # 检查是否为弱密钥模式
        is_weak_pattern = any(pattern.lower() in v.lower() for pattern in weak_patterns)

        # 检查长度
        is_too_short = len(v) < 32

        # 生产环境强制检查
        # 优先使用Settings中的ENVIRONMENT，其次回退到环境变量
        environment = (
            (info.data or {}).get("ENVIRONMENT")
            or os.getenv("ENVIRONMENT")
            or "production"
        )
        environment = environment.lower()

        if environment == "production":
            if is_weak_pattern:
                raise PydanticCustomError(
                    "weak_secret_key",
                    "生产环境禁止使用弱密钥模式。检测到包含常见弱密钥标识符。"
                    "请使用 python -c 'import secrets; print(secrets.token_urlsafe(32))' 生成强密钥。",
                    {},
                )
            if is_too_short:
                raise PydanticCustomError(
                    "secret_key_too_short",
                    "生产环境 SECRET_KEY 长度必须至少 32 字符，当前: {length} 字符",
                    {"length": len(v)},
                )
        elif is_weak_pattern or is_too_short:
            # 非生产环境发出警告
            if is_weak_pattern:
                logger.warning(
                    "检测到弱 SECRET_KEY 模式（仅用于开发环境）。生产环境必须设置强密钥。"
                )
            if is_too_short:
                logger.warning(
                    f"SECRET_KEY 长度不足 ({len(v)} < 32)。生产环境建议使用至少 32 字符的密钥。"
                )

        return v

    @model_validator(mode="after")
    def validate_security_configuration(self) -> "SecuritySettings":
        """
        统一安全配置验证
        处理所有安全检查并根据环境记录警告或抛出错误
        """
        warnings = []
        environment = (getattr(self, "ENVIRONMENT", None) or "production").lower()
        is_testing = (
            environment == "testing"
            or os.getenv("TESTING_MODE", "false").lower() == "true"
        )
        is_production = environment == "production"

        # 1. JWT 密钥安全性检查
        insecure_keys = [
            "EMERGENCY-ONLY-REPLACE-WITH-ENV-SECRET-KEY-NOW",
            "dev-secret-key-DO-NOT-USE-IN-PRODUCTION-REPLACE-WITH-ENV-VAR",
            "dev-secret-key-change-in-production",
            "your-secret-key-change-in-production",
            "secret-key",
        ]

        if self.SECRET_KEY in insecure_keys:
            msg = "严重安全风险: 使用了默认或不安全的 JWT 密钥！请立即设置环境变量 SECRET_KEY 为强随机密钥。"
            if is_production and not is_testing:
                raise PydanticCustomError(
                    "insecure_secret_key",
                    msg,
                    {},
                )
            warnings.append(msg)

        if len(self.SECRET_KEY) < 32:
            msg = f"警告: JWT 密钥长度不足 ({len(self.SECRET_KEY)}字符)，建议使用至少 32 字符的密钥。"
            if is_production and not is_testing:
                raise PydanticCustomError(
                    "secret_key_too_short",
                    "生产环境要求 SECRET_KEY 至少 32 字符",
                    {},
                )
            warnings.append(msg)

        # 2. DATA_ENCRYPTION_KEY 检查
        if not self.DATA_ENCRYPTION_KEY:
            msg = "未设置 DATA_ENCRYPTION_KEY。PII 字段加密将不可用。"
            if is_production and not is_testing:
                # 生产环境记录错误日志
                logger.error(f"配置缺失: {msg}")
            warnings.append(f"提醒: {msg}")

        # 3. 调试模式检查
        if bool(getattr(self, "DEBUG", False)):
            msg = "警告: 当前在调试模式运行，生产环境必须设置 DEBUG=false。"
            warnings.append(msg)

        # 4. 记录警告
        if warnings and not is_testing:
            logger.warning("=" * 60)
            logger.warning("安全配置检查发现以下问题:")
            for warning in warnings:
                logger.warning(f"  {warning}")
            logger.warning("=" * 60)
        elif not is_testing:
            logger.info("安全配置检查通过")

        return self
