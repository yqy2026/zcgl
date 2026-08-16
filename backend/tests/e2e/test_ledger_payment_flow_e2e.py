"""
End-to-end ledger payment flow tests (REQ-RNT-005 / REQ-RNT-006).

Covers the money path across the public API: payment flow registration,
allocation to rent ledger entries (with derived payment status), voucher
upload/download/audit, correction and voiding with ledger recalculation,
service fee generation for agency groups, and recalculate protection of
paid entries.
"""

from decimal import Decimal
from uuid import uuid4

import fitz
import pytest
from fastapi.testclient import TestClient

from src.models.contract_group import ContractRentTerm
from tests.e2e.factories import create_approved_legal_party

pytestmark = pytest.mark.e2e


def _minimal_pdf_bytes() -> bytes:
    doc = fitz.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


def _create_project(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    *,
    suffix: str,
    manager_party_id: str,
) -> str:
    response = authenticated_client.post(
        "/api/v1/projects",
        json={
            "project_name": f"E2E台账项目-{suffix}",
            "status": "planning",
            "manager_party_id": manager_party_id,
            "data_status": "正常",
        },
        headers=csrf_headers,
    )
    assert response.status_code == 200, response.text
    project_id = response.json().get("id")
    assert isinstance(project_id, str) and project_id != ""
    return project_id


def _create_contract_group(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    *,
    project_id: str,
    operator_party_id: str,
    owner_party_id: str,
    revenue_mode: str,
    suffix: str,
) -> str:
    response = authenticated_client.post(
        "/api/v1/contract-groups",
        json={
            "project_id": project_id,
            "revenue_mode": revenue_mode,
            "operator_party_id": operator_party_id,
            "owner_party_id": owner_party_id,
            "effective_from": "2026-01-01",
            "settlement_rule": {
                "version": "v1",
                "cycle": "月付",
                "settlement_mode": "固定",
                "amount_rule": {"base": 5000},
                "payment_rule": {"due_day": 10},
            },
        },
        headers=csrf_headers,
    )
    assert response.status_code == 201, response.text
    group_id = response.json().get("contract_group_id")
    assert isinstance(group_id, str) and group_id != ""
    return group_id


def _add_contract(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    *,
    group_id: str,
    lessor_party_id: str,
    lessee_party_id: str,
    suffix: str,
    group_relation_type: str = "下游",
    with_rent_terms: bool = True,
    agency_detail: dict[str, object] | None = None,
) -> str:
    payload: dict[str, object] = {
        "contract_group_id": group_id,
        "contract_number": f"E2E-HT-{suffix}",
        "contract_direction": "出租",
        "group_relation_type": group_relation_type,
        "lessor_party_id": lessor_party_id,
        "lessee_party_id": lessee_party_id,
        "sign_date": "2026-01-01",
        "effective_from": "2026-01-01",
        "effective_to": "2026-12-31",
        "payment_cycle": "月付",
    }
    if agency_detail is not None:
        payload["agency_detail"] = agency_detail
    if with_rent_terms:
        payload["lease_detail"] = {
            "total_deposit": 10000,
            "rent_amount": 5000,
            "monthly_rent_base": 5000,
            "payment_cycle": "月付",
            "tenant_name": f"E2E租户-{suffix}",
        }
        payload["rent_terms"] = [
            {
                "sort_order": 1,
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "monthly_rent": 5000,
            }
        ]
    response = authenticated_client.post(
        f"/api/v1/contract-groups/{group_id}/contracts",
        json=payload,
        headers=csrf_headers,
    )
    assert response.status_code == 201, response.text
    contract_id = response.json().get("contract_id")
    assert isinstance(contract_id, str) and contract_id != ""
    return contract_id


def _ledger_entry(
    authenticated_client: TestClient, contract_id: str, year_month: str
) -> dict[str, object]:
    response = authenticated_client.get(f"/api/v1/contracts/{contract_id}/ledger")
    assert response.status_code == 200, response.text
    for item in response.json().get("items", []):
        if item.get("year_month") == year_month:
            return item
    raise AssertionError(f"ledger entry {year_month} not found for {contract_id}")


