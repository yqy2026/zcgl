import importlib
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.core.exception_handler import BusinessValidationError
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
        attributed_project_id="project-001",
        attributed_owner_party_id="owner-001",
        attributed_operator_party_id="operator-001",
        attributed_asset_ids=["asset-001"],
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

    assert result == {"created": 1, "updated": 0, "voided": 0, "source_mismatches": 0}
    assert created_payloads[0]["contract_group_id"] == "group-1"
    assert created_payloads[0]["agency_contract_id"] == "contract-direct"
    assert created_payloads[0]["agency_agreement_contract_id"] == "contract-entrust"
    assert created_payloads[0]["source_ledger_ids"] == ["entry-001"]
    assert created_payloads[0]["calculation_base_amount"] == Decimal("500.00")
    assert created_payloads[0]["amount_due"] == Decimal("50.00")
    assert created_payloads[0]["paid_amount"] == Decimal("0")
    assert created_payloads[0]["payment_status"] == "unpaid"
    assert created_payloads[0]["service_fee_ratio"] == Decimal("0.1000")
    assert created_payloads[0]["attributed_project_id"] == "project-001"
    assert created_payloads[0]["attributed_owner_party_id"] == "owner-001"
    assert created_payloads[0]["attributed_operator_party_id"] == "operator-001"
    assert created_payloads[0]["attributed_asset_ids"] == ["asset-001"]


async def test_sync_should_select_service_fee_ratio_by_rent_ledger_month(
    mock_db,
) -> None:
    service_fee_module = importlib.import_module(
        "src.services.contract.service_fee_ledger_service"
    )
    service = service_fee_module.service_fee_ledger_service

    agency_group = SimpleNamespace(
        contract_group_id="group-1",
        revenue_mode=RevenueMode.AGENCY,
    )
    old_entrusted_contract = SimpleNamespace(
        contract_id="contract-entrust-old",
        group_relation_type=GroupRelationType.ENTRUSTED,
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 6, 30),
        agency_detail=SimpleNamespace(service_fee_ratio=Decimal("0.2000")),
    )
    current_entrusted_contract = SimpleNamespace(
        contract_id="contract-entrust-current",
        group_relation_type=GroupRelationType.ENTRUSTED,
        effective_from=date(2026, 7, 1),
        effective_to=None,
        agency_detail=SimpleNamespace(service_fee_ratio=Decimal("0.3000")),
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
        attributed_project_id="project-001",
        attributed_owner_party_id="owner-001",
        attributed_operator_party_id="operator-001",
        attributed_asset_ids=["asset-001"],
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
            new=AsyncMock(
                return_value=[
                    old_entrusted_contract,
                    current_entrusted_contract,
                    direct_contract,
                ]
            ),
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

    assert result == {"created": 1, "updated": 0, "voided": 0, "source_mismatches": 0}
    assert created_payloads[0]["agency_agreement_contract_id"] == "contract-entrust-old"
    assert created_payloads[0]["service_fee_ratio"] == Decimal("0.2000")
    assert created_payloads[0]["calculation_base_amount"] == Decimal("500.00")
    assert created_payloads[0]["amount_due"] == Decimal("100.00")


async def test_sync_should_reject_source_month_crossing_service_fee_ratio_interval(
    mock_db,
) -> None:
    service_fee_module = importlib.import_module(
        "src.services.contract.service_fee_ledger_service"
    )
    service = service_fee_module.service_fee_ledger_service

    agency_group = SimpleNamespace(
        contract_group_id="group-1",
        revenue_mode=RevenueMode.AGENCY,
    )
    mid_month_entrusted_contract = SimpleNamespace(
        contract_id="contract-entrust-current",
        group_relation_type=GroupRelationType.ENTRUSTED,
        effective_from=date(2026, 7, 15),
        effective_to=None,
        agency_detail=SimpleNamespace(service_fee_ratio=Decimal("0.3000")),
    )
    direct_contract = SimpleNamespace(
        contract_id="contract-direct",
        group_relation_type=GroupRelationType.DIRECT_LEASE,
        agency_detail=None,
    )
    source_entry = SimpleNamespace(
        entry_id="entry-001",
        year_month="2026-07",
        amount_due=Decimal("2000.00"),
        paid_amount=Decimal("500.00"),
        payment_status="partial",
        currency_code="CNY",
        attributed_project_id="project-001",
        attributed_owner_party_id="owner-001",
        attributed_operator_party_id="operator-001",
        attributed_asset_ids=["asset-001"],
    )

    with (
        patch(
            "src.services.contract.service_fee_ledger_service.contract_group_crud.get",
            new=AsyncMock(return_value=agency_group),
        ),
        patch(
            "src.services.contract.service_fee_ledger_service.contract_crud.list_by_group",
            new=AsyncMock(return_value=[mid_month_entrusted_contract, direct_contract]),
        ),
        patch(
            "src.services.contract.service_fee_ledger_service.contract_group_crud.list_ledger_entries_by_contract",
            new=AsyncMock(return_value=[source_entry]),
        ),
    ):
        with pytest.raises(BusinessValidationError, match="split rent ledger period"):
            await service.sync_contract_group(mock_db, group_id="group-1")


async def test_sync_should_preserve_existing_service_fee_when_source_changes(
    mock_db,
) -> None:
    service_fee_module = importlib.import_module(
        "src.services.contract.service_fee_ledger_service"
    )
    service = service_fee_module.service_fee_ledger_service

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
        attributed_project_id="project-new",
        attributed_owner_party_id="owner-new",
        attributed_operator_party_id="operator-new",
        attributed_asset_ids=["asset-new"],
    )
    existing_entry = SimpleNamespace(
        agency_agreement_contract_id="contract-entrust",
        source_ledger_ids=["entry-old"],
        calculation_base_amount=Decimal("2000.00"),
        amount_due=Decimal("200.00"),
        paid_amount=Decimal("0.00"),
        payment_status="partial",
        currency_code="CNY",
        service_fee_ratio=Decimal("0.1000"),
        year_month="2026-05",
        agency_contract_id="contract-direct",
        attributed_project_id="project-old",
        attributed_owner_party_id="owner-new",
        attributed_operator_party_id="operator-old",
        attributed_asset_ids=["asset-old"],
        updated_at=None,
    )

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
            new=AsyncMock(return_value=[existing_entry]),
            create=True,
        ),
    ):
        result = await service.sync_contract_group(mock_db, group_id="group-1")

    assert result == {"created": 0, "updated": 0, "voided": 0, "source_mismatches": 1}
    assert existing_entry.source_ledger_ids == ["entry-old"]
    assert existing_entry.calculation_base_amount == Decimal("2000.00")
    assert existing_entry.amount_due == Decimal("200.00")
    assert existing_entry.attributed_project_id == "project-old"
    assert existing_entry.attributed_owner_party_id == "owner-new"
    assert existing_entry.attributed_operator_party_id == "operator-old"
    assert existing_entry.attributed_asset_ids == ["asset-old"]
    assert existing_entry.updated_at is None
