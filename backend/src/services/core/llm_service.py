#!/usr/bin/env python3
"""
LLM 服务模块

提供统一的 LLM 服务接口和工厂模式实现
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel

from ...core.exception_handler import ConfigurationError
from ..document.config import LLMProvider

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================


def _env_first(keys: list[str], default: str) -> str:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return default


class LLMResponse(BaseModel):
    """LLM 响应模型"""

    content: str
    raw_response: Any = None
    usage: dict[str, Any] = {}
    provider: str = ""


# ============================================================================
# LLM 服务接口
# ============================================================================


class LLMServiceInterface(ABC):
    """
    LLM 服务接口

    定义所有 LLM 服务必须实现的基础方法
    """

    @property
    @abstractmethod
    def provider(self) -> LLMProvider:
        """获取提供商"""
        pass

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        json_mode: bool = False,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """
        发送聊天完成请求

        Args:
            messages: 消息列表
            temperature: 温度参数
            json_mode: 是否返回 JSON 格式
            max_tokens: 最大 tokens

        Returns:
            LLMResponse: LLM 响应
        """
        pass


# ============================================================================
# 通用 OpenAI 兼容服务
# ============================================================================


class BaseOpenAILLM(LLMServiceInterface):
    """
    基础 OpenAI 兼容 LLM 服务

    支持任何兼容 OpenAI API 的服务
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 60,
        provider: LLMProvider = LLMProvider.GLM,
    ):
        """
        初始化服务

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
            timeout: 超时时间（秒）
            provider: 提供商枚举
        """
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._provider = provider

    @property
    def provider(self) -> LLMProvider:
        return self._provider

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        json_mode: bool = False,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """发送聊天完成请求"""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions", json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()

                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})

                return LLMResponse(
                    content=content,
                    raw_response=data,
                    usage=usage,
                    provider=self._provider.value,
                )

        except Exception as e:
            logger.error(f"LLM Request Failed ({self._provider.value}): {e}")
            raise


# ============================================================================
# 服务工厂
# ============================================================================


