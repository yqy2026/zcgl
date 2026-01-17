"""
Comprehensive Unit Tests for Asset Attachments API Routes (src/api/v1/asset_attachments.py)

This test module covers all endpoints in the asset_attachments router to achieve 70%+ coverage:

Endpoints Tested:
1. POST /{asset_id}/attachments - Upload asset attachments (PDF files)
2. GET /{asset_id}/attachments - Get asset attachments list
3. GET /{asset_id}/attachments/{filename} - Download asset attachment
4. DELETE /{asset_id}/attachments/{attachment_id} - Delete asset attachment

Testing Approach:
- Mock all dependencies (asset_crud, file operations, file_security utilities)
- Test successful responses and error scenarios
- Test file validation (size, type, security)
- Test edge cases (missing files, invalid filenames, etc.)
- Test permission checks
"""

import io
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch, mock_open

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse

pytestmark = pytest.mark.api


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """Create mock database session"""
    return MagicMock()


@pytest.fixture
def mock_admin_user():
    """Create mock admin user"""
    user = MagicMock()
    user.id = "admin-id"
    user.username = "admin"
    user.role = "admin"
    user.is_active = True
    return user


@pytest.fixture
def mock_regular_user():
    """Create mock regular user"""
    user = MagicMock()
    user.id = "user-id"
    user.username = "testuser"
    user.role = "user"
    user.is_active = True
    return user


@pytest.fixture
def mock_asset():
    """Create mock asset"""
    asset = MagicMock()
    asset.id = "asset-123"
    asset.name = "Test Asset"
    return asset


@pytest.fixture
def mock_pdf_file():
    """Create mock PDF upload file"""
    file = MagicMock(spec=UploadFile)
    file.filename = "test_document.pdf"
    file.content_type = "application/pdf"
    content = io.BytesIO(b"%PDF-1.4 fake pdf content")
    file.file = io.BytesIO(b"%PDF-1.4 fake pdf content")
    file.file.seek = Mock(return_value=None)
    file.file.tell = Mock(return_value=100)
    return file


@pytest.fixture
def mock_large_pdf_file():
    """Create mock PDF file exceeding size limit (>10MB)"""
    file = MagicMock(spec=UploadFile)
    file.filename = "large_document.pdf"
    file.content_type = "application/pdf"
    large_content = b"x" * (11 * 1024 * 1024)  # 11MB
    file.file = io.BytesIO(large_content)
    file.file.seek = Mock(return_value=None)
    file.file.tell = Mock(return_value=11 * 1024 * 1024)
    return file


@pytest.fixture
def mock_non_pdf_file():
    """Create mock non-PDF file"""
    file = MagicMock(spec=UploadFile)
    file.filename = "test.txt"
    file.content_type = "text/plain"
    file.file = io.BytesIO(b"not a pdf")
    file.file.seek = Mock(return_value=None)
    file.file.tell = Mock(return_value=10)
    return file


@pytest.fixture
def mock_none_filename_file():
    """Create mock file with None filename"""
    file = MagicMock(spec=UploadFile)
    file.filename = None
    file.content_type = "application/pdf"
    file.file = io.BytesIO(b"%PDF-1.4")
    file.file.seek = Mock(return_value=None)
    file.file.tell = Mock(return_value=10)
    return file


# ============================================================================
# Test: POST /{asset_id}/attachments - Upload Asset Attachments
# ============================================================================


