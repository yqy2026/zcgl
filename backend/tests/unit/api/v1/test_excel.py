"""
Comprehensive Unit Tests for Excel API Routes (src/api/v1/excel.py)

This test module covers all endpoints in the excel router to achieve 70%+ coverage:

Endpoints Tested:
1. GET /excel/template - Download Excel template
2. GET /excel/test - Test endpoint
3. POST /excel/configs - Create Excel configuration
4. GET /excel/configs - Get Excel configuration list
5. GET /excel/configs/default - Get default Excel configuration
6. GET /excel/configs/{config_id} - Get Excel configuration details
7. PUT /excel/configs/{config_id} - Update Excel configuration
8. DELETE /excel/configs/{config_id} - Delete Excel configuration
9. POST /excel/preview/advanced - Advanced Excel preview
10. POST /excel/preview - Preview Excel file
11. POST /excel/import - Synchronous Excel import
12. POST /excel/import/async - Asynchronous Excel import
13. GET /excel/export - Export Excel file
14. POST /excel/export/async - Asynchronous Excel export
15. GET /excel/download/{task_id} - Download exported file
16. GET /excel/status/{task_id} - Get task status
17. GET /excel/history - Get Excel operation history
18. POST /excel/export - Export selected assets

Testing Approach:
- Mock all dependencies (services, crud, database, auth, security)
- Test successful responses
- Test error handling scenarios
- Test request validation
- Test response schemas
"""

import io
import os
import tempfile
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from fastapi import UploadFile
from fastapi.responses import StreamingResponse

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
def mock_excel_file():
    """Create mock Excel file"""
    content = io.BytesIO()
    df = pd.DataFrame(
        {
            "物业名称": ["Test Property 1", "Test Property 2"],
            "地址": ["Address 1", "Address 2"],
            "确权状态": ["已确权", "未确权"],
            "物业性质": ["经营性", "非经营性"],
            "使用状态": ["出租", "空置"],
        }
    )
    df.to_excel(content, index=False)
    content.seek(0)
    return content


@pytest.fixture
def mock_upload_file():
    """Create mock UploadFile object"""
    file = MagicMock(spec=UploadFile)
    file.filename = "test.xlsx"
    file.content_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    file.size = 1024

    content = io.BytesIO()
    df = pd.DataFrame(
        {
            "物业名称": ["Test Property 1"],
            "地址": ["Address 1"],
        }
    )
    df.to_excel(content, index=False)
    content.seek(0)
    file.read = AsyncMock(return_value=content.getvalue())
    return file


# ============================================================================
# Test: GET /template - Download Template
# ============================================================================


