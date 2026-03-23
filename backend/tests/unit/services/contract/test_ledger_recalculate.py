from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import BusinessValidationError
from src.models.contract_group import ContractLifecycleStatus
from src.services.contract.ledger_service_v2 import ledger_service_v2

pytestmark = pytest.mark.asyncio


def _make_contract(
    *,
    contract_id: str = "contract-ledger",
    status: ContractLifecycleStatus = ContractLifecycleStatus.ACTIVE,
    payment_cycle: str = "月付",
) -> MagicMock:
    contract = MagicMock()
    contract.contract_id = contract_id
    contract.status = status
    contract.currency_code = "CNY"
    contract.is_tax_included = True
    contract.tax_rate = Decimal("0.09")
    contract.lease_detail = MagicMock(payment_cycle=payment_cycle)
    return contract


def _make_rent_term(
    *,
    start_date: date,
    end_date: date,
    monthly_rent: str,
    total_monthly_amount: str | None = None,
    sort_order: int = 1,
) -> MagicMock:
    rent_term = MagicMock()
    rent_term.start_date = start_date
    rent_term.end_date = end_date
    rent_term.monthly_rent = Decimal(monthly_rent)
    rent_term.total_monthly_amount = (
        Decimal(total_monthly_amount) if total_monthly_amount is not None else None
    )
    rent_term.sort_order = sort_order
    return rent_term


def _make_entry(
    *,
    entry_id: str,
    year_month: str,
    amount_due: str,
    due_date: date,
    payment_status: str = "unpaid",
    paid_amount: str = "0",
) -> SimpleNamespace:
    return SimpleNamespace(
        entry_id=entry_id,
        year_month=year_month,
        amount_due=Decimal(amount_due),
        due_date=due_date,
        payment_status=payment_status,
        paid_amount=Decimal(paid_amount),
        updated_at=None,
    )


async def test_recalculate_ledger_creates_voids_updates_and_skips_paid_entries() -> None:
    contract = _make_contract(payment_cycle="季付")
    rent_terms = [
        _make_rent_term(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            monthly_rent="1000.00",
            total_monthly_amount="1200.00",
        )
    ]
    jan_entry = _make_entry(
        entry_id="entry-jan",
        year_month="2026-01",
        amount_due="1000.00",
        due_date=date(2026, 1, 1),
    )
    feb_entry = _make_entry(
        entry_id="entry-feb",
        year_month="2026-02",
        amount_due="1000.00",
        due_date=date(2026, 2, 1),
        payment_status="paid",
        paid_amount="1000.00",
    )
    apr_entry = _make_entry(
        entry_id="entry-apr",
        year_month="2026-04",
        amount_due="1000.00",
        due_date=date(2026, 4, 1),
    )
    created_payloads: list[dict] = []
    mock_db = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    async def _create_entry(db, *, data, commit=False):  # noqa: ANN001
        created_payloads.append(data)
        return SimpleNamespace(**data)

    with (
        patch(
            "src.services.contract.ledger_service_v2.contract_crud.get",
            new=AsyncMock(return_value=contract),
        ),
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.list_rent_terms_by_contract",
            new=AsyncMock(return_value=rent_terms),
        ),
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.list_ledger_entries_by_contract",
            new=AsyncMock(return_value=[jan_entry, feb_entry, apr_entry]),
        ),
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.create_ledger_entry",
            new=_create_entry,
        ),
    ):
        result = await ledger_service_v2.recalculate_ledger(
            mock_db,
            contract_id="contract-ledger",
        )

    assert result == {
        "created": 1,
        "updated": 1,
        "voided": 1,
        "skipped_entries": [
            {
                "entry_id": "entry-feb",
                "year_month": "2026-02",
                "payment_status": "paid",
                "reason": "paid_or_partial_entry_requires_manual_resolution",
            }
        ],
    }
    assert jan_entry.amount_due == Decimal("1200.00")
    assert jan_entry.due_date == date(2026, 1, 1)
    assert feb_entry.amount_due == Decimal("1000.00")
    assert feb_entry.due_date == date(2026, 2, 1)
    assert apr_entry.payment_status == "voided"
    assert created_payloads[0]["year_month"] == "2026-03"
    assert created_payloads[0]["amount_due"] == Decimal("1200.00")
    assert created_payloads[0]["due_date"] == date(2026, 1, 1)
    mock_db.flush.assert_awaited_once()
    mock_db.commit.assert_awaited_once()


async def test_recalculate_ledger_revives_voided_entries_and_refreshes_due_date() -> None:
    contract = _make_contract(payment_cycle="半年付")
    rent_terms = [
        _make_rent_term(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            monthly_rent="1800.00",
            total_monthly_amount="2100.00",
        )
    ]
    voided_entry = _make_entry(
        entry_id="entry-voided",
        year_month="2026-07",
        amount_due="900.00",
        due_date=date(2026, 7, 15),
        payment_status="voided",
    )
    mock_db = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    with (
        patch(
            "src.services.contract.ledger_service_v2.contract_crud.get",
            new=AsyncMock(return_value=contract),
        ),
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.list_rent_terms_by_contract",
            new=AsyncMock(return_value=rent_terms),
        ),
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.list_ledger_entries_by_contract",
            new=AsyncMock(return_value=[voided_entry]),
        ),
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.create_ledger_entry",
            new=AsyncMock(),
        ),
    ):
        result = await ledger_service_v2.recalculate_ledger(
            mock_db,
            contract_id="contract-ledger",
        )

    assert result == {
        "created": 0,
        "updated": 1,
        "voided": 0,
        "skipped_entries": [],
    }
    assert voided_entry.payment_status == "unpaid"
    assert voided_entry.paid_amount == Decimal("0")
    assert voided_entry.amount_due == Decimal("2100.00")
    assert voided_entry.due_date == date(2026, 7, 1)


