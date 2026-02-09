"""分层约束测试：excel export_ops 路由应委托服务层。"""

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.excel_advanced import ExcelExportRequest

pytestmark = pytest.mark.api


def test_excel_export_ops_module_should_not_use_crud_adapter_calls():
    """路由模块不应直接调用 task_crud。"""
    from src.api.v1.documents.excel import export_ops

    module_source = inspect.getsource(export_ops)
    assert "task_crud." not in module_source
    assert "rollback(" not in module_source
    assert "datetime.utcnow(" not in module_source


@pytest.mark.asyncio
async def test_export_excel_async_should_delegate_task_creation(mock_db):
    """异步导出路由应委托 task_service.create_task。"""
    from src.api.v1.documents.excel.export_ops import export_excel_async
    from src.schemas.excel_advanced import ExcelExportRequest

    mock_task = MagicMock()
    mock_task.id = "task-2"
    mock_task.status = "pending"
    mock_task_service = MagicMock()
    mock_task_service.create_task = AsyncMock(return_value=mock_task)

    result = await export_excel_async(
        background_tasks=MagicMock(),
        request=ExcelExportRequest(),
        db=mock_db,
        current_user=MagicMock(id="user-1"),
        task_service=mock_task_service,
    )

    assert result["task_id"] == "task-2"
    mock_task_service.create_task.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_excel_export_async_should_delegate_failure_handling_to_task_service(
    mock_db,
):
    """导出后台失败处理应委托 task_service.mark_task_failed。"""
    from src.api.v1.documents.excel.export_ops import _process_excel_export_async

    mock_task = MagicMock(id="task-export-failed-1")
    mock_task_service = MagicMock()
    mock_task_service.get_task = AsyncMock(return_value=mock_task)
    mock_task_service.update_task = AsyncMock()
    mock_task_service.mark_task_failed = AsyncMock(return_value=None)

    with pytest.MonkeyPatch.context() as monkeypatch:
        mock_export_service = MagicMock()
        mock_export_service.export_assets_to_file_async = AsyncMock(
            side_effect=Exception("Export failed")
        )
        monkeypatch.setattr(
            "src.api.v1.documents.excel.export_ops.ExcelExportService",
            MagicMock(return_value=mock_export_service),
        )
        await _process_excel_export_async(
            task_id="task-export-failed-1",
            request=ExcelExportRequest(),
            db_session=mock_db,
            task_service=mock_task_service,
        )

    mock_task_service.mark_task_failed.assert_awaited_once_with(
        db=mock_db,
        task_id="task-export-failed-1",
        error_message="Export failed",
    )
