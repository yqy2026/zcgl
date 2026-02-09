"""分层约束测试：excel status 路由应委托 ExcelStatusService。"""

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def test_excel_status_api_module_should_not_use_crud_adapter_calls():
    """路由层不应直接调用 task_crud。"""
    from src.api.v1.documents.excel import status

    module_source = inspect.getsource(status)
    assert "task_crud." not in module_source


@pytest.mark.asyncio
async def test_get_excel_task_status_should_delegate_to_service(mock_db):
    """任务状态路由应委托给 service.get_task_status。"""
    from src.api.v1.documents.excel.status import get_excel_task_status

    current_user = MagicMock(id="user-1")
    expected = MagicMock()
    expected.task_id = "task-1"
    mock_service = MagicMock()
    mock_service.get_task_status = AsyncMock(return_value=expected)

    result = await get_excel_task_status(
        task_id="task-1",
        db=mock_db,
        current_user=current_user,
        service=mock_service,
    )

    assert result == expected
    mock_service.get_task_status.assert_awaited_once_with(
        db=mock_db,
        task_id="task-1",
        current_user=current_user,
    )


@pytest.mark.asyncio
async def test_get_excel_history_should_delegate_to_service(mock_db):
    """任务历史路由应委托给 service.get_history。"""
    from src.api.v1.documents.excel.status import get_excel_history

    current_user = MagicMock(id="user-1")
    expected = {"items": [], "total": 0, "page": 1, "page_size": 20}
    mock_service = MagicMock()
    mock_service.get_history = AsyncMock(return_value=expected)

    result = await get_excel_history(
        task_type="excel_import",
        status="completed",
        page=1,
        page_size=20,
        db=mock_db,
        current_user=current_user,
        service=mock_service,
    )

    assert result == expected
    mock_service.get_history.assert_awaited_once_with(
        db=mock_db,
        task_type="excel_import",
        status="completed",
        page=1,
        page_size=20,
        current_user=current_user,
    )
