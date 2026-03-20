"""
合同组 CRUD 聚合查询单元测试。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.contract_group import CRUDContractGroup
from src.crud.query_builder import PartyFilter

pytestmark = pytest.mark.asyncio


@pytest.fixture
def crud() -> CRUDContractGroup:
    return CRUDContractGroup()


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    db.execute = AsyncMock()
    return db


def _mock_scalar_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar.return_value = value
    result.scalar_one.return_value = value
    return result


class TestOwnershipAggregates:
    async def test_count_by_ownership_uses_new_contract_tables(
        self, crud: CRUDContractGroup, mock_db: MagicMock
    ) -> None:
        legacy_contract_table = "_".join(("rent", "contracts"))
        mock_db.execute.return_value = _mock_scalar_result(3)

        result = await crud.count_by_ownership_async(mock_db, "owner-1")

        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert result == 3
        assert "contract_groups" in compiled
        assert "contracts" in compiled
        assert "owner_party_id = 'owner-1'" in compiled
        assert legacy_contract_table not in compiled

    async def test_count_active_by_ownership_uses_new_contract_tables(
        self, crud: CRUDContractGroup, mock_db: MagicMock
    ) -> None:
        legacy_contract_table = "_".join(("rent", "contracts"))
        mock_db.execute.return_value = _mock_scalar_result(2)

        result = await crud.count_active_by_ownership_async(mock_db, "owner-1")

        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert result == 2
        assert "contract_groups" in compiled
        assert "contracts" in compiled
        assert "owner_party_id = 'owner-1'" in compiled
        assert "ACTIVE" in compiled
        assert legacy_contract_table not in compiled

    async def test_sum_due_amount_by_ownership_uses_new_contract_ledger_tables(
        self, crud: CRUDContractGroup, mock_db: MagicMock
    ) -> None:
        mock_db.execute.return_value = _mock_scalar_result(10000.0)

        result = await crud.sum_due_amount_by_ownership_async(mock_db, "owner-1")

        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert result == 10000.0
        assert "contract_ledger_entries" in compiled
        assert "contract_groups" in compiled
        assert "contracts" in compiled
        assert "owner_party_id = 'owner-1'" in compiled
        assert "rent_ledger" not in compiled

    async def test_sum_paid_amount_by_ownership_uses_new_contract_ledger_tables(
        self, crud: CRUDContractGroup, mock_db: MagicMock
    ) -> None:
        mock_db.execute.return_value = _mock_scalar_result(8000.0)

        result = await crud.sum_paid_amount_by_ownership_async(mock_db, "owner-1")

        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert result == 8000.0
        assert "contract_ledger_entries" in compiled
        assert "contract_groups" in compiled
        assert "contracts" in compiled
        assert "owner_party_id = 'owner-1'" in compiled
        assert "rent_ledger" not in compiled

    async def test_sum_overdue_amount_by_ownership_uses_due_minus_paid(
        self, crud: CRUDContractGroup, mock_db: MagicMock
    ) -> None:
        mock_db.execute.return_value = _mock_scalar_result(2000.0)

        result = await crud.sum_overdue_amount_by_ownership_async(mock_db, "owner-1")

        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert result == 2000.0
        assert "contract_ledger_entries" in compiled
        assert "amount_due" in compiled
        assert "paid_amount" in compiled
        assert "owner_party_id = 'owner-1'" in compiled
        assert "rent_ledger" not in compiled


class TestTenantScopeFilters:
    async def test_list_by_filters_applies_owner_and_operator_scope(
        self, crud: CRUDContractGroup, mock_db: MagicMock
    ) -> None:
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[count_result, items_result])

        party_filter = PartyFilter(
            party_ids=["owner-1", "manager-1"],
            owner_party_ids=["owner-1"],
            manager_party_ids=["manager-1"],
        )

        await crud.list_by_filters(mock_db, party_filter=party_filter)

        stmt = mock_db.execute.await_args_list[0].args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "contract_groups.owner_party_id IN ('owner-1')" in compiled
        assert "contract_groups.operator_party_id IN ('manager-1')" in compiled

    async def test_list_by_filters_returns_empty_for_fail_closed_scope(
        self, crud: CRUDContractGroup, mock_db: MagicMock
    ) -> None:
        result = await crud.list_by_filters(
            mock_db,
            party_filter=PartyFilter(party_ids=[]),
        )

        assert result == ([], 0)
        mock_db.execute.assert_not_called()

    async def test_query_ledger_entries_applies_owner_and_operator_scope(
        self, crud: CRUDContractGroup, mock_db: MagicMock
    ) -> None:
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[count_result, items_result])

        party_filter = PartyFilter(
            party_ids=["owner-1", "manager-1"],
            owner_party_ids=["owner-1"],
            manager_party_ids=["manager-1"],
        )

        await crud.query_ledger_entries(
            mock_db,
            contract_id="contract-001",
            party_filter=party_filter,
        )

        stmt = mock_db.execute.await_args_list[0].args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "contract_groups.owner_party_id IN ('owner-1')" in compiled
        assert "contract_groups.operator_party_id IN ('manager-1')" in compiled

    async def test_query_ledger_entries_returns_empty_for_fail_closed_scope(
        self, crud: CRUDContractGroup, mock_db: MagicMock
    ) -> None:
        result = await crud.query_ledger_entries(
            mock_db,
            contract_id="contract-001",
            party_filter=PartyFilter(party_ids=[]),
        )

        assert result == ([], 0)
        mock_db.execute.assert_not_called()
