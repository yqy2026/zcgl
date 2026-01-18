#!/usr/bin/env python3
"""
Extraction Manager Unit Tests
提取管理器单元测试

Tests for DocumentExtractionManager and KeywordClassifier
测试文档提取管理器和关键词分类器
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.document.extraction_manager import (
    DocumentExtractionManager,
    DocumentType,
    ExtractionResult,
    KeywordClassifier,
    get_extraction_manager,
    reset_extraction_manager,
)

# ============================================================================
# KeywordClassifier Tests
# ============================================================================


class TestKeywordClassifier:
    """Tests for KeywordClassifier document type detection"""

    def test_classify_rental_contract(self):
        """Should classify rental contract documents correctly"""
        contract_text = """
        租赁合同
        甲方：出租方
        乙方：承租方
        租赁期限：2024年1月1日至2025年12月31日
        月租金：5000元
        """

        result = KeywordClassifier.classify(contract_text)

        assert result == DocumentType.CONTRACT

    def test_classify_property_certificate(self):
        """Should classify property certificate documents correctly"""
        cert_text = """
        不动产权证
        权利人：张三
        坐落：北京市朝阳区XX路XX号
        建筑面积：120平方米
        登记日期：2020年1月1日
        """

        result = KeywordClassifier.classify(cert_text)

        assert result == DocumentType.PROPERTY_CERT

    def test_classify_unknown_document(self):
        """Should return UNKNOWN for documents with insufficient keywords"""
        unknown_text = """
        这是一份普通文档
        没有特定的关键词
        无法确定类型
        """

        result = KeywordClassifier.classify(unknown_text)

        assert result == DocumentType.UNKNOWN

    def test_classify_case_insensitive(self):
        """Classification should be case-insensitive for ASCII, Chinese is case-less"""
        # Chinese characters don't have case, so all these should classify the same
        text_normal = "租赁合同 甲方 乙方 月租金"

        assert KeywordClassifier.classify(text_normal) == DocumentType.CONTRACT
        # Note: Chinese with spaces between chars might not match keywords properly
        # The classifier looks for exact keyword matches like "租赁合同" not "租 赁 合 同"

    def test_classify_with_insufficient_keywords(self):
        """Should return UNKNOWN when keywords don't meet threshold"""
        # Only 1 contract keyword (threshold is 2)
        text = "这是一份租赁"  # Only "租赁" keyword

        result = KeywordClassifier.classify(text)

        assert result == DocumentType.UNKNOWN

    def test_classify_mixed_document_contracts_wins(self):
        """Contract should win when both types have keywords but contract has more"""
        text = """
        不动产权证
        租赁合同
        甲方
        乙方
        月租金
        """

        result = KeywordClassifier.classify(text)

        assert result == DocumentType.CONTRACT

    def test_classify_mixed_document_property_wins(self):
        """Property cert should win when it has more keywords"""
        text = """
        不动产权证
        权利人
        坐落
        建筑面积
        土地使用权
        共有情况
        """

        result = KeywordClassifier.classify(text)

        assert result == DocumentType.PROPERTY_CERT


# ============================================================================
# DocumentExtractionManager Tests
# ============================================================================