class TestUploadAssetAttachments:
    """Tests for POST /{asset_id}/attachments endpoint"""

    @patch("src.utils.file_security.validate_upload_file")
    @patch("src.utils.file_security.create_safe_upload_directory")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_upload_single_attachment_success(
        self,
        mock_asset_crud_obj,
        mock_create_dir,
        mock_validate_file,
        mock_db,
        mock_admin_user,
        mock_asset,
        mock_pdf_file,
    ):
        """Test uploading single attachment successfully"""
        from src.api.v1.asset_attachments import upload_asset_attachments

        # Setup mocks
        mock_asset_crud_obj.get.return_value = mock_asset
        mock_create_dir.return_value = Path("uploads/attachments/asset-123")
        mock_validate_file.return_value = {
            "valid": True,
            "safe_filename": "test_document.pdf",
            "errors": [],
        }

        # Mock file operations
        m_open = mock_open()

        with patch("builtins.open", m_open):
            result = await upload_asset_attachments(
                asset_id="asset-123",
                files=[mock_pdf_file],
                db=mock_db,
                current_user=mock_admin_user,
            )

        assert result["success"] == ["test_document.pdf"]
        assert result["failed"] == []
        assert "成功上传 1 个文件" in result["message"]
        mock_asset_crud_obj.get.assert_called_once_with(db=mock_db, id="asset-123")

    @patch("src.utils.file_security.validate_upload_file")
    @patch("src.utils.file_security.create_safe_upload_directory")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_upload_multiple_attachments_success(
        self,
        mock_asset_crud_obj,
        mock_create_dir,
        mock_validate_file,
        mock_db,
        mock_admin_user,
        mock_asset,
    ):
        """Test uploading multiple attachments successfully"""
        from src.api.v1.asset_attachments import upload_asset_attachments

        # Create multiple files
        file1 = MagicMock(spec=UploadFile)
        file1.filename = "doc1.pdf"
        file1.content_type = "application/pdf"
        file1.file = io.BytesIO(b"%PDF-1.4 doc1")
        file1.file.seek = Mock(return_value=None)
        file1.file.tell = Mock(return_value=20)

        file2 = MagicMock(spec=UploadFile)
        file2.filename = "doc2.pdf"
        file2.content_type = "application/pdf"
        file2.file = io.BytesIO(b"%PDF-1.4 doc2")
        file2.file.seek = Mock(return_value=None)
        file2.file.tell = Mock(return_value=20)

        # Setup mocks
        mock_asset_crud_obj.get.return_value = mock_asset
        mock_create_dir.return_value = Path("uploads/attachments/asset-123")

        def validate_side_effect(filename, content_type, file_size, **kwargs):
            return {
                "valid": True,
                "safe_filename": filename,
                "errors": [],
            }

        mock_validate_file.side_effect = validate_side_effect

        m_open = mock_open()

        with patch("builtins.open", m_open):
            result = await upload_asset_attachments(
                asset_id="asset-123",
                files=[file1, file2],
                db=mock_db,
                current_user=mock_admin_user,
            )

        assert len(result["success"]) == 2
        assert result["failed"] == []
        assert "成功上传 2 个文件" in result["message"]

    @patch("src.utils.file_security.validate_upload_file")
    @patch("src.utils.file_security.create_safe_upload_directory")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_upload_attachment_asset_not_found(
        self,
        mock_asset_crud_obj,
        mock_create_dir,
        mock_validate_file,
        mock_db,
        mock_admin_user,
        mock_pdf_file,
    ):
        """Test uploading attachment to non-existent asset"""
        from src.api.v1.asset_attachments import upload_asset_attachments
        from src.core.exception_handler import ResourceNotFoundError

        mock_asset_crud_obj.get.return_value = None
        mock_create_dir.return_value = Path("uploads/attachments/asset-123")
        mock_validate_file.return_value = {
            "valid": True,
            "safe_filename": "test.pdf",
            "errors": [],
        }

        with pytest.raises(ResourceNotFoundError):
            await upload_asset_attachments(
                asset_id="nonexistent-asset",
                files=[mock_pdf_file],
                db=mock_db,
                current_user=mock_admin_user,
            )

    @patch("src.utils.file_security.validate_upload_file")
    @patch("src.utils.file_security.create_safe_upload_directory")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_upload_attachment_file_too_large(
        self,
        mock_asset_crud_obj,
        mock_create_dir,
        mock_validate_file,
        mock_db,
        mock_admin_user,
        mock_asset,
        mock_large_pdf_file,
    ):
        """Test uploading attachment with file exceeding size limit"""
        from src.api.v1.asset_attachments import upload_asset_attachments

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_create_dir.return_value = Path("uploads/attachments/asset-123")
        mock_validate_file.return_value = {
            "valid": False,
            "safe_filename": None,
            "errors": ["文件大小超过限制"],
        }

        result = await upload_asset_attachments(
            asset_id="asset-123",
            files=[mock_large_pdf_file],
            db=mock_db,
            current_user=mock_admin_user,
        )

        assert len(result["success"]) == 0
        assert len(result["failed"]) == 1
        assert "文件大小超过限制" in result["failed"][0]

    @patch("src.utils.file_security.validate_upload_file")
    @patch("src.utils.file_security.create_safe_upload_directory")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_upload_attachment_invalid_file_type(
        self,
        mock_asset_crud_obj,
        mock_create_dir,
        mock_validate_file,
        mock_db,
        mock_admin_user,
        mock_asset,
        mock_non_pdf_file,
    ):
        """Test uploading attachment with invalid file type"""
        from src.api.v1.asset_attachments import upload_asset_attachments

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_create_dir.return_value = Path("uploads/attachments/asset-123")
        mock_validate_file.return_value = {
            "valid": False,
            "safe_filename": None,
            "errors": ["不支持的文件类型"],
        }

        result = await upload_asset_attachments(
            asset_id="asset-123",
            files=[mock_non_pdf_file],
            db=mock_db,
            current_user=mock_admin_user,
        )

        assert len(result["success"]) == 0
        assert len(result["failed"]) == 1
        assert "不支持的文件类型" in result["failed"][0]

    @patch("src.utils.file_security.validate_upload_file")
    @patch("src.utils.file_security.create_safe_upload_directory")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_upload_attachment_none_filename(
        self,
        mock_asset_crud_obj,
        mock_create_dir,
        mock_validate_file,
        mock_db,
        mock_admin_user,
        mock_asset,
        mock_none_filename_file,
    ):
        """Test uploading attachment with None filename"""
        from src.api.v1.asset_attachments import upload_asset_attachments

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_create_dir.return_value = Path("uploads/attachments/asset-123")

        result = await upload_asset_attachments(
            asset_id="asset-123",
            files=[mock_none_filename_file],
            db=mock_db,
            current_user=mock_admin_user,
        )

        assert len(result["success"]) == 0
        assert len(result["failed"]) == 1
        assert "文件名不能为空" in result["failed"][0]
        mock_validate_file.assert_not_called()

    @patch("src.utils.file_security.validate_upload_file")
    @patch("src.utils.file_security.create_safe_upload_directory")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_upload_mixed_success_and_failure(
        self,
        mock_asset_crud_obj,
        mock_create_dir,
        mock_validate_file,
        mock_db,
        mock_admin_user,
        mock_asset,
        mock_pdf_file,
        mock_non_pdf_file,
    ):
        """Test uploading multiple files with mixed success and failure"""
        from src.api.v1.asset_attachments import upload_asset_attachments

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_create_dir.return_value = Path("uploads/attachments/asset-123")

        # First file (PDF) succeeds, second (TXT) fails
        call_count = [0]

        def validate_side_effect(filename, content_type, file_size, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {
                    "valid": True,
                    "safe_filename": filename,
                    "errors": [],
                }
            else:
                return {
                    "valid": False,
                    "safe_filename": None,
                    "errors": ["不支持的文件类型"],
                }

        mock_validate_file.side_effect = validate_side_effect

        m_open = mock_open()

        with patch("builtins.open", m_open):
            result = await upload_asset_attachments(
                asset_id="asset-123",
                files=[mock_pdf_file, mock_non_pdf_file],
                db=mock_db,
                current_user=mock_admin_user,
            )

        assert len(result["success"]) == 1
        assert len(result["failed"]) == 1
        assert "成功上传 1 个文件，失败 1 个文件" in result["message"]

    @patch("src.utils.file_security.validate_upload_file")
    @patch("src.utils.file_security.create_safe_upload_directory")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_upload_attachment_file_write_exception(
        self,
        mock_asset_crud_obj,
        mock_create_dir,
        mock_validate_file,
        mock_db,
        mock_admin_user,
        mock_asset,
        mock_pdf_file,
    ):
        """Test uploading attachment when file write fails"""
        from src.api.v1.asset_attachments import upload_asset_attachments

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_create_dir.return_value = Path("uploads/attachments/asset-123")
        mock_validate_file.return_value = {
            "valid": True,
            "safe_filename": "test_document.pdf",
            "errors": [],
        }

        # Mock open to raise IOError
        m_open = mock_open()
        m_open.side_effect = IOError("Disk full")

        with patch("builtins.open", m_open):
            result = await upload_asset_attachments(
                asset_id="asset-123",
                files=[mock_pdf_file],
                db=mock_db,
                current_user=mock_admin_user,
            )

        assert len(result["success"]) == 0
        assert len(result["failed"]) == 1
        assert "Disk full" in result["failed"][0] or "IOError" in result["failed"][0]

    @patch("src.utils.file_security.validate_upload_file")
    @patch("src.utils.file_security.create_safe_upload_directory")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_upload_attachment_exception_handling(
        self,
        mock_asset_crud_obj,
        mock_create_dir,
        mock_validate_file,
        mock_db,
        mock_admin_user,
        mock_asset,
        mock_pdf_file,
    ):
        """Test upload endpoint exception handling"""
        from src.api.v1.asset_attachments import upload_asset_attachments

        mock_asset_crud_obj.get.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await upload_asset_attachments(
                asset_id="asset-123",
                files=[mock_pdf_file],
                db=mock_db,
                current_user=mock_admin_user,
            )

        assert exc_info.value.status_code == 500
        assert "上传附件失败" in exc_info.value.detail


# ============================================================================
# Test: GET /{asset_id}/attachments - Get Asset Attachments List
# ============================================================================


class TestGetAssetAttachments:
    """Tests for GET /{asset_id}/attachments endpoint"""

    @patch("os.path.exists")
    @patch("os.listdir")
    @patch("os.path.join")
    @patch("os.stat")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_get_attachments_success(
        self,
        mock_asset_crud_obj,
        mock_stat,
        mock_join,
        mock_listdir,
        mock_exists,
        mock_db,
        mock_regular_user,
        mock_asset,
    ):
        """Test getting attachments list successfully"""
        from src.api.v1.asset_attachments import get_asset_attachments

        # Setup mocks
        mock_asset_crud_obj.get.return_value = mock_asset
        mock_exists.return_value = True
        mock_listdir.return_value = ["document1.pdf", "document2.pdf"]
        mock_join.return_value = "uploads/attachments/asset-123/document1.pdf"

        mock_file_stat = MagicMock()
        mock_file_stat.st_size = 1024000
        mock_file_stat.st_mtime = 1234567890.0
        mock_stat.return_value = mock_file_stat

        result = await get_asset_attachments(
            asset_id="asset-123",
            db=mock_db,
            current_user=mock_regular_user,
        )

        assert len(result) == 2
        assert result[0]["id"] == "document1.pdf"
        assert result[0]["name"] == "document1.pdf"
        assert result[0]["size"] == 1024000
        assert result[0]["url"] == "/api/v1/assets/asset-123/attachments/document1.pdf"
        assert result[0]["upload_time"] == 1234567890.0

    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_get_attachments_asset_not_found(
        self, mock_asset_crud_obj, mock_db, mock_regular_user
    ):
        """Test getting attachments for non-existent asset"""
        from src.api.v1.asset_attachments import get_asset_attachments
        from src.core.exception_handler import ResourceNotFoundError

        mock_asset_crud_obj.get.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await get_asset_attachments(
                asset_id="nonexistent-asset",
                db=mock_db,
                current_user=mock_regular_user,
            )

    @patch("os.path.exists")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_get_attachments_directory_not_exists(
        self, mock_asset_crud_obj, mock_exists, mock_db, mock_regular_user, mock_asset
    ):
        """Test getting attachments when directory doesn't exist"""
        from src.api.v1.asset_attachments import get_asset_attachments

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_exists.return_value = False

        result = await get_asset_attachments(
            asset_id="asset-123",
            db=mock_db,
            current_user=mock_regular_user,
        )

        assert result == []

    @patch("os.path.exists")
    @patch("os.listdir")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_get_attachments_empty_directory(
        self, mock_asset_crud_obj, mock_listdir, mock_exists, mock_db, mock_regular_user, mock_asset
    ):
        """Test getting attachments from empty directory"""
        from src.api.v1.asset_attachments import get_asset_attachments

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_exists.return_value = True
        mock_listdir.return_value = []

        result = await get_asset_attachments(
            asset_id="asset-123",
            db=mock_db,
            current_user=mock_regular_user,
        )

        assert result == []

    @patch("os.path.exists")
    @patch("os.listdir")
    @patch("os.path.join")
    @patch("os.stat")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_get_attachments_filters_non_pdf_files(
        self,
        mock_asset_crud_obj,
        mock_stat,
        mock_join,
        mock_listdir,
        mock_exists,
        mock_db,
        mock_regular_user,
        mock_asset,
    ):
        """Test that only PDF files are returned"""
        from src.api.v1.asset_attachments import get_asset_attachments

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_exists.return_value = True
        mock_listdir.return_value = ["document.pdf", "image.jpg", "data.txt", "report.PDF"]
        mock_join.return_value = "uploads/attachments/asset-123/document.pdf"

        mock_file_stat = MagicMock()
        mock_file_stat.st_size = 1024
        mock_file_stat.st_mtime = 1234567890.0
        mock_stat.return_value = mock_file_stat

        result = await get_asset_attachments(
            asset_id="asset-123",
            db=mock_db,
            current_user=mock_regular_user,
        )

        # Should only return PDF files (case insensitive)
        assert len(result) == 2

    @patch("os.path.exists")
    @patch("os.listdir")
    @patch("os.path.join")
    @patch("os.stat")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_get_attachments_exception_handling(
        self,
        mock_asset_crud_obj,
        mock_stat,
        mock_join,
        mock_listdir,
        mock_exists,
        mock_db,
        mock_regular_user,
        mock_asset,
    ):
        """Test get attachments exception handling"""
        from src.api.v1.asset_attachments import get_asset_attachments

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_exists.side_effect = Exception("Filesystem error")

        with pytest.raises(HTTPException) as exc_info:
            await get_asset_attachments(
                asset_id="asset-123",
                db=mock_db,
                current_user=mock_regular_user,
            )

        assert exc_info.value.status_code == 500
        assert "获取附件列表失败" in exc_info.value.detail


# ============================================================================
# Test: GET /{asset_id}/attachments/{filename} - Download Asset Attachment
# ============================================================================


class TestDownloadAssetAttachment:
    """Tests for GET /{asset_id}/attachments/{filename} endpoint"""

    @patch("os.path.exists")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_download_attachment_success(
        self, mock_asset_crud_obj, mock_exists, mock_db, mock_regular_user, mock_asset
    ):
        """Test downloading attachment successfully"""
        from src.api.v1.asset_attachments import download_asset_attachment

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_exists.return_value = True

        # Mock FileResponse
        with patch("src.api.v1.asset_attachments.FileResponse") as mock_file_response:
            mock_response = MagicMock()
            mock_file_response.return_value = mock_response

            result = await download_asset_attachment(
                asset_id="asset-123",
                filename="document.pdf",
                db=mock_db,
                current_user=mock_regular_user,
            )

            assert result == mock_response
            mock_file_response.assert_called_once_with(
                "uploads/attachments/asset-123/document.pdf",
                filename="document.pdf",
                media_type="application/pdf",
            )

    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_download_attachment_asset_not_found(
        self, mock_asset_crud_obj, mock_db, mock_regular_user
    ):
        """Test downloading attachment for non-existent asset"""
        from src.api.v1.asset_attachments import download_asset_attachment
        from src.core.exception_handler import ResourceNotFoundError

        mock_asset_crud_obj.get.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await download_asset_attachment(
                asset_id="nonexistent-asset",
                filename="document.pdf",
                db=mock_db,
                current_user=mock_regular_user,
            )

    @patch("os.path.exists")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_download_attachment_file_not_found(
        self, mock_asset_crud_obj, mock_exists, mock_db, mock_regular_user, mock_asset
    ):
        """Test downloading non-existent file"""
        from src.api.v1.asset_attachments import download_asset_attachment

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_exists.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await download_asset_attachment(
                asset_id="asset-123",
                filename="nonexistent.pdf",
                db=mock_db,
                current_user=mock_regular_user,
            )

        assert exc_info.value.status_code == 404
        assert "文件不存在" in exc_info.value.detail

    @patch("os.path.exists")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_download_attachment_invalid_file_type(
        self, mock_asset_crud_obj, mock_exists, mock_db, mock_regular_user, mock_asset
    ):
        """Test downloading non-PDF file"""
        from src.api.v1.asset_attachments import download_asset_attachment

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_exists.return_value = True

        with pytest.raises(HTTPException) as exc_info:
            await download_asset_attachment(
                asset_id="asset-123",
                filename="document.txt",
                db=mock_db,
                current_user=mock_regular_user,
            )

        assert exc_info.value.status_code == 400
        assert "仅支持PDF文件" in exc_info.value.detail

    @patch("os.path.exists")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_download_attachment_case_insensitive_extension(
        self, mock_asset_crud_obj, mock_exists, mock_db, mock_regular_user, mock_asset
    ):
        """Test downloading PDF with uppercase extension"""
        from src.api.v1.asset_attachments import download_asset_attachment

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_exists.return_value = True

        with patch("src.api.v1.asset_attachments.FileResponse") as mock_file_response:
            mock_response = MagicMock()
            mock_file_response.return_value = mock_response

            result = await download_asset_attachment(
                asset_id="asset-123",
                filename="document.PDF",
                db=mock_db,
                current_user=mock_regular_user,
            )

            assert result == mock_response

    @patch("os.path.exists")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_download_attachment_exception_handling(
        self, mock_asset_crud_obj, mock_exists, mock_db, mock_regular_user, mock_asset
    ):
        """Test download attachment exception handling"""
        from src.api.v1.asset_attachments import download_asset_attachment

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_exists.side_effect = Exception("Filesystem error")

        with pytest.raises(HTTPException) as exc_info:
            await download_asset_attachment(
                asset_id="asset-123",
                filename="document.pdf",
                db=mock_db,
                current_user=mock_regular_user,
            )

        assert exc_info.value.status_code == 500
        assert "下载附件失败" in exc_info.value.detail


# ============================================================================
# Test: DELETE /{asset_id}/attachments/{attachment_id} - Delete Asset Attachment
# ============================================================================


class TestDeleteAssetAttachment:
    """Tests for DELETE /{asset_id}/attachments/{attachment_id} endpoint"""

    @patch("os.path.exists")
    @patch("os.remove")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_delete_attachment_success(
        self,
        mock_asset_crud_obj,
        mock_remove,
        mock_exists,
        mock_db,
        mock_admin_user,
        mock_asset,
    ):
        """Test deleting attachment successfully"""
        from src.api.v1.asset_attachments import delete_asset_attachment

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_exists.return_value = True

        result = await delete_asset_attachment(
            asset_id="asset-123",
            attachment_id="document.pdf",
            db=mock_db,
            current_user=mock_admin_user,
        )

        assert result["message"] == "附件删除成功"
        mock_remove.assert_called_once_with("uploads/attachments/asset-123/document.pdf")

    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_delete_attachment_asset_not_found(
        self, mock_asset_crud_obj, mock_db, mock_admin_user
    ):
        """Test deleting attachment for non-existent asset"""
        from src.api.v1.asset_attachments import delete_asset_attachment
        from src.core.exception_handler import ResourceNotFoundError

        mock_asset_crud_obj.get.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await delete_asset_attachment(
                asset_id="nonexistent-asset",
                attachment_id="document.pdf",
                db=mock_db,
                current_user=mock_admin_user,
            )

    @patch("os.path.exists")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_delete_attachment_file_not_found(
        self, mock_asset_crud_obj, mock_exists, mock_db, mock_admin_user, mock_asset
    ):
        """Test deleting non-existent file"""
        from src.api.v1.asset_attachments import delete_asset_attachment

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_exists.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await delete_asset_attachment(
                asset_id="asset-123",
                attachment_id="nonexistent.pdf",
                db=mock_db,
                current_user=mock_admin_user,
            )

        assert exc_info.value.status_code == 404
        assert "文件不存在" in exc_info.value.detail

    @patch("os.path.exists")
    @patch("os.remove")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_delete_attachment_success_with_special_filename(
        self,
        mock_asset_crud_obj,
        mock_remove,
        mock_exists,
        mock_db,
        mock_admin_user,
        mock_asset,
    ):
        """Test deleting attachment with special characters in filename"""
        from src.api.v1.asset_attachments import delete_asset_attachment

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_exists.return_value = True

        result = await delete_asset_attachment(
            asset_id="asset-123",
            attachment_id="report_2024-01-15_final.pdf",
            db=mock_db,
            current_user=mock_admin_user,
        )

        assert result["message"] == "附件删除成功"
        mock_remove.assert_called_once_with(
            "uploads/attachments/asset-123/report_2024-01-15_final.pdf"
        )

    @patch("os.path.exists")
    @patch("os.remove")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_delete_attachment_exception_handling(
        self,
        mock_asset_crud_obj,
        mock_remove,
        mock_exists,
        mock_db,
        mock_admin_user,
        mock_asset,
    ):
        """Test delete attachment exception handling"""
        from src.api.v1.asset_attachments import delete_asset_attachment

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_exists.return_value = True
        mock_remove.side_effect = Exception("Permission denied")

        with pytest.raises(HTTPException) as exc_info:
            await delete_asset_attachment(
                asset_id="asset-123",
                attachment_id="document.pdf",
                db=mock_db,
                current_user=mock_admin_user,
            )

        assert exc_info.value.status_code == 500
        assert "删除附件失败" in exc_info.value.detail


# ============================================================================
# Test: Edge Cases and Integration
# ============================================================================


class TestAssetAttachmentsEdgeCases:
    """Tests for edge cases and integration scenarios"""

    @patch("os.path.exists")
    @patch("os.listdir")
    @patch("os.path.join")
    @patch("os.stat")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_get_attachments_with_unicode_filenames(
        self,
        mock_asset_crud_obj,
        mock_stat,
        mock_join,
        mock_listdir,
        mock_exists,
        mock_db,
        mock_regular_user,
        mock_asset,
    ):
        """Test getting attachments with Unicode filenames"""
        from src.api.v1.asset_attachments import get_asset_attachments

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_exists.return_value = True
        mock_listdir.return_value = ["文档.pdf", "文件.pdf"]
        mock_join.return_value = "uploads/attachments/asset-123/文档.pdf"

        mock_file_stat = MagicMock()
        mock_file_stat.st_size = 1024
        mock_file_stat.st_mtime = 1234567890.0
        mock_stat.return_value = mock_file_stat

        result = await get_asset_attachments(
            asset_id="asset-123",
            db=mock_db,
            current_user=mock_regular_user,
        )

        assert len(result) == 2
        assert result[0]["id"] == "文档.pdf"

    @patch("src.utils.file_security.validate_upload_file")
    @patch("src.utils.file_security.create_safe_upload_directory")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_upload_attachment_with_unicode_filename(
        self,
        mock_asset_crud_obj,
        mock_create_dir,
        mock_validate_file,
        mock_db,
        mock_admin_user,
        mock_asset,
    ):
        """Test uploading attachment with Unicode filename"""
        from src.api.v1.asset_attachments import upload_asset_attachments

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_create_dir.return_value = Path("uploads/attachments/asset-123")
        mock_validate_file.return_value = {
            "valid": True,
            "safe_filename": "文档_2024.pdf",
            "errors": [],
        }

        file = MagicMock(spec=UploadFile)
        file.filename = "文档 2024.pdf"
        file.content_type = "application/pdf"
        file.file = io.BytesIO(b"%PDF-1.4")
        file.file.seek = Mock(return_value=None)
        file.file.tell = Mock(return_value=10)

        m_open = mock_open()

        with patch("builtins.open", m_open):
            result = await upload_asset_attachments(
                asset_id="asset-123",
                files=[file],
                db=mock_db,
                current_user=mock_admin_user,
            )

        assert len(result["success"]) == 1

    @patch("os.path.exists")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_download_attachment_with_unicode_filename(
        self, mock_asset_crud_obj, mock_exists, mock_db, mock_regular_user, mock_asset
    ):
        """Test downloading attachment with Unicode filename"""
        from src.api.v1.asset_attachments import download_asset_attachment

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_exists.return_value = True

        with patch("src.api.v1.asset_attachments.FileResponse") as mock_file_response:
            mock_response = MagicMock()
            mock_file_response.return_value = mock_response

            result = await download_asset_attachment(
                asset_id="asset-123",
                filename="文档.pdf",
                db=mock_db,
                current_user=mock_regular_user,
            )

            assert result == mock_response

    @patch("src.utils.file_security.validate_upload_file")
    @patch("src.utils.file_security.create_safe_upload_directory")
    @patch("src.api.v1.asset_attachments.asset_crud")
    @pytest.mark.asyncio
    async def test_upload_attachment_validates_all_files_before_failing(
        self,
        mock_asset_crud_obj,
        mock_create_dir,
        mock_validate_file,
        mock_db,
        mock_admin_user,
        mock_asset,
    ):
        """Test that all files are validated even if some fail"""
        from src.api.v1.asset_attachments import upload_asset_attachments

        mock_asset_crud_obj.get.return_value = mock_asset
        mock_create_dir.return_value = Path("uploads/attachments/asset-123")

        # Create 3 files - first succeeds, second fails, third succeeds
        files = []
        for i in range(3):
            file = MagicMock(spec=UploadFile)
            file.filename = f"file{i}.pdf" if i != 1 else f"file{i}.txt"
            file.content_type = "application/pdf" if i != 1 else "text/plain"
            file.file = io.BytesIO(b"%PDF-1.4")
            file.file.seek = Mock(return_value=None)
            file.file.tell = Mock(return_value=10)
            files.append(file)

        call_count = [0]

        def validate_side_effect(filename, content_type, file_size, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                return {
                    "valid": False,
                    "safe_filename": None,
                    "errors": ["不支持的文件类型"],
                }
            return {
                "valid": True,
                "safe_filename": filename,
                "errors": [],
            }

        mock_validate_file.side_effect = validate_side_effect

        m_open = mock_open()

        with patch("builtins.open", m_open):
            result = await upload_asset_attachments(
                asset_id="asset-123",
                files=files,
                db=mock_db,
                current_user=mock_admin_user,
            )

        assert len(result["success"]) == 2
        assert len(result["failed"]) == 1
        assert "成功上传 2 个文件，失败 1 个文件" in result["message"]
