"""
Comprehensive Unit Tests for PDF Upload API Routes (src/api/v1/documents/pdf_upload.py)

This test module covers all endpoints in the pdf_upload router to achieve 70%+ coverage:

Endpoints Tested:
1. POST /upload - Upload PDF file and begin processing
2. POST /upload_and_extract - Upload and extract PDF (V1 compatible)

Testing Approach:
- Mock all dependencies (services, database, file operations, error handlers)
- Test successful responses and error scenarios
- Test request validation
- Test edge cases (file size, type validation, etc.)
- Test with and without enhanced error handler
"""

import io
from unittest.mock import AsyncMock, MagicMock, Mock, mock_open, patch

import pytest
from fastapi import UploadFile

from src.core.exception_handler import BaseBusinessError

pytestmark = pytest.mark.api

mock_current_user = MagicMock()
mock_current_user.id = "test-user-id"
mock_current_user.username = "testuser"
mock_current_user.is_active = True


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_pdf_file():
    """Create mock PDF upload file"""
    file = MagicMock(spec=UploadFile)
    file.filename = "test_document.pdf"
    file.content_type = "application/pdf"
    # Use smaller content to avoid polluting test output
    content_bytes = b"%PDF-1.4\n%Test PDF content for unit tests\n"
    file.file = io.BytesIO(content_bytes)
    file.size = len(content_bytes)
    file.read = AsyncMock(side_effect=[content_bytes, content_bytes, b""])
    file.seek = AsyncMock(return_value=None)
    return file


@pytest.fixture
def mock_large_pdf_file():
    """Create mock PDF file exceeding size limit (>50MB)"""
    file = MagicMock(spec=UploadFile)
    file.filename = "large_document.pdf"
    file.content_type = "application/pdf"
    header = b"%PDF-1.4\n" + b"x" * (2048 - 9)
    large_content = b"x" * (51 * 1024 * 1024)  # 51MB
    file.file = io.BytesIO(header)
    file.size = 51 * 1024 * 1024
    file.read = AsyncMock(side_effect=[header, large_content, b""])
    file.seek = AsyncMock(return_value=None)
    return file


@pytest.fixture
def mock_non_pdf_file():
    """Create mock non-PDF file"""
    file = MagicMock(spec=UploadFile)
    file.filename = "test.txt"
    file.content_type = "text/plain"
    content_bytes = b"not a pdf"
    file.file = io.BytesIO(content_bytes)
    file.size = len(content_bytes)
    file.read = AsyncMock(side_effect=[content_bytes, content_bytes, b""])
    file.seek = AsyncMock(return_value=None)
    return file


@pytest.fixture
def mock_pdf_import_service():
    """Create mock PDFImportService"""
    service = MagicMock()
    service.process_pdf_file = AsyncMock(
        return_value={
            "success": True,
            "session_id": "test-session-123",
            "message": "PDF processing started",
        }
    )
    return service


@pytest.fixture
def mock_session_service():
    """Create mock PDFSessionService"""
    service = MagicMock()

    mock_session = MagicMock()
    mock_session.session_id = "test-session-123"
    mock_session.original_filename = "test_document.pdf"

    service.create_session = AsyncMock(return_value=mock_session)
    return service


@pytest.fixture
def mock_enhanced_error_handler():
    """Create mock enhanced error handler"""
    handler = MagicMock()
    handler.max_file_size_mb = 50
    handler.handle_error = MagicMock(
        return_value={
            "error": "Test error message",
            "suggested_action": "Test action",
        }
    )
    return handler


@pytest.fixture
def mock_optional_services():
    """Create mock optional services container"""
    optional = MagicMock()
    optional.pdf_session_service = None
    optional.pdf_processing_service = None
    optional.enhanced_error_handler = None
    return optional


@pytest.fixture
def mock_optional_services_with_all(mock_session_service, mock_enhanced_error_handler):
    """Create mock optional services with all services available"""
    optional = MagicMock()
    optional.pdf_session_service = mock_session_service

    # Create mock pdf_processing_service
    mock_pdf_processing = MagicMock()
    mock_pdf_processing.extract_text_from_pdf = AsyncMock(
        return_value={"success": True, "text": "Sample text"}
    )
    optional.pdf_processing_service = mock_pdf_processing

    optional.enhanced_error_handler = mock_enhanced_error_handler
    return optional


@pytest.fixture(autouse=True)
def mock_pdf_upload_open(monkeypatch):
    """Mock file writes in pdf_upload to avoid filesystem access."""
    m_open = mock_open()
    m_open.return_value.write = MagicMock()
    monkeypatch.setattr("src.api.v1.documents.pdf_upload.open", m_open, raising=False)
    return m_open


# ============================================================================
# Test: POST /upload - Upload PDF File
# ============================================================================


