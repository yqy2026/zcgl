"""HistoryService 业务边界测试。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import ResourceNotFoundError
from src.services.history.history_service import HistoryService

pytestmark = pytest.mark.asyncio


async def test_list_should_fail_loud_when_asset_filter_missing(mock_db, monkeypatch):
    """按资产筛选历史时，服务层先校验资产存在性而不是直接转发 CRUD。"""
    service = HistoryService()
    mock_asset_crud = MagicMock()
    mock_asset_crud.get_async = AsyncMock(return_value=None)
    mock_history_crud = MagicMock()
    mock_history_crud.get_multi_with_count_async = AsyncMock(return_value=([], 0))

    monkeypatch.setattr(
        "src.services.history.history_service.asset_crud", mock_asset_crud
    )
    monkeypatch.setattr(
        "src.services.history.history_service.history_crud", mock_history_crud
    )

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await service.get_history_list(
            mock_db,
            skip=0,
            limit=20,
            asset_id="missing-asset",
        )

    assert exc_info.value.details["resource_type"] == "Asset"
    assert exc_info.value.details["resource_id"] == "missing-asset"
    mock_asset_crud.get_async.assert_awaited_once_with(db=mock_db, id="missing-asset")
    mock_history_crud.get_multi_with_count_async.assert_not_called()


async def test_list_should_delegate_when_asset_filter_exists(mock_db, monkeypatch):
    """资产筛选存在时，服务层把分页参数完整交给 history CRUD。"""
    service = HistoryService()
    mock_asset_crud = MagicMock()
    mock_asset_crud.get_async = AsyncMock(return_value=MagicMock(id="asset-1"))
    mock_history_crud = MagicMock()
    mock_history_crud.get_multi_with_count_async = AsyncMock(return_value=(["row"], 1))

    monkeypatch.setattr(
        "src.services.history.history_service.asset_crud", mock_asset_crud
    )
    monkeypatch.setattr(
        "src.services.history.history_service.history_crud", mock_history_crud
    )

    items, total = await service.get_history_list(
        mock_db,
        skip=20,
        limit=10,
        asset_id="asset-1",
    )

    assert items == ["row"]
    assert total == 1
    mock_history_crud.get_multi_with_count_async.assert_awaited_once_with(
        mock_db,
        skip=20,
        limit=10,
        asset_id="asset-1",
    )


async def test_detail_should_fail_loud_when_history_missing(mock_db, monkeypatch):
    """历史详情缺失时，服务层统一返回 history 资源 404。"""
    service = HistoryService()
    mock_history_crud = MagicMock()
    mock_history_crud.get_async = AsyncMock(return_value=None)

    monkeypatch.setattr(
        "src.services.history.history_service.history_crud", mock_history_crud
    )

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await service.get_history_detail(mock_db, history_id="missing-history")

    assert exc_info.value.details["resource_type"] == "history"
    assert exc_info.value.details["resource_id"] == "missing-history"
    mock_history_crud.get_async.assert_awaited_once_with(db=mock_db, id="missing-history")


async def test_delete_should_not_remove_missing_history(mock_db, monkeypatch):
    """删除缺失历史时，服务层必须先 fail loud，不能继续调用 remove。"""
    service = HistoryService()
    mock_history_crud = MagicMock()
    mock_history_crud.get_async = AsyncMock(return_value=None)
    mock_history_crud.remove_async = AsyncMock()

    monkeypatch.setattr(
        "src.services.history.history_service.history_crud", mock_history_crud
    )

    with pytest.raises(ResourceNotFoundError):
        await service.delete_history(mock_db, history_id="missing-history")

    mock_history_crud.remove_async.assert_not_called()
