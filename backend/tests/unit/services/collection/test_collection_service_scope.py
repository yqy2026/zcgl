from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crud.query_builder import PartyFilter
from src.services.collection.service import CollectionService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def service() -> CollectionService:
    return CollectionService()


async def test_get_summary_should_resolve_and_forward_party_filter(service) -> None:
    db = MagicMock()
    party_filter = PartyFilter(
        party_ids=["owner-1", "manager-1"],
        owner_party_ids=["owner-1"],
        manager_party_ids=["manager-1"],
    )

    with (
        patch.object(
            service,
            "_resolve_party_filter",
            new=AsyncMock(return_value=party_filter),
        ) as mock_resolve,
        patch(
            "src.services.collection.service.collection_crud.get_overdue_ledger_stats_async",
            new=AsyncMock(return_value=(0, Decimal("0"))),
        ) as mock_overdue,
        patch(
            "src.services.collection.service.collection_crud.count_by_statuses_async",
            new=AsyncMock(side_effect=[0, 0]),
        ),
        patch(
            "src.services.collection.service.collection_crud.count_since_date_async",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "src.services.collection.service.collection_crud.count_total_async",
            new=AsyncMock(return_value=0),
        ),
    ):
        summary = await service.get_summary_async(db, current_user_id="user-1")

    assert summary.total_overdue_count == 0
    mock_resolve.assert_awaited_once_with(
        db,
        current_user_id="user-1",
        party_filter=None,
    )
    assert mock_overdue.await_args.kwargs["party_filter"] == party_filter


async def test_list_records_should_fail_closed_for_empty_scope(service) -> None:
    db = MagicMock()
    with patch.object(
        service,
        "_resolve_party_filter",
        new=AsyncMock(return_value=PartyFilter(party_ids=[])),
    ):
        result = await service.list_records_async(
            db,
            current_user_id="user-1",
        )

    assert result == {"items": [], "total": 0, "page": 1, "page_size": 20}


async def test_get_by_id_should_resolve_scope(service) -> None:
    db = MagicMock()
    record = MagicMock()
    party_filter = PartyFilter(party_ids=["owner-1"])
    with (
        patch.object(
            service,
            "_resolve_party_filter",
            new=AsyncMock(return_value=party_filter),
        ) as mock_resolve,
        patch(
            "src.services.collection.service.collection_crud.get_by_id_async",
            new=AsyncMock(return_value=record),
        ) as mock_get,
    ):
        result = await service.get_by_id_async(
            db,
            record_id="record-1",
            current_user_id="user-1",
        )

    assert result == record
    mock_resolve.assert_awaited_once_with(
        db,
        current_user_id="user-1",
        party_filter=None,
    )
    mock_get.assert_awaited_once_with(
        db,
        record_id="record-1",
        party_filter=party_filter,
    )