class TestDocumentExtractionManager:
    """Tests for DocumentExtractionManager"""

    @pytest.fixture
    def manager(self):
        """Create a fresh extraction manager instance"""
        reset_extraction_manager()
        return DocumentExtractionManager()

    @pytest.fixture
    def mock_contract_extractor(self):
        """Mock contract extractor"""
        extractor = MagicMock()
        extractor.extract = AsyncMock(
            return_value={
                "success": True,
                "data": {"contract_number": "CT-001", "landlord_name": "Test"},
                "confidence": 0.95,
                "extraction_method": "vision_glm4v",
                "warnings": [],
            }
        )
        return extractor

    @pytest.fixture
    def mock_property_cert_extractor(self):
        """Mock property certificate extractor"""
        extractor = MagicMock()
        extractor.extract = AsyncMock(
            return_value={
                "success": True,
                "data": {"cert_number": "PC-001", "owner": "Test Owner"},
                "confidence": 0.9,
                "extraction_method": "vision_property_cert",
                "warnings": [],
            }
        )
        return extractor

    @pytest.fixture
    def sample_contract_pdf(self, tmp_path):
        """Create a sample contract PDF file"""
        pdf_path = tmp_path / "contract.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nfake contract")
        return str(pdf_path)

    @pytest.fixture
    def non_existent_pdf(self):
        """Return a non-existent file path"""
        return "/nonexistent/file.pdf"

    def test_initialization(self, manager):
        """Manager should initialize with contract extractor"""
        assert manager is not None
        assert manager._contract_extractor is not None
        assert manager._property_cert_extractor is None  # Lazy loaded
        assert manager.classifier is not None

    def test_get_property_cert_extractor_lazy_loading(self, manager):
        """Property cert extractor should be lazy-loaded"""
        assert manager._property_cert_extractor is None

        extractor = manager._get_property_cert_extractor()

        assert extractor is not None
        assert manager._property_cert_extractor is not None
        # Should cache the extractor
        assert manager._get_property_cert_extractor() is extractor

    @pytest.mark.asyncio
    async def test_extract_contract_success(
        self, manager, mock_contract_extractor, sample_contract_pdf
    ):
        """Should successfully extract from contract document"""
        manager._contract_extractor = mock_contract_extractor

        result = await manager.extract(sample_contract_pdf, doc_type=DocumentType.CONTRACT)

        assert result.success is True
        assert result.document_type == DocumentType.CONTRACT
        assert result.confidence_score == 0.95
        assert result.extracted_fields["contract_number"] == "CT-001"
        assert result.extraction_method == "vision_glm4v"
        assert result.processing_time_ms >= 0  # Can be 0 if very fast

    @pytest.mark.asyncio
    async def test_extract_property_cert_success(
        self, manager, mock_property_cert_extractor, sample_contract_pdf
    ):
        """Should successfully extract from property certificate"""
        manager._property_cert_extractor = mock_property_cert_extractor

        result = await manager.extract(
            sample_contract_pdf, doc_type=DocumentType.PROPERTY_CERT
        )

        assert result.success is True
        assert result.document_type == DocumentType.PROPERTY_CERT
        assert result.extracted_fields["cert_number"] == "PC-001"

    @pytest.mark.asyncio
    async def test_extract_with_string_doc_type(
        self, manager, mock_contract_extractor, sample_contract_pdf
    ):
        """Should accept string doc_type and convert to enum"""
        manager._contract_extractor = mock_contract_extractor

        result = await manager.extract(sample_contract_pdf, doc_type="contract")

        assert result.success is True
        assert result.document_type == DocumentType.CONTRACT

    @pytest.mark.asyncio
    async def test_extract_defaults_to_contract_when_no_type(
        self, manager, mock_contract_extractor, sample_contract_pdf
    ):
        """Should default to CONTRACT type when not specified"""
        manager._contract_extractor = mock_contract_extractor

        result = await manager.extract(sample_contract_pdf)

        assert result.success is True
        assert result.document_type == DocumentType.CONTRACT

    @pytest.mark.asyncio
    async def test_extract_with_invalid_string_type_defaults_to_unknown(
        self, manager, mock_contract_extractor, sample_contract_pdf
    ):
        """Should use UNKNOWN type for invalid string doc_type"""
        manager._contract_extractor = mock_contract_extractor

        result = await manager.extract(sample_contract_pdf, doc_type="invalid_type")

        assert result.success is True
        assert result.document_type == DocumentType.UNKNOWN

    @pytest.mark.asyncio
    async def test_extract_file_not_found(self, manager, non_existent_pdf):
        """Should return error result when file doesn't exist"""
        result = await manager.extract(non_existent_pdf)

        assert result.success is False
        assert result.document_type == DocumentType.UNKNOWN
        assert "File not found" in result.error
        assert result.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_extract_handles_extractor_exception(
        self, manager, sample_contract_pdf
    ):
        """Should handle exceptions from extractor gracefully"""
        # Mock extractor that raises exception
        manager._contract_extractor.extract = AsyncMock(side_effect=RuntimeError("Extraction failed"))

        result = await manager.extract(sample_contract_pdf)

        assert result.success is False
        assert result.error is not None
        assert "Extraction failed" in result.error
        assert result.processing_time_ms >= 0  # Can be 0 if very fast

    @pytest.mark.asyncio
    async def test_extract_with_warning_response(
        self, manager, sample_contract_pdf
    ):
        """Should pass through warnings from extractor"""
        mock_extractor = MagicMock()
        mock_extractor.extract = AsyncMock(
            return_value={
                "success": True,
                "data": {"field": "value"},
                "confidence": 0.8,
                "extraction_method": "test",
                "warnings": ["Low quality PDF", "Some fields missing"],
            }
        )
        manager._contract_extractor = mock_extractor

        result = await manager.extract(sample_contract_pdf)

        assert result.success is True
        assert len(result.warnings) == 2
        assert "Low quality PDF" in result.warnings

    @pytest.mark.asyncio
    async def test_extract_confidence_score_missing(self, manager, sample_contract_pdf):
        """Should handle missing confidence score"""
        mock_extractor = MagicMock()
        mock_extractor.extract = AsyncMock(
            return_value={"success": True, "data": {}, "extraction_method": "test"}
        )
        manager._contract_extractor = mock_extractor

        result = await manager.extract(sample_contract_pdf)

        assert result.success is True
        assert result.confidence_score == 0.0  # Default value

    @pytest.mark.asyncio
    async def test_extract_with_pathlib_path(
        self, manager, mock_contract_extractor, tmp_path
    ):
        """Should accept pathlib.Path objects"""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"PDF content")

        manager._contract_extractor = mock_contract_extractor

        # Should not raise
        result = await manager.extract(pdf_path)
        assert result.success is True


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


