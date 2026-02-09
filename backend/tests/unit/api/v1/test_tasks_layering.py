"""分层约束测试：tasks 路由应委托 TaskService。"""

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.api


def test_tasks_api_module_should_not_use_task_crud_adapter_calls():
    """路由层不应直接调用 task_crud / excel_task_config_crud。"""
    from src.api.v1.system import tasks

    module_source = inspect.getsource(tasks)
    assert "task_crud." not in module_source
    assert "excel_task_config_crud." not in module_source


@pytest.mark.asyncio
@patch("src.api.v1.system.tasks.resolve_task_user_filter", new_callable=AsyncMock)
async def test_get_tasks_should_delegate_to_service(mock_resolve_user, mock_db):
    """列表路由应委托给 service.get_tasks。"""
    from src.api.v1.system.tasks import get_tasks

    mock_resolve_user.return_value = "filtered-user-id"
    mock_service = MagicMock()
    mock_service.get_tasks = AsyncMock(return_value=([], 0))

    response = await get_tasks(
        page=1,
        page_size=20,
        task_type=None,
        status=None,
        user_id=None,
        created_after=None,
        created_before=None,
        order_by="created_at",
        order_dir="desc",
        db=mock_db,
        current_user=MagicMock(id="user-1"),
        service=mock_service,
    )

    assert response.status_code == 200
    mock_service.get_tasks.assert_awaited_once_with(
        db=mock_db,
        skip=0,
        limit=20,
        task_type=None,
        status=None,
        user_id="filtered-user-id",
        created_after=None,
        created_before=None,
        order_by="created_at",
        order_dir="desc",
    )


@pytest.mark.asyncio
async def test_get_excel_configs_should_delegate_to_service(mock_db):
    """配置列表路由应委托给 service.get_excel_configs。"""
    from src.api.v1.system.tasks import get_excel_configs

    mock_service = MagicMock()
    mock_service.get_excel_configs = AsyncMock(return_value=[])

    result = await get_excel_configs(
        config_type="export",
        task_type="excel_export",
        db=mock_db,
        current_user=MagicMock(id="user-1"),
        service=mock_service,
    )

    assert result == []
    mock_service.get_excel_configs.assert_awaited_once_with(
        db=mock_db,
        config_type="export",
        task_type="excel_export",
        limit=50,
    )

