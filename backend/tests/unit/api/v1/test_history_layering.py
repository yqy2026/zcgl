"""分层约束测试：history 路由应委托 HistoryService。"""

import inspect
import json
import re
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def test_history_api_module_should_not_use_crud_adapter_calls():
    """路由层不应直接调用 asset_crud/history_crud。"""
    from src.api.v1.system import history

    module_source = inspect.getsource(history)
    assert "asset_crud." not in module_source
    assert "history_crud." not in module_source


def test_history_endpoints_should_use_require_authz() -> None:
    """history 关键端点应接入 require_authz。"""
    from src.api.v1.system import history

    module_source = inspect.getsource(history)
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source

    patterns = [
        r"async def get_history_list[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"history\"",
        r"async def get_history_detail[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"history\"[\s\S]*?resource_id=\"\{history_id\}\"",
        r"async def delete_history[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"history\"[\s\S]*?resource_id=\"\{history_id\}\"",
    ]
    for pattern in patterns:
        assert re.search(pattern, module_source), pattern


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
        current_user=MagicMock(id="user-1"),
        service=mock_service,
    )

    payload = json.loads(response.body)
    assert payload["data"]["pagination"]["total"] == 0
    mock_service.get_history_list.assert_awaited_once_with(
        db=mock_db,
        skip=0,
        limit=20,
        asset_id="asset-1",
        current_user_id="user-1",
        party_filter=None,
    )


@pytest.mark.asyncio
async def test_get_history_detail_should_delegate_current_user_id(mock_db):
    """详情路由应把 current_user.id 透传给 service。"""
    from src.api.v1.system import history as history_module
    from src.api.v1.system.history import get_history_detail

    mock_service = MagicMock()
    mock_service.get_history_detail = AsyncMock(return_value=MagicMock(id="history-1"))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            history_module.AssetHistoryResponse,
            "model_validate",
            staticmethod(lambda _: MagicMock(id="history-1")),
        )
        result = await get_history_detail(
            history_id="history-1",
            db=mock_db,
            current_user=MagicMock(id="user-1"),
            service=mock_service,
        )

    assert result.id == "history-1"
    mock_service.get_history_detail.assert_awaited_once_with(
        db=mock_db,
        history_id="history-1",
        current_user_id="user-1",
        party_filter=None,
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
