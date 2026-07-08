from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import BusinessValidationError, OperationNotAllowedError
from src.models.contract_group import ContractLifecycleStatus, GroupRelationType
from src.services.contract.ledger_service_v2 import (
    find_stale_paid_or_partial_ledger_entries,
    ledger_service_v2,
)

pytestmark = pytest.mark.asyncio


def _make_contract(
    *,
    contract_id: str = "contract-ledger",
    status: ContractLifecycleStatus = ContractLifecycleStatus.ACTIVE,
    payment_cycle: str = "月付",
    assets: list[str] | None = None,
) -> MagicMock:
    contract = MagicMock()
    contract.contract_group_id = "group-ledger"
    contract.contract_id = contract_id
    contract.status = status
    contract.group_relation_type = GroupRelationType.DOWNSTREAM
    contract.currency_code = "CNY"
    contract.is_tax_included = True
    contract.tax_rate = Decimal("0.09")
    contract.assets = [MagicMock(id=asset_id) for asset_id in (assets or [])]
    contract.lease_detail = MagicMock(payment_cycle=payment_cycle)
    return contract


def _make_contract_group(*, assets: list[str] | None = None) -> MagicMock:
    return MagicMock(
        project_id="project-ledger",
        owner_party_id="owner-ledger",
        operator_party_id="operator-ledger",
        assets=[MagicMock(id=asset_id) for asset_id in (assets or [])],
    )


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


async def test_find_stale_paid_or_partial_ledger_entries_derives_manual_correction_signal() -> (
    None
):
    rent_terms = [
        _make_rent_term(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 28),
            monthly_rent="1000.00",
            total_monthly_amount="1200.00",
        )
    ]
    stale_amount_entry = _make_entry(
        entry_id="entry-jan",
        year_month="2026-01",
        amount_due="1000.00",
        due_date=date(2026, 1, 1),
        payment_status="paid",
        paid_amount="1000.00",
    )
    stale_period_entry = _make_entry(
        entry_id="entry-mar",
        year_month="2026-03",
        amount_due="1000.00",
        due_date=date(2026, 3, 1),
        payment_status="partial",
        paid_amount="500.00",
    )

    stale_entries = find_stale_paid_or_partial_ledger_entries(
        rent_terms=rent_terms,
        ledger_entries=[stale_amount_entry, stale_period_entry],
        payment_cycle="月付",
    )

    assert [
        (entry.entry_id, entry.year_month, entry.payment_status, entry.reason)
        for entry in stale_entries
    ] == [
        (
            "entry-jan",
            "2026-01",
            "paid",
            "paid_or_partial_entry_requires_manual_resolution",
        ),
        (
            "entry-mar",
            "2026-03",
            "partial",
            "paid_or_partial_entry_outside_current_terms",
        ),
    ]


async def test_find_stale_paid_or_partial_ledger_entries_self_heals_after_manual_alignment() -> (
    None
):
    rent_terms = [
        _make_rent_term(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            monthly_rent="1000.00",
            total_monthly_amount="1200.00",
        )
    ]
    aligned_paid_entry = _make_entry(
        entry_id="entry-jan",
        year_month="2026-01",
        amount_due="1200.00",
        due_date=date(2026, 1, 1),
        payment_status="paid",
        paid_amount="1200.00",
    )

    stale_entries = find_stale_paid_or_partial_ledger_entries(
        rent_terms=rent_terms,
        ledger_entries=[aligned_paid_entry],
        payment_cycle="月付",
    )

    assert stale_entries == []


async def test_recalculate_ledger_creates_voids_updates_and_skips_paid_entries() -> (
    None
):
    contract = _make_contract(payment_cycle="quarterly", assets=["asset-contract"])
    contract_group = _make_contract_group(assets=["asset-group"])
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
            "src.services.contract.ledger_service_v2.contract_group_crud.get_with_assets",
            new=AsyncMock(return_value=contract_group),
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
    assert created_payloads[0]["due_date"] == date(2026, 3, 1)
    assert created_payloads[0]["attributed_project_id"] == "project-ledger"
    assert created_payloads[0]["attributed_owner_party_id"] == "owner-ledger"
    assert created_payloads[0]["attributed_operator_party_id"] == "operator-ledger"
    assert created_payloads[0]["attributed_asset_ids"] == ["asset-contract"]
    mock_db.flush.assert_awaited_once()
    mock_db.commit.assert_awaited_once()


async def test_recalculate_ledger_falls_back_to_group_assets_for_whole_rent() -> None:
    contract = _make_contract(assets=[])
    contract_group = _make_contract_group(assets=["asset-a", "asset-b"])
    rent_terms = [
        _make_rent_term(
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 30),
            monthly_rent="1000.00",
            total_monthly_amount="1200.00",
        )
    ]
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
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.get_with_assets",
            new=AsyncMock(return_value=contract_group),
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

    assert result["created"] == 1
    assert created_payloads[0]["attributed_asset_ids"] == ["asset-a", "asset-b"]
    assert created_payloads[0]["attributed_project_id"] == "project-ledger"


async def test_recalculate_ledger_revives_voided_entries_and_refreshes_due_date() -> (
    None
):
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
    contract_group = _make_contract_group()

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
            "src.services.contract.ledger_service_v2.contract_group_crud.get_with_assets",
            new=AsyncMock(return_value=contract_group),
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
    contract_group = _make_contract_group()

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
            "src.services.contract.ledger_service_v2.contract_group_crud.get_with_assets",
            new=AsyncMock(return_value=contract_group),
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
    contract_group = _make_contract_group()

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
            "src.services.contract.ledger_service_v2.contract_group_crud.get_with_assets",
            new=AsyncMock(return_value=contract_group),
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
    contract_group = _make_contract_group()

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
            "src.services.contract.ledger_service_v2.contract_group_crud.get_with_assets",
            new=AsyncMock(return_value=contract_group),
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


async def test_reverse_correction_uses_paid_amount_as_receipt_guard() -> None:
    paid_zero_entry = _make_entry(
        entry_id="entry-paid-zero",
        year_month="2026-06",
        amount_due="1000.00",
        due_date=date(2026, 6, 1),
        payment_status="paid",
        paid_amount="0",
    )
    received_entry = _make_entry(
        entry_id="entry-received",
        year_month="2026-07",
        amount_due="1000.00",
        due_date=date(2026, 7, 1),
        payment_status="unpaid",
        paid_amount="1.00",
    )
    mock_db = MagicMock()
    mock_db.flush = AsyncMock()

    with patch(
        "src.services.contract.ledger_service_v2.contract_group_crud.list_ledger_entries_by_contract",
        new=AsyncMock(return_value=[paid_zero_entry, received_entry]),
    ):
        with pytest.raises(OperationNotAllowedError):
            await ledger_service_v2.reverse_correction_source_entries(
                mock_db,
                contract_id="contract-ledger",
                year_month_start="2026-06",
            )

    assert paid_zero_entry.payment_status == "voided"
    assert received_entry.payment_status == "unpaid"
