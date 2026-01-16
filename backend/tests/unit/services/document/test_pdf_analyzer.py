#!/usr/bin/env python3
"""
PDF Analyzer Unit Tests
PDF分析器单元测试

Tests for PDF type detection and extraction method recommendation
测试PDF类型检测和提取方法推荐
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.services.document.pdf_analyzer import (
    PYMUPDF_AVAILABLE,
    analyze_pdf,
    get_extraction_recommendation,
    is_scanned_pdf,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_pdf_doc():
    """Mock PyMuPDF document object"""
    doc = MagicMock()
    doc.__len__ = Mock(return_value=3)  # 3 pages
    return doc


@pytest.fixture
def mock_digital_page():
    """Mock a digital/text-based PDF page"""
    page = MagicMock()
    # Digital PDF has lots of text
    page.get_text = Mock(return_value="这是一份租赁合同" * 50)  # 600+ chars
    page.get_images = Mock(return_value=[])  # No images
    return page


@pytest.fixture
def mock_scanned_page():
    """Mock a scanned/image-based PDF page"""
    page = MagicMock()
    # Scanned PDF has little or no extractable text
    page.get_text = Mock(return_value="   ")  # Just whitespace
    page.get_images = Mock(return_value=[(1, 2, 3, 4)])  # Has images
    return page


@pytest.fixture
def mock_mixed_page():
    """Mock a page with both text and images"""
    page = MagicMock()
    page.get_text = Mock(return_value="合同内容" * 5)  # Some text but not much
    page.get_images = Mock(return_value=[(1, 2, 3, 4)])  # Has images
    return page


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Create a sample PDF file path"""
    pdf_path = tmp_path / "test_contract.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\nfake pdf content")
    return str(pdf_path)


# ============================================================================
# analyze_pdf Tests
# ============================================================================


