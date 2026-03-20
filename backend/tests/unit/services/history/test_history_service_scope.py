from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crud.query_builder import PartyFilter
from src.services.history.history_service import HistoryService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def service() -> HistoryService:
    return HistoryService()


async def test_get_history_list_should_resolve_scope_before_asset_lookup(service) -> None:
    db = MagicMock()
    party_filter = PartyFilter(party_ids=["owner-1"])

    with (
        patch.object(
            service,
            "_resolve_party_filter",
            new=AsyncMock(return_value=party_filter),
        ) as mock_resolve,
        patch(
            "src.services.history.history_service.asset_crud.get_async",
            new=AsyncMock(return_value=MagicMock(id="asset-1")),
        ) as mock_get_asset,
        patch(
            "src.services.history.history_service.history_crud.get_multi_with_count_async",
            new=AsyncMock(return_value=([], 0)),
        ) as mock_get_history,
    ):
        result = await service.get_history_list(
            db=db,
            skip=0,
            limit=20,
            asset_id="asset-1",
            current_user_id="user-1",
        )

    assert result == ([], 0)
    mock_resolve.assert_awaited_once_with(
        db,
        current_user_id="user-1",
        party_filter=None,
    )
    mock_get_asset.assert_awaited_once_with(
        db=db,
        id="asset-1",
        party_filter=party_filter,
    )
    mock_get_history.assert_awaited_once_with(
        db,
        skip=0,
        limit=20,
        asset_id="asset-1",
        party_filter=party_filter,
    )


async def test_get_history_list_should_apply_scope_without_asset_id(service) -> None:
    db = MagicMock()
    party_filter = PartyFilter(party_ids=["owner-1"])

    with (
        patch.object(
            service,
            "_resolve_party_filter",
            new=AsyncMock(return_value=party_filter),
        ) as mock_resolve,
        patch(
            "src.services.history.history_service.asset_crud.get_async",
            new=AsyncMock(),
        ) as mock_get_asset,
        patch(
            "src.services.history.history_service.history_crud.get_multi_with_count_async",
            new=AsyncMock(return_value=([], 0)),
        ) as mock_get_history,
    ):
        result = await service.get_history_list(
            db=db,
            skip=0,
            limit=20,
            asset_id=None,
            current_user_id="user-1",
        )

    assert result == ([], 0)
    mock_resolve.assert_awaited_once_with(
        db,
        current_user_id="user-1",
        party_filter=None,
    )
    mock_get_asset.assert_not_awaited()
    mock_get_history.assert_awaited_once_with(
        db,
        skip=0,
        limit=20,
        asset_id=None,
        party_filter=party_filter,
    )


async def test_get_history_detail_should_check_asset_scope(service) -> None:
    db = MagicMock()
    party_filter = PartyFilter(party_ids=["owner-1"])
    history_record = MagicMock(id="history-1", asset_id="asset-1")

    with (
        patch.object(
            service,
            "_resolve_party_filter",
            new=AsyncMock(return_value=party_filter),
        ) as mock_resolve,
        patch(
            "src.services.history.history_service.history_crud.get_async",
            new=AsyncMock(return_value=history_record),
        ) as mock_get_history,
        patch(
            "src.services.history.history_service.asset_crud.get_async",
            new=AsyncMock(return_value=MagicMock(id="asset-1")),
        ) as mock_get_asset,
    ):
        result = await service.get_history_detail(
            db=db,
            history_id="history-1",
            current_user_id="user-1",
        )

    assert result == history_record
    mock_resolve.assert_awaited_once_with(
        db,
        current_user_id="user-1",
        party_filter=None,
    )
    mock_get_history.assert_awaited_once_with(db=db, id="history-1")
    mock_get_asset.assert_awaited_once_with(
        db=db,
        id="asset-1",
        party_filter=party_filter,
    )


async def test_get_history_detail_should_fail_closed_on_empty_scope(service) -> None:
    db = MagicMock()

    with patch.object(
        service,
        "_resolve_party_filter",
        new=AsyncMock(return_value=PartyFilter(party_ids=[])),
    ):
        with pytest.raises(Exception):
            await service.get_history_detail(
                db=db,
                history_id="history-1",
                current_user_id="user-1",
            )
