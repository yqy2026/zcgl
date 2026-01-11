#!/usr/bin/env python3
"""
LLM 合同提取器单元测试
测试 LLMContractExtractor Facade 类及其方法
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.services.document.llm_contract_extractor import (
    LLMContractExtractor,
    get_llm_contract_extractor,
)
from src.services.document.extractors.factory import reset_extractor


# ============================================================================
# LLMContractExtractor 基础测试
# ============================================================================

class TestLLMContractExtractor:
    """LLMContractExtractor Facade 类测试"""

    @pytest.fixture
    def extractor(self):
        """创建提取器实例（使用 reset 确保每次都是新的）"""
        reset_extractor()
        return LLMContractExtractor()

    def test_initialization(self, extractor):
        """测试提取器初始化 - 应该有适配器"""
        assert extractor.adapter is not None
        assert hasattr(extractor.adapter, 'extract')

    def test_singleton(self):
        """测试单例模式"""
        reset_extractor()
        extractor1 = get_llm_contract_extractor()
        extractor2 = get_llm_contract_extractor()
        assert extractor1 is extractor2

    def test_singleton_reset(self):
        """测试单例重置"""
        extractor1 = get_llm_contract_extractor()

        # 使用工厂提供的 reset_extractor() 函数重置工厂单例
        reset_extractor()

        # 重置 LLMContractExtractor 模块级单例
        import src.services.document.llm_contract_extractor as llm_module
        llm_module._llm_extractor = None

        extractor2 = get_llm_contract_extractor()

        # 验证重置后是不同的实例
        assert extractor1 is not extractor2


# ============================================================================
# extract_smart 方法测试
# ============================================================================

class TestExtractSmart:
    """extract_smart 方法测试"""

    @pytest.fixture
    def extractor(self):
        """创建提取器实例"""
        reset_extractor()
        return LLMContractExtractor()

    @pytest.fixture
    def sample_pdf(self, tmp_path):
        """创建临时 PDF 文件"""
        pdf_file = tmp_path / "test_contract.pdf"
        # 创建一个简单的文本文件伪装成 PDF（仅用于测试路径传递）
        pdf_file.write_text("%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF")
        return str(pdf_file)

    @pytest.mark.asyncio
    async def test_smart_chooses_vision_method(self, extractor, sample_pdf):
        """测试智能提取选择视觉方法"""
        # Mock adapter.extract() 方法
        with patch.object(extractor.adapter, 'extract', new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {
                "success": True,
                "extraction_method": "vision",
                "confidence": 0.95
            }

            result = await extractor.extract_smart(sample_pdf)

            assert result["success"] is True
            assert result["extraction_method"] == "vision"
            mock_extract.assert_called_once_with(sample_pdf, force_method=None)

    @pytest.mark.asyncio
    async def test_smart_forces_vision_method(self, extractor, sample_pdf):
        """测试强制使用视觉方法"""
        with patch.object(extractor.adapter, 'extract', new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {
                "success": True,
                "extraction_method": "vision",
            }

            result = await extractor.extract_smart(sample_pdf, force_method="vision")

            assert result["success"] is True
            mock_extract.assert_called_once_with(sample_pdf, force_method="vision")

    @pytest.mark.asyncio
    async def test_smart_adapter_error_handling(self, extractor, sample_pdf):
        """测试适配器错误处理"""
        with patch.object(extractor.adapter, 'extract', new_callable=AsyncMock) as mock_extract:
            mock_extract.side_effect = Exception("Adapter error")

            result = await extractor.extract_smart(sample_pdf)

            assert result["success"] is False
            assert "Adapter error" in result["error"]


# ============================================================================
# 适配器选择测试
# ============================================================================

class TestAdapterFactory:
    """测试工厂模式创建提取器"""

    def test_extractor_has_adapter(self):
        """测试提取器包含适配器"""
        reset_extractor()
        extractor = LLMContractExtractor()
        # 验证适配器是有效的
        assert hasattr(extractor.adapter, 'provider_name')
        assert hasattr(extractor.adapter, 'api_key_env_name')

    def test_adapter_is_singleton(self):
        """测试适配器使用工厂单例"""
        reset_extractor()
        from src.services.document.extractors.factory import get_llm_extractor as get_adapter

        adapter1 = get_adapter()
        adapter2 = get_adapter()
        assert adapter1 is adapter2

    def test_adapter_can_be_swapped(self):
        """测试可以通过配置切换适配器"""
        from src.services.document.extractors.factory import ExtractorFactory

        # 获取不同提供商的适配器
        glm_adapter = ExtractorFactory.get_extractor("glm")
        qwen_adapter = ExtractorFactory.get_extractor("qwen")
        deepseek_adapter = ExtractorFactory.get_extractor("deepseek")

        # 验证它们是不同的实例（不同的提供商）
        assert type(glm_adapter).__name__ != type(qwen_adapter).__name__
        assert type(glm_adapter).__name__ != type(deepseek_adapter).__name__


# ============================================================================
# 向后兼容性测试
# ============================================================================

class TestBackwardCompatibility:
    """测试向后兼容性"""

    @pytest.fixture
    def extractor(self):
        """创建提取器实例"""
        reset_extractor()
        return LLMContractExtractor()

    def test_has_adapter_attribute(self, extractor):
        """测试有 adapter 属性（新架构）"""
        assert hasattr(extractor, 'adapter')
        assert extractor.adapter is not None

    @pytest.mark.asyncio
    async def test_extract_smart_is_async(self, extractor):
        """测试 extract_smart 是异步方法"""
        import asyncio
        sample_path = "/fake/path.pdf"

        with patch.object(extractor.adapter, 'extract', new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {"success": True}

            # 验证可以 await
            result = await extractor.extract_smart(sample_path)
            assert result["success"] is True