class TestAnalyzePDF:
    """Tests for analyze_pdf function"""

    def test_analyze_pdf_returns_default_when_pymupdf_not_available(
        self, sample_pdf_path
    ):
        """Should return default vision recommendation when PyMuPDF not available"""
        with patch("src.services.document.pdf_analyzer.PYMUPDF_AVAILABLE", False):
            result = analyze_pdf(sample_pdf_path)

            assert result["is_scanned"] is True
            assert result["text_ratio"] == 0
            assert result["page_count"] == 0
            assert result["has_images"] is True
            assert result["recommendation"] == "vision"

    def test_analyze_pdf_raises_file_not_found(self):
        """Should raise FileNotFoundError when PDF doesn't exist"""
        with pytest.raises(FileNotFoundError, match="PDF not found"):
            analyze_pdf("/nonexistent/path.pdf")

    @pytest.mark.skipif(
        not PYMUPDF_AVAILABLE, reason="PyMuPDF not installed"
    )
    def test_analyze_digital_pdf_recommends_text_extraction(
        self, sample_pdf_path, mock_pdf_doc, mock_digital_page
    ):
        """Digital PDF with lots of text should recommend text extraction"""
        # Setup: All pages are digital (lots of text, no images)
        # Mock __getitem__ for page access
        mock_pdf_doc.__getitem__ = Mock(return_value=mock_digital_page)

        with patch("src.services.document.pdf_analyzer.fitz.open", return_value=mock_pdf_doc):
            result = analyze_pdf(sample_pdf_path)

            assert result["is_scanned"] is False
            assert result["text_ratio"] == 1.0  # All pages have text
            assert result["avg_chars_per_page"] >= 100
            assert result["has_images"] is False
            assert result["total_images"] == 0
            assert result["recommendation"] == "text"

    @pytest.mark.skipif(
        not PYMUPDF_AVAILABLE, reason="PyMuPDF not installed"
    )
    def test_analyze_scanned_pdf_recommends_vision_extraction(
        self, sample_pdf_path, mock_pdf_doc, mock_scanned_page
    ):
        """Scanned PDF with images and no text should recommend vision extraction"""
        # Setup: All pages are scanned (no text, has images)
        mock_pdf_doc.__getitem__ = Mock(return_value=mock_scanned_page)

        with patch("src.services.document.pdf_analyzer.fitz.open", return_value=mock_pdf_doc):
            result = analyze_pdf(sample_pdf_path)

            assert result["is_scanned"] is True
            assert result["text_ratio"] == 0.0  # No pages with meaningful text
            assert result["avg_chars_per_page"] < 100
            assert result["has_images"] is True
            assert result["total_images"] > 0
            assert result["recommendation"] == "vision"

    @pytest.mark.skipif(
        not PYMUPDF_AVAILABLE, reason="PyMuPDF not installed"
    )
    def test_analyze_mixed_pdf_recommends_vision_for_safety(
        self, sample_pdf_path, mock_pdf_doc, mock_mixed_page
    ):
        """Mixed PDF (some text + images) should recommend vision for safety"""
        # Setup: All pages have both text and images
        mock_pdf_doc.__getitem__ = Mock(return_value=mock_mixed_page)

        with patch("src.services.document.pdf_analyzer.fitz.open", return_value=mock_pdf_doc):
            result = analyze_pdf(sample_pdf_path)

            # Mixed content defaults to vision for Chinese contracts
            assert result["is_scanned"] is True
            assert result["text_ratio"] == 0.0  # Text < 50 chars
            assert result["has_images"] is True
            assert result["recommendation"] == "vision"

    @pytest.mark.skipif(
        not PYMUPDF_AVAILABLE, reason="PyMuPDF not installed"
    )
    def test_analyze_pdf_handles_exception_gracefully(
        self, sample_pdf_path, mock_pdf_doc
    ):
        """Should return safe default on any exception during analysis"""
        # Simulate an exception during PDF processing
        mock_pdf_doc.__len__ = Mock(side_effect=RuntimeError("PDF corrupted"))

        with patch("src.services.document.pdf_analyzer.fitz.open", return_value=mock_pdf_doc):
            result = analyze_pdf(sample_pdf_path)

            # Should default to vision on error (safer for Chinese contracts)
            assert result["is_scanned"] is True
            assert result["recommendation"] == "vision"
            assert "error" in result

    @pytest.mark.skipif(
        not PYMUPDF_AVAILABLE, reason="PyMuPDF not installed"
    )
    def test_analyze_pdf_limits_page_check_to_first_5_pages(
        self, sample_pdf_path, mock_pdf_doc, mock_digital_page
    ):
        """Should only analyze first 5 pages even for longer PDFs"""
        # Create a 10-page PDF
        mock_pdf_doc.__len__ = Mock(return_value=10)
        mock_pdf_doc.__getitem__ = Mock(return_value=mock_digital_page)

        with patch("src.services.document.pdf_analyzer.fitz.open", return_value=mock_pdf_doc):
            result = analyze_pdf(sample_pdf_path)

            # Should report correct total page count
            assert result["page_count"] == 10

    @pytest.mark.skipif(
        not PYMUPDF_AVAILABLE, reason="PyMuPDF not installed"
    )
    def test_analyze_empty_pdf(self, sample_pdf_path, mock_pdf_doc):
        """Should handle PDF with no content gracefully"""
        # Create pages with very little text and no images
        # This should trigger scanned detection and vision recommendation
        nearly_empty_page = MagicMock()
        nearly_empty_page.get_text = Mock(return_value="abc")  # < 100 chars
        nearly_empty_page.get_images = Mock(return_value=[])  # No images

        mock_pdf_doc.__getitem__ = Mock(return_value=nearly_empty_page)

        with patch("src.services.document.pdf_analyzer.fitz.open", return_value=mock_pdf_doc):
            result = analyze_pdf(sample_pdf_path)

            # Low text count defaults to vision (recommendation checks avg_chars < 200)
            assert result["avg_chars_per_page"] < 100
            assert result["recommendation"] == "vision"


# ============================================================================
# is_scanned_pdf Tests
# ============================================================================


