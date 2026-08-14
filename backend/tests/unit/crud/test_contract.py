"""
Contract CRUD query predicate tests.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.contract import CRUDContract

pytestmark = pytest.mark.asyncio


@pytest.fixture
def crud() -> CRUDContract:
    return CRUDContract()


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)
    return db


class TestAnalyticsQueries:
    async def test_list_active_for_analytics_applies_scope_and_date_overlap(
        self,
        crud: CRUDContract,
        mock_db: MagicMock,
    ) -> None:
        await crud.list_active_for_analytics(
            mock_db,
            party_ids=["manager-1"],
            filter_mode="manager",
            date_from=date(2026, 5, 1),
            date_to=date(2026, 5, 31),
        )

        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))

        assert "contract_groups.operator_party_id IN ('manager-1')" in compiled
        assert "contracts.effective_from <= '2026-05-31'" in compiled
        assert "contracts.effective_to IS NULL" in compiled
        assert "contracts.effective_to >= '2026-05-01'" in compiled


class TestContractNumberQueries:
    async def test_shared_scan_scope_excludes_deleted_contract_groups(
        self,
        crud: CRUDContract,
        mock_db: MagicMock,
    ) -> None:
        await crud.list_by_contract_number(
            mock_db,
            contract_number="HT-SHARED-001",
            lessor_party_id="owner-party",
            lessee_party_id="operator-party",
            shared_scan_scope_only=True,
        )

        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))

        assert "contracts.contract_number = 'HT-SHARED-001'" in compiled
        assert "contracts.group_relation_type = 'ENTRUSTED'" in compiled
        assert "contract_groups.revenue_mode = 'AGENCY'" in compiled
        assert "contract_groups.data_status = '正常'" in compiled


@pytest.mark.asyncio
async def test_contract_main_table_rejects_payment_cycle_kwarg(
    crud: CRUDContract,
) -> None:
    """Contract 主表不接受 payment_cycle；它属于 LeaseContractDetail。

    service 必须把 payment_cycle 合并进 lease_detail 数据，而不是放进
    Contract 构造 dict——否则真实 ORM 构造直接 TypeError 崩溃。
    """
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    with pytest.raises(TypeError, match="payment_cycle"):
        await crud.create(
            db,
            data={
                "contract_id": "contract-1",
                "payment_cycle": "月付",
            },
        )


@pytest.mark.asyncio
async def test_contract_create_builds_real_orm_object_without_crash(
    crud: CRUDContract,
) -> None:
    """合法 Contract 字段能真实构造 ORM 对象（回归：payment_cycle 曾导致 TypeError）。"""
    from src.models.contract_group import Contract

    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    result = await crud.create(
        db,
        data={"contract_id": "contract-2", "contract_number": "HT-REAL-001"},
        commit=False,
    )

    assert isinstance(result, Contract)
    assert result.contract_id == "contract-2"
