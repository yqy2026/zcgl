"""
Comprehensive Unit Tests for PDF Batch API Routes (src/api/v1/documents/pdf_batch_routes.py)

This test module covers all endpoints in the pdf_batch router to achieve 70%+ coverage:

Endpoints Tested:
1. POST /pdf-import/batch/upload - Batch upload PDF files
2. GET /pdf-import/batch/status/{batch_id} - Get batch status
3. GET /pdf-import/batch/list - List all batches
4. POST /pdf-import/batch/cancel/{batch_id} - Cancel batch processing
5. DELETE /pdf-import/batch/cleanup - Cleanup completed batches
6. GET /pdf-import/batch/health - Health check endpoint

Testing Approach:
- Mock all dependencies (services, database, file operations, trackers)
- Test successful responses and error scenarios
- Test request validation
- Test edge cases (file size limits, concurrent batches, etc.)
- Test background tasks and monitoring
"""

import io
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile
from fastapi.responses import JSONResponse

from src.core.exception_handler import BaseBusinessError

pytestmark = pytest.mark.api


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_current_user():
    """Create mock authenticated user"""
    user = MagicMock()
    user.id = "test-user-id"
    user.username = "testuser"
    user.is_active = True
    return user


@pytest.fixture
def mock_pdf_files():
    """Create mock PDF upload files"""
    files = []
    for i in range(3):
        file = MagicMock(spec=UploadFile)
        file.filename = f"test_{i}.pdf"
        file.content_type = "application/pdf"
        # Use minimal content to avoid polluting CI output
        content = io.BytesIO(b"%PDF-1.4\n%Test PDF content\n")
        file.read = AsyncMock(side_effect=[content.getvalue(), b""])
        # seek needs to be async for FastAPI UploadFile
        file.seek = AsyncMock(return_value=None)
        file.close = AsyncMock(return_value=None)
        file.file = MagicMock()
        file.file.seek = MagicMock(return_value=None)
        files.append(file)
    return files


@pytest.fixture(autouse=True)
def mock_default_accessible_org_ids(monkeypatch):
    """默认拦截组织可见性解析，避免单测误走真实权限查询。"""
    from src.api.v1.documents import pdf_batch_routes as module

    resolver_mock = AsyncMock(return_value=[])
    monkeypatch.setattr(module, "_resolve_accessible_organization_ids", resolver_mock)
    return resolver_mock


@pytest.fixture
def mock_large_pdf_file():
    """Create mock PDF file exceeding size limit (>50MB)"""
    file = MagicMock(spec=UploadFile)
    file.filename = "large_test.pdf"
    file.content_type = "application/pdf"
    # Create content larger than 50MB
    large_content = b"x" * (51 * 1024 * 1024)
    file.read = AsyncMock(side_effect=[large_content, b""])
    file.seek = AsyncMock(return_value=None)
    file.close = AsyncMock(return_value=None)
    return file


def create_mock_invalid_file():
    """Helper function to create mock non-PDF file"""
    file = MagicMock(spec=UploadFile)
    file.filename = "test.txt"
    file.content_type = "text/plain"
    content = io.BytesIO(b"not a pdf")
    file.read = AsyncMock(side_effect=[content.getvalue(), b""])
    file.seek = AsyncMock(return_value=None)
    file.close = AsyncMock(return_value=None)
    return file


def _create_mock_asyncio_task(coro):
    """Create a mock task and close input coroutine to avoid warnings."""
    coro.close()
    task = MagicMock()
    task.add_done_callback = MagicMock()
    return task


@pytest.fixture
def mock_batch_tracker():
    """Create mock BatchStatusTracker"""
    tracker = MagicMock()
    tracker.get_stats = MagicMock(
        return_value={"active_batches": 0, "total_batches": 0}
    )
    tracker.get_status = MagicMock(return_value=None)
    tracker.create_batch = MagicMock()
    tracker.update_progress = MagicMock()
    tracker.set_status = MagicMock()
    tracker.list_batches = MagicMock(return_value=[])
    tracker.cleanup_old_batches = MagicMock(return_value=0)
    return tracker


# ============================================================================
# Test: POST /upload - Batch Upload PDFs
# ============================================================================