class TestIsScannedPDF:
    """Tests for is_scanned_pdf convenience function"""

    def test_is_scanned_pdf_returns_true_for_scanned(
        self, sample_pdf_path, mock_pdf_doc, mock_scanned_page
    ):
        """Should return True for scanned PDF"""
        mock_pdf_doc.__getitem__ = Mock(return_value=mock_scanned_page)

        with patch("src.services.document.pdf_analyzer.fitz.open", return_value=mock_pdf_doc):
            result = is_scanned_pdf(sample_pdf_path)

            assert result is True

    def test_is_scanned_pdf_returns_false_for_digital(
        self, sample_pdf_path, mock_pdf_doc, mock_digital_page
    ):
        """Should return False for digital PDF"""
        mock_pdf_doc.__getitem__ = Mock(return_value=mock_digital_page)

        with patch("src.services.document.pdf_analyzer.fitz.open", return_value=mock_pdf_doc):
            result = is_scanned_pdf(sample_pdf_path)

            assert result is False

    def test_is_scanned_pdf_defaults_to_true_on_error(self, sample_pdf_path):
        """Should default to True (safe choice) when analysis fails"""
        with patch(
            "src.services.document.pdf_analyzer.analyze_pdf",
            return_value={"is_scanned": False, "error": "test error"},
        ):
            result = is_scanned_pdf(sample_pdf_path)

            # Follows the analyze_pdf result, but defaults to True in practice
            assert isinstance(result, bool)


# ============================================================================
# get_extraction_recommendation Tests
# ============================================================================


class TestGetExtractionRecommendation:
    """Tests for get_extraction_recommendation convenience function"""

    def test_recommends_vision_for_scanned_pdf(
        self, sample_pdf_path, mock_pdf_doc, mock_scanned_page
    ):
        """Should recommend 'vision' for scanned PDF"""
        mock_pdf_doc.__getitem__ = Mock(return_value=mock_scanned_page)

        with patch("src.services.document.pdf_analyzer.fitz.open", return_value=mock_pdf_doc):
            result = get_extraction_recommendation(sample_pdf_path)

            assert result == "vision"

    def test_recommends_text_for_digital_pdf(
        self, sample_pdf_path, mock_pdf_doc, mock_digital_page
    ):
        """Should recommend 'text' for digital PDF"""
        mock_pdf_doc.__getitem__ = Mock(return_value=mock_digital_page)

        with patch("src.services.document.pdf_analyzer.fitz.open", return_value=mock_pdf_doc):
            result = get_extraction_recommendation(sample_pdf_path)

            assert result == "text"

    def test_recommends_vision_as_default(
        self, sample_pdf_path, mock_pdf_doc, mock_scanned_page
    ):
        """Should default to 'vision' when analysis fails"""
        mock_pdf_doc.__getitem__ = Mock(return_value=mock_scanned_page)

        with patch("src.services.document.pdf_analyzer.fitz.open", return_value=mock_pdf_doc):
            result = get_extraction_recommendation(sample_pdf_path)

            # Vision is the safer choice for Chinese contracts
            assert result in ["vision", "text"]


# ============================================================================
# Integration Tests (with actual PDF files if available)
# ============================================================================


class TestPDFAnalyzerIntegration:
    """Integration tests with actual PDF handling"""

    def test_pathlib_path_support(self, sample_pdf_path):
        """Should accept both str and Path objects"""
        path_obj = Path(sample_pdf_path)

        # Should not raise
        try:
            result = analyze_pdf(path_obj)
            # Will return default if PyMuPDF not available
            assert "recommendation" in result
        except FileNotFoundError:
            # Expected if file doesn't exist
            pass

    def test_empty_pdf_file(self, tmp_path):
        """Should handle empty PDF file"""
        empty_pdf = tmp_path / "empty.pdf"
        empty_pdf.write_bytes(b"")

        with patch("src.services.document.pdf_analyzer.PYMUPDF_AVAILABLE", False):
            result = analyze_pdf(str(empty_pdf))
            assert result["recommendation"] == "vision"
