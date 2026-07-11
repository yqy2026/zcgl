from datetime import date
from pathlib import Path
from unittest.mock import ANY, AsyncMock, patch

import pytest

pytestmark = pytest.mark.api


def _module_source() -> str:
    from src.api.v1.contracts import ledger as mod

    return Path(mod.__file__).read_text(encoding="utf-8")


def test_ledger_module_should_not_import_crud_directly() -> None:
    source = _module_source()
    assert "contract_group_crud" not in source
    assert "contract_crud" not in source


def test_ledger_module_should_use_require_authz() -> None:
    source = _module_source()
    assert "require_authz" in source
    assert 'resource_id="{contract_id}"' in source
    assert "resolve_service_fee_group_resource_id" in source
    assert 'resource_type="contract_group"' in source


def test_get_ledger_entries_delegates_to_service(client) -> None:
    payload = {
        "items": [
            {
                "entry_id": "entry-001",
                "contract_id": "contract-001",
                "year_month": "2026-01",
                "due_date": "2026-01-01",
                "amount_due": "1000.00",
                "ledger_views": ["terminal_collection"],
                "currency_code": "CNY",
                "is_tax_included": True,
                "tax_rate": "0.09",
                "payment_status": "unpaid",
                "paid_amount": "0",
                "notes": None,
                "created_at": None,
                "updated_at": None,
            }
        ],
        "total": 1,
        "offset": 0,
        "limit": 20,
    }

    with patch(
        "src.api.v1.contracts.ledger.ledger_service_v2.query_ledger_entries",
        new=AsyncMock(return_value=payload),
    ) as mock_query:
        response = client.get(
            "/api/v1/ledger/entries",
            params={"contract_id": "contract-001", "year_month_start": "2026-01"},
        )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    mock_query.assert_awaited_once_with(
        ANY,
        ledger_view=None,
        project_id=None,
        asset_id=None,
        party_id=None,
        contract_id="contract-001",
        year_month_start="2026-01",
        year_month_end=None,
        flow_occurred_on_start=None,
        flow_occurred_on_end=None,
        payment_status=None,
        include_voided=False,
        offset=0,
        limit=20,
        current_user_id="test_user_001",
        party_filter=None,
    )


def test_get_ledger_entries_delegates_operations_filters(client) -> None:
    payload = {
        "items": [],
        "total": 0,
        "offset": 0,
        "limit": 20,
    }

    with patch(
        "src.api.v1.contracts.ledger.ledger_service_v2.query_ledger_entries",
        new=AsyncMock(return_value=payload),
    ) as mock_query:
        response = client.get(
            "/api/v1/ledger/entries",
            params={
                "ledger_view": "terminal_collection",
                "project_id": "project-001",
                "flow_occurred_on_start": "2026-05-01",
                "flow_occurred_on_end": "2026-05-31",
            },
        )

    assert response.status_code == 200
    mock_query.assert_awaited_once_with(
        ANY,
        ledger_view="terminal_collection",
        project_id="project-001",
        asset_id=None,
        party_id=None,
        contract_id=None,
        year_month_start=None,
        year_month_end=None,
        flow_occurred_on_start=ANY,
        flow_occurred_on_end=ANY,
        payment_status=None,
        include_voided=False,
        offset=0,
        limit=20,
        current_user_id="test_user_001",
        party_filter=None,
    )


def test_get_ledger_entries_requires_at_least_one_core_filter(client) -> None:
    response = client.get("/api/v1/ledger/entries")

    assert response.status_code == 422


def test_get_ledger_entries_rejects_inverted_flow_date_range(client) -> None:
    response = client.get(
        "/api/v1/ledger/entries",
        params={
            "project_id": "project-001",
            "flow_occurred_on_start": "2026-05-31",
            "flow_occurred_on_end": "2026-05-01",
        },
    )

    assert response.status_code == 422


def test_get_ledger_entries_rejects_manual_overdue_status(client) -> None:
    response = client.get(
        "/api/v1/ledger/entries",
        params={
            "contract_id": "contract-001",
            "year_month_start": "2026-01",
            "payment_status": "overdue",
        },
    )

    assert response.status_code == 422


def test_recalculate_ledger_delegates_to_service(client) -> None:
    payload = {
        "created": 1,
        "updated": 2,
        "voided": 0,
        "skipped_entries": [],
    }

    with patch(
        "src.api.v1.contracts.ledger.ledger_service_v2.recalculate_ledger",
        new=AsyncMock(return_value=payload),
    ) as mock_recalculate:
        response = client.post("/api/v1/contracts/contract-001/ledger/recalculate")

    assert response.status_code == 200
    assert response.json() == payload
    mock_recalculate.assert_awaited_once_with(ANY, contract_id="contract-001")


