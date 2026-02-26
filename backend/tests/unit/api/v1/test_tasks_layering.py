"""分层约束测试：tasks 路由应委托 TaskService。"""

import inspect
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.api


def test_tasks_api_module_should_not_use_task_crud_adapter_calls():
    """路由层不应直接调用 task_crud / excel_task_config_crud。"""
    from src.api.v1.system import tasks

    module_source = inspect.getsource(tasks)
    assert "task_crud." not in module_source
    assert "excel_task_config_crud." not in module_source


def test_excel_config_endpoints_should_use_require_authz() -> None:
    """Excel 配置端点应统一使用 require_authz。"""
    from src.api.v1.system import tasks

    module_source = inspect.getsource(tasks)
    assert "require_permission(" not in module_source

    patterns = [
        r"async def create_excel_config[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"excel_config\"[\s\S]*?resource_context=_EXCEL_CONFIG_CREATE_RESOURCE_CONTEXT",
        r"async def get_excel_configs[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"excel_config\"",
        r"async def get_default_excel_config[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"excel_config\"",
        r"async def get_excel_config[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"excel_config\"",
        r"async def update_excel_config[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"excel_config\"[\s\S]*?resource_id=\"\{config_id\}\"",
        r"async def delete_excel_config[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"excel_config\"[\s\S]*?resource_id=\"\{config_id\}\"",
    ]

    for pattern in patterns:
        assert re.search(pattern, module_source), f"未命中模式: {pattern}"


def test_task_endpoints_should_use_require_authz() -> None:
    """任务主端点应接入 require_authz。"""
    from src.api.v1.system import tasks

    module_source = inspect.getsource(tasks)

    patterns = [
        r"async def create_task[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"task\"[\s\S]*?resource_context=_TASK_CREATE_RESOURCE_CONTEXT",
        r"async def get_tasks[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"task\"",
        r"async def get_task[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"task\"[\s\S]*?resource_id=\"\{task_id\}\"",
        r"async def update_task[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"task\"[\s\S]*?resource_id=\"\{task_id\}\"",
        r"async def cancel_task[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"task\"[\s\S]*?resource_id=\"\{task_id\}\"",
        r"async def delete_task[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"task\"[\s\S]*?resource_id=\"\{task_id\}\"",
        r"async def get_task_history[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"task\"[\s\S]*?resource_id=\"\{task_id\}\"",
        r"async def get_task_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"task\"",
        r"async def get_running_tasks[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"task\"",
        r"async def get_recent_tasks[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"task\"",
        r"async def cleanup_old_tasks[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"task\"[\s\S]*?resource_context=_TASK_DELETE_RESOURCE_CONTEXT",
    ]

    for pattern in patterns:
        assert re.search(pattern, module_source), f"未命中模式: {pattern}"


def test_tasks_unscoped_write_context_should_be_defined() -> None:
    from src.api.v1.system import tasks

    expected_task_create = "__unscoped__:task:create"
    assert tasks._TASK_CREATE_UNSCOPED_PARTY_ID == expected_task_create
    assert tasks._TASK_CREATE_RESOURCE_CONTEXT == {
        "party_id": expected_task_create,
        "owner_party_id": expected_task_create,
        "manager_party_id": expected_task_create,
    }

    expected_task_delete = "__unscoped__:task:delete"
    assert tasks._TASK_DELETE_UNSCOPED_PARTY_ID == expected_task_delete
    assert tasks._TASK_DELETE_RESOURCE_CONTEXT == {
        "party_id": expected_task_delete,
        "owner_party_id": expected_task_delete,
        "manager_party_id": expected_task_delete,
    }

    expected_excel_create = "__unscoped__:excel_config:create"
    assert tasks._EXCEL_CONFIG_CREATE_UNSCOPED_PARTY_ID == expected_excel_create
    assert tasks._EXCEL_CONFIG_CREATE_RESOURCE_CONTEXT == {
        "party_id": expected_excel_create,
        "owner_party_id": expected_excel_create,
        "manager_party_id": expected_excel_create,
    }


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
