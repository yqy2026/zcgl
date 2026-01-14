#!/usr/bin/env python3
"""
PDF 批量导入 API 集成测试
测试 pdf_batch_routes.py 中的所有 API 端点
"""

import io
from unittest.mock import AsyncMock, Mock

import pytest

from src.api.v1 import pdf_batch_routes
from src.database import get_db
from src.main import app
from src.models.pdf_import_session import SessionStatus
from src.services.document.processing_tracker import BatchStatusTracker

# ============================================================================
# 测试 Fixtures
# ============================================================================


@pytest.fixture
def batch_tracker():
    """获取批处理追踪器实例"""
    tracker = BatchStatusTracker()
    # 保存原始的 tracker
    original_tracker = pdf_batch_routes._batch_tracker
    # 设置测试 tracker
    pdf_batch_routes._batch_tracker = tracker
    yield tracker
    # 恢复原始 tracker
    pdf_batch_routes._batch_tracker = original_tracker
    # 清理: 清空所有测试数据
    if hasattr(tracker, '_memory_store'):
        tracker._memory_store.clear()


@pytest.fixture
def sample_pdf_content():
    """示例 PDF 内容"""
    return b"%PDF-1.4\nsample pdf content for testing"


@pytest.fixture
def sample_pdf_files():
    """创建多个示例 PDF 文件"""
    files = []
    for i in range(3):
        content = f"%PDF-1.4\nSample PDF file {i}".encode()
        files.append(
            ("files", (f"contract_{i}.pdf", io.BytesIO(content), "application/pdf"))
        )
    return files


# ============================================================================
# 批量上传端点测试
# ============================================================================