class TestUploadPdfFile:
    """Tests for POST /upload endpoint"""

    @pytest.mark.asyncio
    async def test_upload_pdf_success(
        self,
        mock_db,
        mock_pdf_file,
        mock_pdf_import_service,
        mock_optional_services_with_all,
    ):
        """Test successful PDF upload with all services"""
        from src.api.v1.documents.pdf_upload import upload_pdf_file

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services_with_all

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_service_class:
                mock_service_class.return_value = mock_pdf_import_service

                # Mock Path operations
                with patch("src.api.v1.documents.pdf_upload.Path") as mock_path_class:
                    mock_temp_dir = MagicMock()
                    mock_temp_file = MagicMock()
                    mock_path_class.return_value = mock_temp_dir
                    mock_temp_dir.__truediv__ = Mock(return_value=mock_temp_file)
                    mock_temp_dir.mkdir = MagicMock()
                    mock_temp_file.unlink = MagicMock()

                    # Mock file operations
                    m_open = mock_open()
                    m_open.return_value.write = MagicMock()

                    # Mock the file_security import
                    with patch(
                        "src.utils.file_security.generate_safe_filename",
                        return_value="safe_test.pdf",
                    ):
                        result = await upload_pdf_file(
                            file=mock_pdf_file,
                            prefer_markitdown=False,
                            prefer_ocr=False,
                            organization_id=1,
                            db=mock_db,
                            pdf_service=mock_pdf_import_service,
                            optional=mock_optional_services_with_all,
                            current_user=mock_current_user,
                        )

        assert result.success is True
        assert result.session_id.startswith("session-")
        assert result.message == "PDF文件上传成功，正在处理中"
        assert result.estimated_time == "30-60秒"

    @pytest.mark.asyncio
    async def test_upload_pdf_without_session_service(
        self, mock_db, mock_pdf_file, mock_optional_services
    ):
        """Test PDF upload when session service is unavailable"""
        from src.api.v1.documents.pdf_upload import upload_pdf_file

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service.process_pdf_file = AsyncMock(return_value=None)
                mock_service_class.return_value = mock_service

                with patch("src.api.v1.documents.pdf_upload.Path") as mock_path_class:
                    mock_temp_dir = MagicMock()
                    mock_temp_file = MagicMock()
                    mock_path_class.return_value = mock_temp_dir
                    mock_temp_dir.__truediv__ = Mock(return_value=mock_temp_file)
                    mock_temp_dir.mkdir = MagicMock()

                    result = await upload_pdf_file(
                        file=mock_pdf_file,
                        prefer_markitdown=False,
                        prefer_ocr=False,
                        organization_id=1,
                        db=mock_db,
                        pdf_service=mock_service,
                        optional=mock_optional_services,
                        current_user=mock_current_user,
                    )

        assert result.success is True
        assert result.message == "PDF文件上传成功，正在处理中"

    @pytest.mark.asyncio
    async def test_upload_pdf_invalid_file_type_without_enhanced_handler(
        self, mock_db, mock_non_pdf_file, mock_optional_services
    ):
        """Test upload with invalid file type without enhanced error handler"""
        from src.api.v1.documents.pdf_upload import upload_pdf_file

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service.process_pdf_file = AsyncMock(return_value=None)
                mock_service_class.return_value = mock_service

                with patch("src.security.file_validation.logger.warning"):
                    with pytest.raises(BaseBusinessError) as exc_info:
                        await upload_pdf_file(
                            file=mock_non_pdf_file,
                            prefer_markitdown=False,
                            prefer_ocr=False,
                            organization_id=None,
                            db=mock_db,
                            pdf_service=mock_service,
                            optional=mock_optional_services,
                            current_user=mock_current_user,
                        )

        assert exc_info.value.status_code == 422
        assert "不支持的文件扩展名" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_upload_pdf_invalid_file_type_with_enhanced_handler(
        self, mock_db, mock_non_pdf_file, mock_optional_services_with_all
    ):
        """Test upload with invalid file type with enhanced error handler"""
        from src.api.v1.documents.pdf_upload import upload_pdf_file

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services_with_all

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service.process_pdf_file = AsyncMock(return_value=None)
                mock_service_class.return_value = mock_service

                with patch("src.security.file_validation.logger.warning"):
                    with pytest.raises(BaseBusinessError) as exc_info:
                        await upload_pdf_file(
                            file=mock_non_pdf_file,
                            prefer_markitdown=False,
                            prefer_ocr=False,
                            organization_id=None,
                            db=mock_db,
                            pdf_service=mock_service,
                            optional=mock_optional_services_with_all,
                            current_user=mock_current_user,
                        )

        assert exc_info.value.status_code == 422
        assert "不支持的文件扩展名" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_upload_pdf_file_too_large_without_enhanced_handler(
        self, mock_db, mock_large_pdf_file, mock_optional_services
    ):
        """Test upload with file exceeding size limit without enhanced handler"""
        from src.api.v1.documents.pdf_upload import upload_pdf_file

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service.process_pdf_file = AsyncMock(return_value=None)
                mock_service_class.return_value = mock_service

                with patch("src.api.v1.documents.pdf_upload.Path") as mock_path_class:
                    mock_temp_dir = MagicMock()
                    mock_temp_file = MagicMock()
                    mock_path_class.return_value = mock_temp_dir
                    mock_temp_dir.__truediv__ = Mock(return_value=mock_temp_file)
                    mock_temp_dir.mkdir = MagicMock()
                    mock_temp_file.unlink = MagicMock()

                    m_open = mock_open()
                    m_open.return_value.write = MagicMock()

                    with pytest.raises(BaseBusinessError) as exc_info:
                        await upload_pdf_file(
                            file=mock_large_pdf_file,
                            prefer_markitdown=False,
                            prefer_ocr=False,
                            organization_id=None,
                            db=mock_db,
                            pdf_service=mock_service,
                            optional=mock_optional_services,
                            current_user=mock_current_user,
                        )

        assert exc_info.value.status_code == 422
        assert "文件过大" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_upload_pdf_file_too_large_with_enhanced_handler(
        self, mock_db, mock_large_pdf_file, mock_optional_services_with_all
    ):
        """Test upload with file exceeding size limit with enhanced handler"""
        from src.api.v1.documents.pdf_upload import upload_pdf_file

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services_with_all

        with patch(
            "src.api.v1.documents.pdf_upload.PDFImportService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.process_pdf_file = AsyncMock(return_value=None)
            mock_service_class.return_value = mock_service

            with patch("src.api.v1.documents.pdf_upload.Path") as mock_path_class:
                mock_temp_dir = MagicMock()
                mock_temp_file = MagicMock()
                mock_path_class.return_value = mock_temp_dir
                mock_temp_dir.__truediv__ = Mock(return_value=mock_temp_file)
                mock_temp_dir.mkdir = MagicMock()
                mock_temp_file.unlink = MagicMock()

                m_open = mock_open()
                m_open.return_value.write = MagicMock()
                m_open.return_value.close = MagicMock()

                with pytest.raises(BaseBusinessError) as exc_info:
                    await upload_pdf_file(
                        file=mock_large_pdf_file,
                        prefer_markitdown=False,
                        prefer_ocr=False,
                        organization_id=None,
                        db=mock_db,
                        pdf_service=mock_service,
                        optional=mock_optional_services_with_all,
                        current_user=mock_current_user,
                    )

        assert exc_info.value.status_code == 422
        assert "文件过大" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_upload_pdf_with_processing_options(
        self,
        mock_db,
        mock_pdf_file,
        mock_pdf_import_service,
        mock_optional_services_with_all,
    ):
        """Test upload with different processing options"""
        from src.api.v1.documents.pdf_upload import upload_pdf_file

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services_with_all

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_service_class:
                mock_service_class.return_value = mock_pdf_import_service

                with patch("src.api.v1.documents.pdf_upload.Path") as mock_path_class:
                    mock_temp_dir = MagicMock()
                    mock_temp_file = MagicMock()
                    mock_path_class.return_value = mock_temp_dir
                    mock_temp_dir.__truediv__ = Mock(return_value=mock_temp_file)
                    mock_temp_dir.mkdir = MagicMock()
                    mock_temp_file.unlink = MagicMock()

                    m_open = mock_open()
                    m_open.return_value.write = MagicMock()

                    result = await upload_pdf_file(
                        file=mock_pdf_file,
                        prefer_markitdown=True,
                        prefer_ocr=True,
                        organization_id=5,
                        db=mock_db,
                        pdf_service=mock_pdf_import_service,
                        optional=mock_optional_services_with_all,
                        current_user=mock_current_user,
                    )

        assert result.success is True
        # Verify process_pdf_file was called with correct options
        call_args = mock_pdf_import_service.process_pdf_file.call_args
        assert call_args.kwargs["processing_options"]["prefer_ocr"] is True
        assert call_args.kwargs["processing_options"]["prefer_markitdown"] is True
        assert call_args.kwargs["organization_id"] == 5

    @pytest.mark.asyncio
    async def test_upload_pdf_processing_fails_without_enhanced_handler(
        self, mock_db, mock_pdf_file, mock_optional_services
    ):
        """Test upload when PDF processing fails without enhanced handler"""
        from src.api.v1.documents.pdf_upload import upload_pdf_file

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services

            mock_service = MagicMock()
            mock_service.process_pdf_file = AsyncMock(
                side_effect=Exception("Processing failed")
            )

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_service_class:
                mock_service_class.return_value = mock_service

                with patch("src.api.v1.documents.pdf_upload.Path") as mock_path_class:
                    mock_temp_dir = MagicMock()
                    mock_temp_file = MagicMock()
                    mock_path_class.return_value = mock_temp_dir
                    mock_temp_dir.__truediv__ = Mock(return_value=mock_temp_file)
                    mock_temp_dir.mkdir = MagicMock()
                    mock_temp_file.unlink = MagicMock()

                    m_open = mock_open()
                    m_open.return_value.write = MagicMock()

                    with patch("src.api.v1.documents.pdf_upload.open", m_open):
                        with pytest.raises(BaseBusinessError) as exc_info:
                            await upload_pdf_file(
                                file=mock_pdf_file,
                                prefer_markitdown=False,
                                prefer_ocr=False,
                                organization_id=None,
                                db=mock_db,
                                pdf_service=mock_service,
                                optional=mock_optional_services,
                                current_user=mock_current_user,
                            )

        assert exc_info.value.status_code == 500
        assert "PDF处理失败" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_upload_pdf_processing_fails_with_enhanced_handler(
        self, mock_db, mock_pdf_file, mock_optional_services_with_all
    ):
        """Test upload when PDF processing fails with enhanced handler"""
        from src.api.v1.documents.pdf_upload import upload_pdf_file

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services_with_all

            mock_service = MagicMock()
            mock_service.process_pdf_file = AsyncMock(
                side_effect=Exception("Timeout error")
            )

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_service_class:
                mock_service_class.return_value = mock_service

                with patch("src.api.v1.documents.pdf_upload.Path") as mock_path_class:
                    mock_temp_dir = MagicMock()
                    mock_temp_file = MagicMock()
                    mock_path_class.return_value = mock_temp_dir
                    mock_temp_dir.__truediv__ = Mock(return_value=mock_temp_file)
                    mock_temp_dir.mkdir = MagicMock()
                    mock_temp_file.unlink = MagicMock()

                    m_open = mock_open()
                    m_open.return_value.write = MagicMock()

                    with pytest.raises(BaseBusinessError) as exc_info:
                        await upload_pdf_file(
                            file=mock_pdf_file,
                            prefer_markitdown=False,
                            prefer_ocr=False,
                            organization_id=None,
                            db=mock_db,
                            pdf_service=mock_service,
                            optional=mock_optional_services_with_all,
                            current_user=mock_current_user,
                        )

        assert exc_info.value.status_code == 500
        assert "PDF处理失败" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_upload_pdf_processing_returns_failure(
        self, mock_db, mock_pdf_file, mock_optional_services_with_all
    ):
        """Test upload when PDF processing returns failure status"""
        from src.api.v1.documents.pdf_upload import upload_pdf_file

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services_with_all

            mock_service = MagicMock()
            mock_service.process_pdf_file = AsyncMock(
                return_value={"success": False, "error_message": "Extraction failed"}
            )

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_service_class:
                mock_service_class.return_value = mock_service

                with patch("src.api.v1.documents.pdf_upload.Path") as mock_path_class:
                    mock_temp_dir = MagicMock()
                    mock_temp_file = MagicMock()
                    mock_path_class.return_value = mock_temp_dir
                    mock_temp_dir.__truediv__ = Mock(return_value=mock_temp_file)
                    mock_temp_dir.mkdir = MagicMock()
                    mock_temp_file.unlink = MagicMock()

                    m_open = mock_open()
                    m_open.return_value.write = MagicMock()

                    result = await upload_pdf_file(
                        file=mock_pdf_file,
                        prefer_markitdown=False,
                        prefer_ocr=False,
                        organization_id=None,
                        db=mock_db,
                        pdf_service=mock_service,
                        optional=mock_optional_services_with_all,
                        current_user=mock_current_user,
                    )

        assert result.success is True
        assert result.message == "PDF文件上传成功，正在处理中"

    @pytest.mark.asyncio
    async def test_upload_pdf_file_write_exception(
        self, mock_db, mock_pdf_file, mock_optional_services
    ):
        """Test upload when file write operation fails"""
        from src.api.v1.documents.pdf_upload import upload_pdf_file

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service.process_pdf_file = AsyncMock(return_value=None)
                mock_service_class.return_value = mock_service

                with patch("src.api.v1.documents.pdf_upload.Path") as mock_path_class:
                    mock_temp_dir = MagicMock()
                    mock_temp_file = MagicMock()
                    mock_path_class.return_value = mock_temp_dir
                    mock_temp_dir.__truediv__ = Mock(return_value=mock_temp_file)
                    mock_temp_dir.mkdir = MagicMock()
                    mock_temp_file.unlink = MagicMock()

                    # Make open raise an exception
                    m_open = mock_open()
                    m_open.return_value.__enter__.side_effect = OSError("Disk full")

                    with patch("src.api.v1.documents.pdf_upload.open", m_open):
                        with pytest.raises(BaseBusinessError) as exc_info:
                            await upload_pdf_file(
                                file=mock_pdf_file,
                                prefer_markitdown=False,
                                prefer_ocr=False,
                                organization_id=None,
                                db=mock_db,
                                pdf_service=mock_service,
                                optional=mock_optional_services,
                                current_user=mock_current_user,
                            )

        assert exc_info.value.status_code == 500
        assert "文件处理失败" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_upload_pdf_validates_filename_extension(
        self,
        mock_db,
        mock_pdf_file,
        mock_pdf_import_service,
        mock_optional_services_with_all,
    ):
        """Test that PDF file with .pdf extension (case insensitive) is accepted"""
        from src.api.v1.documents.pdf_upload import upload_pdf_file

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services_with_all

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_service_class:
                mock_service_class.return_value = mock_pdf_import_service

                # Test with uppercase extension
                mock_pdf_file.filename = "test.PDF"
                mock_pdf_file.content_type = "application/pdf"

                with patch("src.api.v1.documents.pdf_upload.Path") as mock_path_class:
                    mock_temp_dir = MagicMock()
                    mock_temp_file = MagicMock()
                    mock_path_class.return_value = mock_temp_dir
                    mock_temp_dir.__truediv__ = Mock(return_value=mock_temp_file)
                    mock_temp_dir.mkdir = MagicMock()
                    mock_temp_file.unlink = MagicMock()

                    m_open = mock_open()
                    m_open.return_value.write = MagicMock()

                    result = await upload_pdf_file(
                        file=mock_pdf_file,
                        prefer_markitdown=False,
                        prefer_ocr=False,
                        organization_id=None,
                        db=mock_db,
                        pdf_service=mock_pdf_import_service,
                        optional=mock_optional_services_with_all,
                        current_user=mock_current_user,
                    )

        assert result.success is True


# ============================================================================
# Test: POST /upload_and_extract - Upload and Extract PDF (V1 Compatible)
# ============================================================================


class TestUploadAndExtractPdf:
    """Tests for POST /upload_and_extract endpoint"""

    @pytest.mark.asyncio
    async def test_upload_and_extract_success(
        self, mock_db, mock_pdf_file, mock_optional_services_with_all
    ):
        """Test successful upload and extract"""
        from src.api.v1.documents.pdf_upload import upload_and_extract_pdf_v1_compatible

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services_with_all

            # Mock PDFImportService
            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_import_service_class:
                mock_import_service = MagicMock()
                mock_import_service.upload_file = AsyncMock(
                    return_value={"file_path": "/tmp/test.pdf", "filename": "test.pdf"}
                )
                mock_import_service_class.return_value = mock_import_service

                # Mock pdf_processing_service.extract_text_from_pdf
                with patch.object(
                    mock_optional_services_with_all.pdf_processing_service,
                    "extract_text_from_pdf",
                    AsyncMock(
                        return_value={
                            "success": True,
                            "text": "Sample contract text content",
                        }
                    ),
                ):
                    # Mock extract_contract_info
                    with patch(
                        "src.services.document.contract_extractor.ContractExtractor.extract_contract_info",
                        return_value={
                            "success": True,
                            "extracted_fields": {"field1": "value1"},
                            "overall_confidence": 0.85,
                            "validation_passed": True,
                        },
                    ):
                        result = await upload_and_extract_pdf_v1_compatible(
                            file=mock_pdf_file,
                            should_include_raw_text=False,
                            should_validate_fields=True,
                            background_tasks=MagicMock(),
                            optional=mock_optional_services_with_all,
                            current_user=mock_current_user,
                        )

        assert result.success is True
        assert result.confidence == 0.85
        assert result.extracted_fields == {"field1": "value1"}
        assert result.real_data_verified is True

    @pytest.mark.asyncio
    async def test_upload_and_extract_invalid_content_type(
        self, mock_db, mock_non_pdf_file
    ):
        """Test upload and extract with invalid content type"""
        from src.api.v1.documents.pdf_upload import upload_and_extract_pdf_v1_compatible

        optional = MagicMock()
        optional.pdf_processing_service = None

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = optional

            with pytest.raises(BaseBusinessError) as exc_info:
                await upload_and_extract_pdf_v1_compatible(
                    file=mock_non_pdf_file,
                    should_include_raw_text=False,
                    should_validate_fields=True,
                    background_tasks=MagicMock(),
                    optional=optional,
                    current_user=mock_current_user,
                )

        assert exc_info.value.status_code == 400
        assert "只支持PDF文件上传" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_upload_and_extract_file_too_large(
        self, mock_db, mock_large_pdf_file
    ):
        """Test upload and extract with file exceeding size limit"""
        from src.api.v1.documents.pdf_upload import upload_and_extract_pdf_v1_compatible

        optional = MagicMock()
        optional.pdf_processing_service = None
        mock_large_pdf_file.read = AsyncMock(
            return_value=b"%PDF-1.4\n" + b"x" * (51 * 1024 * 1024)
        )

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = optional

            with pytest.raises(BaseBusinessError) as exc_info:
                await upload_and_extract_pdf_v1_compatible(
                    file=mock_large_pdf_file,
                    should_include_raw_text=False,
                    should_validate_fields=True,
                    background_tasks=MagicMock(),
                    optional=optional,
                    current_user=mock_current_user,
                )

        assert exc_info.value.status_code == 400
        assert "文件大小超过限制" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_upload_and_extract_service_unavailable(self, mock_db, mock_pdf_file):
        """Test upload and extract when processing service is unavailable"""
        from src.api.v1.documents.pdf_upload import upload_and_extract_pdf_v1_compatible

        # Optional services without pdf_processing_service
        optional = MagicMock()
        optional.pdf_processing_service = None

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = optional

            result = await upload_and_extract_pdf_v1_compatible(
                file=mock_pdf_file,
                should_include_raw_text=False,
                should_validate_fields=True,
                background_tasks=MagicMock(),
                optional=optional,
                current_user=mock_current_user,
            )

        assert result.success is False
        assert "PDF处理服务不可用" in result.error
        assert result.real_data_verified is False

    @pytest.mark.asyncio
    async def test_upload_and_extract_text_extraction_fails(
        self, mock_db, mock_pdf_file, mock_optional_services_with_all
    ):
        """Test upload and extract when text extraction fails"""
        from src.api.v1.documents.pdf_upload import upload_and_extract_pdf_v1_compatible

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services_with_all

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_import_service_class:
                mock_import_service = MagicMock()
                mock_import_service.upload_file = AsyncMock(
                    return_value={"file_path": "/tmp/test.pdf", "filename": "test.pdf"}
                )
                mock_import_service_class.return_value = mock_import_service

                with patch.object(
                    mock_optional_services_with_all.pdf_processing_service,
                    "extract_text_from_pdf",
                    AsyncMock(
                        return_value={"success": False, "error": "Extraction failed"}
                    ),
                ):
                    result = await upload_and_extract_pdf_v1_compatible(
                        file=mock_pdf_file,
                        should_include_raw_text=False,
                        should_validate_fields=True,
                        background_tasks=MagicMock(),
                        optional=mock_optional_services_with_all,
                        current_user=mock_current_user,
                    )

        assert result.success is False
        assert "PDF文本提取失败" in result.error
        assert result.real_data_verified is False

    @pytest.mark.asyncio
    async def test_upload_and_extract_with_raw_text(
        self, mock_db, mock_pdf_file, mock_optional_services_with_all
    ):
        """Test upload and extract with raw text included"""
        from src.api.v1.documents.pdf_upload import upload_and_extract_pdf_v1_compatible

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services_with_all

            sample_text = "Sample contract text content"

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_import_service_class:
                mock_import_service = MagicMock()
                mock_import_service.upload_file = AsyncMock(
                    return_value={"file_path": "/tmp/test.pdf", "filename": "test.pdf"}
                )
                mock_import_service_class.return_value = mock_import_service

                with patch.object(
                    mock_optional_services_with_all.pdf_processing_service,
                    "extract_text_from_pdf",
                    AsyncMock(return_value={"success": True, "text": sample_text}),
                ):
                    with patch(
                        "src.services.document.contract_extractor.ContractExtractor.extract_contract_info",
                        return_value={
                            "success": True,
                            "extracted_fields": {"field1": "value1"},
                            "overall_confidence": 0.85,
                            "validation_passed": True,
                        },
                    ):
                        result = await upload_and_extract_pdf_v1_compatible(
                            file=mock_pdf_file,
                            should_include_raw_text=True,
                            should_validate_fields=True,
                            background_tasks=MagicMock(),
                            optional=mock_optional_services_with_all,
                            current_user=mock_current_user,
                        )

        assert result.success is True
        assert result.extracted_fields.get("_raw_text") == sample_text

    @pytest.mark.asyncio
    async def test_upload_and_extract_without_field_validation(
        self, mock_db, mock_pdf_file, mock_optional_services_with_all
    ):
        """Test upload and extract without field validation"""
        from src.api.v1.documents.pdf_upload import upload_and_extract_pdf_v1_compatible

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services_with_all

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_import_service_class:
                mock_import_service = MagicMock()
                mock_import_service.upload_file = AsyncMock(
                    return_value={"file_path": "/tmp/test.pdf", "filename": "test.pdf"}
                )
                mock_import_service_class.return_value = mock_import_service

                with patch.object(
                    mock_optional_services_with_all.pdf_processing_service,
                    "extract_text_from_pdf",
                    AsyncMock(return_value={"success": True, "text": "Sample text"}),
                ):
                    with patch(
                        "src.services.document.contract_extractor.ContractExtractor.extract_contract_info",
                        return_value={
                            "success": True,
                            "extracted_fields": {"field1": "value1"},
                            "overall_confidence": 0.85,
                            "validation_passed": True,
                        },
                    ):
                        result = await upload_and_extract_pdf_v1_compatible(
                            file=mock_pdf_file,
                            should_include_raw_text=False,
                            should_validate_fields=False,
                            background_tasks=MagicMock(),
                            optional=mock_optional_services_with_all,
                            current_user=mock_current_user,
                        )

        assert result.success is True
        assert result.validation_results == {}

    @pytest.mark.asyncio
    async def test_upload_and_extract_extraction_fails(
        self, mock_db, mock_pdf_file, mock_optional_services_with_all
    ):
        """Test upload and extract when contract info extraction fails"""
        from src.api.v1.documents.pdf_upload import upload_and_extract_pdf_v1_compatible

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services_with_all

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_import_service_class:
                mock_import_service = MagicMock()
                mock_import_service.upload_file = AsyncMock(
                    return_value={"file_path": "/tmp/test.pdf", "filename": "test.pdf"}
                )
                mock_import_service_class.return_value = mock_import_service

                with patch.object(
                    mock_optional_services_with_all.pdf_processing_service,
                    "extract_text_from_pdf",
                    AsyncMock(return_value={"success": True, "text": "Sample text"}),
                ):
                    with patch(
                        "src.services.document.contract_extractor.ContractExtractor.extract_contract_info",
                        return_value={
                            "success": False,
                            "error": "Cannot extract fields",
                        },
                    ):
                        result = await upload_and_extract_pdf_v1_compatible(
                            file=mock_pdf_file,
                            should_include_raw_text=False,
                            should_validate_fields=True,
                            background_tasks=MagicMock(),
                            optional=mock_optional_services_with_all,
                            current_user=mock_current_user,
                        )

        assert result.success is False
        assert "Cannot extract fields" in result.error
        assert result.real_data_verified is False

    @pytest.mark.asyncio
    async def test_upload_and_extract_exception_handling(
        self, mock_db, mock_pdf_file, mock_optional_services_with_all
    ):
        """Test upload and extract exception handling"""
        from src.api.v1.documents.pdf_upload import upload_and_extract_pdf_v1_compatible

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services_with_all

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_import_service_class:
                mock_import_service = MagicMock()
                mock_import_service.upload_file = AsyncMock(
                    side_effect=Exception("Unexpected error")
                )
                mock_import_service_class.return_value = mock_import_service

                result = await upload_and_extract_pdf_v1_compatible(
                    file=mock_pdf_file,
                    should_include_raw_text=False,
                    should_validate_fields=True,
                    background_tasks=MagicMock(),
                    optional=mock_optional_services_with_all,
                    current_user=mock_current_user,
                )

        assert result.success is False
        assert "PDF处理异常" in result.error
        assert result.real_data_verified is False


# ============================================================================
# Test: Helper Functions
# ============================================================================


class TestValidateExtractedFieldsV1:
    """Tests for _validate_extracted_fields_v1 helper function"""

    def test_validate_extracted_fields_v1_with_valid_fields(self):
        """Test validation with valid fields"""
        from src.api.v1.documents.pdf_upload import _validate_extracted_fields_v1

        fields = {
            "contract_number": "CONTRACT-001",
            "party_a": "Company A",
            "party_b": "Company B",
        }

        result = _validate_extracted_fields_v1(fields)

        assert result["contract_number"]["is_valid"] is True
        assert result["contract_number"]["confidence"] == 0.8
        assert result["party_a"]["is_valid"] is True
        assert result["party_b"]["is_valid"] is True

    def test_validate_extracted_fields_v1_with_empty_fields(self):
        """Test validation with empty fields"""
        from src.api.v1.documents.pdf_upload import _validate_extracted_fields_v1

        fields = {"contract_number": "", "party_a": None, "party_b": "   "}

        result = _validate_extracted_fields_v1(fields)

        assert result["contract_number"]["is_valid"] is False
        assert "字段值为空" in result["contract_number"]["validation_errors"][0]
        assert result["contract_number"]["confidence"] == 0.0
        assert result["party_a"]["is_valid"] is False
        assert result["party_b"]["is_valid"] is False

    def test_validate_extracted_fields_v1_mixed_fields(self):
        """Test validation with mixed valid and empty fields"""
        from src.api.v1.documents.pdf_upload import _validate_extracted_fields_v1

        fields = {
            "contract_number": "CONTRACT-001",
            "party_a": "",
            "party_b": "Company B",
        }

        result = _validate_extracted_fields_v1(fields)

        assert result["contract_number"]["is_valid"] is True
        assert result["party_a"]["is_valid"] is False
        assert result["party_b"]["is_valid"] is True

    def test_validate_extracted_fields_v1_empty_dict(self):
        """Test validation with empty dictionary"""
        from src.api.v1.documents.pdf_upload import _validate_extracted_fields_v1

        result = _validate_extracted_fields_v1({})

        assert result == {}

    def test_validate_extracted_fields_v1_with_numeric_values(self):
        """Test validation with numeric values"""
        from src.api.v1.documents.pdf_upload import _validate_extracted_fields_v1

        fields = {"amount": 10000, "area": 500.5, "empty": 0}

        result = _validate_extracted_fields_v1(fields)

        assert result["amount"]["is_valid"] is True
        assert result["area"]["is_valid"] is True
        assert result["empty"]["is_valid"] is False  # 0 is falsy


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error scenarios"""

    @pytest.mark.asyncio
    async def test_upload_pdf_with_none_filename(
        self, mock_db, mock_pdf_file, mock_optional_services
    ):
        """Test upload with None filename"""
        from src.api.v1.documents.pdf_upload import upload_pdf_file

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service.process_pdf_file = AsyncMock(return_value=None)
                mock_service_class.return_value = mock_service

                mock_pdf_file.filename = None
                mock_pdf_file.content_type = "application/pdf"

                with pytest.raises(BaseBusinessError) as exc_info:
                    await upload_pdf_file(
                        file=mock_pdf_file,
                        prefer_markitdown=False,
                        prefer_ocr=False,
                        organization_id=None,
                        db=mock_db,
                        pdf_service=mock_service,
                        optional=mock_optional_services,
                        current_user=mock_current_user,
                    )

        assert exc_info.value.status_code == 422
        assert "文件名不能为空" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_upload_pdf_with_custom_max_size(
        self,
        mock_db,
        mock_pdf_file,
        mock_pdf_import_service,
        mock_optional_services_with_all,
    ):
        """Test upload with custom max file size from enhanced handler"""
        from src.api.v1.documents.pdf_upload import upload_pdf_file

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services_with_all
            mock_optional_services_with_all.enhanced_error_handler.max_file_size_mb = (
                100
            )

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_service_class:
                mock_service_class.return_value = mock_pdf_import_service

                with patch("src.api.v1.documents.pdf_upload.Path") as mock_path_class:
                    mock_temp_dir = MagicMock()
                    mock_temp_file = MagicMock()
                    mock_path_class.return_value = mock_temp_dir
                    mock_temp_dir.__truediv__ = Mock(return_value=mock_temp_file)
                    mock_temp_dir.mkdir = MagicMock()
                    mock_temp_file.unlink = MagicMock()

                    m_open = mock_open()
                    m_open.return_value.write = MagicMock()

                    result = await upload_pdf_file(
                        file=mock_pdf_file,
                        prefer_markitdown=False,
                        prefer_ocr=False,
                        organization_id=None,
                        db=mock_db,
                        pdf_service=mock_pdf_import_service,
                        optional=mock_optional_services_with_all,
                        current_user=mock_current_user,
                    )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_upload_pdf_streaming_in_chunks(
        self,
        mock_db,
        mock_pdf_file,
        mock_pdf_import_service,
        mock_optional_services_with_all,
    ):
        """Test that file is read in chunks during upload"""
        from src.api.v1.documents.pdf_upload import upload_pdf_file

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services_with_all

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_service_class:
                mock_service_class.return_value = mock_pdf_import_service

                # Create a file that requires multiple chunks and passes magic check
                large_content = b"%PDF-1.4\n" + (b"x" * (100 * 1024))
                mock_pdf_file.read = AsyncMock(
                    side_effect=[large_content[:2048], large_content, b""]
                )

                with patch("src.api.v1.documents.pdf_upload.Path") as mock_path_class:
                    mock_temp_dir = MagicMock()
                    mock_temp_file = MagicMock()
                    mock_path_class.return_value = mock_temp_dir
                    mock_temp_dir.__truediv__ = Mock(return_value=mock_temp_file)
                    mock_temp_dir.mkdir = MagicMock()
                    mock_temp_file.unlink = MagicMock()

                    m_open = mock_open()
                    m_open.return_value.write = MagicMock()

                    result = await upload_pdf_file(
                        file=mock_pdf_file,
                        prefer_markitdown=False,
                        prefer_ocr=False,
                        organization_id=None,
                        db=mock_db,
                        pdf_service=mock_pdf_import_service,
                        optional=mock_optional_services_with_all,
                        current_user=mock_current_user,
                    )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_upload_and_extract_with_timeout_error(
        self, mock_db, mock_pdf_file, mock_optional_services_with_all
    ):
        """Test upload and extract with timeout in processing"""
        from src.api.v1.documents.pdf_upload import upload_and_extract_pdf_v1_compatible

        with patch(
            "src.api.v1.documents.pdf_upload.get_optional_services"
        ) as mock_get_optional:
            mock_get_optional.return_value = mock_optional_services_with_all

            with patch(
                "src.api.v1.documents.pdf_upload.PDFImportService"
            ) as mock_import_service_class:
                mock_import_service = MagicMock()
                mock_import_service.upload_file = AsyncMock(
                    side_effect=TimeoutError("Processing timeout")
                )
                mock_import_service_class.return_value = mock_import_service

                result = await upload_and_extract_pdf_v1_compatible(
                    file=mock_pdf_file,
                    should_include_raw_text=False,
                    should_validate_fields=True,
                    background_tasks=MagicMock(),
                    optional=mock_optional_services_with_all,
                    current_user=mock_current_user,
                )

        assert result.success is False
        assert "PDF处理异常" in result.error