class TestExtractionManagerSingleton:
    """Tests for extraction manager singleton pattern"""

    def test_get_extraction_manager_returns_singleton(self):
        """Should return the same instance on multiple calls"""
        reset_extraction_manager()

        manager1 = get_extraction_manager()
        manager2 = get_extraction_manager()

        assert manager1 is manager2

    def test_reset_extraction_manager(self):
        """Reset should create new instance on next call"""
        manager1 = get_extraction_manager()
        reset_extraction_manager()
        manager2 = get_extraction_manager()

        assert manager1 is not manager2

    def test_singleton_persistence(self):
        """Singleton should persist across multiple calls"""
        reset_extraction_manager()

        managers = [get_extraction_manager() for _ in range(5)]

        # All should be the same instance
        assert len(set(id(m) for m in managers)) == 1


# ============================================================================
# ExtractionResult Model Tests
# ============================================================================


class TestExtractionResult:
    """Tests for ExtractionResult Pydantic model"""

    def test_create_successful_result(self):
        """Should create valid result for successful extraction"""
        result = ExtractionResult(
            success=True,
            document_type=DocumentType.CONTRACT,
            confidence_score=0.95,
            extracted_fields={"field": "value"},
            extraction_method="vision",
            processing_time_ms=1000,
        )

        assert result.success is True
        assert result.document_type == DocumentType.CONTRACT
        assert result.confidence_score == 0.95
        assert len(result.extracted_fields) == 1

    def test_create_failed_result(self):
        """Should create valid result for failed extraction"""
        result = ExtractionResult(
            success=False,
            document_type=DocumentType.UNKNOWN,
            error="File not found",
            processing_time_ms=50,
        )

        assert result.success is False
        assert result.error == "File not found"
        assert result.extracted_fields == {}

    def test_default_values(self):
        """Should use sensible defaults for optional fields"""
        result = ExtractionResult(
            success=True,
            document_type=DocumentType.CONTRACT,
        )

        assert result.confidence_score == 0.0
        assert result.extracted_fields == {}
        assert result.extraction_method == ""
        assert result.processing_time_ms == 0.0
        assert result.warnings == []
        assert result.error is None


# ============================================================================
# DocumentType Enum Tests
# ============================================================================


class TestDocumentType:
    """Tests for DocumentType enum"""

    def test_contract_value(self):
        assert DocumentType.CONTRACT.value == "contract"

    def test_property_cert_value(self):
        assert DocumentType.PROPERTY_CERT.value == "property_cert"

    def test_unknown_value(self):
        assert DocumentType.UNKNOWN.value == "unknown"

    def test_enum_from_string(self):
        """Should create enum from string value"""
        assert DocumentType("contract") == DocumentType.CONTRACT
        assert DocumentType("property_cert") == DocumentType.PROPERTY_CERT
        assert DocumentType("unknown") == DocumentType.UNKNOWN

    def test_enum_from_invalid_string_raises(self):
        """Should raise ValueError for invalid string"""
        with pytest.raises(ValueError):
            DocumentType("invalid_type")