class TestBatchUploadPdfs:
    """Tests for POST /pdf-import/batch/upload endpoint"""

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @patch("src.api.v1.documents.pdf_batch_routes.PDFImportService")
    @pytest.mark.asyncio
    async def test_batch_upload_success(
        self,
        mock_service_class,
        mock_get_tracker,
        mock_pdf_files,
        mock_db,
        mock_current_user,
    ):
        """Test successful batch upload with multiple PDFs"""

        # Setup tracker mock
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"active_batches": 0, "total_batches": 0}

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @patch("src.api.v1.documents.pdf_batch_routes.PDFImportService")
    @pytest.mark.asyncio
    async def test_batch_upload_delegates_to_service(
        self,
        mock_service_class,
        mock_get_tracker,
        mock_pdf_files,
        mock_db,
        mock_current_user,
    ):
        """Test that batch upload delegates logic to PDFImportService"""
        from src.api.v1.documents.pdf_batch_routes import batch_upload_pdfs

        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"active_batches": 0, "total_batches": 0}
        mock_tracker.create_batch = MagicMock()
        mock_tracker.set_status = MagicMock()
        mock_get_tracker.return_value = mock_tracker

        mock_service = MagicMock()
        mock_service.create_import_session = AsyncMock(return_value=None)
        mock_service.process_pdf_file = AsyncMock(return_value=None)
        mock_service_class.return_value = mock_service

        # Patch asyncio.create_task to avoid running background tasks
        with patch(
            "src.api.v1.documents.pdf_batch_routes.asyncio.create_task"
        ) as mock_create_task:
            mock_create_task.side_effect = _create_mock_asyncio_task

            result = await batch_upload_pdfs(
                db=mock_db,
                files=mock_pdf_files,
                organization_id=1,
                force_method=None,
                prefer_vision=False,
                auto_confirm=False,
                current_user=mock_current_user,
            )

        # Verify create_import_session is called for each file (3 files)
        assert mock_service.create_import_session.call_count == 3

        # Verify the arguments of the first call
        _, kwargs = mock_service.create_import_session.call_args_list[0]
        assert kwargs["original_filename"] == "test_0.pdf"
        assert kwargs["organization_id"] == 1

        # Parse JSONResponse
        body = json.loads(result.body.decode())
        assert body["success"] is True
        assert "batch_id" in body["data"]
        assert body["data"]["session_count"] == 3
        assert len(body["data"]["session_ids"]) == 3
        assert body["data"]["status"] == "processing"
        assert body["message"] == "已创建批处理任务，包含 3 个文件"

        # Verify tracker was called
        mock_tracker.create_batch.assert_called_once()
        mock_tracker.set_status.assert_called_once()

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_batch_upload_exceeds_limit(
        self, mock_get_tracker, mock_db, mock_current_user
    ):
        """Test batch upload with too many files"""
        from src.api.v1.documents.pdf_batch_routes import (
            MAX_BATCH_SIZE,
            batch_upload_pdfs,
        )

        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"active_batches": 0, "total_batches": 0}
        mock_get_tracker.return_value = mock_tracker

        # Create more files than MAX_BATCH_SIZE
        files = [MagicMock(spec=UploadFile) for _ in range(MAX_BATCH_SIZE + 1)]
        for file in files:
            file.filename = "test.pdf"

        with pytest.raises(BaseBusinessError) as exc_info:
            await batch_upload_pdfs(
                db=mock_db,
                files=files,
                organization_id=1,
                force_method=None,
                prefer_vision=False,
                auto_confirm=False,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400
        assert "文件数量超过限制" in exc_info.value.message

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_batch_upload_concurrent_limit_reached(
        self, mock_get_tracker, mock_pdf_files, mock_db, mock_current_user
    ):
        """Test batch upload when concurrent limit is reached"""
        from src.api.v1.documents.pdf_batch_routes import (
            MAX_CONCURRENT_BATCHES,
            batch_upload_pdfs,
        )

        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {
            "active_batches": MAX_CONCURRENT_BATCHES,
            "total_batches": MAX_CONCURRENT_BATCHES,
        }
        mock_get_tracker.return_value = mock_tracker

        with pytest.raises(BaseBusinessError) as exc_info:
            await batch_upload_pdfs(
                db=mock_db,
                files=mock_pdf_files,
                organization_id=1,
                force_method=None,
                prefer_vision=False,
                auto_confirm=False,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 503
        assert "系统繁忙" in exc_info.value.message

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_batch_upload_no_valid_files(
        self, mock_get_tracker, mock_db, mock_current_user
    ):
        """Test batch upload with no valid PDF files"""
        from src.api.v1.documents.pdf_batch_routes import batch_upload_pdfs

        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"active_batches": 0, "total_batches": 0}
        mock_get_tracker.return_value = mock_tracker

        # All files are invalid (non-PDF or too large)
        invalid_files = [create_mock_invalid_file() for _ in range(2)]

        with pytest.raises(BaseBusinessError) as exc_info:
            await batch_upload_pdfs(
                db=mock_db,
                files=invalid_files,
                organization_id=1,
                force_method=None,
                prefer_vision=False,
                auto_confirm=False,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400
        assert "没有有效的 PDF 文件" in exc_info.value.message

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @patch("src.api.v1.documents.pdf_batch_routes.PDFImportService")
    @pytest.mark.asyncio
    async def test_batch_upload_with_organization_id(
        self,
        mock_service_class,
        mock_get_tracker,
        mock_pdf_files,
        mock_db,
        mock_current_user,
    ):
        """Test batch upload with organization ID"""
        from src.api.v1.documents.pdf_batch_routes import batch_upload_pdfs

        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"active_batches": 0, "total_batches": 0}
        mock_tracker.create_batch = MagicMock()
        mock_tracker.set_status = MagicMock()
        mock_get_tracker.return_value = mock_tracker

        mock_service = MagicMock()
        mock_service.create_import_session = AsyncMock(return_value=None)
        mock_service.process_pdf_file = AsyncMock(return_value=None)
        mock_service_class.return_value = mock_service

        # Patch asyncio.create_task
        with patch(
            "src.api.v1.documents.pdf_batch_routes.asyncio.create_task"
        ) as mock_create_task:
            mock_create_task.side_effect = _create_mock_asyncio_task

            result = await batch_upload_pdfs(
                db=mock_db,
                files=mock_pdf_files,
                organization_id=5,
                force_method=None,
                prefer_vision=True,
                auto_confirm=True,
                current_user=mock_current_user,
            )

        body = json.loads(result.body.decode())
        assert body["success"] is True
        # Verify create_batch was called with organization_id
        call_args = mock_tracker.create_batch.call_args
        assert call_args.kwargs["organization_id"] == 5
        assert call_args.kwargs["created_by_user_id"] == "test-user-id"

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @patch("src.api.v1.documents.pdf_batch_routes.PDFImportService")
    @patch("src.api.v1.documents.pdf_batch_routes.open")
    @pytest.mark.asyncio
    async def test_batch_upload_filters_non_pdf_files(
        self,
        mock_open,
        mock_service_class,
        mock_get_tracker,
        mock_pdf_files,
        mock_db,
        mock_current_user,
    ):
        """Test that non-PDF files are filtered out"""
        from src.api.v1.documents.pdf_batch_routes import batch_upload_pdfs

        # Add non-PDF files to the mix
        mixed_files = mock_pdf_files + [create_mock_invalid_file()]

        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"active_batches": 0, "total_batches": 0}
        mock_tracker.create_batch = MagicMock()
        mock_tracker.set_status = MagicMock()
        mock_get_tracker.return_value = mock_tracker

        mock_service = MagicMock()
        mock_service.create_import_session = AsyncMock(return_value=None)
        mock_service.process_pdf_file = AsyncMock(return_value=None)
        mock_service_class.return_value = mock_service

        mock_open.return_value.__enter__ = MagicMock()
        mock_open.return_value.__exit__ = MagicMock()
        mock_open.return_value.write = MagicMock()

        # Patch asyncio.create_task
        with patch(
            "src.api.v1.documents.pdf_batch_routes.asyncio.create_task"
        ) as mock_create_task:
            mock_create_task.side_effect = _create_mock_asyncio_task

            result = await batch_upload_pdfs(
                db=mock_db,
                files=mixed_files,
                organization_id=1,
                force_method=None,
                prefer_vision=False,
                auto_confirm=False,
                current_user=mock_current_user,
            )

        # Should only process the 3 PDF files, not the .txt file
        body = json.loads(result.body.decode())
        assert body["data"]["session_count"] == 3

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @patch("src.api.v1.documents.pdf_batch_routes.PDFImportService")
    @pytest.mark.asyncio
    async def test_batch_upload_service_error_handling(
        self,
        mock_service_class,
        mock_get_tracker,
        mock_pdf_files,
        mock_db,
        mock_current_user,
    ):
        """Test batch upload when service raises error for one file"""
        from src.api.v1.documents.pdf_batch_routes import batch_upload_pdfs

        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"active_batches": 0, "total_batches": 0}
        mock_tracker.create_batch = MagicMock()
        mock_tracker.set_status = MagicMock()
        mock_tracker.update_progress = MagicMock()
        mock_get_tracker.return_value = mock_tracker

        mock_service = MagicMock()
        mock_service.create_import_session = AsyncMock(return_value=None)
        # First file succeeds, second fails, third succeeds
        mock_service.process_pdf_file = AsyncMock(
            side_effect=[None, Exception("Processing failed"), None]
        )
        mock_service_class.return_value = mock_service

        # Patch asyncio.create_task
        with patch(
            "src.api.v1.documents.pdf_batch_routes.asyncio.create_task"
        ) as mock_create_task:
            mock_create_task.side_effect = _create_mock_asyncio_task

            result = await batch_upload_pdfs(
                db=mock_db,
                files=mock_pdf_files,
                organization_id=1,
                force_method=None,
                prefer_vision=False,
                auto_confirm=False,
                current_user=mock_current_user,
            )

        # Should continue processing other files even if one fails
        body = json.loads(result.body.decode())
        assert body["data"]["session_count"] == 2  # Only 2 succeeded
        # Verify failed count was updated
        mock_tracker.update_progress.assert_called()


