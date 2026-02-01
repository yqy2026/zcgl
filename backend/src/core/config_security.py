"""
Security and authentication settings.
"""

from __future__ import annotations

import logging
import os

from typing import Literal, cast

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator
from pydantic_core import PydanticCustomError

logger = logging.getLogger(__name__)

DEFAULT_SECURITY_ANALYZER_PATTERNS = [
    r"<script",
    r"javascript:",
    r"vbscript:",
    r"onload=",
    r"onerror=",
    r"document\.cookie",
    r"eval\(",
    r"alert\(",
    r"window\.",
    r"select\s+.*\s+from",
    r"union\s+select",
    r"drop\s+table",
    r"delete\s+from",
    r"insert\s+into",
    r"update\s+.*\s+set",
]


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

    # CSRF 配置
    CSRF_ENABLED: bool = Field(
        default=True, json_schema_extra={"env": "CSRF_ENABLED"}
    )
    CSRF_COOKIE_NAME: str = Field(
        default="csrf_token", json_schema_extra={"env": "CSRF_COOKIE_NAME"}
    )
    CSRF_HEADER_NAME: str = Field(
        default="X-CSRF-Token", json_schema_extra={"env": "CSRF_HEADER_NAME"}
    )
    CSRF_SAMESITE: Literal["lax", "strict", "none"] = Field(
        default="strict", json_schema_extra={"env": "CSRF_SAMESITE"}
    )

    # IP黑名单配置
    IP_BLACKLIST: list[str] = Field(
        default=[],
        description="IP黑名单列表（建议使用JSON数组）",
        json_schema_extra={"env": "IP_BLACKLIST"},
    )
    IP_AUTO_BLOCK_ENABLED: bool = Field(
        default=True, json_schema_extra={"env": "IP_AUTO_BLOCK_ENABLED"}
    )
    IP_AUTO_BLOCK_THRESHOLD: int = Field(
        default=10, json_schema_extra={"env": "IP_AUTO_BLOCK_THRESHOLD"}
    )
    IP_AUTO_BLOCK_DURATION: int = Field(
        default=3600, json_schema_extra={"env": "IP_AUTO_BLOCK_DURATION"}
    )

    # 安全分析配置
    SECURITY_ANALYZER_ENABLED: bool = Field(
        default=True, json_schema_extra={"env": "SECURITY_ANALYZER_ENABLED"}
    )
    SECURITY_ANALYZER_ENABLE_IP_BLOCK: bool = Field(
        default=True, json_schema_extra={"env": "SECURITY_ANALYZER_ENABLE_IP_BLOCK"}
    )
    SECURITY_ANALYZER_MAX_SUSPICIOUS_REQUESTS: int = Field(
        default=5, json_schema_extra={"env": "SECURITY_ANALYZER_MAX_SUSPICIOUS_REQUESTS"}
    )
    SECURITY_ANALYZER_BLOCK_DURATION: int = Field(
        default=3600, json_schema_extra={"env": "SECURITY_ANALYZER_BLOCK_DURATION"}
    )
    SECURITY_ANALYZER_PATTERNS: list[str] = Field(
        default_factory=lambda: list(DEFAULT_SECURITY_ANALYZER_PATTERNS),
        description="安全分析可疑模式列表（支持JSON数组或逗号分隔）",
        json_schema_extra={"env": "SECURITY_ANALYZER_PATTERNS"},
    )

    # 安全中间件配置
    SECURITY_MIDDLEWARE_ENABLED: bool = Field(
        default=True, json_schema_extra={"env": "SECURITY_MIDDLEWARE_ENABLED"}
    )
    SECURITY_MIDDLEWARE_IP_BLACKLIST_ENABLED: bool = Field(
        default=True,
        json_schema_extra={"env": "SECURITY_MIDDLEWARE_IP_BLACKLIST_ENABLED"},
    )
    SECURITY_MIDDLEWARE_RATE_LIMIT_ENABLED: bool = Field(
        default=True,
        json_schema_extra={"env": "SECURITY_MIDDLEWARE_RATE_LIMIT_ENABLED"},
    )
    SECURITY_MIDDLEWARE_USER_AGENT_CHECK_ENABLED: bool = Field(
        default=True,
        json_schema_extra={"env": "SECURITY_MIDDLEWARE_USER_AGENT_CHECK_ENABLED"},
    )
    SECURITY_MIDDLEWARE_USER_AGENT_MIN_LENGTH: int = Field(
        default=10,
        json_schema_extra={"env": "SECURITY_MIDDLEWARE_USER_AGENT_MIN_LENGTH"},
    )
    SECURITY_MIDDLEWARE_RATE_LIMITS: dict[str, dict[str, int]] | None = Field(
        default=None,
        description="安全中间件速率限制配置（JSON对象，键为端点名，值含 requests/window）",
        json_schema_extra={"env": "SECURITY_MIDDLEWARE_RATE_LIMITS"},
    )

    # 自适应限流配置
    ADAPTIVE_RATE_LIMIT_ENABLED: bool = Field(
        default=True, json_schema_extra={"env": "ADAPTIVE_RATE_LIMIT_ENABLED"}
    )
    ADAPTIVE_RATE_LIMIT_MAX_ERROR_RATE: float = Field(
        default=0.3, json_schema_extra={"env": "ADAPTIVE_RATE_LIMIT_MAX_ERROR_RATE"}
    )
    ADAPTIVE_RATE_LIMIT_SUSPICIOUS_MAX_ERROR_RATE: float = Field(
        default=0.1,
        json_schema_extra={"env": "ADAPTIVE_RATE_LIMIT_SUSPICIOUS_MAX_ERROR_RATE"},
    )
    ADAPTIVE_RATE_LIMIT_RESET_SECONDS: int = Field(
        default=60, json_schema_extra={"env": "ADAPTIVE_RATE_LIMIT_RESET_SECONDS"}
    )

    # 请求限制配置
    REQUEST_LIMIT_ENABLED: bool = Field(
        default=True, json_schema_extra={"env": "REQUEST_LIMIT_ENABLED"}
    )
    REQUEST_LIMIT_MAX_REQUESTS_PER_MINUTE: int = Field(
        default=100,
        json_schema_extra={"env": "REQUEST_LIMIT_MAX_REQUESTS_PER_MINUTE"},
    )
    REQUEST_LIMIT_RESET_SECONDS: int = Field(
        default=60, json_schema_extra={"env": "REQUEST_LIMIT_RESET_SECONDS"}
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

    @field_validator("CSRF_SAMESITE")
    @classmethod
    def validate_csrf_samesite(cls, v: str) -> Literal["lax", "strict", "none"]:
        """验证 CSRF SameSite 配置"""
        normalized = v.lower().strip()
        if normalized not in {"lax", "strict", "none"}:
            raise PydanticCustomError(
                "invalid_csrf_samesite",
                "CSRF_SAMESITE 必须是 lax / strict / none 之一",
                {"value": v},
            )
        return cast(Literal["lax", "strict", "none"], normalized)

    @field_validator("IP_BLACKLIST", mode="before")
    @classmethod
    def parse_ip_blacklist(cls, v: object) -> list[str]:
        """解析 IP 黑名单配置（兼容JSON数组与逗号分隔字符串）"""
        if v is None:
            return []
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return []

    @field_validator("IP_AUTO_BLOCK_THRESHOLD", "IP_AUTO_BLOCK_DURATION")
    @classmethod
    def validate_ip_blacklist_thresholds(cls, v: int) -> int:
        """验证 IP 黑名单阈值配置"""
        if v <= 0:
            raise PydanticCustomError(
                "invalid_ip_blacklist_value",
                "IP 黑名单阈值配置必须为正整数，当前值: {value}",
                {"value": v},
            )
        return v

    @field_validator("SECURITY_ANALYZER_PATTERNS", mode="before")
    @classmethod
    def parse_security_analyzer_patterns(cls, v: object) -> list[str]:
        """解析安全分析模式配置（兼容JSON数组与逗号分隔字符串）"""
        if v is None:
            return []
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return []

    @field_validator(
        "SECURITY_ANALYZER_MAX_SUSPICIOUS_REQUESTS",
        "SECURITY_ANALYZER_BLOCK_DURATION",
    )
    @classmethod
    def validate_security_analyzer_values(cls, v: int) -> int:
        """验证安全分析配置"""
        if v <= 0:
            raise PydanticCustomError(
                "invalid_security_analyzer_value",
                "安全分析配置必须为正整数，当前值: {value}",
                {"value": v},
            )
        return v

    @field_validator(
        "ADAPTIVE_RATE_LIMIT_MAX_ERROR_RATE",
        "ADAPTIVE_RATE_LIMIT_SUSPICIOUS_MAX_ERROR_RATE",
    )
    @classmethod
    def validate_adaptive_rate_limit_error_rate(cls, v: float) -> float:
        """验证自适应限流错误率阈值"""
        if v < 0 or v > 1:
            raise PydanticCustomError(
                "invalid_adaptive_rate_limit_value",
                "自适应限流错误率必须在 0 和 1 之间，当前值: {value}",
                {"value": v},
            )
        return float(v)

    @field_validator(
        "ADAPTIVE_RATE_LIMIT_RESET_SECONDS",
        "REQUEST_LIMIT_MAX_REQUESTS_PER_MINUTE",
        "REQUEST_LIMIT_RESET_SECONDS",
    )
    @classmethod
    def validate_rate_limit_positive_values(cls, v: int) -> int:
        """验证限流配置必须为正整数"""
        if v <= 0:
            raise PydanticCustomError(
                "invalid_rate_limit_value",
                "限流配置必须为正整数，当前值: {value}",
                {"value": v},
            )
        return v

    @field_validator("SECURITY_MIDDLEWARE_USER_AGENT_MIN_LENGTH")
    @classmethod
    def validate_security_middleware_user_agent_min_length(cls, v: int) -> int:
        """验证安全中间件 User-Agent 最小长度"""
        if v <= 0:
            raise PydanticCustomError(
                "invalid_security_middleware_value",
                "安全中间件 User-Agent 最小长度必须为正整数，当前值: {value}",
                {"value": v},
            )
        return v

    @field_validator("SECURITY_MIDDLEWARE_RATE_LIMITS")
    @classmethod
    def validate_security_middleware_rate_limits(
        cls, v: dict[str, dict[str, int]] | None
    ) -> dict[str, dict[str, int]] | None:
        """验证安全中间件速率限制配置"""
        if v is None:
            return None

        for endpoint, config in v.items():
            if not isinstance(config, dict):
                raise PydanticCustomError(
                    "invalid_security_middleware_rate_limits",
                    "安全中间件速率限制配置无效: {endpoint}",
                    {"endpoint": endpoint},
                )

            requests = config.get("requests")
            window = config.get("window")

            if not isinstance(requests, int) or not isinstance(window, int):
                raise PydanticCustomError(
                    "invalid_security_middleware_rate_limits",
                    "安全中间件速率限制配置需要整型 requests/window: {endpoint}",
                    {"endpoint": endpoint},
                )
            if requests <= 0 or window <= 0:
                raise PydanticCustomError(
                    "invalid_security_middleware_rate_limits",
                    "安全中间件速率限制配置必须为正整数: {endpoint}",
                    {"endpoint": endpoint},
                )

        return v

    @model_validator(mode="after")
    def validate_security_configuration(self) -> SecuritySettings:
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
