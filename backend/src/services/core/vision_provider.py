"""Unified vision provider selection for document AI."""

from __future__ import annotations

import os
from typing import Any

from src.core.config import settings
from src.core.exception_handler import ConfigurationError
from src.services.document.config import LLMProvider

from .deepseek_vision_service import get_deepseek_vision_service
from .hunyuan_vision_service import get_hunyuan_vision_service
from .qwen_vision_service import get_qwen_vision_service
from .zhipu_vision_service import get_zhipu_vision_service

VISION_PROVIDER_GETTERS = {
    LLMProvider.QWEN: get_qwen_vision_service,
    LLMProvider.DEEPSEEK: get_deepseek_vision_service,
    LLMProvider.GLM: get_zhipu_vision_service,
    LLMProvider.HUNYUAN: get_hunyuan_vision_service,
}


def resolve_vision_provider(provider: str | LLMProvider | None = None) -> LLMProvider:
    """Resolve the document vision provider from explicit input or VISION_MODEL."""
    if isinstance(provider, LLMProvider):
        return provider
    if isinstance(provider, str) and provider.strip() != "":
        return LLMProvider.normalize(provider)

    provider_name = (
        os.getenv("VISION_MODEL")
        or settings.VISION_MODEL
        or settings.EXTRACTION_LLM_PROVIDER
        or settings.LLM_PROVIDER
    )
    if provider_name is None or provider_name.strip() == "":
        raise ConfigurationError(
            "VISION_MODEL is required for document vision extraction",
            config_key="VISION_MODEL",
        )
    return LLMProvider.normalize(provider_name)


def get_vision_provider(provider: str | LLMProvider | None = None) -> Any:
    """Return the configured vision service adapter, failing loud on bad config."""
    resolved_provider = resolve_vision_provider(provider)
    getter = VISION_PROVIDER_GETTERS.get(resolved_provider)
    if getter is None:
        supported = [item.value for item in VISION_PROVIDER_GETTERS]
        raise ConfigurationError(
            f"Unsupported vision provider: {resolved_provider.value}. "
            f"Supported providers: {supported}",
            config_key="VISION_MODEL",
        )

    service = getter()
    if not getattr(service, "is_available", False):
        api_key_name = {
            LLMProvider.QWEN: "DASHSCOPE_API_KEY",
            LLMProvider.DEEPSEEK: "DEEPSEEK_API_KEY",
            LLMProvider.GLM: "ZHIPU_API_KEY",
            LLMProvider.HUNYUAN: "HUNYUAN_API_KEY",
        }[resolved_provider]
        raise ConfigurationError(
            f"{api_key_name} not configured for VISION_MODEL={resolved_provider.value}",
            config_key=api_key_name,
        )

    return service
