"""分层约束测试：excel import_ops 路由应委托服务层。"""

import inspect
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.excel_advanced import ExcelImportRequest

pytestmark = pytest.mark.api


def test_excel_import_ops_module_should_not_use_crud_adapter_calls():
    """路由模块不应直接调用 task_crud。"""
    from src.api.v1.documents.excel import import_ops

    module_source = inspect.getsource(import_ops)
    assert "task_crud." not in module_source
    assert "rollback(" not in module_source
    assert "datetime.utcnow(" not in module_source


@pytest.mark.asyncio
async def test_import_excel_async_should_delegate_task_creation(
    mock_db,
):
    """异步导入路由应委托 task_service.create_task。"""
    from src.api.v1.documents.excel.import_ops import import_excel_async

    file = MagicMock()
    file.filename = "test.xlsx"
    file.size = 128
    file.read = AsyncMock(return_value=b"excel-bytes")

    mock_task = MagicMock()
    mock_task.id = "task-1"
    mock_task.status = "pending"
    mock_task_service = MagicMock()
    mock_task_service.create_task = AsyncMock(return_value=mock_task)

    background_tasks = MagicMock()
    current_user = MagicMock(id="user-1")

    with pytest.MonkeyPatch.context() as monkeypatch:
        mock_security = MagicMock()
        mock_security.validate_file_upload = AsyncMock(return_value={"hash": "h1"})
        monkeypatch.setattr(
            "src.api.v1.documents.excel.import_ops.security_middleware",
            mock_security,
        )
        monkeypatch.setattr(
            "src.api.v1.documents.excel.import_ops.security_auditor",
            MagicMock(log_security_event=MagicMock()),
        )

        result = await import_excel_async(
            background_tasks=background_tasks,
            file=file,
            request=ExcelImportRequest(),
            db=mock_db,
            current_user=current_user,
            task_service=mock_task_service,
        )

    assert result["task_id"] == "task-1"
    mock_task_service.create_task.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_excel_import_async_should_delegate_failure_handling_to_task_service(
    mock_db,
):
    """导入后台失败处理应委托 task_service.mark_task_failed。"""
    from src.api.v1.documents.excel.import_ops import _process_excel_import_async

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
        tmp_file.write(b"excel-bytes")
        file_path = tmp_file.name

    mock_task = MagicMock(id="task-failed-1")
    mock_task_service = MagicMock()
    mock_task_service.get_task = AsyncMock(return_value=mock_task)
    mock_task_service.update_task = AsyncMock()
    mock_task_service.mark_task_failed = AsyncMock(return_value=None)

    with pytest.MonkeyPatch.context() as monkeypatch:
        mock_import_service = MagicMock()
        mock_import_service.import_assets_from_excel = AsyncMock(
            side_effect=Exception("Import failed")
        )
        monkeypatch.setattr(
            "src.api.v1.documents.excel.import_ops.ExcelImportService",
            MagicMock(return_value=mock_import_service),
        )
        await _process_excel_import_async(
            task_id="task-failed-1",
            file_path=file_path,
            request=ExcelImportRequest(),
            db_session=mock_db,
            task_service=mock_task_service,
        )

    mock_task_service.mark_task_failed.assert_awaited_once_with(
        db=mock_db,
        task_id="task-failed-1",
        error_message="Import failed",
    )
    assert not os.path.exists(file_path)
