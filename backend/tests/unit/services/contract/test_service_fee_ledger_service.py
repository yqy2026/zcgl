import importlib
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.models.contract_group import GroupRelationType, RevenueMode

pytestmark = pytest.mark.asyncio


async def test_sync_should_create_service_fee_entries_from_direct_lease_ledgers(
    mock_db,
) -> None:
    try:
        service_fee_module = importlib.import_module(
            "src.services.contract.service_fee_ledger_service"
        )
    except ImportError as exc:
        pytest.fail(f"service_fee_ledger_service module missing: {exc}")

    service = getattr(service_fee_module, "service_fee_ledger_service", None)
    assert service is not None, "service_fee_ledger_service 尚未实现"

    agency_group = SimpleNamespace(
        contract_group_id="group-1",
        revenue_mode=RevenueMode.AGENCY,
    )
    entrusted_contract = SimpleNamespace(
        contract_id="contract-entrust",
        group_relation_type=GroupRelationType.ENTRUSTED,
        agency_detail=SimpleNamespace(service_fee_ratio=Decimal("0.1000")),
    )
    direct_contract = SimpleNamespace(
        contract_id="contract-direct",
        group_relation_type=GroupRelationType.DIRECT_LEASE,
        agency_detail=None,
    )
    source_entry = SimpleNamespace(
        entry_id="entry-001",
        year_month="2026-05",
        amount_due=Decimal("2000.00"),
        paid_amount=Decimal("500.00"),
        payment_status="partial",
        currency_code="CNY",
    )
    created_payloads: list[dict] = []

    async def _create_service_fee_entry(db, *, data, commit=False):  # noqa: ANN001
        created_payloads.append(data)
        return SimpleNamespace(**data)

    with (
        patch(
            "src.services.contract.service_fee_ledger_service.contract_group_crud.get",
            new=AsyncMock(return_value=agency_group),
        ),
        patch(
            "src.services.contract.service_fee_ledger_service.contract_crud.list_by_group",
            new=AsyncMock(return_value=[entrusted_contract, direct_contract]),
        ),
        patch(
            "src.services.contract.service_fee_ledger_service.contract_group_crud.list_ledger_entries_by_contract",
            new=AsyncMock(return_value=[source_entry]),
        ),
        patch(
            "src.services.contract.service_fee_ledger_service.contract_group_crud.list_service_fee_entries_by_group",
            new=AsyncMock(return_value=[]),
            create=True,
        ),
        patch(
            "src.services.contract.service_fee_ledger_service.contract_group_crud.create_service_fee_entry",
            new=_create_service_fee_entry,
            create=True,
        ),
    ):
        result = await service.sync_contract_group(mock_db, group_id="group-1")

    assert result == {"created": 1, "updated": 0, "voided": 0}
    assert created_payloads[0]["contract_group_id"] == "group-1"
    assert created_payloads[0]["agency_contract_id"] == "contract-direct"
    assert created_payloads[0]["source_ledger_id"] == "entry-001"
    assert created_payloads[0]["amount_due"] == Decimal("200.00")
    assert created_payloads[0]["paid_amount"] == Decimal("50.00")
    assert created_payloads[0]["payment_status"] == "partial"
    assert created_payloads[0]["service_fee_ratio"] == Decimal("0.1000")
