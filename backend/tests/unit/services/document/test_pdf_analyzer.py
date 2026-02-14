from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.services.document.pdf_analyzer import (
    analyze_pdf,
    get_extraction_recommendation,
    is_scanned_pdf,
)


@pytest.fixture
def mock_pdf_doc():
    doc = MagicMock()
    doc.__len__.return_value = 3
    doc.__enter__.return_value = doc
    return doc


@pytest.fixture
def mock_digital_page():
    page = MagicMock()
    page.get_text = Mock(return_value="这是一份租赁合同" * 50)
    page.get_images = Mock(return_value=[])
    return page


@pytest.fixture
def mock_scanned_page():
    page = MagicMock()
    page.get_text = Mock(return_value=" ")
    page.get_images = Mock(return_value=[(1, 2, 3, 4)])
    return page


@pytest.fixture
def mock_mixed_page():
    page = MagicMock()
    page.get_text = Mock(return_value="合同内容" * 5)
    page.get_images = Mock(return_value=[(1, 2, 3, 4)])
    return page


@pytest.fixture
def sample_pdf_path(tmp_path):
    pdf_path = tmp_path / "test_contract.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%Test PDF content for unit tests")
    return str(pdf_path)


@pytest.fixture
def mock_pymupdf():
    with patch("src.services.document.pdf_analyzer.PYMUPDF_AVAILABLE", True):
        with patch("src.services.document.pdf_analyzer.fitz") as mock_fitz:
            yield mock_fitz


class TestAnalyzePDF:
    def test_analyze_pdf_returns_default_when_pymupdf_not_available(
        self, sample_pdf_path
    ):
        with patch("src.services.document.pdf_analyzer.PYMUPDF_AVAILABLE", False):
            result = analyze_pdf(sample_pdf_path)

        assert result["is_scanned"] is True
        assert result["text_ratio"] == 0
        assert result["page_count"] == 0
        assert result["has_images"] is True
        assert result["recommendation"] == "vision"

    def test_analyze_pdf_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="PDF not found"):
            analyze_pdf("/nonexistent/path.pdf")

    def test_analyze_digital_pdf_recommends_text_extraction(
        self, sample_pdf_path, mock_pdf_doc, mock_digital_page, mock_pymupdf
    ):
        mock_pdf_doc.__getitem__.return_value = mock_digital_page
        mock_pymupdf.open.return_value = mock_pdf_doc

        result = analyze_pdf(sample_pdf_path)

        assert result["is_scanned"] is False
        assert result["text_ratio"] == 1.0
        assert result["avg_chars_per_page"] >= 100
        assert result["has_images"] is False
        assert result["total_images"] == 0
        assert result["recommendation"] == "text"

    def test_analyze_scanned_pdf_recommends_vision_extraction(
        self, sample_pdf_path, mock_pdf_doc, mock_scanned_page, mock_pymupdf
    ):
        mock_pdf_doc.__getitem__.return_value = mock_scanned_page
        mock_pymupdf.open.return_value = mock_pdf_doc

        result = analyze_pdf(sample_pdf_path)

        assert result["is_scanned"] is True
        assert result["text_ratio"] == 0.0
        assert result["avg_chars_per_page"] < 100
        assert result["has_images"] is True
        assert result["total_images"] > 0
        assert result["recommendation"] == "vision"

    def test_analyze_mixed_pdf_recommends_vision_for_safety(
        self, sample_pdf_path, mock_pdf_doc, mock_mixed_page, mock_pymupdf
    ):
        mock_pdf_doc.__getitem__.return_value = mock_mixed_page
        mock_pymupdf.open.return_value = mock_pdf_doc

        result = analyze_pdf(sample_pdf_path)

        assert result["is_scanned"] is True
        assert result["text_ratio"] == 0.0
        assert result["has_images"] is True
        assert result["recommendation"] == "vision"

    def test_analyze_pdf_handles_exception_gracefully(
        self, sample_pdf_path, mock_pymupdf
    ):
        mock_pymupdf.open.side_effect = RuntimeError("PDF corrupted")

        result = analyze_pdf(sample_pdf_path)

        assert result["is_scanned"] is True
        assert result["recommendation"] == "vision"
        assert "error" in result

    def test_analyze_pdf_limits_page_check_to_first_5_pages(
        self, sample_pdf_path, mock_pdf_doc, mock_digital_page, mock_pymupdf
    ):
        mock_pdf_doc.__len__.return_value = 10
        mock_pdf_doc.__getitem__.return_value = mock_digital_page
        mock_pymupdf.open.return_value = mock_pdf_doc

        result = analyze_pdf(sample_pdf_path)

        assert result["page_count"] == 10
        assert mock_pdf_doc.__getitem__.call_count == 5


class TestIsScannedPDF:
    def test_is_scanned_pdf_returns_true_for_scanned(
        self, sample_pdf_path, mock_pdf_doc, mock_scanned_page, mock_pymupdf
    ):
        mock_pdf_doc.__getitem__.return_value = mock_scanned_page
        mock_pymupdf.open.return_value = mock_pdf_doc

        result = is_scanned_pdf(sample_pdf_path)
        assert result is True

    def test_is_scanned_pdf_returns_false_for_digital(
        self, sample_pdf_path, mock_pdf_doc, mock_digital_page, mock_pymupdf
    ):
        mock_pdf_doc.__getitem__.return_value = mock_digital_page
        mock_pymupdf.open.return_value = mock_pdf_doc

        result = is_scanned_pdf(sample_pdf_path)
        assert result is False

    def test_is_scanned_pdf_defaults_to_boolean_on_error(self, sample_pdf_path):
        with patch(
            "src.services.document.pdf_analyzer.analyze_pdf",
            return_value={"is_scanned": False, "error": "test error"},
        ):
            result = is_scanned_pdf(sample_pdf_path)

        assert isinstance(result, bool)


class TestGetExtractionRecommendation:
    def test_recommends_vision_for_scanned_pdf(
        self, sample_pdf_path, mock_pdf_doc, mock_scanned_page, mock_pymupdf
    ):
        mock_pdf_doc.__getitem__.return_value = mock_scanned_page
        mock_pymupdf.open.return_value = mock_pdf_doc

        result = get_extraction_recommendation(sample_pdf_path)
        assert result == "vision"

    def test_recommends_text_for_digital_pdf(
        self, sample_pdf_path, mock_pdf_doc, mock_digital_page, mock_pymupdf
    ):
        mock_pdf_doc.__getitem__.return_value = mock_digital_page
        mock_pymupdf.open.return_value = mock_pdf_doc

        result = get_extraction_recommendation(sample_pdf_path)
        assert result == "text"


class TestPDFAnalyzerIntegration:
    def test_pathlib_path_support(self, sample_pdf_path):
        path_obj = Path(sample_pdf_path)
        with patch("src.services.document.pdf_analyzer.PYMUPDF_AVAILABLE", False):
            result = analyze_pdf(path_obj)
        assert "recommendation" in result

    def test_empty_pdf_file_defaults_to_vision_when_no_pymupdf(self, tmp_path):
        empty_pdf = tmp_path / "empty.pdf"
        empty_pdf.write_bytes(b"")

        with patch("src.services.document.pdf_analyzer.PYMUPDF_AVAILABLE", False):
            result = analyze_pdf(str(empty_pdf))
        assert result["recommendation"] == "vision"
