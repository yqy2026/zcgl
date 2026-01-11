#!/usr/bin/env python3
"""
Unit tests for ExtractorFactory
提取器工厂单元测试
"""

from unittest.mock import Mock, patch

import pytest

from src.services.document.extractors.base import ContractExtractorInterface
from src.services.document.extractors.factory import (
    EXTRACTOR_MAP,
    ExtractorFactory,
    get_llm_extractor,
    reset_extractor,
)
from src.services.document.config import LLMProvider


class TestExtractorMap:
    """提取器映射测试"""

    def test_extractor_map_completeness(self):
        """测试提取器映射包含所有提供商"""
        assert LLMProvider.GLM in EXTRACTOR_MAP
        assert LLMProvider.QWEN in EXTRACTOR_MAP
        assert LLMProvider.DEEPSEEK in EXTRACTOR_MAP

    def test_extractor_map_values_are_classes(self):
        """测试映射值是提取器类"""
        from src.services.document.extractors.glm_adapter import GLMAdapter
        from src.services.document.extractors.qwen_adapter import QwenAdapter
        from src.services.document.extractors.deepseek_adapter import DeepSeekAdapter

        assert EXTRACTOR_MAP[LLMProvider.GLM] == GLMAdapter
        assert EXTRACTOR_MAP[LLMProvider.QWEN] == QwenAdapter
        assert EXTRACTOR_MAP[LLMProvider.DEEPSEEK] == DeepSeekAdapter


