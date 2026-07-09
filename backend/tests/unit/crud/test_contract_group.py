"""
合同组 CRUD 聚合查询单元测试。
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.contract_group import CRUDContractGroup
from src.models.contract_group import ContractLedgerEntry

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


def _ledger_entry(
    *,
    paid_amount: Decimal = Decimal("0.00"),
    payment_status: str = "unpaid",
) -> ContractLedgerEntry:
    return ContractLedgerEntry(
        entry_id="entry-1",
        contract_id="contract-1",
        year_month="2026-01",
        due_date=date(2026, 1, 1),
        amount_due=Decimal("1000.00"),
        ledger_views=["terminal_collection"],
        currency_code="CNY",
        is_tax_included=True,
        paid_amount=paid_amount,
        payment_status=payment_status,
    )


def _assert_active_ledger_allocation_sql(sql: str) -> None:
    assert "payment_allocations" in sql
    assert "operational_payment_flows" in sql
    assert "target_type = 'contract_ledger_entry'" in sql
    assert "operational_payment_flows.status = 'active'" in sql
    assert "count(payment_allocations.allocation_id)" in sql


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

    async def test_sum_paid_amount_by_ownership_uses_active_allocations(
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
        _assert_active_ledger_allocation_sql(compiled)
        assert "contract_groups" not in compiled
        assert "rent_ledger" not in compiled

    async def test_sum_overdue_amount_by_ownership_uses_active_allocations(
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
        _assert_active_ledger_allocation_sql(compiled)
        assert "contract_groups" not in compiled
        assert "rent_ledger" not in compiled


class TestLedgerAggregateQueries:
    async def test_query_ledger_entries_filters_asset_by_frozen_attribution(
        self, crud: CRUDContractGroup, mock_db: MagicMock
    ) -> None:
        page_result = MagicMock()
        page_result.scalar_one.return_value = 0
        page_result.all.return_value = []
        mock_db.execute.return_value = page_result

        await crud.query_ledger_entries(mock_db, asset_id="asset-1")

        count_stmt = mock_db.execute.await_args_list[0].args[0]
        compiled = count_stmt.compile()
        sql = str(compiled)
        assert "contract_ledger_entries" in sql
        assert "attributed_asset_ids" in sql
        assert "asset-1" in repr(compiled.params)
        assert "contract_assets" not in sql

    async def test_query_ledger_entries_uses_active_allocations_for_status_and_paid_amount(
        self, crud: CRUDContractGroup, mock_db: MagicMock
    ) -> None:
        entry = _ledger_entry()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        items_result = MagicMock()
        items_result.all.return_value = [(entry, Decimal("600.00"), "partial")]
        mock_db.execute.side_effect = [count_result, items_result]

        items, total = await crud.query_ledger_entries(
            mock_db,
            contract_id="contract-1",
            payment_status="partial",
        )

        count_stmt = mock_db.execute.await_args_list[0].args[0]
        compiled = count_stmt.compile(compile_kwargs={"literal_binds": True})
        sql = str(compiled)
        assert total == 1
        assert items == [entry]
        assert entry.paid_amount == Decimal("600.00")
        assert entry.payment_status == "partial"
        assert "payment_allocations" in sql
        assert "operational_payment_flows" in sql
        assert "target_type = 'contract_ledger_entry'" in sql
        assert "operational_payment_flows.status = 'active'" in sql
        assert "partial" in sql

    async def test_list_ledger_entries_by_contract_applies_active_allocation_facts(
        self, crud: CRUDContractGroup, mock_db: MagicMock
    ) -> None:
        entry = _ledger_entry()
        result = MagicMock()
        result.all.return_value = [(entry, Decimal("1000.00"), "paid", 2)]
        mock_db.execute.return_value = result

        items = await crud.list_ledger_entries_by_contract(
            mock_db,
            contract_id="contract-1",
        )

        stmt = mock_db.execute.await_args.args[0]
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert items == [entry]
        assert entry.paid_amount == Decimal("1000.00")
        assert entry.payment_status == "paid"
        _assert_active_ledger_allocation_sql(sql)

    async def test_get_overdue_with_contract_uses_active_allocations(
        self, crud: CRUDContractGroup, mock_db: MagicMock
    ) -> None:
        entry = _ledger_entry()
        result = MagicMock()
        result.all.return_value = [(entry, Decimal("600.00"), "partial")]
        mock_db.execute.return_value = result

        items = await crud.get_overdue_with_contract_async(
            mock_db,
            today=date(2026, 2, 1),
        )

        stmt = mock_db.execute.await_args.args[0]
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert items == [entry]
        assert entry.paid_amount == Decimal("600.00")
        assert entry.payment_status == "partial"
        assert "contract_ledger_entries.due_date < '2026-02-01'" in sql
        _assert_active_ledger_allocation_sql(sql)

    async def test_get_due_soon_with_contract_uses_active_allocations(
        self, crud: CRUDContractGroup, mock_db: MagicMock
    ) -> None:
        entry = _ledger_entry()
        result = MagicMock()
        result.all.return_value = [(entry, Decimal("0.00"), "unpaid")]
        mock_db.execute.return_value = result

        items = await crud.get_due_soon_with_contract_async(
            mock_db,
            today=date(2026, 1, 1),
            warning_date=date(2026, 1, 31),
        )

        stmt = mock_db.execute.await_args.args[0]
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert items == [entry]
        assert entry.paid_amount == Decimal("0.00")
        assert entry.payment_status == "unpaid"
        assert "contract_ledger_entries.due_date <= '2026-01-31'" in sql
        assert "contract_ledger_entries.due_date >= '2026-01-01'" in sql
        _assert_active_ledger_allocation_sql(sql)
