import importlib
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.core.exception_handler import BusinessValidationError, ResourceNotFoundError
from src.models.contract_group import GroupRelationType, RevenueMode

pytestmark = pytest.mark.asyncio


async def test_list_contract_group_entries_should_return_agency_service_fees(
    mock_db,
) -> None:
    service_fee_module = importlib.import_module(
        "src.services.contract.service_fee_ledger_service"
    )
    service = service_fee_module.service_fee_ledger_service
    agency_group = SimpleNamespace(
        contract_group_id="group-1",
        revenue_mode=RevenueMode.AGENCY,
        owner_party_id="owner-1",
        operator_party_id="operator-1",
    )
    service_fee_entries = [
        SimpleNamespace(
            service_fee_entry_id="service-fee-1",
            source_ledger_ids=["rent-ledger-1"],
            year_month="2026-05",
        )
    ]

    with (
        patch(
            "src.services.contract.service_fee_ledger_service.contract_group_crud.get",
            new=AsyncMock(return_value=agency_group),
        ),
        patch(
            "src.services.contract.service_fee_ledger_service.contract_group_crud.list_service_fee_entries_by_group",
            new=AsyncMock(return_value=service_fee_entries),
        ) as mock_list,
    ):
        result = await service.list_contract_group_entries(mock_db, group_id="group-1")

    assert result == service_fee_entries
    mock_list.assert_awaited_once_with(mock_db, group_id="group-1")


async def test_list_contract_group_entries_should_allow_scoped_party(
    mock_db,
) -> None:
    service_fee_module = importlib.import_module(
        "src.services.contract.service_fee_ledger_service"
    )
    service = service_fee_module.service_fee_ledger_service
    agency_group = SimpleNamespace(
        contract_group_id="group-1",
        revenue_mode=RevenueMode.AGENCY,
        owner_party_id="owner-1",
        operator_party_id="operator-1",
    )
    service_fee_entries = [SimpleNamespace(service_fee_entry_id="service-fee-1")]

    with (
        patch(
            "src.services.contract.service_fee_ledger_service.contract_group_crud.get",
            new=AsyncMock(return_value=agency_group),
        ),
        patch(
            "src.services.contract.service_fee_ledger_service.contract_group_crud.list_service_fee_entries_by_group",
            new=AsyncMock(return_value=service_fee_entries),
        ) as mock_list,
    ):
        result = await service.list_contract_group_entries(
            mock_db,
            group_id="group-1",
            binding_type="manager",
            effective_party_ids=["operator-1"],
        )

    assert result == service_fee_entries
    mock_list.assert_awaited_once_with(mock_db, group_id="group-1")


async def test_list_contract_group_entries_should_hide_out_of_scope_group(
    mock_db,
) -> None:
    service_fee_module = importlib.import_module(
        "src.services.contract.service_fee_ledger_service"
    )
    service = service_fee_module.service_fee_ledger_service
    agency_group = SimpleNamespace(
        contract_group_id="group-1",
        revenue_mode=RevenueMode.AGENCY,
        owner_party_id="owner-1",
        operator_party_id="operator-1",
    )

    with (
        patch(
            "src.services.contract.service_fee_ledger_service.contract_group_crud.get",
            new=AsyncMock(return_value=agency_group),
        ),
        patch(
            "src.services.contract.service_fee_ledger_service.contract_group_crud.list_service_fee_entries_by_group",
            new=AsyncMock(return_value=[]),
        ) as mock_list,
    ):
        with pytest.raises(ResourceNotFoundError):
            await service.list_contract_group_entries(
                mock_db,
                group_id="group-1",
                binding_type="owner",
                effective_party_ids=["other-owner"],
            )

    mock_list.assert_not_awaited()


async def test_list_contract_group_entries_should_hide_empty_all_scope(
    mock_db,
) -> None:
    service_fee_module = importlib.import_module(
        "src.services.contract.service_fee_ledger_service"
    )
    service = service_fee_module.service_fee_ledger_service
    agency_group = SimpleNamespace(
        contract_group_id="group-1",
        revenue_mode=RevenueMode.AGENCY,
        owner_party_id="owner-1",
        operator_party_id="operator-1",
    )

    with (
        patch(
            "src.services.contract.service_fee_ledger_service.contract_group_crud.get",
            new=AsyncMock(return_value=agency_group),
        ),
        patch(
            "src.services.contract.service_fee_ledger_service.contract_group_crud.list_service_fee_entries_by_group",
            new=AsyncMock(return_value=[]),
        ) as mock_list,
    ):
        with pytest.raises(ResourceNotFoundError):
            await service.list_contract_group_entries(
                mock_db,
                group_id="group-1",
                binding_type="all",
                effective_party_ids=[],
            )

    mock_list.assert_not_awaited()


async def test_list_contract_group_entries_should_skip_non_agency_group(
    mock_db,
) -> None:
    service_fee_module = importlib.import_module(
        "src.services.contract.service_fee_ledger_service"
    )
    service = service_fee_module.service_fee_ledger_service
    lease_group = SimpleNamespace(
        contract_group_id="group-1",
        revenue_mode=RevenueMode.LEASE,
    )

    with (
        patch(
            "src.services.contract.service_fee_ledger_service.contract_group_crud.get",
            new=AsyncMock(return_value=lease_group),
        ),
        patch(
            "src.services.contract.service_fee_ledger_service.contract_group_crud.list_service_fee_entries_by_group",
            new=AsyncMock(return_value=[]),
        ) as mock_list,
    ):
        result = await service.list_contract_group_entries(mock_db, group_id="group-1")

    assert result == []
    mock_list.assert_not_awaited()


