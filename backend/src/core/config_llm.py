"""
LLM and notification settings.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

logger = logging.getLogger(__name__)


class LlmSettings(BaseModel):
    """LLM 相关配置"""

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
    def validate_llm_configuration(self) -> LlmSettings:
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
    def validate_wecom_configuration(self) -> LlmSettings:
        """验证企业微信配置一致性"""
        if self.WECOM_ENABLED and not self.WECOM_WEBHOOK_URL:
            logger.warning("企业微信通知已启用但未配置 Webhook URL，通知功能将无法工作")
        return self
