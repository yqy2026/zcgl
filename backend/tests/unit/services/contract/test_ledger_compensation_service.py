from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.models.contract_group import ContractLifecycleStatus

pytestmark = pytest.mark.asyncio


def _make_contract(contract_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        contract_id=contract_id,
        status=ContractLifecycleStatus.ACTIVE,
        lease_detail=SimpleNamespace(payment_cycle="月付"),
        data_status="正常",
    )


def _make_rent_term(
    *,
    start_date: date,
    end_date: date,
    sort_order: int = 1,
) -> SimpleNamespace:
    return SimpleNamespace(
        start_date=start_date,
        end_date=end_date,
        sort_order=sort_order,
    )


def _make_entry(*, year_month: str, payment_status: str = "unpaid") -> SimpleNamespace:
    return SimpleNamespace(
        year_month=year_month,
        payment_status=payment_status,
    )


async def test_compensation_should_fill_missing_months_for_active_contract(mock_db) -> None:
    try:
        from src.services.contract import (
            ledger_compensation_service as ledger_compensation_module,
        )
    except ImportError as exc:
        pytest.fail(f"ledger_compensation_service module missing: {exc}")

    service = getattr(ledger_compensation_module, "ledger_compensation_service", None)
    assert service is not None, "ledger_compensation_service 尚未实现"

    drift_contract = _make_contract("contract-drift")
    clean_contract = _make_contract("contract-clean")
    rent_terms = [
        _make_rent_term(
            start_date=date(2026, 5, 1),
            end_date=date(2026, 6, 30),
            sort_order=1,
        )
    ]

    with (
        patch(
            "src.services.contract.ledger_compensation_service.contract_crud.list_active_lease_contracts_for_ledger",
            new=AsyncMock(return_value=[drift_contract, clean_contract]),
            create=True,
        ),
        patch(
            "src.services.contract.ledger_compensation_service.contract_group_crud.list_rent_terms_by_contract",
            new=AsyncMock(side_effect=[rent_terms, rent_terms]),
        ),
        patch(
            "src.services.contract.ledger_compensation_service.contract_group_crud.list_ledger_entries_by_contract",
            new=AsyncMock(
                side_effect=[
                    [_make_entry(year_month="2026-05")],
                    [
                        _make_entry(year_month="2026-05"),
                        _make_entry(year_month="2026-06"),
                    ],
                ]
            ),
        ),
        patch(
            "src.services.contract.ledger_compensation_service.ledger_service_v2.recalculate_ledger",
            new=AsyncMock(
                return_value={
                    "created": 1,
                    "updated": 0,
                    "voided": 0,
                    "skipped_entries": [],
                }
            ),
        ) as mock_recalculate,
    ):
        result = await service.run(mock_db)

    assert result["contracts_scanned"] == 2
    assert result["contracts_repaired"] == 1
    assert result["rent_entries_created"] == 1
    assert result["rent_entries_voided"] == 0
    assert result["failures"] == []
    assert "timestamp" in result
    mock_recalculate.assert_awaited_once_with(
        mock_db,
        contract_id="contract-drift",
        commit=False,
    )
    mock_db.commit.assert_awaited_once()


async def test_compensation_should_resync_service_fee_even_without_rent_drift(
    mock_db,
) -> None:
    from src.services.contract import (
        ledger_compensation_service as ledger_compensation_module,
    )

    service = getattr(ledger_compensation_module, "ledger_compensation_service", None)
    assert service is not None, "ledger_compensation_service 尚未实现"

    agency_contract = SimpleNamespace(
        contract_id="contract-direct",
        contract_group_id="group-agency",
        status=ContractLifecycleStatus.ACTIVE,
        lease_detail=SimpleNamespace(payment_cycle="月付"),
        data_status="正常",
    )
    rent_terms = [
        _make_rent_term(
            start_date=date(2026, 5, 1),
            end_date=date(2026, 6, 30),
            sort_order=1,
        )
    ]
    clean_entries = [
        _make_entry(year_month="2026-05"),
        _make_entry(year_month="2026-06"),
    ]

    mock_db.commit.reset_mock()

    with (
        patch(
            "src.services.contract.ledger_compensation_service.contract_crud.list_active_lease_contracts_for_ledger",
            new=AsyncMock(return_value=[agency_contract]),
        ),
        patch(
            "src.services.contract.ledger_compensation_service.contract_group_crud.list_rent_terms_by_contract",
            new=AsyncMock(return_value=rent_terms),
        ),
        patch(
            "src.services.contract.ledger_compensation_service.contract_group_crud.list_ledger_entries_by_contract",
            new=AsyncMock(return_value=clean_entries),
        ),
        patch(
            "src.services.contract.ledger_compensation_service.ledger_service_v2.recalculate_ledger",
            new=AsyncMock(),
        ) as mock_recalculate,
        patch(
            "src.services.contract.ledger_compensation_service.service_fee_ledger_service.sync_contract_group",
            new=AsyncMock(return_value={"created": 1, "updated": 0, "voided": 0}),
        ) as mock_sync_service_fee,
    ):
        result = await service.run(mock_db)

    assert result["contracts_scanned"] == 1
    assert result["contracts_repaired"] == 0
    assert result["rent_entries_created"] == 0
    assert result["rent_entries_voided"] == 0
    assert result["failures"] == []
    mock_recalculate.assert_not_awaited()
    mock_sync_service_fee.assert_awaited_once_with(
        mock_db,
        group_id="group-agency",
        commit=False,
    )
    mock_db.commit.assert_awaited_once()
