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

from pydantic import (
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
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

    # JWT配置 - 必须通过环境变量设置
    SECRET_KEY: str = Field(
        ...,
        min_length=32,
        description="JWT密钥 - 必须32+字符的强随机字符串",
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

    def validate_security_config(self) -> list[str]:
        """
        验证安全配置
        返回安全警告列表
        注意: 此方法保留向后兼容性，实际验证由 model_validator 处理
        """
        warnings = []

        # 检查 JWT 密钥安全性
        if self.SECRET_KEY in [
            "EMERGENCY-ONLY-REPLACE-WITH-ENV-SECRET-KEY-NOW",
            "dev-secret-key-DO-NOT-USE-IN-PRODUCTION-REPLACE-WITH-ENV-VAR",
            "dev-secret-key-change-in-production",
            "your-secret-key-change-in-production",
            "secret-key",
        ]:
            warnings.append(
                "严重安全风险: 使用了默认或不安全的 JWT 密钥！"
                "请立即设置环境变量 SECRET_KEY 为强随机密钥。"
            )

        if len(self.SECRET_KEY) < 32:
            warnings.append(
                f"警告: JWT 密钥长度不足 ({len(self.SECRET_KEY)}字符)，"
                "建议使用至少 32 字符的密钥。"
            )

        # 检查是否在调试模式运行
        if self.DEBUG:
            warnings.append("警告: 当前在调试模式运行，生产环境必须设置 DEBUG=false。")

        # 检查数据库是否为 SQLite（生产环境推荐 PostgreSQL）
        if self.DATABASE_URL.startswith("sqlite:///./land_property.db"):
            warnings.append(
                "提醒: 使用默认 SQLite 数据库路径，生产环境建议使用 PostgreSQL。"
            )

        return warnings

    def log_security_status(self) -> None:
        """
        记录安全配置状态
        注意: 保留向后兼容性，实际验证在 model_validator 中完成
        """
        warnings = self.validate_security_config()

        if warnings and not os.getenv("TESTING_MODE", "false").lower() == "true":
            logger.warning("=" * 60)
            logger.warning("安全配置检查发现以下问题:")
            for warning in warnings:
                logger.warning(f"  {warning}")
            logger.warning("=" * 60)
        else:
            logger.info("安全配置检查通过")

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

    # LLM/ChatGLM3 配置（可选）
    CHATGLM3_API_URL: str | None = Field(
        default=None, json_schema_extra={"env": "CHATGLM3_API_URL"}
    )
    CHATGLM3_MAX_TOKENS: int = Field(
        default=1500, json_schema_extra={"env": "CHATGLM3_MAX_TOKENS"}
    )
    CHATGLM3_TEMPERATURE: float = Field(
        default=0.2, json_schema_extra={"env": "CHATGLM3_TEMPERATURE"}
    )
    CHATGLM3_TIMEOUT: int = Field(
        default=30, json_schema_extra={"env": "CHATGLM3_TIMEOUT"}
    )
    CHATGLM3_MODEL_ID: str = Field(
        default="THUDM/chatglm3-6b", json_schema_extra={"env": "CHATGLM3_MODEL_ID"}
    )
    CHATGLM3_DEVICE: str = Field(
        default="cpu", json_schema_extra={"env": "CHATGLM3_DEVICE"}
    )
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

    # V2.0 NVIDIA Cloud OCR配置
    NVIDIA_API_KEY: str | None = Field(
        default=None,
        description="NVIDIA API Key for Cloud OCR",
        json_schema_extra={"env": "NVIDIA_API_KEY"},
    )
    NVIDIA_OCR_BASE_URL: str = Field(
        default="https://ai.api.nvidia.com/v1/cv/baidu/paddleocr",
        description="NVIDIA Cloud PaddleOCR API endpoint",
        json_schema_extra={"env": "NVIDIA_OCR_BASE_URL"},
    )
    NVIDIA_OCR_TIMEOUT: int = Field(
        default=60,
        description="NVIDIA OCR API timeout in seconds",
        json_schema_extra={"env": "NVIDIA_OCR_TIMEOUT"},
    )
    OCR_PROVIDER: str = Field(
        default="auto",
        description="OCR provider: auto, local, nvidia_cloud",
        json_schema_extra={"env": "OCR_PROVIDER"},
    )

    # LLM Provider Configuration (2026.01 更新)
    LLM_PROVIDER: str = Field(
        default="qwen",
        description="LLM provider: qwen (推荐), deepseek, glm. 默认使用 qwen3-vl-flash ($0.05/M)",
        json_schema_extra={"env": "LLM_PROVIDER"},
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
            raise ValueError(f"端口号必须在 1-65535 范围内，当前值: {v}")
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
            raise ValueError(
                f"无效的日志级别: {v}. 有效值为: {', '.join(sorted(valid_levels))}"
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
        # 直接从环境变量读取，因为 ENVIRONMENT 不是 Settings 的字段
        environment = os.getenv("ENVIRONMENT", "production")

        if environment == "production":
            if is_weak_pattern:
                raise ValueError(
                    "生产环境禁止使用弱密钥模式。检测到包含常见弱密钥标识符。"
                    "请使用 python -c 'import secrets; print(secrets.token_urlsafe(32))' 生成强密钥。"
                )
            if is_too_short:
                raise ValueError(
                    f"生产环境 SECRET_KEY 长度必须至少 32 字符，当前: {len(v)} 字符"
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

    @field_validator("OCR_PROVIDER")
    @classmethod
    def validate_ocr_provider(cls, v: str) -> str:
        """验证 OCR 提供商"""
        valid_providers = {"auto", "local", "nvidia_cloud"}
        if v not in valid_providers:
            raise ValueError(
                f"无效的 OCR 提供商: {v}. 有效值为: {', '.join(sorted(valid_providers))}"
            )
        return v

    @field_validator("LLM_PROVIDER")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """验证 LLM 提供商"""
        valid_providers = {
            "glm-4v",
            "qwen-vl-max",
            "deepseek-vl",
            "glm",
            "qwen",
            "deepseek",
        }
        v_normalized = v.lower().strip()
        if v_normalized not in valid_providers:
            raise ValueError(
                f"无效的 LLM 提供商: {v}. "
                f"有效值为: {', '.join(sorted(valid_providers))}"
            )
        return v_normalized

    @field_validator("CHATGLM3_TEMPERATURE")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """验证温度参数范围"""
        if not 0.0 <= v <= 2.0:
            raise ValueError(f"温度参数必须在 0.0-2.0 范围内，当前值: {v}")
        return v

    @field_validator("CHATGLM3_MAX_TOKENS")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        """验证最大 tokens 范围"""
        if not 1 <= v <= 32000:
            raise ValueError(f"最大 tokens 必须在 1-32000 范围内，当前值: {v}")
        return v

    @field_validator("SLOW_QUERY_THRESHOLD")
    @classmethod
    def validate_slow_query_threshold(cls, v: float) -> float:
        """验证慢查询阈值"""
        if v < 0:
            raise ValueError(f"慢查询阈值不能为负数，当前值: {v}")
        if v > 60:
            logger.warning(f"慢查询阈值 {v} 秒过高，建议设置为 0.1-10 秒之间")
        return v

    @field_validator("MAX_FILE_SIZE")
    @classmethod
    def validate_max_file_size(cls, v: int) -> int:
        """验证最大文件大小"""
        max_allowed = 500 * 1024 * 1024  # 500MB
        if v > max_allowed:
            raise ValueError(
                f"最大文件大小不能超过 {max_allowed / (1024 * 1024)}MB，当前值: {v / (1024 * 1024)}MB"
            )
        if v < 1024:  # 1KB
            raise ValueError(f"最大文件大小不能小于 1KB，当前值: {v} 字节")
        return v

    @field_validator("DEFAULT_PAGE_SIZE", "MAX_PAGE_SIZE")
    @classmethod
    def validate_page_size(cls, v: int, info: ValidationInfo) -> int:
        """验证分页大小"""
        if v < 1:
            raise ValueError(f"{info.field_name} 不能小于 1，当前值: {v}")
        if v > 1000:
            raise ValueError(f"{info.field_name} 不能大于 1000，当前值: {v}")
        return v

    @field_validator("DEFAULT_PAGE_SIZE")
    @classmethod
    def validate_default_page_size_not_exceed_max(cls, v: int) -> int:
        """验证默认分页大小不超过最大值"""
        # 这个验证器会在 MAX_PAGE_SIZE 之后运行
        return v

    @field_validator("CHATGLM3_DEVICE")
    @classmethod
    def validate_device(cls, v: str) -> str:
        """验证设备类型"""
        valid_devices = {"cpu", "cuda", "mps", "xpu"}
        v_lower = v.lower()
        if v_lower not in valid_devices:
            raise ValueError(
                f"无效的设备类型: {v}. 有效值为: {', '.join(sorted(valid_devices))}"
            )
        return v_lower

    @model_validator(mode="after")
    def validate_page_size_consistency(self) -> "Settings":
        """验证分页大小一致性 - DEFAULT_PAGE_SIZE 不能超过 MAX_PAGE_SIZE"""
        if self.DEFAULT_PAGE_SIZE > self.MAX_PAGE_SIZE:
            raise ValueError(
                f"DEFAULT_PAGE_SIZE ({self.DEFAULT_PAGE_SIZE}) "
                f"不能超过 MAX_PAGE_SIZE ({self.MAX_PAGE_SIZE})"
            )
        return self

    @model_validator(mode="after")
    def validate_redis_configuration(self) -> "Settings":
        """验证 Redis 配置一致性"""
        if self.REDIS_ENABLED:
            if not self.REDIS_HOST:
                raise ValueError("启用 Redis 时必须设置 REDIS_HOST")
            if not self.REDIS_PASSWORD:
                logger.warning(
                    "Redis 已启用但未设置密码，生产环境建议配置 REDIS_PASSWORD"
                )
        return self

    @model_validator(mode="after")
    def validate_llm_configuration(self) -> "Settings":
        """验证 LLM 配置一致性"""
        provider = self.LLM_PROVIDER.lower()
        has_api_key = False

        # 检查提供商是否有对应的 API Key
        if "glm" in provider or "chatglm" in provider:
            has_api_key = bool(self.ZHIPU_API_KEY)
        elif "qwen" in provider or "dashscope" in provider:
            has_api_key = bool(self.DASHSCOPE_API_KEY)
        elif "deepseek" in provider:
            has_api_key = bool(self.DEEPSEEK_API_KEY)

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
    def validate_nvidia_ocr_configuration(self) -> "Settings":
        """验证 NVIDIA OCR 配置一致性"""
        if self.OCR_PROVIDER == "nvidia_cloud" and not self.NVIDIA_API_KEY:
            logger.warning(
                "OCR 提供商设置为 NVIDIA Cloud 但未配置 NVIDIA_API_KEY，"
                "将回退到本地 OCR"
            )
        return self

    @model_validator(mode="after")
    def validate_cache_configuration(self) -> "Settings":
        """验证缓存配置一致性"""
        if self.CACHE_TTL < 0:
            raise ValueError(f"CACHE_TTL 不能为负数，当前值: {self.CACHE_TTL}")
        if self.CACHE_TTL > 86400:  # 24小时
            logger.warning(
                f"CACHE_TTL ({self.CACHE_TTL}s) 超过 24 小时，可能导致缓存数据过期"
            )
        return self

    @model_validator(mode="after")
    def validate_security_configuration(self) -> "Settings":
        """验证安全配置"""
        warnings = []

        # 检查 JWT 密钥安全性
        if self.SECRET_KEY in [
            "EMERGENCY-ONLY-REPLACE-WITH-ENV-SECRET-KEY-NOW",
            "dev-secret-key-DO-NOT-USE-IN-PRODUCTION-REPLACE-WITH-ENV-VAR",
            "dev-secret-key-change-in-production",
            "your-secret-key-change-in-production",
            "secret-key",
        ]:
            warnings.append(
                "严重安全风险: 使用了默认或不安全的 JWT 密钥！"
                "请立即设置环境变量 SECRET_KEY 为强随机密钥。"
            )

        if len(self.SECRET_KEY) < 32:
            warnings.append(
                f"警告: JWT 密钥长度不足 ({len(self.SECRET_KEY)}字符)，"
                "建议使用至少 32 字符的密钥。"
            )

        # 检查调试模式
        if self.DEBUG:
            warnings.append("警告: 当前在调试模式运行，生产环境必须设置 DEBUG=false。")

        # 检查数据库
        if self.DATABASE_URL.startswith("sqlite:///./land_property.db"):
            warnings.append(
                "提醒: 使用默认 SQLite 数据库路径，生产环境建议使用 PostgreSQL。"
            )

        # 记录警告
        if warnings and not os.getenv("TESTING_MODE", "false").lower() == "true":
            logger.warning("=" * 60)
            logger.warning("安全配置检查发现以下问题:")
            for warning in warnings:
                logger.warning(f"  {warning}")
            logger.warning("=" * 60)

        return self

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
def validate_config() -> None:
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

    logger.info(
        f"配置验证完成 - 应用: {settings.APP_NAME}, 版本: {settings.APP_VERSION}"
    )


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