class LLMServiceFactory:
    """
    LLM 服务工厂

    负责创建和管理 LLM 服务实例
    """

    _services: dict[LLMProvider, type[LLMServiceInterface]] = {}
    _config: dict[LLMProvider, dict[str, Any]] = {}

    @classmethod
    def register(
        cls,
        provider: LLMProvider,
        service_class: type[LLMServiceInterface],
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        注册 LLM 服务

        Args:
            provider: 提供商枚举
            service_class: 服务类
            config: 配置参数
        """
        cls._services[provider] = service_class
        if config:
            cls._config[provider] = config

    @classmethod
    def create(cls, provider: LLMProvider, **kwargs: Any) -> LLMServiceInterface:
        """
        创建 LLM 服务实例

        Args:
            provider: 提供商枚举
            **kwargs: 额外配置参数

        Returns:
            LLMServiceInterface: 服务实例

        Raises:
            ValueError: 如果提供商未注册
        """
        service_class = cls._services.get(provider)
        if not service_class:
            raise ConfigurationError(
                f"Unknown LLM provider: {provider}. "
                f"Registered providers: {list[Any](cls._services.keys())}",
                config_key="LLM_PROVIDER",
            )

        # 合并配置
        config = {**cls._config.get(provider, {}), **kwargs}
        return service_class(**config)

    @classmethod
    def create_from_env(
        cls, provider: LLMProvider | None = None
    ) -> LLMServiceInterface:
        """
        从环境变量创建 LLM 服务实例

        Args:
            provider: 提供商枚举（默认从环境变量读取）

        Returns:
            LLMServiceInterface: 服务实例
        """
        # 从环境变量读取提供商
        if provider is None:
            provider_str = os.getenv("LLM_PROVIDER", "hunyuan")
            provider = LLMProvider.normalize(provider_str)

        # 根据提供商创建服务
        if provider == LLMProvider.GLM:
            return cls._create_glm_service()
        elif provider == LLMProvider.QWEN:
            return cls._create_qwen_service()
        elif provider == LLMProvider.DEEPSEEK:
            return cls._create_deepseek_service()
        elif provider == LLMProvider.HUNYUAN:
            return cls._create_hunyuan_service()
        else:
            raise ConfigurationError(
                f"Unsupported provider: {provider}",
                config_key="LLM_PROVIDER",
            )

    @classmethod
    def _create_glm_service(cls) -> LLMServiceInterface:
        """创建智谱 GLM 服务"""
        return BaseOpenAILLM(
            api_key=os.getenv("ZHIPU_API_KEY", os.getenv("LLM_API_KEY", "")),
            base_url=_env_first(
                ["ZHIPU_BASE_URL", "ZHIPU_API_BASE"],
                "https://open.bigmodel.cn/api/paas/v4",
            ),
            model=os.getenv("ZHIPU_MODEL", "glm-4v"),
            timeout=int(os.getenv("LLM_TIMEOUT", "30")),
            provider=LLMProvider.GLM,
        )

    @classmethod
    def _create_qwen_service(cls) -> LLMServiceInterface:
        """创建通义千问服务"""
        return BaseOpenAILLM(
            api_key=os.getenv("DASHSCOPE_API_KEY", os.getenv("LLM_API_KEY", "")),
            base_url=_env_first(
                ["DASHSCOPE_BASE_URL", "DASHSCOPE_API_BASE"],
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
            model=os.getenv("DASHSCOPE_MODEL", "qwen-vl-max"),
            timeout=int(os.getenv("LLM_TIMEOUT", "30")),
            provider=LLMProvider.QWEN,
        )

    @classmethod
    def _create_deepseek_service(cls) -> LLMServiceInterface:
        """创建 DeepSeek 服务"""
        return BaseOpenAILLM(
            api_key=os.getenv("DEEPSEEK_API_KEY", os.getenv("LLM_API_KEY", "")),
            base_url=_env_first(
                ["DEEPSEEK_BASE_URL", "DEEPSEEK_API_BASE"],
                "https://api.deepseek.com",
            ),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            timeout=int(os.getenv("LLM_TIMEOUT", "30")),
            provider=LLMProvider.DEEPSEEK,
        )

    @classmethod
    def _create_hunyuan_service(cls) -> LLMServiceInterface:
        """创建腾讯混元服务"""
        return BaseOpenAILLM(
            api_key=os.getenv("HUNYUAN_API_KEY", os.getenv("LLM_API_KEY", "")),
            base_url=_env_first(
                ["HUNYUAN_BASE_URL", "HUNYUAN_API_BASE"],
                "https://api.hunyuan.cloud.tencent.com/v1",
            ),
            model=os.getenv(
                "HUNYUAN_MODEL",
                os.getenv("HUNYUAN_VISION_MODEL", "hunyuan-vision"),
            ),
            timeout=int(os.getenv("LLM_TIMEOUT", "30")),
            provider=LLMProvider.HUNYUAN,
        )


# ============================================================================
# 向后兼容函数（逐步废弃）
# ============================================================================


class LLMService(BaseOpenAILLM):
    """
    兼容类 - 保持向后兼容

    保留原有的 LLMService 类作为 BaseOpenAILLM 的别名
    """

    def __init__(self) -> None:
        provider_str = os.getenv("LLM_PROVIDER", "hunyuan")
        provider = LLMProvider.normalize(provider_str)

        api_key = os.getenv("LLM_API_KEY", "dummy-key")
        base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        timeout = int(os.getenv("LLM_TIMEOUT", "60"))

        # 根据提供商设置默认配置
        if provider == LLMProvider.GLM:
            base_url = _env_first(
                ["ZHIPU_BASE_URL", "ZHIPU_API_BASE"],
                "https://open.bigmodel.cn/api/paas/v4",
            )
            model = os.getenv("ZHIPU_MODEL", "glm-4v")
            api_key = os.getenv("ZHIPU_API_KEY", api_key)
            timeout = int(os.getenv("LLM_TIMEOUT", "30"))
        elif provider == LLMProvider.QWEN:
            base_url = _env_first(
                ["DASHSCOPE_BASE_URL", "DASHSCOPE_API_BASE"],
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            model = os.getenv("DASHSCOPE_MODEL", "qwen-vl-max")
            api_key = os.getenv("DASHSCOPE_API_KEY", api_key)
            timeout = int(os.getenv("LLM_TIMEOUT", "30"))
        elif provider == LLMProvider.DEEPSEEK:
            base_url = _env_first(
                ["DEEPSEEK_BASE_URL", "DEEPSEEK_API_BASE"],
                "https://api.deepseek.com",
            )
            model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            api_key = os.getenv("DEEPSEEK_API_KEY", api_key)
            timeout = int(os.getenv("LLM_TIMEOUT", "30"))
        elif provider == LLMProvider.HUNYUAN:
            base_url = _env_first(
                ["HUNYUAN_BASE_URL", "HUNYUAN_API_BASE"],
                "https://api.hunyuan.cloud.tencent.com/v1",
            )
            model = os.getenv(
                "HUNYUAN_MODEL",
                os.getenv("HUNYUAN_VISION_MODEL", "hunyuan-vision"),
            )
            api_key = os.getenv("HUNYUAN_API_KEY", api_key)
            timeout = int(os.getenv("LLM_TIMEOUT", "30"))

        super().__init__(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=timeout,
            provider=provider,
        )


# 单例（保留向后兼容，建议使用工厂）
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """
    获取 LLM 服务单例（向后兼容）

    建议使用 LLMServiceFactory.create_from_env() 替代
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


# ============================================================================
# 便捷函数
# ============================================================================


def create_llm_service(provider: LLMProvider | None = None) -> LLMServiceInterface:
    """
    创建 LLM 服务实例（推荐使用）

    Args:
        provider: 提供商枚举（默认从环境变量读取）

    Returns:
        LLMServiceInterface: 服务实例
    """
    return LLMServiceFactory.create_from_env(provider)
