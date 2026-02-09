"""分层约束测试：history 路由应委托 HistoryService。"""

import inspect
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def test_history_api_module_should_not_use_crud_adapter_calls():
    """路由层不应直接调用 asset_crud/history_crud。"""
    from src.api.v1.system import history

    module_source = inspect.getsource(history)
    assert "asset_crud." not in module_source
    assert "history_crud." not in module_source


@pytest.mark.asyncio
async def test_get_history_list_should_delegate_to_service(mock_db):
    """历史列表路由应委托给 service.get_history_list。"""
    from src.api.v1.system.history import get_history_list

    mock_service = MagicMock()
    mock_service.get_history_list = AsyncMock(return_value=([], 0))

    response = await get_history_list(
        page=1,
        page_size=20,
        asset_id="asset-1",
        db=mock_db,
        service=mock_service,
    )

    payload = json.loads(response.body)
    assert payload["data"]["pagination"]["total"] == 0
    mock_service.get_history_list.assert_awaited_once_with(
        db=mock_db,
        skip=0,
        limit=20,
        asset_id="asset-1",
    )


@pytest.mark.asyncio
async def test_delete_history_should_delegate_to_service(mock_db):
    """删除路由应委托给 service.delete_history。"""
    from src.api.v1.system.history import delete_history

    mock_service = MagicMock()
    mock_service.delete_history = AsyncMock(return_value=True)

    result = await delete_history(
        history_id="history-1",
        db=mock_db,
        current_user=MagicMock(id="admin-1"),
        service=mock_service,
    )

    assert result["message"] == "历史记录 history-1 已成功删除"
    mock_service.delete_history.assert_awaited_once_with(
        db=mock_db,
        history_id="history-1",
    )
