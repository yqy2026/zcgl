"""资产历史端点功能测试：序列化、分页、操作类型过滤、增强字段回填。"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def _build_history_model(**overrides) -> object:
    """构造一个最小可序列化的 AssetHistory ORM 实例。"""
    from src.models.asset_history import AssetHistory

    defaults = {
        "id": "history-1",
        "asset_id": "asset-1",
        "operation_type": "create",
        "field_name": "asset_name",
        "old_value": None,
        "new_value": "越华路穗南大厦",
        "operator": "admin",
        "operation_time": datetime(2026, 8, 3, 15, 33, 49),
        "description": None,
        "change_reason": None,
        "ip_address": None,
        "user_agent": None,
        "session_id": None,
    }
    defaults.update(overrides)
    return AssetHistory(**defaults)


@pytest.mark.asyncio
async def test_get_asset_history_serializes_items_with_enhanced_fields() -> None:
    """历史记录应被正确序列化，且 change_type / changed_fields 由基础字段回填。"""
    from src.api.v1.assets import assets as module
    from src.api.v1.assets.assets import get_asset_history

    record = _build_history_model()
    mock_service = MagicMock()
    mock_service.get_asset_history_records = AsyncMock(return_value=([record], 1))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "AsyncAssetService", MagicMock(return_value=mock_service))
        result = await get_asset_history(
            asset_id="asset-1",
            page=1,
            page_size=20,
            change_type=None,
            db=MagicMock(),
            current_user=MagicMock(id="user-1"),
        )

    payload = json.loads(result.body)
    assert payload["success"] is True
    items = payload["data"]["items"]
    assert len(items) == 1
    assert items[0]["id"] == "history-1"
    assert items[0]["operation_type"] == "create"
    assert items[0]["operator"] == "admin"
    assert items[0]["new_value"] == "越华路穗南大厦"
    # 增强字段回填
    assert items[0]["change_type"] == "create"
    assert items[0]["changed_fields"] == ["asset_name"]
    pagination = payload["data"]["pagination"]
    assert pagination["total"] == 1
    assert pagination["page"] == 1
    assert pagination["page_size"] == 20
    assert pagination["total_pages"] == 1
    mock_service.get_asset_history_records.assert_awaited_once_with(
        "asset-1",
        page=1,
        page_size=20,
        change_type=None,
        current_user_id="user-1",
    )


@pytest.mark.asyncio
async def test_get_asset_history_passes_page_and_change_type_to_service() -> None:
    """分页与操作类型过滤参数应透传服务层。"""
    from src.api.v1.assets import assets as module
    from src.api.v1.assets.assets import get_asset_history

    mock_service = MagicMock()
    mock_service.get_asset_history_records = AsyncMock(return_value=([], 0))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "AsyncAssetService", MagicMock(return_value=mock_service))
        result = await get_asset_history(
            asset_id="asset-1",
            page=2,
            page_size=10,
            change_type="update",
            db=MagicMock(),
            current_user=MagicMock(id="user-1"),
        )

    payload = json.loads(result.body)
    assert payload["success"] is True
    assert payload["data"]["items"] == []
    assert payload["data"]["pagination"]["page"] == 2
    assert payload["data"]["pagination"]["page_size"] == 10
    assert payload["data"]["pagination"]["total_pages"] == 0
    mock_service.get_asset_history_records.assert_awaited_once_with(
        "asset-1",
        page=2,
        page_size=10,
        change_type="update",
        current_user_id="user-1",
    )
