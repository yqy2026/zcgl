"""
Contract Extractor Factory
合同提取器工厂 - 简化版本

使用字典映射替代 if-elif 链，支持统一的 LLMProvider 枚举
"""

import logging

from src.core.config import settings
from src.core.exception_handler import ConfigurationError

from ..config import LLMProvider
from .base import ContractExtractorInterface
from .deepseek_adapter import DeepSeekAdapter
from .glm_adapter import GLMAdapter
from .hunyuan_adapter import HunyuanAdapter
from .qwen_adapter import QwenAdapter

logger = logging.getLogger(__name__)


# ============================================================================
# 简化的提取器工厂
# ============================================================================

# 提取器类型映射（字典替代 if-elif 链）
EXTRACTOR_MAP: dict[LLMProvider, type[ContractExtractorInterface]] = {
    LLMProvider.QWEN: QwenAdapter,
    LLMProvider.DEEPSEEK: DeepSeekAdapter,
    LLMProvider.GLM: GLMAdapter,
    LLMProvider.HUNYUAN: HunyuanAdapter,
}


class ExtractorFactory:
    """
    合同提取器工厂（简化版）

    使用字典映射创建提取器实例，支持统一的 LLMProvider 枚举

    注意：工厂模式每次创建新实例
    """

    @classmethod
    def get_extractor(
        cls, provider: str | LLMProvider | None = None
    ) -> ContractExtractorInterface:
        """
        获取 LLM 提取器实例

        Args:
            provider: 提供商名称或枚举（可选，默认从配置读取）

        Returns:
            ContractExtractorInterface: 提取器实例

        Raises:
            ValueError: 如果提供商不支持
        """
        # 解析提供商
        if provider is None:
            provider_str = settings.EXTRACTION_LLM_PROVIDER or settings.LLM_PROVIDER
            provider = LLMProvider.normalize(provider_str)
        elif isinstance(provider, str):
            provider = LLMProvider.normalize(provider)

        # 获取提取器类
        extractor_class = EXTRACTOR_MAP.get(provider)
        if not extractor_class:
            supported = [p.value for p in EXTRACTOR_MAP.keys()]
            raise ConfigurationError(
                f"Unsupported LLM provider: {provider.value}. "
                f"Supported providers: {supported}",
                config_key="EXTRACTION_LLM_PROVIDER",
            )

        logger.info(f"Creating extractor for provider: {provider.value}")
        return extractor_class()

    @classmethod
    def list_providers(cls) -> dict[str, list[str]]:
        """
        列出可用的提供商及其别名

        Returns:
            Dict mapping provider names to their aliases
        """
        return {
            "glm": ["glm-4v", "glm", "zhipu", "智谱", "chatglm"],
            "qwen": [
                "qwen-vl-max",
                "qwen-vl-plus",
                "qwen",
                "alibaba",
                "阿里",
                "通义",
                "dashscope",
            ],
            "deepseek": ["deepseek-vl", "deepseek", "深度求索"],
            "hunyuan": ["hunyuan-vision", "hunyuan", "tencent", "腾讯", "混元"],
        }


# ============================================================================
# 便捷函数
# ============================================================================

# 单例实例（用于便捷函数）
_llm_extractor_singleton: ContractExtractorInterface | None = None


def get_llm_extractor(
    force_provider: str | LLMProvider | None = None,
) -> ContractExtractorInterface:
    """
    获取 LLM 提取器实例（推荐使用，单例模式）

    Args:
        force_provider: 强制指定提供商（可选）

    Returns:
        ContractExtractorInterface: 提取器实例
    """
    global _llm_extractor_singleton

    # 如果强制指定提供商，重置单例
    if force_provider is not None:
        _llm_extractor_singleton = ExtractorFactory.get_extractor(force_provider)
        return _llm_extractor_singleton

    # 返回单例实例
    if _llm_extractor_singleton is None:
        _llm_extractor_singleton = ExtractorFactory.get_extractor()

    return _llm_extractor_singleton


def reset_extractor() -> None:
    """
    重置提取器单例（保留向后兼容）

    清除单例实例，用于测试隔离
    """
    global _llm_extractor_singleton
    _llm_extractor_singleton = None
    logger.info("Extractor singleton reset")


# ============================================================================
# 向后兼容
# ============================================================================

# 保留旧的别名映射（内部使用）
_PROVIDER_ALIASES = {
    # GLM 别名
    "glm-4v": LLMProvider.GLM,
    "glm": LLMProvider.GLM,
    "zhipu": LLMProvider.GLM,
    "智谱": LLMProvider.GLM,
    "chatglm": LLMProvider.GLM,
    # Qwen 别名
    "qwen-vl-max": LLMProvider.QWEN,
    "qwen-vl-plus": LLMProvider.QWEN,
    "qwen": LLMProvider.QWEN,
    "alibaba": LLMProvider.QWEN,
    "阿里": LLMProvider.QWEN,
    "通义": LLMProvider.QWEN,
    "dashscope": LLMProvider.QWEN,
    # DeepSeek 别名
    "deepseek-vl": LLMProvider.DEEPSEEK,
    "deepseek": LLMProvider.DEEPSEEK,
    "深度求索": LLMProvider.DEEPSEEK,
}
