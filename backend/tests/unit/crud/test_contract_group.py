"""
合同组 CRUD 聚合查询单元测试。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.contract_group import CRUDContractGroup

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
        assert "contracts" in compiled
        assert "attributed_owner_party_id = 'owner-1'" in compiled
        assert "contract_groups" not in compiled
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
        assert "contracts" in compiled
        assert "attributed_owner_party_id = 'owner-1'" in compiled
        assert "contract_groups" not in compiled
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
        assert "attributed_owner_party_id = 'owner-1'" in compiled
        assert "contract_groups" not in compiled
        assert "rent_ledger" not in compiled


class TestLedgerAggregateQueries:
    async def test_query_ledger_entries_filters_asset_by_frozen_attribution(
        self, crud: CRUDContractGroup, mock_db: MagicMock
    ) -> None:
        page_result = MagicMock()
        page_result.scalar_one.return_value = 0
        page_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = page_result

        await crud.query_ledger_entries(mock_db, asset_id="asset-1")

        count_stmt = mock_db.execute.await_args_list[0].args[0]
        compiled = count_stmt.compile()
        sql = str(compiled)
        assert "contract_ledger_entries" in sql
        assert "attributed_asset_ids" in sql
        assert "asset-1" in repr(compiled.params)
        assert "contract_assets" not in sql
