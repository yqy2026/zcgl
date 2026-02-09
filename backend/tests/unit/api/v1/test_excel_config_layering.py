"""分层约束测试：excel config 路由应委托 ExcelConfigService。"""

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def test_excel_config_api_module_should_not_use_crud_adapter_calls():
    """路由层不应直接调用 excel_task_config_crud。"""
    from src.api.v1.documents.excel import config

    module_source = inspect.getsource(config)
    assert "excel_task_config_crud." not in module_source


@pytest.mark.asyncio
async def test_get_excel_configs_should_delegate_to_service(mock_db):
    """配置列表路由应委托给 service.get_configs。"""
    from src.api.v1.documents.excel.config import get_excel_configs

    mock_service = MagicMock()
    mock_service.get_configs = AsyncMock(return_value=[MagicMock(), MagicMock()])

    result = await get_excel_configs(
        config_type="import",
        task_type="excel_import",
        db=mock_db,
        current_user=MagicMock(id="user-1"),
        service=mock_service,
    )

    assert result["total"] == 2
    mock_service.get_configs.assert_awaited_once_with(
        db=mock_db,
        config_type="import",
        task_type="excel_import",
        limit=50,
    )


@pytest.mark.asyncio
async def test_delete_excel_config_should_delegate_to_service(mock_db):
    """删除路由应委托给 service.delete_config。"""
    from src.api.v1.documents.excel.config import delete_excel_config

    mock_service = MagicMock()
    mock_service.delete_config = AsyncMock(return_value=None)

    result = await delete_excel_config(
        config_id="config-1",
        db=mock_db,
        current_user=MagicMock(id="user-1"),
        service=mock_service,
    )

    assert result["message"] == "配置删除成功"
    mock_service.delete_config.assert_awaited_once_with(
        db=mock_db,
        config_id="config-1",
    )