async def test_recalculate_ledger_is_idempotent_when_entries_already_match() -> None:
    contract = _make_contract(payment_cycle="年付")
    rent_terms = [
        _make_rent_term(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            monthly_rent="1000.00",
            total_monthly_amount="1500.00",
        )
    ]
    existing_entry = _make_entry(
        entry_id="entry-idempotent",
        year_month="2026-01",
        amount_due="1500.00",
        due_date=date(2026, 1, 1),
    )
    mock_db = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    with (
        patch(
            "src.services.contract.ledger_service_v2.contract_crud.get",
            new=AsyncMock(return_value=contract),
        ),
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.list_rent_terms_by_contract",
            new=AsyncMock(return_value=rent_terms),
        ),
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.list_ledger_entries_by_contract",
            new=AsyncMock(return_value=[existing_entry]),
        ),
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.create_ledger_entry",
            new=AsyncMock(),
        ) as mock_create,
    ):
        result = await ledger_service_v2.recalculate_ledger(
            mock_db,
            contract_id="contract-ledger",
        )

    assert result == {
        "created": 0,
        "updated": 0,
        "voided": 0,
        "skipped_entries": [],
    }
    mock_create.assert_not_awaited()


async def test_recalculate_ledger_requires_active_contract() -> None:
    contract = _make_contract(status=ContractLifecycleStatus.DRAFT)

    with patch(
        "src.services.contract.ledger_service_v2.contract_crud.get",
        new=AsyncMock(return_value=contract),
    ):
        with pytest.raises(BusinessValidationError, match="仅生效合同允许重算"):
            await ledger_service_v2.recalculate_ledger(
                AsyncMock(),
                contract_id="contract-ledger",
            )


async def test_recalculate_ledger_skips_partial_entry() -> None:
    """R-05: partial 条目应被跳过并记入 skipped_entries。"""
    contract = _make_contract()
    rent_terms = [
        _make_rent_term(
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 31),
            monthly_rent="800.00",
            total_monthly_amount="1000.00",
        )
    ]
    partial_entry = _make_entry(
        entry_id="entry-partial",
        year_month="2026-05",
        amount_due="500.00",
        due_date=date(2026, 5, 1),
        payment_status="partial",
        paid_amount="200.00",
    )
    mock_db = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    with (
        patch(
            "src.services.contract.ledger_service_v2.contract_crud.get",
            new=AsyncMock(return_value=contract),
        ),
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.list_rent_terms_by_contract",
            new=AsyncMock(return_value=rent_terms),
        ),
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.list_ledger_entries_by_contract",
            new=AsyncMock(return_value=[partial_entry]),
        ),
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.create_ledger_entry",
            new=AsyncMock(),
        ),
    ):
        result = await ledger_service_v2.recalculate_ledger(
            mock_db,
            contract_id="contract-ledger",
        )

    assert result["skipped_entries"] == [
        {
            "entry_id": "entry-partial",
            "year_month": "2026-05",
            "payment_status": "partial",
            "reason": "paid_or_partial_entry_requires_manual_resolution",
        }
    ]
    assert result["created"] == 0
    assert result["updated"] == 0
    assert result["voided"] == 0
    # partial 条目的金额不应被修改
    assert partial_entry.amount_due == Decimal("500.00")
    assert partial_entry.paid_amount == Decimal("200.00")


async def test_recalculate_ledger_updates_due_date_only_when_amount_unchanged() -> None:
    """R-10: payment_cycle 变化导致仅 due_date 变更，amount_due 不变。"""
    # 季付 → due_date 为季初
    contract = _make_contract(payment_cycle="季付")
    rent_terms = [
        _make_rent_term(
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
            monthly_rent="3000.00",
            total_monthly_amount="3000.00",
        )
    ]
    # 现有条目 amount_due 已匹配，但 due_date 是月付的（月初）
    existing_entry = _make_entry(
        entry_id="entry-due-only",
        year_month="2026-02",
        amount_due="3000.00",
        due_date=date(2026, 2, 1),  # 月付 due_date
    )
    mock_db = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    with (
        patch(
            "src.services.contract.ledger_service_v2.contract_crud.get",
            new=AsyncMock(return_value=contract),
        ),
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.list_rent_terms_by_contract",
            new=AsyncMock(return_value=rent_terms),
        ),
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.list_ledger_entries_by_contract",
            new=AsyncMock(return_value=[existing_entry]),
        ),
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.create_ledger_entry",
            new=AsyncMock(),
        ),
    ):
        result = await ledger_service_v2.recalculate_ledger(
            mock_db,
            contract_id="contract-ledger",
        )

    # 季付 due_date = 季初 = 2026-01-01
    assert existing_entry.due_date == date(2026, 1, 1)
    # amount_due 不变
    assert existing_entry.amount_due == Decimal("3000.00")
    assert result["updated"] == 1
    assert result["created"] == 0
    assert result["voided"] == 0


async def test_batch_update_status_rejects_voided_for_internal_callers() -> None:
    with pytest.raises(
        BusinessValidationError,
        match="voided 为系统保留状态",
    ):
        await ledger_service_v2.batch_update_status(
            AsyncMock(),
            contract_id="contract-ledger",
            entry_ids=["entry-001"],
            payment_status="voided",
        )


async def test_batch_update_status_rejects_unknown_status_for_internal_callers() -> None:
    with pytest.raises(
        BusinessValidationError,
        match="payment_status 必须为",
    ):
        await ledger_service_v2.batch_update_status(
            AsyncMock(),
            contract_id="contract-ledger",
            entry_ids=["entry-001"],
            payment_status="foo",
        )