class TestExtractorFactory:
    """ExtractorFactory 测试套件"""

    def test_get_extractor_default(self):
        """测试获取默认提取器"""
        with patch('src.services.document.extractors.factory.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = "glm"

            extractor = ExtractorFactory.get_extractor()

            assert isinstance(extractor, ContractExtractorInterface)
            assert extractor is not None

    def test_get_extractor_with_provider_enum(self):
        """测试使用枚举指定提供商"""
        extractor = ExtractorFactory.get_extractor(LLMProvider.QWEN)

        assert isinstance(extractor, ContractExtractorInterface)

    def test_get_extractor_with_provider_string(self):
        """测试使用字符串指定提供商"""
        extractor = ExtractorFactory.get_extractor("deepseek")

        assert isinstance(extractor, ContractExtractorInterface)

    def test_get_extractor_with_alias(self):
        """测试使用别名指定提供商"""
        # glm-4v 应该被标准化为 glm
        extractor = ExtractorFactory.get_extractor("glm-4v")

        assert isinstance(extractor, ContractExtractorInterface)

    def test_get_extractor_invalid_provider(self):
        """测试无效提供商抛出异常"""
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            ExtractorFactory.get_extractor("invalid-provider")

    def test_get_extractor_none_uses_config(self):
        """测试不指定提供商时使用配置"""
        with patch('src.services.document.extractors.factory.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = "qwen"

            extractor = ExtractorFactory.get_extractor()

            # 应该创建 QwenAdapter
            from src.services.document.extractors.qwen_adapter import QwenAdapter
            assert isinstance(extractor, QwenAdapter)

    def test_list_providers(self):
        """测试列出提供商"""
        providers = ExtractorFactory.list_providers()

        assert "glm" in providers
        assert "qwen" in providers
        assert "deepseek" in providers

        # 验证别名
        assert "glm-4v" in providers["glm"]
        assert "zhipu" in providers["glm"]
        assert "dashscope" in providers["qwen"]


class TestConvenienceFunctions:
    """便捷函数测试套件"""

    def test_get_llm_extractor(self):
        """测试 get_llm_extractor 函数"""
        with patch('src.services.document.extractors.factory.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = "glm"

            extractor = get_llm_extractor()

            assert isinstance(extractor, ContractExtractorInterface)

    def test_get_llm_extractor_with_force_provider(self):
        """测试强制指定提供商"""
        extractor = get_llm_extractor(force_provider="qwen")

        assert isinstance(extractor, ContractExtractorInterface)

    def test_get_llm_extractor_with_enum(self):
        """测试使用枚举强制指定提供商"""
        extractor = get_llm_extractor(force_provider=LLMProvider.DEEPSEEK)

        assert isinstance(extractor, ContractExtractorInterface)

    def test_reset_extractor(self):
        """测试重置提取器（兼容性函数）"""
        # 函数应该成功执行（在新实现中是 no-op）
        reset_extractor()


class TestProviderNormalization:
    """提供商标准化测试"""

    @pytest.mark.parametrize("alias,expected", [
        # GLM 别名
        ("glm", LLMProvider.GLM),
        ("glm-4v", LLMProvider.GLM),
        ("zhipu", LLMProvider.GLM),
        ("智谱", LLMProvider.GLM),
        ("chatglm", LLMProvider.GLM),
        # Qwen 别名
        ("qwen", LLMProvider.QWEN),
        ("qwen-vl-max", LLMProvider.QWEN),
        ("dashscope", LLMProvider.QWEN),
        ("通义", LLMProvider.QWEN),
        # DeepSeek 别名
        ("deepseek", LLMProvider.DEEPSEEK),
        ("deepseek-vl", LLMProvider.DEEPSEEK),
    ])
    def test_get_extractor_with_various_aliases(self, alias, expected):
        """测试使用各种别名获取提取器"""
        extractor = ExtractorFactory.get_extractor(alias)

        # 验证返回了提取器实例
        assert isinstance(extractor, ContractExtractorInterface)

    def test_case_insensitive_provider(self):
        """测试提供商名称大小写不敏感"""
        with patch('src.services.document.extractors.factory.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = "GLM"

            extractor = ExtractorFactory.get_extractor()

            assert isinstance(extractor, ContractExtractorInterface)


class TestExtractorCreation:
    """提取器创建测试"""

    def test_each_provider_creates_correct_instance(self):
        """测试每个提供商创建正确的实例"""
        from src.services.document.extractors.glm_adapter import GLMAdapter
        from src.services.document.extractors.qwen_adapter import QwenAdapter
        from src.services.document.extractors.deepseek_adapter import DeepSeekAdapter

        # GLM
        glm_extractor = ExtractorFactory.get_extractor(LLMProvider.GLM)
        assert isinstance(glm_extractor, GLMAdapter)

        # Qwen
        qwen_extractor = ExtractorFactory.get_extractor(LLMProvider.QWEN)
        assert isinstance(qwen_extractor, QwenAdapter)

        # DeepSeek
        deepseek_extractor = ExtractorFactory.get_extractor(LLMProvider.DEEPSEEK)
        assert isinstance(deepseek_extractor, DeepSeekAdapter)

    def test_factory_creates_new_instances(self):
        """测试工厂每次创建新实例（非单例）"""
        extractor1 = ExtractorFactory.get_extractor(LLMProvider.GLM)
        extractor2 = ExtractorFactory.get_extractor(LLMProvider.GLM)

        # 应该是不同的实例
        assert extractor1 is not extractor2

    def test_factory_supports_all_llm_providers(self):
        """测试工厂支持所有 LLM 提供商"""
        for provider in LLMProvider:
            extractor = ExtractorFactory.get_extractor(provider)
            assert isinstance(extractor, ContractExtractorInterface)


class TestErrorHandling:
    """错误处理测试"""

    def test_invalid_provider_raises_error(self):
        """测试无效提供商抛出有意义的错误"""
        with pytest.raises(ValueError) as exc_info:
            ExtractorFactory.get_extractor("nonexistent-provider")

        error_message = str(exc_info.value)
        assert "Unsupported LLM provider" in error_message
        assert "nonexistent-provider" in error_message

    def test_error_message_lists_supported_providers(self):
        """测试错误消息包含支持的提供商列表"""
        with pytest.raises(ValueError) as exc_info:
            ExtractorFactory.get_extractor("invalid")

        error_message = str(exc_info.value)
        assert "Supported providers:" in error_message
        assert "glm" in error_message
        assert "qwen" in error_message
        assert "deepseek" in error_message
