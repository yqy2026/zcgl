"""
催缴 CRUD 单元测试。
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.collection import CRUDCollectionRecord
from src.crud.query_builder import PartyFilter
from src.models.collection import CollectionRecord

pytestmark = pytest.mark.asyncio


@pytest.fixture
def crud() -> CRUDCollectionRecord:
    return CRUDCollectionRecord(CollectionRecord)


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    db.execute = AsyncMock()
    return db


class TestCollectionCrudV2:
    async def test_get_overdue_ledger_stats_uses_contract_ledger_entries(
        self, crud: CRUDCollectionRecord, mock_db: MagicMock
    ) -> None:
        stats = MagicMock()
        stats.total_count = 2
        stats.total_amount = Decimal("3000.00")
        execute_result = MagicMock()
        execute_result.first.return_value = stats
        mock_db.execute.return_value = execute_result

        result = await crud.get_overdue_ledger_stats_async(
            mock_db,
            today=date(2026, 3, 7),
        )

        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert result == (2, Decimal("3000.00"))
        assert "contract_ledger_entries" in compiled
        assert "amount_due" in compiled
        assert "paid_amount" in compiled
        assert "unpaid" in compiled
        assert "partial" in compiled
        assert "overdue" in compiled
        assert "rent_ledger" not in compiled

    async def test_get_ledger_by_id_uses_contract_ledger_entries(
        self, crud: CRUDCollectionRecord, mock_db: MagicMock
    ) -> None:
        execute_result = MagicMock()
        execute_result.scalars.return_value.first.return_value = MagicMock()
        mock_db.execute.return_value = execute_result

        await crud.get_ledger_by_id_async(mock_db, ledger_id="entry-1")

        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "contract_ledger_entries" in compiled
        assert "entry_id = 'entry-1'" in compiled
        assert "rent_ledger" not in compiled

    async def test_get_multi_with_filters_applies_contract_group_scope(
        self, crud: CRUDCollectionRecord, mock_db: MagicMock
    ) -> None:
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[count_result, items_result])

        party_filter = PartyFilter(
            party_ids=["owner-1", "manager-1"],
            owner_party_ids=["owner-1"],
            manager_party_ids=["manager-1"],
        )

        await crud.get_multi_with_filters_async(
            mock_db,
            contract_id="contract-1",
            party_filter=party_filter,
        )

        stmt = mock_db.execute.await_args_list[0].args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "contract_groups.owner_party_id IN ('owner-1')" in compiled
        assert "contract_groups.operator_party_id IN ('manager-1')" in compiled

    async def test_get_by_id_returns_none_for_fail_closed_scope(
        self, crud: CRUDCollectionRecord, mock_db: MagicMock
    ) -> None:
        result = await crud.get_by_id_async(
            mock_db,
            record_id="record-1",
            party_filter=PartyFilter(party_ids=[]),
        )

        assert result is None
        mock_db.execute.assert_not_called()