def _register_flow(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    *,
    amount: str,
    counterparty_id: str,
    flow_type: str = "terminal_rent_receipt",
) -> dict[str, object]:
    response = authenticated_client.post(
        "/api/v1/ledger/payment-flows",
        json={
            "flow_type": flow_type,
            "occurred_on": "2026-02-10",
            "amount": amount,
            "counterparty_id": counterparty_id,
            "voucher_attachment_ids": [],
            "notes": "e2e 收付流水",
        },
        headers=csrf_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _allocate(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    *,
    flow_id: str,
    target_id: str,
    amount: str,
    year_month: str = "2026-01",
    target_type: str = "contract_ledger_entry",
) -> dict[str, object]:
    response = authenticated_client.post(
        f"/api/v1/ledger/payment-flows/{flow_id}/allocations",
        json={
            "allocations": [
                {
                    "target_type": target_type,
                    "target_id": target_id,
                    "year_month": year_month,
                    "amount": amount,
                }
            ]
        },
        headers=csrf_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _setup_terminal_collection_contract(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
    *,
    suffix: str,
    revenue_mode: str = "lease",
) -> tuple[str, str, str]:
    """Create parties + project + group + downstream lease contract (terminal view)."""
    operator = create_approved_legal_party(
        db_session, suffix=suffix, name=f"台账运营方-{suffix}"
    )
    owner = create_approved_legal_party(
        db_session, suffix=suffix, name=f"台账产权方-{suffix}"
    )
    lessor = create_approved_legal_party(
        db_session, suffix=suffix, name=f"台账出租方-{suffix}"
    )
    lessee = create_approved_legal_party(
        db_session, suffix=suffix, name=f"台账承租方-{suffix}"
    )
    project_id = _create_project(
        authenticated_client,
        csrf_headers,
        suffix=suffix,
        manager_party_id=operator.id,
    )
    group_id = _create_contract_group(
        authenticated_client,
        csrf_headers,
        project_id=project_id,
        operator_party_id=operator.id,
        owner_party_id=owner.id,
        revenue_mode=revenue_mode,
        suffix=suffix,
    )
    contract_id = _add_contract(
        authenticated_client,
        csrf_headers,
        group_id=group_id,
        lessor_party_id=lessor.id,
        lessee_party_id=lessee.id,
        suffix=suffix,
    )
    return group_id, contract_id, lessee.id


def test_payment_flow_full_lifecycle_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Register → allocate (replace) → voucher → correct → void round-trip."""
    suffix = uuid4().hex[:8]
    _, contract_id, lessee_party_id = _setup_terminal_collection_contract(
        authenticated_client, csrf_headers, db_session, suffix=suffix
    )

    entry = _ledger_entry(authenticated_client, contract_id, "2026-01")
    entry_id = entry["entry_id"]
    assert entry["payment_status"] == "unpaid"
    assert Decimal(str(entry["paid_amount"])) == Decimal("0")

    # A partial receipt: the flow must be allocated in full, so a smaller
    # flow leaves the 5000 entry partially paid.
    flow = _register_flow(
        authenticated_client,
        csrf_headers,
        amount="3000.00",
        counterparty_id=lessee_party_id,
    )
    flow_id = flow["flow_id"]
    assert flow["status"] == "active"
    assert flow["registered_by"] == getattr(authenticated_client, "_user_id")

    _allocate(
        authenticated_client,
        csrf_headers,
        flow_id=flow_id,
        target_id=entry_id,
        amount="3000.00",
    )
    entry = _ledger_entry(authenticated_client, contract_id, "2026-01")
    assert entry["payment_status"] == "partial"
    assert Decimal(str(entry["paid_amount"])) == Decimal("3000")

    # Re-submitting allocations replaces instead of accumulating.
    _allocate(
        authenticated_client,
        csrf_headers,
        flow_id=flow_id,
        target_id=entry_id,
        amount="3000.00",
    )
    entry = _ledger_entry(authenticated_client, contract_id, "2026-01")
    assert entry["payment_status"] == "partial"
    assert Decimal(str(entry["paid_amount"])) == Decimal("3000")

    # The flow is queryable by ledger target with its allocations.
    flows_response = authenticated_client.get(
        "/api/v1/ledger/payment-flows",
        params={"target_type": "contract_ledger_entry", "target_id": entry_id},
    )
    assert flows_response.status_code == 200, flows_response.text
    flows = flows_response.json()
    matching = [f for f in flows if f.get("flow_id") == flow_id]
    assert len(matching) == 1
    assert len(matching[0].get("allocations", [])) == 1
    assert matching[0].get("voucher_attachments", []) == []

    # Upload a real PDF voucher, then download it and check the audit trail.
    upload = authenticated_client.post(
        f"/api/v1/ledger/payment-flows/{flow_id}/vouchers",
        files={"file": ("receipt-e2e.pdf", _minimal_pdf_bytes(), "application/pdf")},
        headers=csrf_headers,
    )
    assert upload.status_code == 200, upload.text
    voucher = upload.json()
    attachment_id = voucher["id"]
    assert voucher["file_name"] == "receipt-e2e.pdf"

    download = authenticated_client.get(
        f"/api/v1/ledger/payment-flows/{flow_id}/vouchers/{attachment_id}/download"
    )
    assert download.status_code == 200, download.text
    assert download.content.startswith(b"%PDF-")

    audits = authenticated_client.get(
        f"/api/v1/ledger/payment-flows/{flow_id}/voucher-download-audits"
    )
    assert audits.status_code == 200, audits.text
    assert any(
        log.get("attachment_id") == attachment_id and log.get("result") == "success"
        for log in audits.json()
    )

    # Correct the flow to the full amount: the entry becomes fully paid.
    correction = authenticated_client.post(
        f"/api/v1/ledger/payment-flows/{flow_id}/correct",
        json={
            "reason": "金额录入错误",
            "replacement": {
                "flow_type": "terminal_rent_receipt",
                "occurred_on": "2026-02-11",
                "amount": "5000.00",
                "counterparty_id": lessee_party_id,
                "voucher_attachment_ids": [],
                "notes": "e2e 更正后流水",
            },
            "allocations": [
                {
                    "target_type": "contract_ledger_entry",
                    "target_id": entry_id,
                    "year_month": "2026-01",
                    "amount": "5000.00",
                }
            ],
        },
        headers=csrf_headers,
    )
    assert correction.status_code == 200, correction.text
    corrected_flow = correction.json()
    assert corrected_flow["corrected_from_flow_id"] == flow_id
    assert corrected_flow["status"] == "active"

    entry = _ledger_entry(authenticated_client, contract_id, "2026-01")
    assert entry["payment_status"] == "paid"
    assert Decimal(str(entry["paid_amount"])) == Decimal("5000")

    # The corrected original is terminal: no second correction lifecycle.
    revoid = authenticated_client.post(
        f"/api/v1/ledger/payment-flows/{flow_id}/void",
        json={"reason": "对已更正流水作废应被拒绝"},
        headers=csrf_headers,
    )
    assert revoid.status_code == 422
    assert revoid.json().get("error", {}).get("code") == "VALIDATION_ERROR"

    # Void the replacement: the entry returns to unpaid.
    void = authenticated_client.post(
        f"/api/v1/ledger/payment-flows/{corrected_flow['flow_id']}/void",
        json={"reason": "e2e 冲销"},
        headers=csrf_headers,
    )
    assert void.status_code == 200, void.text
    assert void.json()["status"] == "voided"
    assert void.json()["status_change_reason"] == "e2e 冲销"

    entry = _ledger_entry(authenticated_client, contract_id, "2026-01")
    assert entry["payment_status"] == "unpaid"
    assert Decimal(str(entry["paid_amount"])) == Decimal("0")


def test_payment_flow_validation_guards_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Amount, allocation and view guards reject invalid money operations."""
    suffix = uuid4().hex[:8]
    _, contract_id, lessee_party_id = _setup_terminal_collection_contract(
        authenticated_client, csrf_headers, db_session, suffix=suffix
    )
    entry = _ledger_entry(authenticated_client, contract_id, "2026-01")
    entry_id = entry["entry_id"]

    # Non-positive amounts are rejected by schema validation.
    for bad_amount in ("0", "-5"):
        response = authenticated_client.post(
            "/api/v1/ledger/payment-flows",
            json={
                "flow_type": "terminal_rent_receipt",
                "occurred_on": "2026-02-10",
                "amount": bad_amount,
                "counterparty_id": lessee_party_id,
            },
            headers=csrf_headers,
        )
        assert response.status_code == 422, response.text

    # Missing CSRF header on flow registration → 403.
    no_csrf = authenticated_client.post(
        "/api/v1/ledger/payment-flows",
        json={
            "flow_type": "terminal_rent_receipt",
            "occurred_on": "2026-02-10",
            "amount": "1000.00",
        },
    )
    assert no_csrf.status_code == 403

    flow = _register_flow(
        authenticated_client,
        csrf_headers,
        amount="1000.00",
        counterparty_id=lessee_party_id,
    )
    flow_id = flow["flow_id"]

    # Allocation total must equal the flow amount exactly.
    mismatch = authenticated_client.post(
        f"/api/v1/ledger/payment-flows/{flow_id}/allocations",
        json={
            "allocations": [
                {
                    "target_type": "contract_ledger_entry",
                    "target_id": entry_id,
                    "year_month": "2026-01",
                    "amount": "900.00",
                }
            ]
        },
        headers=csrf_headers,
    )
    assert mismatch.status_code == 422, mismatch.text
    assert mismatch.json().get("error", {}).get("code") == "VALIDATION_ERROR"

    # The allocation period must match the target entry's ledger period.
    wrong_period = authenticated_client.post(
        f"/api/v1/ledger/payment-flows/{flow_id}/allocations",
        json={
            "allocations": [
                {
                    "target_type": "contract_ledger_entry",
                    "target_id": entry_id,
                    "year_month": "2026-02",
                    "amount": "1000.00",
                }
            ]
        },
        headers=csrf_headers,
    )
    assert wrong_period.status_code == 422, wrong_period.text

    # An upstream cost payment cannot land on a terminal-collection entry.
    upstream_flow = _register_flow(
        authenticated_client,
        csrf_headers,
        amount="1000.00",
        counterparty_id=lessee_party_id,
        flow_type="upstream_cost_payment",
    )
    view_mismatch = authenticated_client.post(
        f"/api/v1/ledger/payment-flows/{upstream_flow['flow_id']}/allocations",
        json={
            "allocations": [
                {
                    "target_type": "contract_ledger_entry",
                    "target_id": entry_id,
                    "year_month": "2026-01",
                    "amount": "1000.00",
                }
            ]
        },
        headers=csrf_headers,
    )
    assert view_mismatch.status_code == 422, view_mismatch.text

    # A flow without allocations cannot be voided.
    void_without_allocations = authenticated_client.post(
        f"/api/v1/ledger/payment-flows/{flow_id}/void",
        json={"reason": "无分摊作废应被拒绝"},
        headers=csrf_headers,
    )
    assert void_without_allocations.status_code == 422

    # The aggregated ledger endpoint requires at least one filter.
    unfiltered = authenticated_client.get("/api/v1/ledger/entries")
    assert unfiltered.status_code == 422


def test_service_fee_generation_and_reconcile_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Agency groups derive service fees from paid direct-lease receipts."""
    suffix = uuid4().hex[:8]
    operator = create_approved_legal_party(
        db_session, suffix=suffix, name=f"代理运营方-{suffix}"
    )
    owner = create_approved_legal_party(
        db_session, suffix=suffix, name=f"代理产权方-{suffix}"
    )
    lessor = create_approved_legal_party(
        db_session, suffix=suffix, name=f"直租出租方-{suffix}"
    )
    lessee = create_approved_legal_party(
        db_session, suffix=suffix, name=f"直租承租方-{suffix}"
    )

    project_id = _create_project(
        authenticated_client,
        csrf_headers,
        suffix=suffix,
        manager_party_id=operator.id,
    )
    group_id = _create_contract_group(
        authenticated_client,
        csrf_headers,
        project_id=project_id,
        operator_party_id=operator.id,
        owner_party_id=owner.id,
        revenue_mode="agency",
        suffix=suffix,
    )
    direct_contract_id = _add_contract(
        authenticated_client,
        csrf_headers,
        group_id=group_id,
        lessor_party_id=lessor.id,
        lessee_party_id=lessee.id,
        suffix=f"{suffix}d",
        group_relation_type="直租",
    )

    # Without an entrusted agreement the agency group cannot generate fees.
    early_generate = authenticated_client.post(
        "/api/v1/ledger/service-fees/generate",
        json={"contract_group_id": group_id},
        headers=csrf_headers,
    )
    assert early_generate.status_code == 422, early_generate.text

    _add_contract(
        authenticated_client,
        csrf_headers,
        group_id=group_id,
        lessor_party_id=owner.id,
        lessee_party_id=operator.id,
        suffix=f"{suffix}e",
        group_relation_type="委托",
        with_rent_terms=False,
        agency_detail={
            "service_fee_ratio": "0.10",
            "fee_calculation_base": "actual_received",
        },
    )

    # No receipts yet: generation succeeds but creates nothing.
    empty_generate = authenticated_client.post(
        "/api/v1/ledger/service-fees/generate",
        json={"contract_group_id": group_id},
        headers=csrf_headers,
    )
    assert empty_generate.status_code == 200, empty_generate.text
    assert empty_generate.json().get("created") == 0

    # Pay one rent entry in full; the service fee derives from the receipt.
    entry = _ledger_entry(authenticated_client, direct_contract_id, "2026-01")
    flow = _register_flow(
        authenticated_client,
        csrf_headers,
        amount="5000.00",
        counterparty_id=lessee.id,
    )
    _allocate(
        authenticated_client,
        csrf_headers,
        flow_id=flow["flow_id"],
        target_id=entry["entry_id"],
        amount="5000.00",
    )
    entry = _ledger_entry(authenticated_client, direct_contract_id, "2026-01")
    assert entry["payment_status"] == "paid"

    generate = authenticated_client.post(
        "/api/v1/ledger/service-fees/generate",
        json={"contract_group_id": group_id},
        headers=csrf_headers,
    )
    assert generate.status_code == 200, generate.text
    assert generate.json().get("created") == 1

    fees = authenticated_client.get(
        "/api/v1/ledger/service-fees",
        params={"contract_group_id": group_id},
    )
    assert fees.status_code == 200, fees.text
    fee_list = fees.json()
    assert isinstance(fee_list, list)
    january_fee = next(f for f in fee_list if f.get("year_month") == "2026-01")
    assert Decimal(str(january_fee["amount_due"])) == Decimal("500")
    assert Decimal(str(january_fee["calculation_base_amount"])) == Decimal("5000")
    assert january_fee["payment_status"] == "unpaid"

    # Reconciling a source that already matches is rejected.
    reconcile = authenticated_client.post(
        f"/api/v1/ledger/service-fees/{january_fee['service_fee_entry_id']}/reconcile",
        json={"reason": "来源无漂移时校准应被拒绝"},
        headers=csrf_headers,
    )
    assert reconcile.status_code == 422, reconcile.text


def test_ledger_recalculate_preserves_paid_entries_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Recalculation skips paid entries whose terms drifted out-of-band."""
    suffix = uuid4().hex[:8]
    _, contract_id, lessee_party_id = _setup_terminal_collection_contract(
        authenticated_client, csrf_headers, db_session, suffix=suffix
    )

    entry = _ledger_entry(authenticated_client, contract_id, "2026-01")
    flow = _register_flow(
        authenticated_client,
        csrf_headers,
        amount="5000.00",
        counterparty_id=lessee_party_id,
    )
    _allocate(
        authenticated_client,
        csrf_headers,
        flow_id=flow["flow_id"],
        target_id=entry["entry_id"],
        amount="5000.00",
    )

    # Simulate an out-of-band rent-term change: active contracts cannot
    # mutate rent terms through the API, so seed the drift directly.
    rent_term = (
        db_session.query(ContractRentTerm)
        .filter(ContractRentTerm.contract_id == contract_id)
        .one()
    )
    # amount_due prefers total_monthly_amount when present, so drift both.
    rent_term.monthly_rent = Decimal("6000")
    rent_term.total_monthly_amount = Decimal("6000")
    db_session.commit()

    recalculate = authenticated_client.post(
        f"/api/v1/contracts/{contract_id}/ledger/recalculate",
        headers=csrf_headers,
    )
    assert recalculate.status_code == 200, recalculate.text
    result = recalculate.json()
    assert result.get("created") == 0
    assert result.get("updated") == 11

    skipped = {
        skipped.get("entry_id"): skipped
        for skipped in result.get("skipped_entries", [])
    }
    assert entry["entry_id"] in skipped
    assert skipped[entry["entry_id"]].get("payment_status") == "paid"

    # The paid entry keeps its receipt facts and original amount due.
    entry_after = _ledger_entry(authenticated_client, contract_id, "2026-01")
    assert entry_after["payment_status"] == "paid"
    assert Decimal(str(entry_after["amount_due"])) == Decimal("5000")
    assert Decimal(str(entry_after["paid_amount"])) == Decimal("5000")

    # Unpaid entries pick up the new terms.
    entry_feb = _ledger_entry(authenticated_client, contract_id, "2026-02")
    assert entry_feb["payment_status"] == "unpaid"
    assert Decimal(str(entry_feb["amount_due"])) == Decimal("6000")
