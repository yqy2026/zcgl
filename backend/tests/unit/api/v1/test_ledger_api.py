from datetime import date
from pathlib import Path
from types import SimpleNamespace
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


def test_list_payment_flows_for_target_delegates_scope_to_service(client) -> None:
    payload = [
        {
            "flow_id": "flow-001",
            "flow_type": "terminal_rent_receipt",
            "occurred_on": "2026-05-10",
            "amount": "1200.00",
            "registered_by": "user-001",
            "counterparty_id": "tenant-001",
            "voucher_attachment_ids": ["attachment-001"],
            "notes": None,
            "status": "active",
            "corrected_from_flow_id": None,
            "status_changed_by": None,
            "status_changed_at": None,
            "status_change_reason": None,
            "created_at": "2026-05-10T10:00:00",
            "updated_at": "2026-05-10T10:00:00",
            "allocations": [],
            "voucher_attachments": [
                {
                    "id": "attachment-001",
                    "file_name": "receipt.pdf",
                    "file_type": "pdf",
                    "file_size": 123,
                }
            ],
        }
    ]

    with patch(
        "src.api.v1.contracts.ledger.payment_flow_service.list_flows_by_target",
        new=AsyncMock(return_value=payload),
        create=True,
    ) as mock_list:
        response = client.get(
            "/api/v1/ledger/payment-flows",
            params={
                "target_type": "contract_ledger_entry",
                "target_id": "entry-001",
            },
        )

    assert response.status_code == 200
    assert response.json()[0]["voucher_attachments"][0]["file_name"] == ("receipt.pdf")
    mock_list.assert_awaited_once_with(
        ANY,
        target_type="contract_ledger_entry",
        target_id="entry-001",
        current_user_id="test_user_001",
        party_filter=None,
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


def test_void_payment_flow_delegates_reason_and_scope_to_service(client) -> None:
    payload = {
        "flow_id": "flow-001",
        "flow_type": "terminal_rent_receipt",
        "occurred_on": "2026-05-10",
        "amount": "1200.00",
        "registered_by": "user-001",
        "counterparty_id": "tenant-001",
        "voucher_attachment_ids": [],
        "notes": None,
        "status": "voided",
        "corrected_from_flow_id": None,
        "status_changed_by": "test_user_001",
        "status_changed_at": "2026-05-11T10:00:00",
        "status_change_reason": "重复登记",
        "created_at": "2026-05-10T10:00:00",
        "updated_at": "2026-05-11T10:00:00",
    }

    with patch(
        "src.api.v1.contracts.ledger.payment_flow_service.void_flow",
        new=AsyncMock(return_value=payload),
        create=True,
    ) as mock_void:
        response = client.post(
            "/api/v1/ledger/payment-flows/flow-001/void",
            json={"reason": "重复登记"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "voided"
    mock_void.assert_awaited_once_with(
        ANY,
        flow_id="flow-001",
        reason="重复登记",
        actor_id="test_user_001",
        current_user_id="test_user_001",
        party_filter=None,
    )


def test_correct_payment_flow_delegates_replacement_as_one_action(client) -> None:
    payload = {
        "flow_id": "flow-002",
        "flow_type": "terminal_rent_receipt",
        "occurred_on": "2026-05-11",
        "amount": "1000.00",
        "registered_by": "test_user_001",
        "counterparty_id": "tenant-001",
        "voucher_attachment_ids": [],
        "notes": "corrected",
        "status": "active",
        "corrected_from_flow_id": "flow-001",
        "status_changed_by": None,
        "status_changed_at": None,
        "status_change_reason": None,
        "created_at": "2026-05-11T10:00:00",
        "updated_at": "2026-05-11T10:00:00",
    }

    with patch(
        "src.api.v1.contracts.ledger.payment_flow_service.correct_flow",
        new=AsyncMock(return_value=payload),
        create=True,
    ) as mock_correct:
        response = client.post(
            "/api/v1/ledger/payment-flows/flow-001/correct",
            json={
                "reason": "金额录入错误",
                "replacement": {
                    "flow_type": "terminal_rent_receipt",
                    "occurred_on": "2026-05-11",
                    "amount": "1000.00",
                    "counterparty_id": "tenant-001",
                    "voucher_attachment_ids": [],
                    "notes": "corrected",
                },
                "allocations": [
                    {
                        "target_type": "contract_ledger_entry",
                        "target_id": "entry-001",
                        "year_month": "2026-05",
                        "amount": "1000.00",
                    }
                ],
            },
        )

    assert response.status_code == 200
    assert response.json()["corrected_from_flow_id"] == "flow-001"
    mock_correct.assert_awaited_once()
    assert mock_correct.await_args.kwargs["flow_id"] == "flow-001"
    assert mock_correct.await_args.kwargs["reason"] == "金额录入错误"
    assert mock_correct.await_args.kwargs["actor_id"] == "test_user_001"
    assert mock_correct.await_args.kwargs["replacement_data"]["amount"] == "1000.00"
    assert mock_correct.await_args.kwargs["allocations"][0]["target_id"] == (
        "entry-001"
    )


def test_upload_payment_flow_voucher_delegates_to_scoped_service(client) -> None:
    attachment = {
        "id": "attachment-001",
        "file_name": "receipt.pdf",
        "file_type": "pdf",
        "file_size": 3,
    }
    with patch(
        "src.api.v1.contracts.ledger.payment_voucher_service.upload_voucher",
        new=AsyncMock(return_value=attachment),
        create=True,
    ) as mock_upload:
        response = client.post(
            "/api/v1/ledger/payment-flows/flow-001/vouchers",
            files={"file": ("receipt.pdf", b"pdf", "application/pdf")},
        )

    assert response.status_code == 200
    assert response.json()["id"] == "attachment-001"
    assert mock_upload.await_args.kwargs["flow_id"] == "flow-001"
    assert mock_upload.await_args.kwargs["file"].filename == "receipt.pdf"
    assert mock_upload.await_args.kwargs["user_id"] == "test_user_001"


@pytest.mark.asyncio
async def test_upload_payment_flow_voucher_delegates_without_reading_file() -> None:
    """Owner scope belongs in the service and must run before upload reads."""
    from src.api.v1.contracts.ledger import upload_payment_flow_voucher

    attachment = {
        "id": "attachment-001",
        "file_name": "receipt.pdf",
        "file_type": "pdf",
        "file_size": 3,
    }
    file = SimpleNamespace(
        filename="receipt.pdf",
        content_type="application/pdf",
        read=AsyncMock(return_value=b"pdf"),
    )
    with (
        patch(
            "src.api.v1.contracts.ledger.build_party_filter_from_scope_context",
            return_value=None,
        ),
        patch(
            "src.api.v1.contracts.ledger.payment_voucher_service.upload_voucher",
            new=AsyncMock(return_value=attachment),
        ) as mock_upload,
    ):
        result = await upload_payment_flow_voucher(
            flow_id="flow-001",
            file=file,
            db=AsyncMock(),
            current_user=SimpleNamespace(id="user-001"),
            _scope_ctx=SimpleNamespace(),
            _authz=None,
        )

    assert result.id == "attachment-001"
    file.read.assert_not_awaited()
    assert mock_upload.await_args.kwargs["file"] is file


def test_download_payment_flow_voucher_returns_audited_file(client, tmp_path) -> None:
    file_path = tmp_path / "receipt.pdf"
    file_path.write_bytes(b"pdf")
    prepared = SimpleNamespace(
        path=file_path,
        attachment=SimpleNamespace(
            file_name="receipt.pdf",
            file_type="pdf",
        ),
    )
    with patch(
        "src.api.v1.contracts.ledger.payment_voucher_service.prepare_download",
        new=AsyncMock(return_value=prepared),
        create=True,
    ) as mock_download:
        response = client.get(
            "/api/v1/ledger/payment-flows/flow-001/vouchers/attachment-001/download"
        )

    assert response.status_code == 200
    assert response.content == b"pdf"
    assert mock_download.await_args.kwargs["attachment_id"] == "attachment-001"
    assert mock_download.await_args.kwargs["user_id"] == "test_user_001"


def test_list_payment_flow_voucher_audits_delegates_scope(client) -> None:
    audits = [
        {
            "log_id": "log-1",
            "user_id": "user-1",
            "flow_id": "flow-001",
            "attachment_id": "attachment-001",
            "file_name": "receipt.pdf",
            "downloaded_at": "2026-07-13T10:00:00",
            "result": "success",
        }
    ]
    with patch(
        "src.api.v1.contracts.ledger.payment_voucher_service.list_download_audits",
        new=AsyncMock(return_value=audits),
        create=True,
    ) as mock_list:
        response = client.get(
            "/api/v1/ledger/payment-flows/flow-001/voucher-download-audits"
        )

    assert response.status_code == 200
    assert response.json()[0]["result"] == "success"
    assert mock_list.await_args.kwargs["current_user_id"] == "test_user_001"


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