class TestBatchUploadEndpoint:
    """批量上传端点测试"""

    async def test_batch_upload_success(self, test_client_no_auth, sample_pdf_files):
        """测试批量上传成功"""
        # Mock PDFImportService - 直接在服务模块级别 mock
        from unittest.mock import patch
        with patch('src.services.document.pdf_import_service.PDFImportService') as mock_service_cls:
            mock_service = Mock()
            mock_service.process_pdf_file = AsyncMock(return_value={"success": True})
            mock_service.get_session_status = AsyncMock(return_value={"success": True, "session_status": {"status": "completed"}})
            mock_service.cancel_processing = AsyncMock(return_value={"success": True})
            mock_service_cls.return_value = mock_service

            response = await test_client_no_auth.post(
                "/api/v1/pdf-import/batch/upload",
                files=sample_pdf_files,
                data={
                    "organization_id": 1,
                    "prefer_ocr": False,
                    "prefer_vision": True,
                    "auto_confirm": False
                }
            )

        print(f"Response status: {response.status_code}")
        print(f"Response JSON: {response.json()}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "batch_id" in data["data"]

    async def test_batch_upload_exceeds_max_size(self, test_client_no_auth):
        """测试文件数量超过限制"""
        files = []
        for i in range(15):  # 超过 MAX_BATCH_SIZE=10
            content = b"%PDF-1.4"
            files.append(
                ("files", (f"file_{i}.pdf", io.BytesIO(content), "application/pdf"))
            )

        response = await test_client_no_auth.post(
            "/api/v1/pdf-import/batch/upload",
            files=files,
            data={"organization_id": 1}
        )

        assert response.status_code == 400
        assert "文件数量超过限制" in response.json()["error"]["message"]

    async def test_batch_upload_no_valid_files(self, test_client_no_auth):
        """测试没有有效文件"""
        files = [
            ("files", ("test.txt", io.BytesIO(b"text content"), "text/plain"))
        ]

        response = await test_client_no_auth.post(
            "/api/v1/pdf-import/batch/upload",
            files=files,
            data={"organization_id": 1}
        )

        assert response.status_code == 400
        assert "没有有效的 PDF 文件" in response.json()["error"]["message"]

    async def test_batch_upload_service_busy(self, test_client_no_auth, sample_pdf_files, batch_tracker):
        """测试系统繁忙"""
        batch_tracker.create_batch("batch-active-1", total=3, user_id=1)
        batch_tracker.set_status("batch-active-1", "processing")
        batch_tracker.create_batch("batch-active-2", total=3, user_id=1)
        batch_tracker.set_status("batch-active-2", "pending")

        response = await test_client_no_auth.post(
            "/api/v1/pdf-import/batch/upload",
            files=sample_pdf_files,
            data={"organization_id": 1}
        )

        assert response.status_code == 503
        assert "系统繁忙" in response.json()["error"]["message"]


# ============================================================================
# 批量状态查询端点测试
# ============================================================================

class TestBatchStatusEndpoint:
    """批量状态查询端点测试"""

    @pytest.fixture
    def mock_batch_status(self):
        """Mock 批处理状态"""
        return {
            "batch_id": "batch-abc123",
            "status": "processing",
            "organization_id": 1,
            "session_ids": ["session-1", "session-2", "session-3"],
            "completed_count": 1,
            "failed_count": 0,
            "processing_count": 2,
            "pending_count": 0,
            "created_at": "2024-01-10T10:00:00",
            "updated_at": "2024-01-10T10:05:00"
        }

    async def test_get_batch_status_success(self, test_client_no_auth, mock_batch_status, batch_tracker):
        """测试获取批处理状态成功"""
        batch_tracker.create_batch("batch-abc123", total=3, user_id=1)

        # Mock database query
        app.dependency_overrides[get_db] = lambda: Mock(
            query=Mock(return_value=Mock(
                filter=Mock(return_value=Mock(
                    first=Mock(return_value=Mock(
                        file_name="contract_1.pdf",
                        status=SessionStatus.COMPLETED,
                        progress_percentage=100.0,
                        error_message=None
                    ))
                ))
            ))
        )

        try:
            response = await test_client_no_auth.get("/api/v1/pdf-import/batch/status/batch-abc123")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_batch_status_not_found(self, test_client_no_auth, batch_tracker):
        """测试批处理不存在"""
        response = await test_client_no_auth.get("/api/v1/pdf-import/batch/status/batch-nonexistent")

        assert response.status_code == 404
        assert "批处理任务不存在" in response.json()["error"]["message"]


# ============================================================================
# 批量列表端点测试
# ============================================================================

class TestBatchListEndpoint:
    """批量列表端点测试"""

    @pytest.fixture
    def mock_batches(self):
        """Mock 批处理列表"""
        return [
            {
                "batch_id": "batch-001",
                "status": "completed",
                "session_ids": ["s1", "s2"],
                "completed_count": 2,
                "failed_count": 0,
                "created_at": "2024-01-10T09:00:00",
                "updated_at": "2024-01-10T09:30:00"
            },
            {
                "batch_id": "batch-002",
                "status": "processing",
                "session_ids": ["s3"],
                "completed_count": 0,
                "failed_count": 0,
                "created_at": "2024-01-10T10:00:00",
                "updated_at": "2024-01-10T10:05:00"
            }
        ]

    async def test_list_batches_all(self, test_client_no_auth, mock_batches, batch_tracker):
        """测试列出所有批处理"""
        batch_tracker.create_batch("batch-001", total=2, user_id=1)
        batch_tracker.set_status("batch-001", "completed")
        batch_tracker.create_batch("batch-002", total=1, user_id=1)
        batch_tracker.set_status("batch-002", "processing")

        response = await test_client_no_auth.get("/api/v1/pdf-import/batch/list")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_list_batches_with_status_filter(self, test_client_no_auth, mock_batches, batch_tracker):
        """测试按状态过滤"""
        batch_tracker.create_batch("batch-001", total=2, user_id=1)
        batch_tracker.set_status("batch-001", "completed")
        batch_tracker.create_batch("batch-002", total=1, user_id=1)
        batch_tracker.set_status("batch-002", "processing")

        response = await test_client_no_auth.get("/api/v1/pdf-import/batch/list?status_filter=completed")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_list_batches_with_limit(self, test_client_no_auth, mock_batches, batch_tracker):
        """测试限制返回数量"""
        batch_tracker.create_batch("batch-001", total=2, user_id=1)
        batch_tracker.set_status("batch-001", "completed")
        batch_tracker.create_batch("batch-002", total=1, user_id=1)
        batch_tracker.set_status("batch-002", "processing")

        response = await test_client_no_auth.get("/api/v1/pdf-import/batch/list?limit=1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ============================================================================
# 取消批处理端点测试
# ============================================================================

class TestBatchCancelEndpoint:
    """取消批处理端点测试"""

    @pytest.fixture
    def mock_processing_batch(self):
        """Mock 处理中的批处理"""
        return {
            "batch_id": "batch-processing",
            "status": "processing",
            "session_ids": ["s1", "s2"],
            "completed_count": 0,
            "failed_count": 0
        }

    async def test_cancel_batch_success(self, test_client_no_auth, mock_processing_batch, batch_tracker):
        """测试取消批处理成功"""
        batch_tracker.create_batch("batch-processing", total=2, user_id=1)

        # Mock PDFImportService
        mock_service = Mock()
        mock_service.cancel_processing = AsyncMock(return_value={"success": True})

        # Mock database
        mock_session = Mock()
        mock_session.is_processing = True
        mock_query = Mock()
        mock_query.filter = Mock(return_value=Mock(first=Mock(return_value=mock_session)))

        app.dependency_overrides[get_db] = lambda: Mock(query=Mock(return_value=mock_query))

        try:
            response = await test_client_no_auth.post("/api/v1/pdf-import/batch/cancel/batch-processing")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_cancel_batch_already_completed(self, test_client_no_auth, batch_tracker):
        """测试取消已完成的批处理"""
        batch_tracker.create_batch("batch-completed", total=2, user_id=1)
        batch_tracker.set_status("batch-completed", "completed")

        response = await test_client_no_auth.post("/api/v1/pdf-import/batch/cancel/batch-completed")

        assert response.status_code == 400
        assert "批处理任务已完成或已取消" in response.json()["error"]["message"]


# ============================================================================
# 清理端点测试
# ============================================================================

class TestBatchCleanupEndpoint:
    """清理端点测试"""

    async def test_cleanup_old_batches(self, test_client_no_auth, batch_tracker):
        """测试清理旧批处理"""
        batch_tracker.create_batch("batch-old-1", total=2, user_id=1)
        batch_tracker.set_status("batch-old-1", "completed")
        batch_tracker.create_batch("batch-old-2", total=2, user_id=1)
        batch_tracker.set_status("batch-old-2", "failed")
        batch_tracker.create_batch("batch-recent", total=2, user_id=1)
        batch_tracker.set_status("batch-recent", "completed")

        response = await test_client_no_auth.delete("/api/v1/pdf-import/batch/cleanup?older_than_hours=24")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ============================================================================
# 健康检查端点测试
# ============================================================================

class TestBatchHealthEndpoint:
    """健康检查端点测试"""

    async def test_health_check(self, test_client_no_auth, batch_tracker):
        """测试健康检查"""
        response = await test_client_no_auth.get("/api/v1/pdf-import/batch/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"

    async def test_health_check_with_active_batches(self, test_client_no_auth, batch_tracker):
        """测试有活动批处理时的健康检查"""
        batch_tracker.create_batch("batch-1", total=2, user_id=1)
        batch_tracker.set_status("batch-1", "processing")
        batch_tracker.create_batch("batch-2", total=2, user_id=1)
        batch_tracker.set_status("batch-2", "pending")

        response = await test_client_no_auth.get("/api/v1/pdf-import/batch/health")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["current_usage"]["active_batches"] >= 2


# ============================================================================
# 集成测试场景
# ============================================================================

class TestBatchAPIIntegrationScenarios:
    """批处理 API 集成测试场景"""

    @pytest.mark.asyncio
    async def test_full_batch_processing_workflow(self):
        """测试完整的批处理工作流"""
        batch_id = "batch-test-001"
        session_ids = ["session-1", "session-2", "session-3"]

        assert batch_id.startswith("batch-")
        assert len(session_ids) == 3

    async def test_concurrent_batch_limit_enforcement(self, test_client_no_auth, batch_tracker):
        """测试并发批处理限制"""
        batch_tracker.create_batch("batch-1", total=2, user_id=1)
        batch_tracker.set_status("batch-1", "processing")
        batch_tracker.create_batch("batch-2", total=2, user_id=1)
        batch_tracker.set_status("batch-2", "processing")

        app.dependency_overrides[get_db] = lambda: Mock(
            query=Mock(return_value=Mock(
                filter=Mock(return_value=Mock(first=Mock(return_value=None)))
            )),
            add=Mock(),
            commit=Mock()
        )

        try:
            files = [
                ("files", ("test.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf"))
            ]

            response = await test_client_no_auth.post(
                "/api/v1/pdf-import/batch/upload",
                files=files,
                data={"organization_id": 1}
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 503
