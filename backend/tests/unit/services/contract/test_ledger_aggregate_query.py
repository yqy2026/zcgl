from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, patch

import pytest

from src.core.exception_handler import BusinessValidationError
from src.crud.query_builder import PartyFilter
from src.services.contract.ledger_service_v2 import ledger_service_v2

pytestmark = pytest.mark.asyncio


async def test_query_ledger_entries_delegates_filters_and_pagination() -> None:
    items = [
        SimpleNamespace(entry_id="entry-001"),
        SimpleNamespace(entry_id="entry-002"),
    ]

    with patch(
        "src.services.contract.ledger_service_v2.contract_group_crud.query_ledger_entries",
        new=AsyncMock(return_value=(items, 2)),
    ) as mock_query:
        result = await ledger_service_v2.query_ledger_entries(
            AsyncMock(),
            asset_id="asset-001",
            party_id="party-001",
            contract_id="contract-001",
            year_month_start="2026-01",
            year_month_end="2026-03",
            payment_status="overdue",
            include_voided=True,
            offset=10,
            limit=50,
        )

    assert result == {
        "items": items,
        "total": 2,
        "offset": 10,
        "limit": 50,
    }
    mock_query.assert_awaited_once_with(
        ANY,
        asset_id="asset-001",
        party_id="party-001",
        contract_id="contract-001",
        year_month_start="2026-01",
        year_month_end="2026-03",
        payment_status="overdue",
        include_voided=True,
        offset=10,
        limit=50,
        party_filter=None,
    )


async def test_query_ledger_entries_returns_empty_page() -> None:
    with patch(
        "src.services.contract.ledger_service_v2.contract_group_crud.query_ledger_entries",
        new=AsyncMock(return_value=([], 0)),
    ):
        result = await ledger_service_v2.query_ledger_entries(
            AsyncMock(),
            contract_id="contract-001",
        )

    assert result == {
        "items": [],
        "total": 0,
        "offset": 0,
        "limit": 20,
    }


async def test_query_ledger_entries_requires_at_least_one_core_filter() -> None:
    with pytest.raises(
        BusinessValidationError,
        match="至少需要一个筛选条件",
    ):
        await ledger_service_v2.query_ledger_entries(AsyncMock())


async def test_query_ledger_entries_rejects_inverted_year_month_range() -> None:
    with pytest.raises(
        BusinessValidationError,
        match="开始账期不能晚于结束账期",
    ):
        await ledger_service_v2.query_ledger_entries(
            AsyncMock(),
            contract_id="contract-001",
            year_month_start="2026-03",
            year_month_end="2026-01",
        )


async def test_query_ledger_entries_should_resolve_and_forward_party_filter() -> None:
    party_filter = PartyFilter(
        party_ids=["owner-1", "manager-1"],
        owner_party_ids=["owner-1"],
        manager_party_ids=["manager-1"],
    )

    with (
        patch.object(
            ledger_service_v2,
            "_resolve_party_filter",
            new=AsyncMock(return_value=party_filter),
        ) as mock_resolve,
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.query_ledger_entries",
            new=AsyncMock(return_value=([], 0)),
        ) as mock_query,
    ):
        result = await ledger_service_v2.query_ledger_entries(
            AsyncMock(),
            contract_id="contract-001",
            current_user_id="user-1",
        )

    assert result == {
        "items": [],
        "total": 0,
        "offset": 0,
        "limit": 20,
    }
    mock_resolve.assert_awaited_once_with(
        ANY,
        current_user_id="user-1",
        party_filter=None,
    )
    assert mock_query.await_args.kwargs["party_filter"] == party_filter


async def test_query_ledger_entries_should_fail_closed_for_empty_scope() -> None:
    with (
        patch.object(
            ledger_service_v2,
            "_resolve_party_filter",
            new=AsyncMock(return_value=PartyFilter(party_ids=[])),
        ),
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.query_ledger_entries",
            new=AsyncMock(),
        ) as mock_query,
    ):
        result = await ledger_service_v2.query_ledger_entries(
            AsyncMock(),
            contract_id="contract-001",
            current_user_id="user-1",
        )

    assert result == {
        "items": [],
        "total": 0,
        "offset": 0,
        "limit": 20,
    }
    mock_query.assert_not_awaited()