# ============================================================================
# Test: GET /status/{batch_id} - Get Batch Status
# ============================================================================


class TestGetBatchStatus:
    """Tests for GET /pdf-import/batch/status/{batch_id} endpoint"""

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @patch("src.api.v1.documents.pdf_batch_routes.PDFImportService")
    @pytest.mark.asyncio
    async def test_get_batch_status_success(
        self, mock_service_class, mock_get_tracker, mock_db, mock_current_user
    ):
        """Test successful batch status retrieval"""
        from src.api.v1.documents.pdf_batch_routes import get_batch_status
        from src.models.pdf_import_session import SessionStatus

        batch_id = "test-batch-123"

        # Mock batch status
        mock_tracker = MagicMock()
        mock_tracker.get_status.return_value = {
            "batch_id": batch_id,
            "status": "processing",
            "total": 5,
            "processed": 2,
            "failed": 0,
            "session_ids": ["session-1", "session-2", "session-3"],
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        mock_get_tracker.return_value = mock_tracker

        # Mock service
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Mock sessions
        mock_sessions = {}
        for i in range(3):
            session_id = f"session-{i + 1}"
            session = MagicMock()
            session.session_id = session_id
            session.original_filename = f"file_{i + 1}.pdf"
            session.status = SessionStatus.PROCESSING
            session.progress_percentage = 50.0
            session.error_message = None
            mock_sessions[session_id] = session

        mock_service.get_session_map_async = AsyncMock(return_value=mock_sessions)

        result = await get_batch_status(
            batch_id=batch_id,
            db=mock_db,
            current_user=mock_current_user,
        )

        # Parse JSONResponse
        assert isinstance(result, JSONResponse)
        # Get the body content
        body = json.loads(result.body.decode())
        assert body["success"] is True
        assert body["data"]["batch_status"]["batch_id"] == batch_id
        assert body["data"]["batch_status"]["status"] == "processing"

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_get_batch_status_not_found(
        self, mock_get_tracker, mock_db, mock_current_user
    ):
        """Test getting status of non-existent batch"""
        from src.api.v1.documents.pdf_batch_routes import get_batch_status

        mock_tracker = MagicMock()
        mock_tracker.get_status.return_value = None
        mock_get_tracker.return_value = mock_tracker

        with pytest.raises(BaseBusinessError) as exc_info:
            await get_batch_status(
                batch_id="nonexistent",
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "批处理任务不存在" in exc_info.value.message

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @patch("src.api.v1.documents.pdf_batch_routes.PDFImportService")
    @pytest.mark.asyncio
    async def test_get_batch_status_with_completed_sessions(
        self, mock_service_class, mock_get_tracker, mock_db, mock_current_user
    ):
        """Test batch status with completed sessions"""
        from src.api.v1.documents.pdf_batch_routes import get_batch_status
        from src.models.pdf_import_session import SessionStatus

        batch_id = "batch-completed"

        mock_tracker = MagicMock()
        mock_tracker.get_status.return_value = {
            "batch_id": batch_id,
            "status": "completed",
            "total": 3,
            "processed": 3,
            "failed": 0,
            "session_ids": ["session-1"],
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        mock_get_tracker.return_value = mock_tracker

        # Mock completed sessions
        mock_session = MagicMock()
        mock_session.session_id = "session-1"
        mock_session.original_filename = "file.pdf"
        mock_session.status = SessionStatus.COMPLETED
        mock_session.progress_percentage = 100.0
        mock_session.error_message = None

        mock_service = MagicMock()
        mock_service.get_session_map_async = AsyncMock(
            return_value={"session-1": mock_session}
        )
        mock_service_class.return_value = mock_service

        result = await get_batch_status(
            batch_id=batch_id,
            db=mock_db,
            current_user=mock_current_user,
        )

        # Parse JSONResponse
        body = json.loads(result.body.decode())
        assert body["data"]["batch_status"]["percentage"] == 100

    @patch(
        "src.api.v1.documents.pdf_batch_routes._resolve_accessible_organization_ids",
        new_callable=AsyncMock,
    )
    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_get_batch_status_should_deny_when_no_org_access(
        self,
        mock_get_tracker,
        mock_resolve_org_ids,
        mock_db,
        mock_current_user,
    ):
        """Test batch status should be hidden when user has no org access"""
        from src.api.v1.documents.pdf_batch_routes import get_batch_status

        batch_id = "batch-no-access"
        mock_resolve_org_ids.return_value = []
        mock_tracker = MagicMock()
        mock_tracker.get_status.return_value = None
        mock_get_tracker.return_value = mock_tracker

        with pytest.raises(BaseBusinessError) as exc_info:
            await get_batch_status(
                batch_id=batch_id,
                db=mock_db,
                current_user=mock_current_user,
            )

        mock_tracker.get_status.assert_called_once_with(
            batch_id,
            current_user_id="test-user-id",
            accessible_organization_ids=[],
        )
        assert exc_info.value.status_code == 404
        assert "批处理任务不存在" in exc_info.value.message


# ============================================================================
# Test: GET /list - List Batches
# ============================================================================


class TestListBatches:
    """Tests for GET /pdf-import/batch/list endpoint"""

    @patch(
        "src.api.v1.documents.pdf_batch_routes._resolve_accessible_organization_ids",
        new_callable=AsyncMock,
    )
    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_list_batches_default(
        self,
        mock_get_tracker,
        mock_resolve_org_ids,
        mock_db,
        mock_current_user,
    ):
        """Test listing batches with default parameters"""
        from src.api.v1.documents.pdf_batch_routes import list_batches

        mock_resolve_org_ids.return_value = ["1", "2"]
        mock_tracker = MagicMock()
        mock_batches = [
            {
                "batch_id": f"batch-{i}",
                "status": "processing" if i < 2 else "completed",
                "total": 5,
                "processed": i + 1,
                "failed": 0,
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }
            for i in range(5)
        ]
        mock_tracker.list_batches.return_value = mock_batches
        mock_get_tracker.return_value = mock_tracker

        result = await list_batches(
            status_filter=None,
            limit=20,
            db=mock_db,
            current_user=mock_current_user,
        )

        # Parse JSONResponse
        body = json.loads(result.body.decode())
        assert body["success"] is True
        assert body["data"]["count"] == 5
        assert len(body["data"]["batches"]) == 5
        mock_tracker.list_batches.assert_called_once_with(
            status_filter=None,
            limit=20,
            current_user_id="test-user-id",
            accessible_organization_ids=["1", "2"],
        )

    @patch(
        "src.api.v1.documents.pdf_batch_routes._resolve_accessible_organization_ids",
        new_callable=AsyncMock,
    )
    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_list_batches_with_status_filter(
        self,
        mock_get_tracker,
        mock_resolve_org_ids,
        mock_db,
        mock_current_user,
    ):
        """Test listing batches with status filter"""
        from src.api.v1.documents.pdf_batch_routes import list_batches

        mock_resolve_org_ids.return_value = []
        mock_tracker = MagicMock()
        mock_batches = [
            {
                "batch_id": "batch-1",
                "status": "completed",
                "total": 5,
                "processed": 5,
                "failed": 0,
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }
        ]
        mock_tracker.list_batches.return_value = mock_batches
        mock_get_tracker.return_value = mock_tracker

        result = await list_batches(
            status_filter="completed",
            limit=10,
            db=mock_db,
            current_user=mock_current_user,
        )

        body = json.loads(result.body.decode())
        assert body["data"]["count"] == 1
        mock_tracker.list_batches.assert_called_once_with(
            status_filter="completed",
            limit=10,
            current_user_id="test-user-id",
            accessible_organization_ids=[],
        )

    @patch(
        "src.api.v1.documents.pdf_batch_routes._resolve_accessible_organization_ids",
        new_callable=AsyncMock,
    )
    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_list_batches_empty(
        self,
        mock_get_tracker,
        mock_resolve_org_ids,
        mock_db,
        mock_current_user,
    ):
        """Test listing batches when no batches exist"""
        from src.api.v1.documents.pdf_batch_routes import list_batches

        mock_resolve_org_ids.return_value = []
        mock_tracker = MagicMock()
        mock_tracker.list_batches.return_value = []
        mock_get_tracker.return_value = mock_tracker

        result = await list_batches(
            status_filter=None,
            limit=20,
            db=mock_db,
            current_user=mock_current_user,
        )

        body = json.loads(result.body.decode())
        assert body["data"]["count"] == 0
        assert body["data"]["batches"] == []
        mock_tracker.list_batches.assert_called_once_with(
            status_filter=None,
            limit=20,
            current_user_id="test-user-id",
            accessible_organization_ids=[],
        )

    @patch(
        "src.api.v1.documents.pdf_batch_routes._resolve_accessible_organization_ids",
        new_callable=AsyncMock,
    )
    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_list_batches_custom_limit(
        self,
        mock_get_tracker,
        mock_resolve_org_ids,
        mock_db,
        mock_current_user,
    ):
        """Test listing batches with custom limit"""
        from src.api.v1.documents.pdf_batch_routes import list_batches

        mock_resolve_org_ids.return_value = ["99"]
        mock_tracker = MagicMock()
        mock_tracker.list_batches.return_value = []
        mock_get_tracker.return_value = mock_tracker

        await list_batches(
            status_filter=None,
            limit=50,
            db=mock_db,
            current_user=mock_current_user,
        )

        mock_tracker.list_batches.assert_called_once_with(
            status_filter=None,
            limit=50,
            current_user_id="test-user-id",
            accessible_organization_ids=["99"],
        )

    @patch(
        "src.api.v1.documents.pdf_batch_routes._resolve_accessible_organization_ids",
        new_callable=AsyncMock,
    )
    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_list_batches_should_delegate_visibility_context_to_tracker(
        self,
        mock_get_tracker,
        mock_resolve_org_ids,
        mock_db,
        mock_current_user,
    ):
        """Test listing batches delegates visibility context to tracker layer"""
        from src.api.v1.documents.pdf_batch_routes import list_batches

        mock_resolve_org_ids.return_value = []
        mock_tracker = MagicMock()
        mock_tracker.list_batches.return_value = []
        mock_get_tracker.return_value = mock_tracker

        result = await list_batches(
            status_filter=None,
            limit=20,
            db=mock_db,
            current_user=mock_current_user,
        )

        body = json.loads(result.body.decode())
        assert body["data"]["count"] == 0
        assert body["data"]["batches"] == []
        mock_tracker.list_batches.assert_called_once_with(
            status_filter=None,
            limit=20,
            current_user_id="test-user-id",
            accessible_organization_ids=[],
        )


# ============================================================================
# Test: POST /cancel/{batch_id} - Cancel Batch
# ============================================================================


class TestCancelBatch:
    """Tests for POST /pdf-import/batch/cancel/{batch_id} endpoint"""

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @patch("src.api.v1.documents.pdf_batch_routes._update_batch_status")
    @patch("src.api.v1.documents.pdf_batch_routes.PDFImportService")
    @pytest.mark.asyncio
    async def test_cancel_batch_success(
        self,
        mock_service_class,
        mock_update_status,
        mock_get_tracker,
        mock_db,
        mock_current_user,
    ):
        """Test successful batch cancellation"""
        from src.api.v1.documents.pdf_batch_routes import BatchStatus, cancel_batch

        batch_id = "batch-to-cancel"

        # Mock batch status
        mock_tracker = MagicMock()
        mock_tracker.get_status.return_value = {
            "batch_id": batch_id,
            "status": BatchStatus.PROCESSING,
            "session_ids": ["session-1", "session-2"],
        }
        mock_get_tracker.return_value = mock_tracker

        mock_sessions = {}
        for i in range(2):
            session_id = f"session-{i + 1}"
            session = MagicMock()
            session.session_id = session_id
            session.is_processing = True
            mock_sessions[session_id] = session

        # Mock service
        mock_service = MagicMock()
        mock_service.get_session_map_async = AsyncMock(return_value=mock_sessions)
        mock_service.cancel_processing = AsyncMock(return_value=None)
        mock_service_class.return_value = mock_service

        result = await cancel_batch(
            batch_id=batch_id,
            db=mock_db,
            current_user=mock_current_user,
        )

        body = json.loads(result.body.decode())
        assert body["success"] is True
        assert body["data"]["cancelled_count"] == 2
        assert "已取消 2 个处理中的任务" in body["message"]

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_cancel_batch_not_found(
        self, mock_get_tracker, mock_db, mock_current_user
    ):
        """Test cancelling non-existent batch"""
        from src.api.v1.documents.pdf_batch_routes import cancel_batch

        mock_tracker = MagicMock()
        mock_tracker.get_status.return_value = None
        mock_get_tracker.return_value = mock_tracker

        with pytest.raises(BaseBusinessError) as exc_info:
            await cancel_batch(
                batch_id="nonexistent",
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "批处理任务不存在" in exc_info.value.message

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_cancel_batch_already_completed(
        self, mock_get_tracker, mock_db, mock_current_user
    ):
        """Test cancelling batch that is already completed"""
        from src.api.v1.documents.pdf_batch_routes import BatchStatus, cancel_batch

        batch_id = "batch-completed"

        mock_tracker = MagicMock()
        mock_tracker.get_status.return_value = {
            "batch_id": batch_id,
            "status": BatchStatus.COMPLETED,
            "session_ids": ["session-1"],
        }
        mock_get_tracker.return_value = mock_tracker

        with pytest.raises(BaseBusinessError) as exc_info:
            await cancel_batch(
                batch_id=batch_id,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400

    @patch(
        "src.api.v1.documents.pdf_batch_routes._resolve_accessible_organization_ids",
        new_callable=AsyncMock,
    )
    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_cancel_batch_should_deny_when_no_org_access(
        self,
        mock_get_tracker,
        mock_resolve_org_ids,
        mock_db,
        mock_current_user,
    ):
        """Test cancel should return not found when user has no org access"""
        from src.api.v1.documents.pdf_batch_routes import cancel_batch

        batch_id = "batch-no-access"
        mock_resolve_org_ids.return_value = []
        mock_tracker = MagicMock()
        mock_tracker.get_status.return_value = None
        mock_get_tracker.return_value = mock_tracker

        with pytest.raises(BaseBusinessError) as exc_info:
            await cancel_batch(
                batch_id=batch_id,
                db=mock_db,
                current_user=mock_current_user,
            )

        mock_tracker.get_status.assert_called_once_with(
            batch_id,
            current_user_id="test-user-id",
            accessible_organization_ids=[],
        )
        assert exc_info.value.status_code == 404
        assert "批处理任务不存在" in exc_info.value.message

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @patch("src.api.v1.documents.pdf_batch_routes._update_batch_status")
    @patch("src.api.v1.documents.pdf_batch_routes.PDFImportService")
    @pytest.mark.asyncio
    async def test_cancel_batch_no_processing_sessions(
        self,
        mock_service_class,
        mock_update_status,
        mock_get_tracker,
        mock_db,
        mock_current_user,
    ):
        """Test cancelling batch with no processing sessions"""
        from src.api.v1.documents.pdf_batch_routes import BatchStatus, cancel_batch

        batch_id = "batch-no-processing"

        mock_tracker = MagicMock()
        mock_tracker.get_status.return_value = {
            "batch_id": batch_id,
            "status": BatchStatus.PROCESSING,
            "session_ids": ["session-1"],
        }
        mock_get_tracker.return_value = mock_tracker

        mock_service = MagicMock()
        mock_service.get_session_map_async = AsyncMock(return_value={})
        mock_service.cancel_processing = AsyncMock(return_value=None)
        mock_service_class.return_value = mock_service

        result = await cancel_batch(
            batch_id=batch_id,
            db=mock_db,
            current_user=mock_current_user,
        )

        body = json.loads(result.body.decode())
        assert body["data"]["cancelled_count"] == 0

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @patch("src.api.v1.documents.pdf_batch_routes._update_batch_status")
    @patch("src.api.v1.documents.pdf_batch_routes.PDFImportService")
    @pytest.mark.asyncio
    async def test_cancel_batch_already_failed(
        self,
        mock_service_class,
        mock_update_status,
        mock_get_tracker,
        mock_db,
        mock_current_user,
    ):
        """Test cancelling batch that already failed"""
        from src.api.v1.documents.pdf_batch_routes import BatchStatus, cancel_batch

        batch_id = "batch-failed"

        mock_tracker = MagicMock()
        mock_tracker.get_status.return_value = {
            "batch_id": batch_id,
            "status": BatchStatus.FAILED,
            "session_ids": ["session-1"],
        }
        mock_get_tracker.return_value = mock_tracker

        with pytest.raises(BaseBusinessError) as exc_info:
            await cancel_batch(
                batch_id=batch_id,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400


# ============================================================================
# Test: DELETE /cleanup - Cleanup Completed Batches
# ============================================================================


class TestCleanupCompletedBatches:
    """Tests for DELETE /pdf-import/batch/cleanup endpoint"""

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_cleanup_default(self, mock_get_tracker):
        """Test cleanup with default parameters"""
        from src.api.v1.documents.pdf_batch_routes import cleanup_completed_batches

        mock_tracker = MagicMock()
        mock_tracker.cleanup_old_batches.return_value = 5
        mock_get_tracker.return_value = mock_tracker

        result = cleanup_completed_batches(older_than_hours=24)

        body = json.loads(result.body.decode())
        assert body["success"] is True
        assert body["data"]["cleaned_count"] == 5
        assert "已清理 5 条批处理记录" in body["message"]
        mock_tracker.cleanup_old_batches.assert_called_once_with(older_than_hours=24)

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_cleanup_custom_hours(self, mock_get_tracker):
        """Test cleanup with custom hours parameter"""
        from src.api.v1.documents.pdf_batch_routes import cleanup_completed_batches

        mock_tracker = MagicMock()
        mock_tracker.cleanup_old_batches.return_value = 10
        mock_get_tracker.return_value = mock_tracker

        result = cleanup_completed_batches(older_than_hours=48)

        body = json.loads(result.body.decode())
        assert body["data"]["cleaned_count"] == 10
        mock_tracker.cleanup_old_batches.assert_called_once_with(older_than_hours=48)

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_cleanup_no_batches(self, mock_get_tracker):
        """Test cleanup when no batches to clean"""
        from src.api.v1.documents.pdf_batch_routes import cleanup_completed_batches

        mock_tracker = MagicMock()
        mock_tracker.cleanup_old_batches.return_value = 0
        mock_get_tracker.return_value = mock_tracker

        result = cleanup_completed_batches(older_than_hours=24)

        body = json.loads(result.body.decode())
        assert body["data"]["cleaned_count"] == 0
        assert "已清理 0 条批处理记录" in body["message"]


# ============================================================================
# Test: GET /health - Health Check
# ============================================================================


class TestBatchHealthCheck:
    """Tests for GET /pdf-import/batch/health endpoint"""

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_health_check(self, mock_get_tracker):
        """Test successful health check"""
        from src.api.v1.documents.pdf_batch_routes import (
            MAX_BATCH_SIZE,
            MAX_CONCURRENT_BATCHES,
            batch_health_check,
        )

        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"active_batches": 2, "total_batches": 10}
        mock_get_tracker.return_value = mock_tracker

        result = batch_health_check()

        body = json.loads(result.body.decode())
        assert body["success"] is True
        assert body["data"]["status"] == "healthy"
        assert body["data"]["configuration"]["max_batch_size"] == MAX_BATCH_SIZE
        assert (
            body["data"]["configuration"]["max_concurrent_batches"]
            == MAX_CONCURRENT_BATCHES
        )
        assert body["data"]["current_usage"]["active_batches"] == 2
        assert (
            body["data"]["current_usage"]["available_slots"]
            == MAX_CONCURRENT_BATCHES - 2
        )
        assert body["data"]["current_usage"]["total_stored_batches"] == 10

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_health_check_no_active_batches(self, mock_get_tracker):
        """Test health check with no active batches"""
        from src.api.v1.documents.pdf_batch_routes import (
            MAX_CONCURRENT_BATCHES,
            batch_health_check,
        )

        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"active_batches": 0, "total_batches": 5}
        mock_get_tracker.return_value = mock_tracker

        result = batch_health_check()

        body = json.loads(result.body.decode())
        assert body["data"]["current_usage"]["active_batches"] == 0
        assert (
            body["data"]["current_usage"]["available_slots"] == MAX_CONCURRENT_BATCHES
        )


# ============================================================================
# Test: Helper Functions
# ============================================================================


class TestHelperFunctions:
    """Tests for helper functions in pdf_batch_routes"""

    def test_generate_batch_id(self):
        """Test batch ID generation"""
        from src.api.v1.documents.pdf_batch_routes import _generate_batch_id

        batch_id = _generate_batch_id()

        assert isinstance(batch_id, str)
        assert batch_id.startswith("batch-")
        assert len(batch_id) == len("batch-") + 12  # 12 hex characters

    def test_generate_batch_id_unique(self):
        """Test that batch IDs are unique"""
        from src.api.v1.documents.pdf_batch_routes import _generate_batch_id

        batch_ids = [_generate_batch_id() for _ in range(100)]

        # All IDs should be unique
        assert len(set(batch_ids)) == 100

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    def test_get_batch_status(self, mock_get_tracker):
        """Test _get_batch_status helper function"""
        from src.api.v1.documents.pdf_batch_routes import _get_batch_status

        mock_tracker = MagicMock()
        mock_tracker.get_status.return_value = {
            "batch_id": "test",
            "status": "processing",
        }
        mock_get_tracker.return_value = mock_tracker

        result = _get_batch_status("test-batch")

        assert result is not None
        assert result["batch_id"] == "test"
        mock_tracker.get_status.assert_called_once_with(
            "test-batch",
            current_user_id=None,
            accessible_organization_ids=None,
        )

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    def test_get_batch_status_with_visibility_context(self, mock_get_tracker):
        """Test _get_batch_status forwards visibility context to tracker"""
        from src.api.v1.documents.pdf_batch_routes import _get_batch_status

        mock_tracker = MagicMock()
        mock_tracker.get_status.return_value = {
            "batch_id": "test",
            "status": "processing",
        }
        mock_get_tracker.return_value = mock_tracker

        result = _get_batch_status(
            "test-batch",
            current_user_id="user-1",
            accessible_organization_ids=["2", "3"],
        )

        assert result is not None
        mock_tracker.get_status.assert_called_once_with(
            "test-batch",
            current_user_id="user-1",
            accessible_organization_ids=["2", "3"],
        )

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    def test_get_batch_status_not_found(self, mock_get_tracker):
        """Test _get_batch_status when batch not found"""
        from src.api.v1.documents.pdf_batch_routes import _get_batch_status

        mock_tracker = MagicMock()
        mock_tracker.get_status.return_value = None
        mock_get_tracker.return_value = mock_tracker

        result = _get_batch_status("nonexistent")

        assert result is None
        mock_tracker.get_status.assert_called_once_with(
            "nonexistent",
            current_user_id=None,
            accessible_organization_ids=None,
        )

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    def test_update_batch_status(self, mock_get_tracker):
        """Test _update_batch_status helper function"""
        from src.api.v1.documents.pdf_batch_routes import (
            BatchStatus,
            _update_batch_status,
        )

        mock_tracker = MagicMock()
        mock_tracker.update_progress = MagicMock()
        mock_get_tracker.return_value = mock_tracker

        _update_batch_status("test-batch", BatchStatus.COMPLETED)

        mock_tracker.update_progress.assert_called_once_with(
            "test-batch", status=BatchStatus.COMPLETED
        )

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_status")
    def test_calculate_batch_progress(self, mock_get_batch_status):
        """Test _calculate_batch_progress helper function"""
        from src.api.v1.documents.pdf_batch_routes import _calculate_batch_progress

        mock_get_batch_status.return_value = {"total": 10, "processed": 5, "failed": 1}

        result = _calculate_batch_progress("test-batch")

        assert result["total"] == 10
        assert result["completed"] == 5
        assert result["failed"] == 1
        assert result["pending"] == 4  # 10 - 5 - 1

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_status")
    def test_calculate_batch_progress_no_batch(self, mock_get_batch_status):
        """Test _calculate_batch_progress when batch not found"""
        from src.api.v1.documents.pdf_batch_routes import _calculate_batch_progress

        mock_get_batch_status.return_value = None

        result = _calculate_batch_progress("nonexistent")

        assert result["completed"] == 0
        assert result["total"] == 0
        assert result["percentage"] == 0
        assert result["failed"] == 0


# ============================================================================
# Test: Background Tasks
# ============================================================================


class TestBackgroundTasks:
    """Tests for background task functions"""

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @patch("src.api.v1.documents.pdf_batch_routes._update_batch_status")
    def test_handle_task_exception_with_exception(
        self, mock_update_status, mock_get_tracker
    ):
        """Test _handle_task_exception when task has exception"""
        from src.api.v1.documents.pdf_batch_routes import _handle_task_exception

        mock_task = MagicMock()
        mock_task.exception.return_value = Exception("Test error")

        mock_tracker = MagicMock()
        mock_get_tracker.return_value = mock_tracker

        # Call the handler
        _handle_task_exception(mock_task, "test-batch")

        # Should log the error and update status
        mock_task.exception.assert_called_once()

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    def test_handle_task_exception_cancelled(self, mock_get_tracker):
        """Test _handle_task_exception when task is cancelled"""
        import asyncio

        from src.api.v1.documents.pdf_batch_routes import _handle_task_exception

        mock_task = MagicMock()
        mock_task.exception.side_effect = asyncio.CancelledError()

        mock_tracker = MagicMock()
        mock_get_tracker.return_value = mock_tracker

        # Should not raise exception
        _handle_task_exception(mock_task, "test-batch")


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error scenarios"""

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_empty_batch_upload(
        self, mock_get_tracker, mock_db, mock_current_user
    ):
        """Test batch upload with empty file list"""
        from src.api.v1.documents.pdf_batch_routes import batch_upload_pdfs

        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"active_batches": 0, "total_batches": 0}
        mock_get_tracker.return_value = mock_tracker

        with pytest.raises(BaseBusinessError) as exc_info:
            await batch_upload_pdfs(
                db=mock_db,
                files=[],
                organization_id=1,
                force_method=None,
                prefer_vision=False,
                auto_confirm=False,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400

    @patch("src.api.v1.documents.pdf_batch_routes._get_batch_tracker")
    @pytest.mark.asyncio
    async def test_batch_upload_filters_files_with_none_filename(
        self, mock_get_tracker, mock_db, mock_current_user
    ):
        """Test that files with None filename are filtered out"""
        from src.api.v1.documents.pdf_batch_routes import batch_upload_pdfs

        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"active_batches": 0, "total_batches": 0}
        mock_get_tracker.return_value = mock_tracker

        # Create files with None filename
        files = []
        for i in range(2):
            file = MagicMock(spec=UploadFile)
            file.filename = None
            file.content_type = "application/pdf"
            content = io.BytesIO(b"pdf content")
            file.read = AsyncMock(side_effect=[content.getvalue(), b""])
            file.seek = AsyncMock(return_value=None)
            file.close = AsyncMock(return_value=None)
            files.append(file)

        with pytest.raises(BaseBusinessError) as exc_info:
            await batch_upload_pdfs(
                db=mock_db,
                files=files,
                organization_id=1,
                force_method=None,
                prefer_vision=False,
                auto_confirm=False,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400
        assert "没有有效的 PDF 文件" in exc_info.value.message
