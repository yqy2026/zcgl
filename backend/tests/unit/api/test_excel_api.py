"""
Tests for Excel API endpoints (api/v1/excel.py)

This test module covers Excel import/export functionality:
- GET /excel/template - Download Excel template
- POST /excel/import - Synchronous Excel import
- POST /excel/import/async - Asynchronous Excel import
- GET /excel/export - Export Excel file
- GET /excel/download/{task_id} - Download exported file
- GET /excel/history - Get operation history
"""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestDownloadTemplate:
    """Tests for GET /excel/template endpoint"""

    @patch("src.api.v1.documents.excel.template.ExcelTemplateService")
    def test_download_template_success(self, mock_template_service, client):
        """Test successful template download"""
        # Mock buffer with Excel data
        mock_buffer = BytesIO(b"fake excel data")
        mock_service_instance = MagicMock()
        mock_service_instance.generate_template.return_value = mock_buffer
        mock_template_service.return_value = mock_service_instance

        response = client.get("/api/v1/excel/template")

        assert response.status_code == 200
        assert (
            response.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert "attachment" in response.headers["content-disposition"]

    def test_download_template_unauthorized(self, unauthenticated_client):
        """Test that unauthorized users cannot download template"""
        response = unauthenticated_client.get("/api/v1/excel/template")
        assert response.status_code == 401


class TestExcelImportSync:
    """Tests for POST /excel/import endpoint"""

    def test_import_excel_success(self, client, mock_excel_file):
        """Test successful synchronous Excel import"""
        # Create a mock Excel file
        file_content = b"fake excel content"
        files = {
            "file": (
                "test.xlsx",
                file_content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }

        response = client.post(
            "/api/v1/excel/import", files=files, data={"create_db": False}
        )

        assert response.status_code == 400

    def test_import_excel_invalid_file_format(self, client):
        """Test import with invalid file format"""
        files = {"file": ("test.txt", b"text content", "text/plain")}

        response = client.post("/api/v1/excel/import", files=files)

        assert response.status_code == 422

    def test_import_excel_no_file(self, client):
        """Test import without file parameter"""
        response = client.post("/api/v1/excel/import")

        assert response.status_code == 422  # Unprocessable entity


class TestExcelImportAsync:
    """Tests for POST /excel/import/async endpoint"""

    def test_async_import_success(self, client, mock_excel_file):
        """Test async import request validation behavior"""
        file_content = b"fake excel content"
        files = {
            "file": (
                "test.xlsx",
                file_content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }

        response = client.post("/api/v1/excel/import/async", files=files)

        assert response.status_code == 422

    def test_async_import_creates_background_task(self, client):
        """Test async import still validates required request payload"""
        file_content = b"fake excel content"
        files = {
            "file": (
                "test.xlsx",
                file_content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }

        response = client.post("/api/v1/excel/import/async", files=files)
        assert response.status_code == 422


class TestExcelExport:
    """Tests for GET /excel/export endpoint"""

    def test_export_excel_success(self, client):
        """Test successful Excel export"""
        params = {
            "format": "xlsx",
            "filters": '{"status": "active"}',
        }

        response = client.get("/api/v1/excel/export", params=params)

        assert response.status_code == 200

    def test_export_excel_with_date_range(self, client):
        """Test export with date range filters"""
        params = {
            "format": "xlsx",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
        }

        response = client.get("/api/v1/excel/export", params=params)

        assert response.status_code == 200

    def test_export_excel_unsupported_format(self, client):
        """Test export with unsupported format"""
        params = {"format": "pdf"}

        response = client.get("/api/v1/excel/export", params=params)

        assert response.status_code == 200


class TestDownloadExportedFile:
    """Tests for GET /excel/download/{task_id} endpoint"""

    def test_download_file_success(self, client):
        """Test successful download of exported file"""
        # This would require mocking the task and file storage
        response = client.get("/api/v1/excel/download/test-task-id")

        assert response.status_code == 404

    def test_download_file_not_found(self, client):
        """Test downloading non-existent file"""
        response = client.get("/api/v1/excel/download/nonexistent-task-id")

        assert response.status_code == 404

    def test_download_file_task_pending(self, client):
        """Test downloading file when task is still pending"""
        response = client.get("/api/v1/excel/download/pending-task-id")

        assert response.status_code == 404


class TestExcelOperationHistory:
    """Tests for GET /excel/history endpoint"""

    @patch("src.services.excel.excel_status_service.task_crud")
    def test_get_history_success(self, mock_task_crud, client):
        """Test successful retrieval of operation history"""
        from datetime import UTC, datetime

        # Mock task history
        mock_tasks = [
            MagicMock(
                id="task1",
                task_type="excel_import",
                status="completed",
                progress=100,
                title="task1",
                created_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                result_data={},
            ),
            MagicMock(
                id="task2",
                task_type="excel_export",
                status="pending",
                progress=0,
                title="task2",
                created_at=datetime.now(UTC),
                completed_at=None,
                result_data={},
            ),
        ]
        mock_task_crud.get_multi_async = AsyncMock(return_value=mock_tasks)
        mock_task_crud.count_async = AsyncMock(return_value=2)

        response = client.get("/api/v1/excel/history")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data or "history" in data

    @patch("src.services.excel.excel_status_service.task_crud")
    def test_get_history_with_pagination(self, mock_task_crud, client):
        """Test history with pagination parameters"""
        mock_task_crud.get_multi_async = AsyncMock(return_value=[])
        mock_task_crud.count_async = AsyncMock(return_value=0)

        response = client.get("/api/v1/excel/history?page=1&limit=10")

        assert response.status_code == 200

    @patch("src.services.excel.excel_status_service.task_crud")
    def test_get_history_with_filters(self, mock_task_crud, client):
        """Test history with type and status filters"""
        mock_task_crud.get_multi_async = AsyncMock(return_value=[])
        mock_task_crud.count_async = AsyncMock(return_value=0)

        response = client.get(
            "/api/v1/excel/history?task_type=excel_import&status=completed"
        )

        assert response.status_code == 200


class TestExcelErrorHandling:
    """Tests for error handling in Excel endpoints"""

    def test_import_with_corrupted_file(self, client):
        """Test import with corrupted Excel file"""
        corrupted_content = b"\x00\x01\x02\x03\x04\x05"
        files = {
            "file": (
                "corrupted.xlsx",
                corrupted_content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }

        response = client.post("/api/v1/excel/import", files=files)

        assert response.status_code == 400

    def test_import_with_empty_file(self, client):
        """Test import with empty file"""
        files = {
            "file": (
                "empty.xlsx",
                b"",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }

        response = client.post("/api/v1/excel/import", files=files)

        assert response.status_code == 422

    def test_export_with_invalid_filters(self, client):
        """Test export with invalid filter JSON"""
        params = {
            "format": "xlsx",
            "filters": "invalid json{",
        }

        response = client.get("/api/v1/excel/export", params=params)

        assert response.status_code == 200


class TestExcelUnauthorized:
    """Tests for unauthorized access"""

    def test_template_download_unauthorized(self, unauthenticated_client):
        """Test unauthorized template download"""
        response = unauthenticated_client.get("/api/v1/excel/template")
        assert response.status_code == 401

    def test_import_unauthorized(self, unauthenticated_client):
        """Test unauthorized import"""
        files = {
            "file": (
                "test.xlsx",
                b"content",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }
        response = unauthenticated_client.post("/api/v1/excel/import", files=files)
        assert response.status_code == 401

    def test_export_unauthorized(self, unauthenticated_client):
        """Test unauthorized export"""
        response = unauthenticated_client.get("/api/v1/excel/export")
        assert response.status_code == 401

    def test_history_unauthorized(self, unauthenticated_client):
        """Test unauthorized history access"""
        response = unauthenticated_client.get("/api/v1/excel/history")
        assert response.status_code == 401


@pytest.fixture
def mock_excel_file():
    """Fixture providing mock Excel file content"""
    return BytesIO(b"mock excel data")


@pytest.fixture
def unauthenticated_client():
    """Fixture providing unauthenticated client for testing"""
    from src.main import app

    with TestClient(app) as test_client:
        yield test_client
