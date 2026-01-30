"""
配置管理模块
集中管理所有配置项，基于 Pydantic Settings
@lastModified 2026-01-29
"""

import logging
import os

from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic_core import PydanticCustomError
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..constants.rent_contract_constants import CONTRACT_ATTACHMENT_SUBDIR
from .exception_handler import ConfigurationError

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

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
        description="Encryption key for PII fields (format: base64:key:version)",
        json_schema_extra={"env": "DATA_ENCRYPTION_KEY"},
    )
    REQUIRE_ENCRYPTION: bool = Field(
        default=False,
        description="强制要求 DATA_ENCRYPTION_KEY（生产环境默认启用）",
        json_schema_extra={"env": "REQUIRE_ENCRYPTION"},
    )

    # 文件上传配置
    MAX_FILE_SIZE: int = Field(
        default=50 * 1024 * 1024, json_schema_extra={"env": "MAX_FILE_SIZE"}
    )  # 50MB
    UPLOAD_DIR: str = Field(
        default="./uploads", json_schema_extra={"env": "UPLOAD_DIR"}
    )
    RENT_CONTRACT_ATTACHMENT_SUBDIR: str = Field(
        default=CONTRACT_ATTACHMENT_SUBDIR,
        json_schema_extra={"env": "RENT_CONTRACT_ATTACHMENT_SUBDIR"},
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

    # LLM 通用配置
    LLM_TRIGGER_THRESHOLD: float = Field(
        default=0.65, json_schema_extra={"env": "LLM_TRIGGER_THRESHOLD"}
    )

    # V2.0 企业微信通知配置
    WECOM_ENABLED: bool = Field(
        default=False, json_schema_extra={"env": "WECOM_ENABLED"}
    )
    WECOM_WEBHOOK_URL: str | None = Field(
        default=None,
        description="企业微信机器人 Webhook URL",
        json_schema_extra={"env": "WECOM_WEBHOOK_URL"},
    )
    WECOM_MENTION_ALL: bool = Field(
        default=False, json_schema_extra={"env": "WECOM_MENTION_ALL"}
    )

    # LLM Provider Configuration (2026.01 更新)
    LLM_PROVIDER: str = Field(
        default="hunyuan",
        description="LLM provider: hunyuan (默认), qwen (推荐), glm, deepseek. 支持别名如 glm-4v, qwen-vl-max",
        json_schema_extra={"env": "LLM_PROVIDER"},
    )
    EXTRACTION_LLM_PROVIDER: str | None = Field(
        default=None,
        description="可选：仅文档提取使用的 LLM 提供商（覆盖 LLM_PROVIDER）",
        json_schema_extra={"env": "EXTRACTION_LLM_PROVIDER"},
    )

    # Qwen/DashScope Configuration
    DASHSCOPE_API_KEY: str | None = Field(
        default=None,
        description="阿里云 DashScope API Key for Qwen-VL",
        json_schema_extra={"env": "DASHSCOPE_API_KEY"},
    )
    DASHSCOPE_BASE_URL: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="DashScope API 基础地址",
        json_schema_extra={"env": "DASHSCOPE_BASE_URL"},
    )
    QWEN_VISION_MODEL: str = Field(
        default="qwen3-vl-flash",
        description="Qwen 视觉模型: qwen3-vl-flash (便宜), qwen-vl-max (最强)",
        json_schema_extra={"env": "QWEN_VISION_MODEL"},
    )

    # DeepSeek Configuration
    DEEPSEEK_API_KEY: str | None = Field(
        default=None,
        description="DeepSeek API Key for DeepSeek-VL",
        json_schema_extra={"env": "DEEPSEEK_API_KEY"},
    )
    DEEPSEEK_BASE_URL: str = Field(
        default="https://api.deepseek.com/v1",
        description="DeepSeek API 基础地址",
        json_schema_extra={"env": "DEEPSEEK_BASE_URL"},
    )
    DEEPSEEK_VISION_MODEL: str = Field(
        default="deepseek-vl",
        description="DeepSeek 视觉模型",
        json_schema_extra={"env": "DEEPSEEK_VISION_MODEL"},
    )

    # GLM/Zhipu Configuration
    ZHIPU_API_KEY: str | None = Field(
        default=None,
        description="智谱 AI API Key for GLM-4V",
        json_schema_extra={"env": "ZHIPU_API_KEY"},
    )
    ZHIPU_BASE_URL: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4",
        description="智谱 AI API 基础地址",
        json_schema_extra={"env": "ZHIPU_BASE_URL"},
    )
    ZHIPU_VISION_MODEL: str = Field(
        default="glm-4v",
        description="智谱视觉模型: glm-4v, glm-4v-flash, glm-4v-plus, glm-4.6v-flash",
        json_schema_extra={"env": "ZHIPU_VISION_MODEL"},
    )

    # Tencent Hunyuan Configuration (2026-01 新增)
    HUNYUAN_API_KEY: str | None = Field(
        default=None,
        description="腾讯混元 API Key",
        json_schema_extra={"env": "HUNYUAN_API_KEY"},
    )
    HUNYUAN_BASE_URL: str = Field(
        default="https://api.hunyuan.cloud.tencent.com/v1",
        description="腾讯混元 API 基础地址 (OpenAI 兼容)",
        json_schema_extra={"env": "HUNYUAN_BASE_URL"},
    )
    HUNYUAN_VISION_MODEL: str = Field(
        default="hunyuan-vision",
        description="腾讯混元视觉模型: hunyuan-vision, hunyuan-t1-vision",
        json_schema_extra={"env": "HUNYUAN_VISION_MODEL"},
    )

    # ========================================================================
    # 验证器 (Pydantic v2)
    # ========================================================================

    @field_validator("PORT", "REDIS_PORT")
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

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise PydanticCustomError(
                "invalid_log_level",
                "无效的日志级别: {level}. 有效值为: {valid_levels}",
                {
                    "level": v,
                    "valid_levels": ", ".join(sorted(valid_levels)),
                },
            )
        return v_upper

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        """验证 SECRET_KEY 强度，生产环境必须使用强密钥"""
        import os

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

    @field_validator("LLM_PROVIDER", "EXTRACTION_LLM_PROVIDER")
    @classmethod
    def validate_llm_provider(cls, v: str | None) -> str | None:
        """验证 LLM 提供商"""
        if v is None:
            return v
        valid_providers = {
            "glm-4v",
            "glm4v",
            "qwen-vl-max",
            "qwen-vl-plus",
            "qwen-vl",
            "deepseek-vl",
            "glm",
            "qwen",
            "deepseek",
            "hunyuan",
            "hunyuan-vision",
            "zhipu",
            "chatglm",
            "dashscope",
            "alibaba",
            "智谱",
            "通义",
            "阿里",
            "深度求索",
            "腾讯",
            "混元",
            "tencent",
        }
        v_normalized = v.lower().strip()
        if v_normalized not in valid_providers:
            raise PydanticCustomError(
                "invalid_llm_provider",
                "无效的 LLM 提供商: {provider}. 有效值为: {valid_providers}",
                {
                    "provider": v,
                    "valid_providers": ", ".join(sorted(valid_providers)),
                },
            )
        return v_normalized

    @field_validator("CHATGLM3_TEMPERATURE", check_fields=False)
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """验证温度参数范围"""
        if not 0.0 <= v <= 2.0:
            raise PydanticCustomError(
                "invalid_temperature",
                "温度参数必须在 0.0-2.0 范围内，当前值: {value}",
                {"value": v},
            )
        return v

    @field_validator("CHATGLM3_MAX_TOKENS", check_fields=False)
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        """验证最大 tokens 范围"""
        if not 1 <= v <= 32000:
            raise PydanticCustomError(
                "invalid_max_tokens",
                "最大 tokens 必须在 1-32000 范围内，当前值: {value}",
                {"value": v},
            )
        return v

    @field_validator("SLOW_QUERY_THRESHOLD")
    @classmethod
    def validate_slow_query_threshold(cls, v: float) -> float:
        """验证慢查询阈值"""
        if v < 0:
            raise PydanticCustomError(
                "invalid_slow_query_threshold",
                "慢查询阈值不能为负数，当前值: {value}",
                {"value": v},
            )
        if v > 60:
            logger.warning(f"慢查询阈值 {v} 秒过高，建议设置为 0.1-10 秒之间")
        return v

    @field_validator("MAX_FILE_SIZE")
    @classmethod
    def validate_max_file_size(cls, v: int) -> int:
        """验证最大文件大小"""
        max_allowed = 500 * 1024 * 1024  # 500MB
        if v > max_allowed:
            raise PydanticCustomError(
                "max_file_size_exceeded",
                "最大文件大小不能超过 {max_mb}MB，当前值: {current_mb}MB",
                {
                    "max_mb": max_allowed / (1024 * 1024),
                    "current_mb": v / (1024 * 1024),
                },
            )
        if v < 1024:  # 1KB
            raise PydanticCustomError(
                "max_file_size_too_small",
                "最大文件大小不能小于 1KB，当前值: {value} 字节",
                {"value": v},
            )
        return v

    @field_validator("DEFAULT_PAGE_SIZE", "MAX_PAGE_SIZE")
    @classmethod
    def validate_page_size(cls, v: int, info: ValidationInfo) -> int:
        """验证分页大小"""
        if v < 1:
            raise PydanticCustomError(
                "page_size_too_small",
                "{field} 不能小于 1，当前值: {value}",
                {"field": info.field_name, "value": v},
            )
        if v > 1000:
            raise PydanticCustomError(
                "page_size_too_large",
                "{field} 不能大于 1000，当前值: {value}",
                {"field": info.field_name, "value": v},
            )
        return v

    @field_validator("DEFAULT_PAGE_SIZE")
    @classmethod
    def validate_default_page_size_not_exceed_max(cls, v: int) -> int:
        """验证默认分页大小不超过最大值"""
        # 这个验证器会在 MAX_PAGE_SIZE 之后运行
        return v

    @field_validator("CHATGLM3_DEVICE", check_fields=False)
    @classmethod
    def validate_device(cls, v: str) -> str:
        """验证设备类型"""
        valid_devices = {"cpu", "cuda", "mps", "xpu"}
        v_lower = v.lower()
        if v_lower not in valid_devices:
            raise PydanticCustomError(
                "invalid_device",
                "无效的设备类型: {device}. 有效值为: {valid_devices}",
                {
                    "device": v,
                    "valid_devices": ", ".join(sorted(valid_devices)),
                },
            )
        return v_lower

    @model_validator(mode="after")
    def validate_page_size_consistency(self) -> "Settings":
        """验证分页大小一致性 - DEFAULT_PAGE_SIZE 不能超过 MAX_PAGE_SIZE"""
        if self.DEFAULT_PAGE_SIZE > self.MAX_PAGE_SIZE:
            raise PydanticCustomError(
                "page_size_inconsistent",
                "DEFAULT_PAGE_SIZE ({default_size}) 不能超过 MAX_PAGE_SIZE ({max_size})",
                {
                    "default_size": self.DEFAULT_PAGE_SIZE,
                    "max_size": self.MAX_PAGE_SIZE,
                },
            )
        return self

    @model_validator(mode="after")
    def validate_redis_configuration(self) -> "Settings":
        """验证 Redis 配置一致性"""
        if self.REDIS_ENABLED:
            if not self.REDIS_HOST:
                raise PydanticCustomError(
                    "missing_redis_host",
                    "启用 Redis 时必须设置 REDIS_HOST",
                    {},
                )
            if not self.REDIS_PASSWORD:
                logger.warning(
                    "Redis 已启用但未设置密码，生产环境建议配置 REDIS_PASSWORD"
                )
        return self

    @model_validator(mode="after")
    def validate_llm_configuration(self) -> "Settings":
        """验证 LLM 配置一致性"""
        provider = (self.EXTRACTION_LLM_PROVIDER or self.LLM_PROVIDER).lower()
        alias_map = {
            # GLM aliases
            "glm-4v": "glm",
            "glm4v": "glm",
            "zhipu": "glm",
            "chatglm": "glm",
            "智谱": "glm",
            # Qwen aliases
            "qwen-vl": "qwen",
            "qwen-vl-max": "qwen",
            "qwen-vl-plus": "qwen",
            "dashscope": "qwen",
            "通义": "qwen",
            "阿里": "qwen",
            "alibaba": "qwen",
            # DeepSeek aliases
            "deepseek-vl": "deepseek",
            "深度求索": "deepseek",
            # Hunyuan aliases
            "hunyuan-vision": "hunyuan",
            "tencent": "hunyuan",
            "腾讯": "hunyuan",
            "混元": "hunyuan",
        }
        provider = alias_map.get(provider, provider)
        has_api_key = False

        # 检查提供商是否有对应的 API Key
        if "glm" in provider or "chatglm" in provider:
            has_api_key = bool(self.ZHIPU_API_KEY)
        elif "qwen" in provider or "dashscope" in provider:
            has_api_key = bool(self.DASHSCOPE_API_KEY)
        elif "deepseek" in provider:
            has_api_key = bool(self.DEEPSEEK_API_KEY)
        elif "hunyuan" in provider or "tencent" in provider:
            has_api_key = bool(self.HUNYUAN_API_KEY)

        if not has_api_key:
            logger.warning(
                f"LLM 提供商 '{provider}' 可能未配置对应的 API Key，"
                "可能影响 PDF 提取功能"
            )

        return self

    @model_validator(mode="after")
    def validate_wecom_configuration(self) -> "Settings":
        """验证企业微信配置一致性"""
        if self.WECOM_ENABLED and not self.WECOM_WEBHOOK_URL:
            logger.warning("企业微信通知已启用但未配置 Webhook URL，通知功能将无法工作")
        return self

    @model_validator(mode="after")
    def validate_cache_configuration(self) -> "Settings":
        """验证缓存配置一致性"""
        if self.CACHE_TTL < 0:
            raise PydanticCustomError(
                "invalid_cache_ttl",
                "CACHE_TTL 不能为负数，当前值: {value}",
                {"value": self.CACHE_TTL},
            )
        if self.CACHE_TTL > 86400:  # 24小时
            logger.warning(
                f"CACHE_TTL ({self.CACHE_TTL}s) 超过 24 小时，可能导致缓存数据过期"
            )
        return self

    @model_validator(mode="after")
    def validate_security_configuration(self) -> "Settings":
        """
        统一安全配置验证
        处理所有安全检查并根据环境记录警告或抛出错误
        """
        warnings = []
        environment = (self.ENVIRONMENT or "production").lower()
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
        if self.DEBUG:
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

    # 创建全局配置实例


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
    import os

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
__all__ = ["settings", "validate_config"]