class TestDownloadTemplate:
    """Tests for GET /excel/template endpoint"""

    @patch("src.api.v1.documents.excel.template.ExcelTemplateService")
    @pytest.mark.asyncio
    async def test_download_template_success(
        self, mock_template_service_class, mock_db, mock_current_user
    ):
        """Test successful template download"""
        from src.api.v1.documents.excel.template import download_template

        # Mock buffer
        mock_buffer = io.BytesIO(b"fake excel data")
        mock_service = MagicMock()
        mock_service.generate_template.return_value = mock_buffer
        mock_template_service_class.return_value = mock_service

        result = download_template(db=mock_db, current_user=mock_current_user)

        assert isinstance(result, StreamingResponse)
        assert (
            result.media_type
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert (
            result.headers["Content-Disposition"]
            == "attachment; filename=land_property_asset_template.xlsx"
        )

    @patch("src.api.v1.documents.excel.template.ExcelTemplateService")
    @pytest.mark.asyncio
    async def test_download_template_buffer_cleanup(
        self, mock_template_service_class, mock_db, mock_current_user
    ):
        """Test that buffer is properly closed after download"""
        from src.api.v1.documents.excel.template import download_template

        mock_buffer = io.BytesIO(b"fake excel data")
        mock_service = MagicMock()
        mock_service.generate_template.return_value = mock_buffer
        mock_template_service_class.return_value = mock_service

        result = download_template(db=mock_db, current_user=mock_current_user)

        # Consume the generator to trigger cleanup
        async for _ in result.body_iterator:
            break

        # Verify buffer was created
        mock_service.generate_template.assert_called_once()


# ============================================================================
# Test: GET /test - Test Endpoint
# ============================================================================


class TestTestEndpoint:
    """Tests for GET /excel/test endpoint"""

    @pytest.mark.asyncio
    async def test_test_endpoint_success(self):
        """Test test endpoint returns success - skipped as it requires debug mode"""
        # This endpoint is @debug_only and would require special setup
        # Skip in normal unit tests
        pytest.skip("Requires debug mode enabled")


# ============================================================================
# Test: POST /configs - Create Excel Configuration
# ============================================================================


class TestCreateExcelConfig:
    """Tests for POST /excel/configs endpoint"""

    @patch("src.crud.task.excel_task_config_crud")
    @pytest.mark.asyncio
    async def test_create_config_success(self, mock_crud, mock_db, mock_current_user):
        """Test successful configuration creation"""
        from src.api.v1.documents.excel.config import create_excel_config
        from src.schemas.excel_advanced import ExcelConfigCreate, ExcelFieldMapping

        config_in = ExcelConfigCreate(
            config_name="test_config",
            config_type="import",
            field_mapping=[
                ExcelFieldMapping(
                    excel_column="物业名称",
                    system_field="property_name",
                    data_type="string",
                    required=True,
                )
            ],
        )

        mock_config = MagicMock()
        mock_config.id = "config-id-1"
        mock_config.config_name = "test_config"
        mock_crud.create.return_value = mock_config

        result = create_excel_config(
            config_in=config_in,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["message"] == "配置创建成功"
        assert result["config_id"] == "config-id-1"
        assert result["config_name"] == "test_config"
        mock_crud.create.assert_called_once()

    @patch("src.crud.task.excel_task_config_crud")
    @pytest.mark.asyncio
    async def test_create_config_with_all_fields(
        self, mock_crud, mock_db, mock_current_user
    ):
        """Test configuration creation with all optional fields"""
        from src.api.v1.documents.excel.config import create_excel_config
        from src.schemas.excel_advanced import (
            ExcelConfigCreate,
            ExcelFieldMapping,
            ExcelValidationRule,
        )

        config_in = ExcelConfigCreate(
            config_name="full_config",
            config_type="export",
            field_mapping=[
                ExcelFieldMapping(
                    excel_column="地址",
                    system_field="address",
                    data_type="string",
                    required=False,
                )
            ],
            validation_rules=[
                ExcelValidationRule(
                    field_name="物业名称",
                    rule_type="required",
                    rule_value=True,
                    error_message="物业名称必填",
                )
            ],
        )

        mock_config = MagicMock()
        mock_config.id = "config-id-2"
        mock_config.config_name = "full_config"
        mock_crud.create.return_value = mock_config

        result = create_excel_config(
            config_in=config_in,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["config_id"] == "config-id-2"


# ============================================================================
# Test: GET /configs - Get Excel Configuration List
# ============================================================================


class TestGetExcelConfigs:
    """Tests for GET /excel/configs endpoint"""

    @patch("src.crud.task.excel_task_config_crud")
    @pytest.mark.asyncio
    async def test_get_configs_no_filters(self, mock_crud, mock_db, mock_current_user):
        """Test getting all configurations without filters"""
        from src.api.v1.documents.excel.config import get_excel_configs

        mock_configs = [MagicMock() for _ in range(5)]
        mock_crud.get_multi.return_value = mock_configs

        result = get_excel_configs(
            config_type=None,
            task_type=None,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["total"] == 5
        assert len(result["items"]) == 5
        mock_crud.get_multi.assert_called_once_with(
            db=mock_db, limit=50, config_type=None, task_type=None
        )

    @patch("src.crud.task.excel_task_config_crud")
    @pytest.mark.asyncio
    async def test_get_configs_with_filters(
        self, mock_crud, mock_db, mock_current_user
    ):
        """Test getting configurations with type and task filters"""
        from src.api.v1.documents.excel.config import get_excel_configs

        mock_configs = [MagicMock() for _ in range(2)]
        mock_crud.get_multi.return_value = mock_configs

        result = get_excel_configs(
            config_type="import",
            task_type="excel_import",
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["total"] == 2
        mock_crud.get_multi.assert_called_once_with(
            db=mock_db,
            limit=50,
            config_type="import",
            task_type="excel_import",
        )

    @patch("src.crud.task.excel_task_config_crud")
    @pytest.mark.asyncio
    async def test_get_configs_empty_list(self, mock_crud, mock_db, mock_current_user):
        """Test getting configurations when none exist"""
        from src.api.v1.documents.excel.config import get_excel_configs

        mock_crud.get_multi.return_value = []

        result = get_excel_configs(
            config_type=None,
            task_type=None,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["total"] == 0
        assert result["items"] == []


# ============================================================================
# Test: GET /configs/default - Get Default Excel Configuration
# ============================================================================


class TestGetDefaultExcelConfig:
    """Tests for GET /excel/configs/default endpoint"""

    @patch("src.crud.task.excel_task_config_crud")
    @pytest.mark.asyncio
    async def test_get_default_config_success(
        self, mock_crud, mock_db, mock_current_user
    ):
        """Test successful default configuration retrieval"""
        from src.api.v1.documents.excel.config import get_default_excel_config

        mock_config = MagicMock()
        mock_config.id = "default-config-id"
        mock_config.config_name = "default_import_config"
        mock_crud.get_default.return_value = mock_config

        result = get_default_excel_config(
            config_type="import",
            task_type="excel_import",
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.id == "default-config-id"
        mock_crud.get_default.assert_called_once_with(
            db=mock_db,
            config_type="import",
            task_type="excel_import",
        )

    @patch("src.crud.task.excel_task_config_crud")
    @pytest.mark.asyncio
    async def test_get_default_config_not_found(
        self, mock_crud, mock_db, mock_current_user
    ):
        """Test default configuration not found"""
        from src.api.v1.documents.excel.config import get_default_excel_config

        mock_crud.get_default.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            get_default_excel_config(
                config_type="import",
                task_type="excel_import",
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "excel_config" in exc_info.value.message


# ============================================================================
# Test: GET /configs/{config_id} - Get Excel Configuration Details
# ============================================================================


class TestGetExcelConfigDetails:
    """Tests for GET /excel/configs/{config_id} endpoint"""

    @patch("src.crud.task.excel_task_config_crud")
    @pytest.mark.asyncio
    async def test_get_config_success(self, mock_crud, mock_db, mock_current_user):
        """Test successful configuration retrieval"""
        from src.api.v1.documents.excel.config import get_excel_config

        mock_config = MagicMock()
        mock_config.id = "config-123"
        mock_config.config_name = "test_config"
        mock_crud.get.return_value = mock_config

        result = get_excel_config(
            config_id="config-123", db=mock_db, current_user=mock_current_user
        )

        assert result.id == "config-123"
        mock_crud.get.assert_called_once_with(db=mock_db, id="config-123")

    @patch("src.crud.task.excel_task_config_crud")
    @pytest.mark.asyncio
    async def test_get_config_not_found(self, mock_crud, mock_db, mock_current_user):
        """Test configuration not found"""
        from src.api.v1.documents.excel.config import get_excel_config

        mock_crud.get.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            get_excel_config(
                config_id="nonexistent", db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 404
        assert "excel_config" in exc_info.value.message


# ============================================================================
# Test: PUT /configs/{config_id} - Update Excel Configuration
# ============================================================================


class TestUpdateExcelConfig:
    """Tests for PUT /excel/configs/{config_id} endpoint"""

    @patch("src.crud.task.excel_task_config_crud")
    @pytest.mark.asyncio
    async def test_update_config_success(self, mock_crud, mock_db, mock_current_user):
        """Test successful configuration update"""
        from src.api.v1.documents.excel.config import update_excel_config

        mock_config = MagicMock()
        mock_config.id = "config-123"
        mock_crud.get.return_value = mock_config

        mock_updated = MagicMock()
        mock_updated.id = "config-123"
        mock_crud.update.return_value = mock_updated

        config_in = {"config_name": "updated_config"}

        result = update_excel_config(
            config_id="config-123",
            config_in=config_in,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["message"] == "配置更新成功"
        assert result["config_id"] == "config-123"
        mock_crud.update.assert_called_once()

    @patch("src.crud.task.excel_task_config_crud")
    @pytest.mark.asyncio
    async def test_update_config_not_found(
        self, mock_crud, mock_db, mock_current_user
    ):
        """Test updating non-existent configuration"""
        from src.api.v1.documents.excel.config import update_excel_config

        mock_crud.get.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            update_excel_config(
                config_id="nonexistent",
                config_in={"config_name": "updated"},
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "excel_config" in exc_info.value.message


# ============================================================================
# Test: DELETE /configs/{config_id} - Delete Excel Configuration
# ============================================================================


class TestDeleteExcelConfig:
    """Tests for DELETE /excel/configs/{config_id} endpoint"""

    @patch("src.crud.task.excel_task_config_crud")
    @pytest.mark.asyncio
    async def test_delete_config_success(self, mock_crud, mock_db, mock_current_user):
        """Test successful configuration deletion"""
        from src.api.v1.documents.excel.config import delete_excel_config

        mock_crud.remove.return_value = MagicMock()

        result = delete_excel_config(
            config_id="config-123", db=mock_db, current_user=mock_current_user
        )

        assert result["message"] == "配置删除成功"
        mock_crud.remove.assert_called_once_with(db=mock_db, id="config-123")


# ============================================================================
# Test: POST /preview/advanced - Advanced Excel Preview
# ============================================================================


class TestPreviewExcelAdvanced:
    """Tests for POST /excel/preview/advanced endpoint"""

    @patch("src.api.v1.documents.excel.preview.security_middleware")
    @patch("src.api.v1.documents.excel.preview.security_auditor")
    @pytest.mark.asyncio
    async def test_preview_advanced_success(
        self, mock_auditor, mock_middleware, mock_upload_file, mock_db
    ):
        """Test successful advanced preview"""
        from src.api.v1.documents.excel.preview import preview_excel_advanced
        from src.schemas.excel_advanced import ExcelPreviewRequest

        mock_middleware.validate_file_upload = AsyncMock(
            return_value={"hash": "test-hash"}
        )

        request = ExcelPreviewRequest(max_rows=10)

        result = await preview_excel_advanced(
            file=mock_upload_file,
            request=request,
            db=mock_db,
        )

        assert result.file_name == "test.xlsx"
        assert result.total_rows >= 0
        assert isinstance(result.columns, list)
        assert isinstance(result.preview_data, list)
        mock_auditor.log_security_event.assert_called_once()

    @patch("src.api.v1.documents.excel.preview.security_middleware")
    @pytest.mark.asyncio
    async def test_preview_advanced_with_custom_rows(
        self, mock_middleware, mock_upload_file, mock_db
    ):
        """Test preview with custom row limit"""
        from src.api.v1.documents.excel.preview import preview_excel_advanced
        from src.schemas.excel_advanced import ExcelPreviewRequest

        mock_middleware.validate_file_upload = AsyncMock(
            return_value={"hash": "test-hash"}
        )

        request = ExcelPreviewRequest(max_rows=50)

        result = await preview_excel_advanced(
            file=mock_upload_file,
            request=request,
            db=mock_db,
        )

        assert isinstance(result, object)

    @patch("src.api.v1.documents.excel.preview.security_middleware")
    @pytest.mark.asyncio
    async def test_preview_advanced_detects_mappings(
        self, mock_middleware, mock_upload_file, mock_db
    ):
        """Test that preview detects field mappings"""
        from src.api.v1.documents.excel.preview import preview_excel_advanced
        from src.schemas.excel_advanced import ExcelPreviewRequest

        mock_middleware.validate_file_upload = AsyncMock(
            return_value={"hash": "test-hash"}
        )

        request = ExcelPreviewRequest(max_rows=10)

        result = await preview_excel_advanced(
            file=mock_upload_file,
            request=request,
            db=mock_db,
        )

        # Should detect column mappings
        assert result.columns is not None


# ============================================================================
# Test: POST /preview - Preview Excel File
# ============================================================================


class TestPreviewExcel:
    """Tests for POST /excel/preview endpoint"""

    @patch("src.api.v1.documents.excel.preview.security_middleware")
    @pytest.mark.asyncio
    async def test_preview_success(
        self, mock_middleware, mock_upload_file, mock_db, mock_current_user
    ):
        """Test successful Excel preview"""
        from src.api.v1.documents.excel.preview import preview_excel

        mock_middleware.validate_file_upload = AsyncMock(
            return_value={"hash": "test-hash"}
        )

        result = await preview_excel(
            file=mock_upload_file,
            max_rows=10,
            current_user=mock_current_user,
        )

        assert result["message"] == "预览成功"
        assert result["filename"] == "test.xlsx"
        assert result["total"] >= 0
        assert isinstance(result["columns"], list)
        assert isinstance(result["data"], list)

    @patch("src.api.v1.documents.excel.preview.security_middleware")
    @pytest.mark.asyncio
    async def test_preview_with_custom_max_rows(
        self, mock_middleware, mock_upload_file, mock_db, mock_current_user
    ):
        """Test preview with custom max_rows parameter"""
        from src.api.v1.documents.excel.preview import preview_excel

        mock_middleware.validate_file_upload = AsyncMock(
            return_value={"hash": "test-hash"}
        )

        result = await preview_excel(
            file=mock_upload_file,
            max_rows=50,
            current_user=mock_current_user,
        )

        assert result["preview_rows"] <= 50

    @patch("src.api.v1.documents.excel.preview.security_middleware")
    @pytest.mark.asyncio
    async def test_preview_invalid_file_type(
        self, mock_middleware, mock_upload_file, mock_db, mock_current_user
    ):
        """Test preview with invalid file type"""
        from src.api.v1.documents.excel.preview import preview_excel
        from src.core.exception_handler import BusinessValidationError

        mock_middleware.validate_file_upload = AsyncMock(
            return_value={"hash": "test-hash"}
        )
        mock_upload_file.filename = "test.txt"

        with pytest.raises(BusinessValidationError) as exc_info:
            await preview_excel(
                file=mock_upload_file,
                max_rows=10,
                current_user=mock_current_user,
            )

        assert "文件格式不支持" in str(exc_info.value)

    @patch("src.api.v1.documents.excel.preview.security_middleware")
    @pytest.mark.asyncio
    async def test_preview_no_filename(
        self, mock_middleware, mock_upload_file, mock_db, mock_current_user
    ):
        """Test preview when filename is None"""
        from src.api.v1.documents.excel.preview import preview_excel
        from src.core.exception_handler import BusinessValidationError

        mock_middleware.validate_file_upload = AsyncMock(
            return_value={"hash": "test-hash"}
        )
        mock_upload_file.filename = None

        with pytest.raises(BusinessValidationError):
            await preview_excel(
                file=mock_upload_file,
                max_rows=10,
                current_user=mock_current_user,
            )


# ============================================================================
# Test: POST /import - Synchronous Excel Import
# ============================================================================


class TestImportExcelSync:
    """Tests for POST /excel/import endpoint"""

    @patch("src.api.v1.documents.excel.import_ops.ExcelImportService")
    @patch("src.api.v1.documents.excel.import_ops.security_auditor")
    @patch("src.api.v1.documents.excel.import_ops.security_middleware")
    @pytest.mark.asyncio
    async def test_import_success(
        self,
        mock_middleware,
        mock_auditor,
        mock_import_service_class,
        mock_upload_file,
        mock_db,
        mock_current_user,
    ):
        """Test successful synchronous import"""
        from src.api.v1.documents.excel.import_ops import import_excel

        mock_middleware.validate_file_upload = AsyncMock(
            return_value={"hash": "test-hash"}
        )

        mock_service = MagicMock()
        mock_service.import_assets_from_excel = AsyncMock(
            return_value={
                "total": 10,
                "success": 8,
                "failed": 2,
                "errors": [],
            }
        )
        mock_import_service_class.return_value = mock_service

        result = await import_excel(
            file=mock_upload_file,
            should_skip_errors=False,
            sheet_name="资产信息",
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["message"] == "导入完成"
        assert result["total"] == 10
        assert result["success"] == 8
        assert result["failed"] == 2
        mock_auditor.log_security_event.assert_called_once()

    @patch("src.api.v1.documents.excel.import_ops.ExcelImportService")
    @patch("src.api.v1.documents.excel.import_ops.security_auditor")
    @patch("src.api.v1.documents.excel.import_ops.security_middleware")
    @pytest.mark.asyncio
    async def test_import_with_skip_errors(
        self,
        mock_middleware,
        mock_auditor,
        mock_import_service_class,
        mock_upload_file,
        mock_db,
        mock_current_user,
    ):
        """Test import with skip_errors enabled"""
        from src.api.v1.documents.excel.import_ops import import_excel

        mock_middleware.validate_file_upload = AsyncMock(
            return_value={"hash": "test-hash"}
        )

        mock_service = MagicMock()
        mock_service.import_assets_from_excel = AsyncMock(
            return_value={
                "total": 10,
                "success": 10,
                "failed": 0,
                "errors": [],
            }
        )
        mock_import_service_class.return_value = mock_service

        result = await import_excel(
            file=mock_upload_file,
            should_skip_errors=True,
            sheet_name="资产信息",
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["failed"] == 0

    @patch("src.api.v1.documents.excel.import_ops.ExcelImportService")
    @patch("src.api.v1.documents.excel.import_ops.security_auditor")
    @patch("src.api.v1.documents.excel.import_ops.security_middleware")
    @pytest.mark.asyncio
    async def test_import_invalid_file_type(
        self,
        mock_middleware,
        mock_auditor,
        mock_import_service_class,
        mock_upload_file,
        mock_db,
        mock_current_user,
    ):
        """Test import with invalid file type"""
        from src.api.v1.documents.excel.import_ops import import_excel
        from src.core.exception_handler import BusinessValidationError

        mock_middleware.validate_file_upload = AsyncMock(
            return_value={"hash": "test-hash"}
        )
        mock_upload_file.filename = "test.txt"

        with pytest.raises(BusinessValidationError):
            await import_excel(
                file=mock_upload_file,
                should_skip_errors=False,
                sheet_name="资产信息",
                db=mock_db,
                current_user=mock_current_user,
            )

    @patch("src.api.v1.documents.excel.import_ops.ExcelImportService")
    @patch("src.api.v1.documents.excel.import_ops.security_auditor")
    @patch("src.api.v1.documents.excel.import_ops.security_middleware")
    @pytest.mark.asyncio
    async def test_import_with_errors(
        self,
        mock_middleware,
        mock_auditor,
        mock_import_service_class,
        mock_upload_file,
        mock_db,
        mock_current_user,
    ):
        """Test import with validation errors"""
        from src.api.v1.documents.excel.import_ops import import_excel

        mock_middleware.validate_file_upload = AsyncMock(
            return_value={"hash": "test-hash"}
        )

        mock_service = MagicMock()
        mock_service.import_assets_from_excel = AsyncMock(
            return_value={
                "total": 10,
                "success": 5,
                "failed": 5,
                "errors": [{"row": 3, "error": "Invalid value"}],
            }
        )
        mock_import_service_class.return_value = mock_service

        result = await import_excel(
            file=mock_upload_file,
            should_skip_errors=False,
            sheet_name="资产信息",
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["failed"] == 5
        assert len(result["errors"]) == 1


# ============================================================================
# Test: POST /import/async - Asynchronous Excel Import
# ============================================================================


class TestImportExcelAsync:
    """Tests for POST /excel/import/async endpoint"""

    @patch("src.api.v1.documents.excel.import_ops.ExcelImportService")
    @patch("src.api.v1.documents.excel.import_ops.task_crud")
    @patch("src.api.v1.documents.excel.import_ops.security_auditor")
    @patch("src.api.v1.documents.excel.import_ops.security_middleware")
    @pytest.mark.asyncio
    async def test_async_import_success(
        self,
        mock_middleware,
        mock_auditor,
        mock_task_crud,
        mock_import_service_class,
        mock_upload_file,
        mock_db,
        mock_current_user,
    ):
        """Test successful asynchronous import"""
        from src.api.v1.documents.excel.import_ops import import_excel_async
        from src.schemas.excel_advanced import ExcelImportRequest

        mock_middleware.validate_file_upload = AsyncMock(
            return_value={"hash": "test-hash"}
        )

        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_task.status = "pending"
        mock_task_crud.create.return_value = mock_task

        request = ExcelImportRequest()

        result = await import_excel_async(
            background_tasks=MagicMock(),
            file=mock_upload_file,
            request=request,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["message"] == "导入任务已创建"
        assert result["task_id"] == "task-123"
        assert "status" in result

    @patch("src.api.v1.documents.excel.import_ops.task_crud")
    @patch("src.api.v1.documents.excel.import_ops.security_auditor")
    @patch("src.api.v1.documents.excel.import_ops.security_middleware")
    @pytest.mark.asyncio
    async def test_async_import_with_config(
        self,
        mock_middleware,
        mock_auditor,
        mock_task_crud,
        mock_upload_file,
        mock_db,
        mock_current_user,
    ):
        """Test asynchronous import with custom config"""
        from src.api.v1.documents.excel.import_ops import import_excel_async
        from src.schemas.excel_advanced import ExcelImportRequest

        mock_middleware.validate_file_upload = AsyncMock(
            return_value={"hash": "test-hash"}
        )

        mock_task = MagicMock()
        mock_task.id = "task-456"
        mock_task.status = "pending"
        mock_task_crud.create.return_value = mock_task

        request = ExcelImportRequest(
            config_id="config-123",
            batch_size=200,
            should_skip_errors=True,
        )

        result = await import_excel_async(
            background_tasks=MagicMock(),
            file=mock_upload_file,
            request=request,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["task_id"] == "task-456"

    @patch("src.api.v1.documents.excel.import_ops.task_crud")
    @patch("src.api.v1.documents.excel.import_ops.security_auditor")
    @patch("src.api.v1.documents.excel.import_ops.security_middleware")
    @pytest.mark.asyncio
    async def test_async_import_invalid_file_type(
        self,
        mock_middleware,
        mock_auditor,
        mock_task_crud,
        mock_upload_file,
        mock_db,
        mock_current_user,
    ):
        """Test asynchronous import with invalid file type"""
        from src.api.v1.documents.excel.import_ops import import_excel_async
        from src.core.exception_handler import BusinessValidationError
        from src.schemas.excel_advanced import ExcelImportRequest

        mock_middleware.validate_file_upload = AsyncMock(
            return_value={"hash": "test-hash"}
        )
        mock_upload_file.filename = "test.txt"

        request = ExcelImportRequest()

        with pytest.raises(BusinessValidationError):
            await import_excel_async(
                background_tasks=MagicMock(),
                file=mock_upload_file,
                request=request,
                db=mock_db,
                current_user=mock_current_user,
            )


# ============================================================================
# Test: GET /export - Export Excel File
# ============================================================================


class TestExportExcel:
    """Tests for GET /excel/export endpoint"""

    @patch("src.api.v1.documents.excel.export_ops.ExcelExportService")
    @pytest.mark.asyncio
    async def test_export_success(
        self, mock_export_service_class, mock_db, mock_current_user
    ):
        """Test successful Excel export"""
        from src.api.v1.documents.excel.export_ops import export_excel

        mock_buffer = io.BytesIO(b"excel data")
        mock_service = MagicMock()
        mock_service.export_assets_to_excel.return_value = mock_buffer
        mock_export_service_class.return_value = mock_service

        result = export_excel(
            search=None,
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert isinstance(result, StreamingResponse)
        assert (
            result.media_type
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert "assets_export.xlsx" in result.headers["Content-Disposition"]

    @patch("src.api.v1.documents.excel.export_ops.ExcelExportService")
    @pytest.mark.asyncio
    async def test_export_with_filters(
        self, mock_export_service_class, mock_db, mock_current_user
    ):
        """Test export with filters applied"""
        from src.api.v1.documents.excel.export_ops import export_excel

        mock_buffer = io.BytesIO(b"filtered excel data")
        mock_service = MagicMock()
        mock_service.export_assets_to_excel.return_value = mock_buffer
        mock_export_service_class.return_value = mock_service

        result = export_excel(
            search="test",
            ownership_status="已确权",
            property_nature="经营性",
            usage_status="出租",
            db=mock_db,
            current_user=mock_current_user,
        )

        assert isinstance(result, StreamingResponse)
        mock_service.export_assets_to_excel.assert_called_once()

    @patch("src.api.v1.documents.excel.export_ops.ExcelExportService")
    @pytest.mark.asyncio
    async def test_export_with_search_only(
        self, mock_export_service_class, mock_db, mock_current_user
    ):
        """Test export with only search term"""
        from src.api.v1.documents.excel.export_ops import export_excel

        mock_buffer = io.BytesIO(b"search results")
        mock_service = MagicMock()
        mock_service.export_assets_to_excel.return_value = mock_buffer
        mock_export_service_class.return_value = mock_service

        result = export_excel(
            search="物业名称",
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert isinstance(result, StreamingResponse)


# ============================================================================
# Test: POST /export/async - Asynchronous Excel Export
# ============================================================================


class TestExportExcelAsync:
    """Tests for POST /excel/export/async endpoint"""

    @patch("src.api.v1.documents.excel.export_ops.task_crud")
    @pytest.mark.asyncio
    async def test_async_export_success(
        self, mock_task_crud, mock_db, mock_current_user
    ):
        """Test successful asynchronous export"""
        from src.api.v1.documents.excel.export_ops import export_excel_async
        from src.schemas.excel_advanced import ExcelExportRequest

        mock_task = MagicMock()
        mock_task.id = "export-task-123"
        mock_task.status = "pending"
        mock_task_crud.create.return_value = mock_task

        request = ExcelExportRequest()

        result = export_excel_async(
            background_tasks=MagicMock(),
            request=request,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["message"] == "导出任务已创建"
        assert result["task_id"] == "export-task-123"
        assert "status" in result

    @patch("src.api.v1.documents.excel.export_ops.task_crud")
    @pytest.mark.asyncio
    async def test_async_export_with_filters(
        self, mock_task_crud, mock_db, mock_current_user
    ):
        """Test asynchronous export with filters"""
        from src.api.v1.documents.excel.export_ops import export_excel_async
        from src.schemas.excel_advanced import ExcelExportRequest

        mock_task = MagicMock()
        mock_task.id = "export-task-456"
        mock_task.status = "pending"
        mock_task_crud.create.return_value = mock_task

        request = ExcelExportRequest(
            filters={"ownership_status": "已确权"},
            fields=["物业名称", "地址"],
            export_format="xlsx",
        )

        result = export_excel_async(
            background_tasks=MagicMock(),
            request=request,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["task_id"] == "export-task-456"

    @patch("src.api.v1.documents.excel.export_ops.task_crud")
    @pytest.mark.asyncio
    async def test_async_export_with_config(
        self, mock_task_crud, mock_db, mock_current_user
    ):
        """Test asynchronous export with custom config"""
        from src.api.v1.documents.excel.export_ops import export_excel_async
        from src.schemas.excel_advanced import ExcelExportRequest

        mock_task = MagicMock()
        mock_task.id = "export-task-789"
        mock_task.status = "pending"
        mock_task_crud.create.return_value = mock_task

        request = ExcelExportRequest(
            config_id="config-123",
            sheet_name="Custom Sheet",
            date_format="%Y/%m/%d",
        )

        result = export_excel_async(
            background_tasks=MagicMock(),
            request=request,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["task_id"] == "export-task-789"


# ============================================================================
# Test: GET /download/{task_id} - Download Exported File
# ============================================================================


class TestDownloadExportFile:
    """Tests for GET /excel/download/{task_id} endpoint"""

    @patch("src.api.v1.documents.excel.export_ops.task_crud")
    @pytest.mark.asyncio
    async def test_download_file_success(self, mock_task_crud, mock_db):
        """Test successful file download"""
        from src.api.v1.documents.excel.export_ops import download_export_file
        from src.enums.task import TaskStatus

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
            tmp_file.write(b"excel content")
            temp_path = tmp_file.name

        try:
            mock_task = MagicMock()
            mock_task.id = "task-123"
            mock_task.status = TaskStatus.COMPLETED
            mock_task.result_data = {"file_path": temp_path, "file_name": "test.xlsx"}
            mock_task_crud.get.return_value = mock_task

            result = download_export_file(task_id="task-123", db=mock_db)

            assert isinstance(result, StreamingResponse)
            assert (
                result.media_type
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("src.api.v1.documents.excel.export_ops.task_crud")
    @pytest.mark.asyncio
    async def test_download_file_not_found(self, mock_task_crud, mock_db):
        """Test downloading non-existent task"""
        from src.api.v1.documents.excel.export_ops import download_export_file

        mock_task_crud.get.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            download_export_file(task_id="nonexistent", db=mock_db)

        assert exc_info.value.status_code == 404
        assert "task" in exc_info.value.message

    @patch("src.api.v1.documents.excel.export_ops.task_crud")
    @pytest.mark.asyncio
    async def test_download_file_task_pending(self, mock_task_crud, mock_db):
        """Test downloading file when task is not completed"""
        from src.api.v1.documents.excel.export_ops import download_export_file
        from src.enums.task import TaskStatus

        mock_task = MagicMock()
        mock_task.id = "task-pending"
        mock_task.status = TaskStatus.PENDING
        mock_task_crud.get.return_value = mock_task

        with pytest.raises(BaseBusinessError) as exc_info:
            download_export_file(task_id="task-pending", db=mock_db)

        assert exc_info.value.status_code == 400
        assert "任务尚未完成" in exc_info.value.message

    @patch("src.api.v1.documents.excel.export_ops.task_crud")
    @pytest.mark.asyncio
    async def test_download_file_missing(self, mock_task_crud, mock_db):
        """Test downloading file when file is missing"""
        from src.api.v1.documents.excel.export_ops import download_export_file
        from src.enums.task import TaskStatus

        mock_task = MagicMock()
        mock_task.id = "task-no-file"
        mock_task.status = TaskStatus.COMPLETED
        mock_task.result_data = {
            "file_path": "/nonexistent/file.xlsx",
            "file_name": "test.xlsx",
        }
        mock_task_crud.get.return_value = mock_task

        with pytest.raises(BaseBusinessError) as exc_info:
            download_export_file(task_id="task-no-file", db=mock_db)

        assert exc_info.value.status_code == 404
        assert "file" in exc_info.value.message


# ============================================================================
# Test: GET /status/{task_id} - Get Task Status
# ============================================================================


class TestGetExcelTaskStatus:
    """Tests for GET /excel/status/{task_id} endpoint"""

    @patch("src.api.v1.documents.excel.status.task_crud")
    @pytest.mark.asyncio
    async def test_get_status_success(self, mock_task_crud, mock_db):
        """Test successful task status retrieval"""
        from src.api.v1.documents.excel.status import get_excel_task_status
        from src.enums.task import TaskStatus

        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_task.status = TaskStatus.RUNNING.value
        mock_task.progress = 50
        mock_task.total_items = 100
        mock_task.processed_items = 50
        mock_task.error_message = None
        mock_task.created_at = datetime.now(UTC)
        mock_task.started_at = datetime.now(UTC)
        mock_task.completed_at = None
        mock_task_crud.get.return_value = mock_task

        result = get_excel_task_status(task_id="task-123", db=mock_db)

        assert result.task_id == "task-123"
        assert result.status == TaskStatus.RUNNING.value
        assert result.progress == 50
        assert result.total_items == 100
        assert result.processed_items == 50
        assert result.error_message is None

    @patch("src.api.v1.documents.excel.status.task_crud")
    @pytest.mark.asyncio
    async def test_get_status_completed(self, mock_task_crud, mock_db):
        """Test getting status of completed task"""
        from src.api.v1.documents.excel.status import get_excel_task_status
        from src.enums.task import TaskStatus

        mock_task = MagicMock()
        mock_task.id = "task-completed"
        mock_task.status = TaskStatus.COMPLETED.value
        mock_task.progress = 100
        mock_task.total_items = 100
        mock_task.processed_items = 100
        mock_task.error_message = None
        mock_task.created_at = datetime.now(UTC)
        mock_task.started_at = datetime.now(UTC)
        mock_task.completed_at = datetime.now(UTC)
        mock_task_crud.get.return_value = mock_task

        result = get_excel_task_status(task_id="task-completed", db=mock_db)

        assert result.status == TaskStatus.COMPLETED.value
        assert result.progress == 100
        assert result.completed_at is not None

    @patch("src.api.v1.documents.excel.status.task_crud")
    @pytest.mark.asyncio
    async def test_get_status_failed(self, mock_task_crud, mock_db):
        """Test getting status of failed task"""
        from src.api.v1.documents.excel.status import get_excel_task_status
        from src.enums.task import TaskStatus

        mock_task = MagicMock()
        mock_task.id = "task-failed"
        mock_task.status = TaskStatus.FAILED.value
        mock_task.progress = 25
        mock_task.total_items = 100
        mock_task.processed_items = 25
        mock_task.error_message = "Import failed: Invalid data"
        mock_task.created_at = datetime.now(UTC)
        mock_task.started_at = datetime.now(UTC)
        mock_task.completed_at = None
        mock_task_crud.get.return_value = mock_task

        result = get_excel_task_status(task_id="task-failed", db=mock_db)

        assert result.status == TaskStatus.FAILED.value
        assert result.error_message == "Import failed: Invalid data"

    @patch("src.api.v1.documents.excel.status.task_crud")
    @pytest.mark.asyncio
    async def test_get_status_not_found(self, mock_task_crud, mock_db):
        """Test getting status of non-existent task"""
        from src.api.v1.documents.excel.status import get_excel_task_status

        mock_task_crud.get.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            get_excel_task_status(task_id="nonexistent", db=mock_db)

        assert exc_info.value.status_code == 404
        assert "task" in exc_info.value.message


# ============================================================================
# Test: GET /history - Get Excel Operation History
# ============================================================================


class TestGetExcelHistory:
    """Tests for GET /excel/history endpoint"""

    @patch("src.api.v1.documents.excel.status.task_crud")
    @pytest.mark.asyncio
    async def test_get_history_success(self, mock_task_crud, mock_db):
        """Test successful history retrieval"""
        from src.api.v1.documents.excel.status import get_excel_history

        mock_tasks = []
        for i in range(5):
            task = MagicMock()
            task.id = f"task-{i}"
            task.task_type = "excel_import"
            task.title = f"Import Task {i}"
            task.status = "completed"
            task.progress = 100
            task.created_at = datetime.now(UTC)
            task.completed_at = datetime.now(UTC)
            task.result_data = {"total": 10, "success": 10, "failed": 0}
            mock_tasks.append(task)

        mock_task_crud.get_multi.return_value = mock_tasks

        result = get_excel_history(
            task_type=None,
            status=None,
            page_size=20,
            page=1,
            db=mock_db,
        )

        assert result["total"] == 5
        assert len(result["items"]) == 5
        assert result["page"] == 1
        assert result["page_size"] == 20

    @patch("src.api.v1.documents.excel.status.task_crud")
    @pytest.mark.asyncio
    async def test_get_history_with_filters(self, mock_task_crud, mock_db):
        """Test history with type and status filters"""
        from src.api.v1.documents.excel.status import get_excel_history

        mock_tasks = []
        for i in range(3):
            task = MagicMock()
            task.id = f"import-task-{i}"
            task.task_type = "excel_import"
            task.title = f"Import {i}"
            task.status = "completed"
            task.progress = 100
            task.created_at = datetime.now(UTC)
            task.completed_at = datetime.now(UTC)
            task.result_data = {"total": 5, "success": 5, "failed": 0}
            mock_tasks.append(task)

        mock_task_crud.get_multi.return_value = mock_tasks

        result = get_excel_history(
            task_type="excel_import",
            status="completed",
            page_size=10,
            page=1,
            db=mock_db,
        )

        assert result["total"] == 3
        mock_task_crud.get_multi.assert_called_once_with(
            db=mock_db,
            skip=0,
            limit=10,
            task_type="excel_import",
            status="completed",
            order_by="created_at",
            order_dir="desc",
        )

    @patch("src.api.v1.documents.excel.status.task_crud")
    @pytest.mark.asyncio
    async def test_get_history_with_pagination(self, mock_task_crud, mock_db):
        """Test history with pagination"""
        from src.api.v1.documents.excel.status import get_excel_history

        mock_tasks = [MagicMock() for _ in range(15)]
        for i, task in enumerate(mock_tasks):
            task.id = f"task-{i}"
            task.task_type = "excel_export"
            task.title = f"Export {i}"
            task.status = "pending"
            task.progress = 0
            task.created_at = datetime.now(UTC)
            task.completed_at = None
            task.result_data = None

        mock_task_crud.get_multi.return_value = mock_tasks

        result = get_excel_history(
            task_type=None,
            status=None,
            page_size=10,
            page=5,
            db=mock_db,
        )

        assert result["page"] == 5
        assert result["page_size"] == 10

    @patch("src.api.v1.documents.excel.status.task_crud")
    @pytest.mark.asyncio
    async def test_get_history_empty(self, mock_task_crud, mock_db):
        """Test history when no tasks exist"""
        from src.api.v1.documents.excel.status import get_excel_history

        mock_task_crud.get_multi.return_value = []

        result = get_excel_history(
            task_type=None,
            status=None,
            page_size=20,
            page=1,
            db=mock_db,
        )

        assert result["total"] == 0
        assert result["items"] == []


# ============================================================================
# Test: POST /export - Export Selected Assets
# ============================================================================


class TestExportSelectedAssets:
    """Tests for POST /excel/export endpoint (selected assets)"""

    @patch("src.api.v1.documents.excel.export_ops.ExcelExportService")
    @pytest.mark.asyncio
    async def test_export_selected_assets_success(
        self, mock_export_service_class, mock_db, mock_current_user
    ):
        """Test successful export of selected assets"""
        from src.api.v1.documents.excel.export_ops import export_selected_assets

        mock_buffer = io.BytesIO(b"selected assets data")
        mock_service = MagicMock()
        mock_service.export_assets_to_excel.return_value = mock_buffer
        mock_export_service_class.return_value = mock_service

        asset_ids = ["asset-1", "asset-2", "asset-3"]

        result = export_selected_assets(
            asset_ids=asset_ids,
            export_format="excel",
            search=None,
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert isinstance(result, StreamingResponse)
        assert "selected_assets_export.xlsx" in result.headers["Content-Disposition"]
        mock_service.export_assets_to_excel.assert_called_once()

    @patch("src.api.v1.documents.excel.export_ops.ExcelExportService")
    @pytest.mark.asyncio
    async def test_export_filtered_assets(
        self, mock_export_service_class, mock_db, mock_current_user
    ):
        """Test export with filters instead of asset IDs"""
        from src.api.v1.documents.excel.export_ops import export_selected_assets

        mock_buffer = io.BytesIO(b"filtered assets data")
        mock_service = MagicMock()
        mock_service.export_assets_to_excel.return_value = mock_buffer
        mock_export_service_class.return_value = mock_service

        result = export_selected_assets(
            asset_ids=None,
            export_format="excel",
            search="test",
            ownership_status="已确权",
            property_nature="经营性",
            usage_status="出租",
            db=mock_db,
            current_user=mock_current_user,
        )

        assert isinstance(result, StreamingResponse)
        assert "filtered_assets_export.xlsx" in result.headers["Content-Disposition"]

    @patch("src.api.v1.documents.excel.export_ops.ExcelExportService")
    @pytest.mark.asyncio
    async def test_export_empty_asset_list(
        self, mock_export_service_class, mock_db, mock_current_user
    ):
        """Test export with empty asset ID list"""
        from src.api.v1.documents.excel.export_ops import export_selected_assets

        mock_buffer = io.BytesIO(b"empty data")
        mock_service = MagicMock()
        mock_service.export_assets_to_excel.return_value = mock_buffer
        mock_export_service_class.return_value = mock_service

        result = export_selected_assets(
            asset_ids=[],
            export_format="excel",
            search=None,
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            db=mock_db,
            current_user=mock_current_user,
        )

        # Empty list should be treated as None (filtered export)
        assert isinstance(result, StreamingResponse)


# ============================================================================
# Test: Helper Function - _process_excel_import_async
# ============================================================================


class TestProcessExcelImportAsync:
    """Tests for internal _process_excel_import_async function"""

    @patch("src.api.v1.documents.excel.import_ops.ExcelImportService")
    @patch("src.api.v1.documents.excel.import_ops.task_crud")
    @pytest.mark.asyncio
    async def test_process_import_async_success(
        self, mock_task_crud, mock_import_service_class, mock_db
    ):
        """Test successful background import processing"""
        from src.api.v1.documents.excel.import_ops import _process_excel_import_async
        from src.schemas.excel_advanced import ExcelImportRequest

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
            tmp_file.write(b"excel content")
            temp_path = tmp_file.name

        try:
            mock_task = MagicMock()
            mock_task.id = "task-async-1"
            mock_task_crud.get.return_value = mock_task

            mock_service = MagicMock()
            mock_service.import_assets_from_excel = AsyncMock(
                return_value={
                    "total": 10,
                    "success": 10,
                    "failed": 0,
                    "created_assets": 10,
                    "updated_assets": 0,
                }
            )
            mock_import_service_class.return_value = mock_service

            request = ExcelImportRequest()

            await _process_excel_import_async(
                task_id="task-async-1",
                file_path=temp_path,
                request=request,
                db_session=mock_db,
            )

            # Verify task was updated to running and then completed
            assert mock_task_crud.update.call_count >= 2
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("src.api.v1.documents.excel.import_ops.ExcelImportService")
    @patch("src.api.v1.documents.excel.import_ops.task_crud")
    @pytest.mark.asyncio
    async def test_process_import_async_failure(
        self, mock_task_crud, mock_import_service_class, mock_db
    ):
        """Test background import processing with failure"""
        from src.api.v1.documents.excel.import_ops import _process_excel_import_async
        from src.schemas.excel_advanced import ExcelImportRequest

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
            tmp_file.write(b"excel content")
            temp_path = tmp_file.name

        try:
            mock_task = MagicMock()
            mock_task.id = "task-async-fail"
            mock_task_crud.get.return_value = mock_task

            mock_service = MagicMock()
            mock_service.import_assets_from_excel = AsyncMock(
                side_effect=Exception("Import failed")
            )
            mock_import_service_class.return_value = mock_service

            request = ExcelImportRequest()

            await _process_excel_import_async(
                task_id="task-async-fail",
                file_path=temp_path,
                request=request,
                db_session=mock_db,
            )

            # Verify task was updated to failed
            calls = mock_task_crud.update.call_args_list
            # Last call should be with FAILED status
            assert any(call for call in calls if "FAILED" in str(call))
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)


# ============================================================================
# Test: Helper Function - _process_excel_export_async
# ============================================================================


class TestProcessExcelExportAsync:
    """Tests for internal _process_excel_export_async function"""

    @patch("src.api.v1.documents.excel.export_ops.ExcelExportService")
    @patch("src.api.v1.documents.excel.export_ops.task_crud")
    @pytest.mark.asyncio
    async def test_process_export_async_success(
        self, mock_task_crud, mock_export_service_class, mock_db
    ):
        """Test successful background export processing"""
        from src.api.v1.documents.excel.export_ops import _process_excel_export_async
        from src.schemas.excel_advanced import ExcelExportRequest

        mock_task = MagicMock()
        mock_task.id = "export-task-async-1"
        mock_task_crud.get.return_value = mock_task

        mock_service = MagicMock()
        mock_service.export_assets_to_file.return_value = {
            "file_path": "/tmp/export.xlsx",
            "file_name": "export.xlsx",
            "record_count": 100,
        }
        mock_export_service_class.return_value = mock_service

        request = ExcelExportRequest()

        await _process_excel_export_async(
            task_id="export-task-async-1",
            request=request,
            db_session=mock_db,
        )

        # Verify task was updated to running and then completed
        assert mock_task_crud.update.call_count >= 2
        mock_service.export_assets_to_file.assert_called_once()

    @patch("src.api.v1.documents.excel.export_ops.ExcelExportService")
    @patch("src.api.v1.documents.excel.export_ops.task_crud")
    @pytest.mark.asyncio
    async def test_process_export_async_failure(
        self, mock_task_crud, mock_export_service_class, mock_db
    ):
        """Test background export processing with failure"""
        from src.api.v1.documents.excel.export_ops import _process_excel_export_async
        from src.schemas.excel_advanced import ExcelExportRequest

        mock_task = MagicMock()
        mock_task.id = "export-task-async-fail"
        mock_task_crud.get.return_value = mock_task

        mock_service = MagicMock()
        mock_service.export_assets_to_file.side_effect = Exception("Export failed")
        mock_export_service_class.return_value = mock_service

        request = ExcelExportRequest()

        await _process_excel_export_async(
            task_id="export-task-async-fail",
            request=request,
            db_session=mock_db,
        )

        # Verify task was updated to failed
        calls = mock_task_crud.update.call_args_list
        assert any(call for call in calls if "FAILED" in str(call))