async def test_list_contract_group_entries_should_raise_when_group_missing(
    mock_db,
) -> None:
    service_fee_module = importlib.import_module(
        "src.services.contract.service_fee_ledger_service"
    )
    service = service_fee_module.service_fee_ledger_service

    with patch(
        "src.services.contract.service_fee_ledger_service.contract_group_crud.get",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(ResourceNotFoundError):
            await service.list_contract_group_entries(mock_db, group_id="missing")


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


def _source_entry(**overrides) -> SimpleNamespace:  # noqa: ANN003
    data = {
        "entry_id": "entry-001",
        "year_month": "2026-05",
        "amount_due": Decimal("500.00"),
        "due_date": date(2026, 5, 1),
        "paid_amount": Decimal("500.00"),
        "payment_status": "partial",
        "currency_code": "CNY",
        "attributed_project_id": "project-001",
        "attributed_owner_party_id": "owner-001",
        "attributed_operator_party_id": "operator-001",
        "attributed_asset_ids": ["asset-001"],
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _rent_term(**overrides) -> SimpleNamespace:  # noqa: ANN003
    data = {
        "start_date": date(2026, 5, 1),
        "end_date": date(2026, 5, 31),
        "monthly_rent": Decimal("500.00"),
        "total_monthly_amount": Decimal("500.00"),
        "sort_order": 1,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _existing_service_fee_entry(**overrides) -> SimpleNamespace:  # noqa: ANN003
    data = {
        "service_fee_entry_id": "fee-001",
        "contract_group_id": "group-1",
        "agency_contract_id": "contract-direct",
        "agency_agreement_contract_id": "contract-entrust",
        "source_ledger_ids": ["entry-001"],
        "calculation_base_amount": Decimal("500.00"),
        "amount_due": Decimal("50.00"),
        "paid_amount": Decimal("0.00"),
        "payment_status": "unpaid",
        "currency_code": "CNY",
        "service_fee_ratio": Decimal("0.1000"),
        "year_month": "2026-05",
        "attributed_project_id": "project-001",
        "attributed_owner_party_id": "owner-001",
        "attributed_operator_party_id": "operator-001",
        "attributed_asset_ids": ["asset-001"],
    }
    data.update(overrides)
    return SimpleNamespace(**data)


async def _find_service_fee_source_mismatches(
    mock_db,
    *,
    source_entry: SimpleNamespace,
    existing_entries: list[SimpleNamespace],
    rent_terms: list[SimpleNamespace] | None = None,
):
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
        lease_detail=SimpleNamespace(payment_cycle="monthly"),
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
            "src.services.contract.service_fee_ledger_service.contract_group_crud.list_rent_terms_by_contract",
            new=AsyncMock(return_value=rent_terms or [_rent_term()]),
        ),
        patch(
            "src.services.contract.service_fee_ledger_service.contract_group_crud.list_service_fee_entries_by_group",
            new=AsyncMock(return_value=existing_entries),
            create=True,
        ),
    ):
        return await service.find_source_mismatches(mock_db, group_id="group-1")


async def test_find_source_mismatches_should_report_preserved_service_fee_source_change(
    mock_db,
) -> None:
    mismatches = await _find_service_fee_source_mismatches(
        mock_db,
        source_entry=_source_entry(
            entry_id="entry-new",
            attributed_project_id="project-new",
            attributed_operator_party_id="operator-new",
            attributed_asset_ids=["asset-new"],
        ),
        existing_entries=[
            _existing_service_fee_entry(
                source_ledger_ids=["entry-old"],
                calculation_base_amount=Decimal("2000.00"),
                amount_due=Decimal("200.00"),
                attributed_project_id="project-old",
                attributed_operator_party_id="operator-old",
                attributed_asset_ids=["asset-old"],
            )
        ],
    )

    assert [
        (item.service_fee_entry_id, item.year_month, item.reason) for item in mismatches
    ] == [("fee-001", "2026-05", "service_fee_source_changed")]


async def test_find_source_mismatches_should_report_stale_source_rent_entry(
    mock_db,
) -> None:
    mismatches = await _find_service_fee_source_mismatches(
        mock_db,
        source_entry=_source_entry(amount_due=Decimal("1000.00")),
        existing_entries=[_existing_service_fee_entry()],
        rent_terms=[
            _rent_term(
                monthly_rent=Decimal("1200.00"),
                total_monthly_amount=Decimal("1200.00"),
            )
        ],
    )

    assert [
        (item.service_fee_entry_id, item.year_month, item.reason) for item in mismatches
    ] == [("fee-001", "2026-05", "service_fee_source_ledger_stale_after_correction")]


async def test_find_source_mismatches_should_ignore_service_fee_payment_status_change(
    mock_db,
) -> None:
    mismatches = await _find_service_fee_source_mismatches(
        mock_db,
        source_entry=_source_entry(),
        existing_entries=[_existing_service_fee_entry(payment_status="paid")],
    )

    assert mismatches == []


async def test_find_source_mismatches_should_ignore_voided_service_fee_entries(
    mock_db,
) -> None:
    mismatches = await _find_service_fee_source_mismatches(
        mock_db,
        source_entry=_source_entry(
            entry_id="entry-new",
            attributed_project_id="project-new",
            attributed_operator_party_id="operator-new",
            attributed_asset_ids=["asset-new"],
        ),
        existing_entries=[
            _existing_service_fee_entry(
                service_fee_entry_id="fee-voided",
                source_ledger_ids=["entry-old"],
                calculation_base_amount=Decimal("2000.00"),
                amount_due=Decimal("200.00"),
                payment_status="voided",
                attributed_project_id="project-old",
                attributed_operator_party_id="operator-old",
                attributed_asset_ids=["asset-old"],
            )
        ],
    )

    assert mismatches == []