def test_export_ledger_entries_delegates_to_service(client) -> None:
    payload = AsyncMock()
    payload.filename = "ledger_entries_20260324.csv"
    payload.media_type = "text/csv; charset=utf-8"
    payload.content = b"entry_id,contract_id\r\nentry-001,contract-001\r\n"

    with patch(
        "src.api.v1.contracts.ledger.ledger_export_service.export_ledger_entries",
        new=AsyncMock(return_value=payload),
        create=True,
    ) as mock_export:
        response = client.get(
            "/api/v1/ledger/entries/export",
            params={"contract_id": "contract-001", "year_month_start": "2026-05"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert (
        "attachment; filename=ledger_entries_20260324.csv"
        in response.headers["content-disposition"]
    )
    assert response.text == "entry_id,contract_id\r\nentry-001,contract-001\r\n"
    mock_export.assert_awaited_once_with(
        ANY,
        params=ANY,
        current_user_id="test_user_001",
        party_filter=None,
    )


def test_run_ledger_compensation_delegates_to_service(client) -> None:
    payload = {
        "contracts_scanned": 2,
        "contracts_repaired": 1,
        "rent_entries_created": 1,
        "rent_entries_voided": 0,
        "failures": [],
        "timestamp": "2026-03-24T11:30:00",
    }

    with patch(
        "src.api.v1.contracts.ledger.ledger_compensation_service.run",
        new=AsyncMock(return_value=payload),
        create=True,
    ) as mock_run:
        response = client.post("/api/v1/ledger/compensation/run")

    assert response.status_code == 200
    assert response.json() == payload
    mock_run.assert_awaited_once_with(ANY)


def test_direct_paid_amount_update_endpoint_is_retired(client) -> None:
    response = client.patch(
        "/api/v1/contracts/contract-001/ledger/batch-update-status",
        json={
            "entry_ids": ["entry-001"],
            "paid_amount": "100.00",
        },
    )

    assert response.status_code == 404


def test_create_payment_flow_delegates_to_service(client) -> None:
    payload = {
        "flow_id": "flow-001",
        "flow_type": "terminal_rent_receipt",
        "occurred_on": "2026-05-10",
        "amount": "1200.00",
        "registered_by": "user-001",
        "counterparty_id": "tenant-001",
        "voucher_attachment_ids": ["attachment-001"],
        "notes": "offline receipt",
        "status": "active",
        "created_at": "2026-05-10T10:00:00",
        "updated_at": "2026-05-10T10:00:00",
    }

    with patch(
        "src.api.v1.contracts.ledger.payment_flow_service.create_flow",
        new=AsyncMock(return_value=payload),
        create=True,
    ) as mock_create:
        response = client.post(
            "/api/v1/ledger/payment-flows",
            json={
                "flow_type": "terminal_rent_receipt",
                "occurred_on": "2026-05-10",
                "amount": "1200.00",
                "registered_by": "forged-user",
                "counterparty_id": "tenant-001",
                "voucher_attachment_ids": ["attachment-001"],
                "notes": "offline receipt",
            },
        )

    assert response.status_code == 200
    assert response.json()["flow_id"] == "flow-001"
    mock_create.assert_awaited_once_with(
        ANY,
        data={
            "flow_type": "terminal_rent_receipt",
            "occurred_on": ANY,
            "amount": ANY,
            "counterparty_id": "tenant-001",
            "voucher_attachment_ids": ["attachment-001"],
            "notes": "offline receipt",
        },
        registered_by="test_user_001",
    )


def test_save_payment_flow_allocations_delegates_to_service(client) -> None:
    payload = [
        {
            "allocation_id": "allocation-001",
            "flow_id": "flow-001",
            "target_type": "contract_ledger_entry",
            "target_id": "entry-001",
            "year_month": "2026-05",
            "amount": "1200.00",
            "created_at": "2026-05-10T10:00:00",
            "updated_at": "2026-05-10T10:00:00",
        }
    ]

    with patch(
        "src.api.v1.contracts.ledger.payment_flow_service.save_allocations",
        new=AsyncMock(return_value=payload),
        create=True,
    ) as mock_save:
        response = client.post(
            "/api/v1/ledger/payment-flows/flow-001/allocations",
            json={
                "allocations": [
                    {
                        "target_type": "contract_ledger_entry",
                        "target_id": "entry-001",
                        "year_month": "2026-05",
                        "amount": "1200.00",
                    }
                ]
            },
        )

    assert response.status_code == 200
    assert response.json()[0]["allocation_id"] == "allocation-001"
    mock_save.assert_awaited_once_with(
        ANY,
        flow_id="flow-001",
        allocations=[
            {
                "target_type": "contract_ledger_entry",
                "target_id": "entry-001",
                "year_month": "2026-05",
                "amount": ANY,
            }
        ],
        current_user_id="test_user_001",
        party_filter=None,
    )


def test_update_ledger_entry_follow_up_delegates_to_service(client) -> None:
    payload = {
        "entry_id": "entry-001",
        "contract_id": "contract-001",
        "year_month": "2026-05",
        "due_date": "2026-05-31",
        "amount_due": "1000.00",
        "ledger_views": ["terminal_collection"],
        "flow_occurred_on_dates": [],
        "currency_code": "CNY",
        "is_tax_included": True,
        "tax_rate": "0.09",
        "payment_status": "unpaid",
        "paid_amount": "0",
        "follow_up_status": "contacted",
        "next_follow_up_date": "2026-05-20",
        "follow_up_note": "已联系租户",
        "notes": None,
        "created_at": None,
        "updated_at": None,
    }

    with patch(
        "src.api.v1.contracts.ledger.ledger_service_v2.update_follow_up",
        new=AsyncMock(return_value=payload),
    ) as mock_update:
        response = client.patch(
            "/api/v1/ledger/entries/entry-001/follow-up",
            json={
                "follow_up_status": "contacted",
                "next_follow_up_date": "2026-05-20",
                "follow_up_note": "已联系租户",
            },
        )

    assert response.status_code == 200
    assert response.json()["follow_up_status"] == "contacted"
    mock_update.assert_awaited_once_with(
        ANY,
        entry_id="entry-001",
        follow_up_status="contacted",
        next_follow_up_date=date(2026, 5, 20),
        follow_up_note="已联系租户",
        current_user_id="test_user_001",
        party_filter=None,
    )


def test_generate_service_fees_delegates_to_service(client) -> None:
    payload = {"created": 2, "updated": 0, "voided": 0, "source_mismatches": 1}

    with patch(
        "src.api.v1.contracts.ledger.service_fee_ledger_service.sync_contract_group",
        new=AsyncMock(return_value=payload),
        create=True,
    ) as mock_generate:
        response = client.post(
            "/api/v1/ledger/service-fees/generate",
            json={"contract_group_id": "group-001"},
        )

    assert response.status_code == 200
    assert response.json() == payload
    mock_generate.assert_awaited_once_with(
        ANY,
        group_id="group-001",
        current_user_id="test_user_001",
        party_filter=None,
    )


def test_list_service_fees_delegates_to_service(client) -> None:
    payload = [
        {
            "service_fee_entry_id": "service-fee-001",
            "contract_group_id": "group-001",
            "agency_contract_id": "contract-direct-001",
            "agency_agreement_contract_id": "contract-entrust-001",
            "source_ledger_ids": ["rent-ledger-001"],
            "year_month": "2026-05",
            "amount_due": "50.00",
            "paid_amount": "20.00",
            "payment_status": "partial",
            "currency_code": "CNY",
            "service_fee_ratio": "0.1000",
            "calculation_base_amount": "500.00",
            "attributed_project_id": "project-001",
            "attributed_owner_party_id": "owner-001",
            "attributed_operator_party_id": "operator-001",
            "attributed_asset_ids": ["asset-001"],
            "created_at": None,
            "updated_at": None,
        }
    ]

    with patch(
        "src.api.v1.contracts.ledger.service_fee_ledger_service.list_entries",
        new=AsyncMock(return_value=payload),
        create=True,
    ) as mock_list:
        response = client.get(
            "/api/v1/ledger/service-fees",
            params={"contract_group_id": "group-001"},
        )

    assert response.status_code == 200
    assert response.json()[0]["service_fee_entry_id"] == "service-fee-001"
    assert response.json()[0]["source_ledger_ids"] == ["rent-ledger-001"]
    mock_list.assert_awaited_once_with(
        ANY,
        group_id="group-001",
        project_id=None,
        current_user_id="test_user_001",
        party_filter=None,
    )


def test_list_service_fees_supports_project_filter(client) -> None:
    with patch(
        "src.api.v1.contracts.ledger.service_fee_ledger_service.list_entries",
        new=AsyncMock(return_value=[]),
        create=True,
    ) as mock_list:
        response = client.get(
            "/api/v1/ledger/service-fees",
            params={"project_id": "project-001"},
        )

    assert response.status_code == 200
    mock_list.assert_awaited_once_with(
        ANY,
        group_id=None,
        project_id="project-001",
        current_user_id="test_user_001",
        party_filter=None,
    )


def test_reconcile_service_fee_source_delegates_to_service(client) -> None:
    payload = {
        "service_fee_entry_id": "service-fee-001",
        "contract_group_id": "group-001",
        "agency_contract_id": "contract-direct-001",
        "agency_agreement_contract_id": "contract-entrust-001",
        "source_ledger_ids": ["rent-ledger-current"],
        "year_month": "2026-05",
        "amount_due": "50.00",
        "paid_amount": "20.00",
        "payment_status": "partial",
        "currency_code": "CNY",
        "service_fee_ratio": "0.1000",
        "calculation_base_amount": "500.00",
        "attributed_project_id": "project-001",
        "attributed_owner_party_id": "owner-001",
        "attributed_operator_party_id": "operator-001",
        "attributed_asset_ids": ["asset-001"],
        "created_at": None,
        "updated_at": None,
    }

    with patch(
        "src.api.v1.contracts.ledger.service_fee_ledger_service.reconcile_source",
        new=AsyncMock(return_value=payload),
        create=True,
    ) as mock_reconcile:
        response = client.post(
            "/api/v1/ledger/service-fees/service-fee-001/reconcile",
            json={"reason": "确认采用当前租金台账来源"},
        )

    assert response.status_code == 200
    assert response.json()["source_ledger_ids"] == ["rent-ledger-current"]
    mock_reconcile.assert_awaited_once_with(
        ANY,
        entry_id="service-fee-001",
        reason="确认采用当前租金台账来源",
        current_user_id="test_user_001",
        party_filter=None,
    )
