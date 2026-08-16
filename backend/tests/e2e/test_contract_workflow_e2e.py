"""
End-to-end contract workflow tests (REQ-RNT-001).

Covers the complete M2/M3 contract lifecycle across the public API:
project → contract group → lease contract → ledger generation →
contract termination, plus the CSRF guard on mutating endpoints.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.e2e.factories import (
    create_approved_legal_party,
)

pytestmark = pytest.mark.e2e


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
            "project_name": f"E2E项目-{suffix}",
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
    suffix: str,
) -> str:
    response = authenticated_client.post(
        "/api/v1/contract-groups",
        json={
            "project_id": project_id,
            "revenue_mode": "lease",
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
    group = response.json()
    group_id = group.get("contract_group_id")
    assert isinstance(group_id, str) and group_id != ""
    assert group.get("group_code", "").startswith("GRP-")
    return group_id


def _add_lease_contract(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    *,
    group_id: str,
    lessor_party_id: str,
    lessee_party_id: str,
    suffix: str,
) -> str:
    response = authenticated_client.post(
        f"/api/v1/contract-groups/{group_id}/contracts",
        json={
            "contract_group_id": group_id,
            "contract_number": f"E2E-HT-{suffix}",
            "contract_direction": "出租",
            "group_relation_type": "上游",
            "lessor_party_id": lessor_party_id,
            "lessee_party_id": lessee_party_id,
            "sign_date": "2026-01-01",
            "effective_from": "2026-01-01",
            "effective_to": "2026-12-31",
            "payment_cycle": "月付",
            "lease_detail": {
                "total_deposit": 10000,
                "rent_amount": 5000,
                "monthly_rent_base": 5000,
                "payment_cycle": "月付",
                "tenant_name": f"E2E租户-{suffix}",
            },
            "rent_terms": [
                {
                    "sort_order": 1,
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                    "monthly_rent": 5000,
                }
            ],
        },
        headers=csrf_headers,
    )
    assert response.status_code == 201, response.text
    contract = response.json()
    contract_id = contract.get("contract_id")
    assert isinstance(contract_id, str) and contract_id != ""
    assert contract.get("contract_number") == f"E2E-HT-{suffix}"
    assert contract.get("status") == "生效"
    return contract_id


def test_contract_full_workflow_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Project → contract group → lease contract → ledger → termination."""
    suffix = uuid4().hex[:8]
    operator = create_approved_legal_party(
        db_session, suffix=suffix, name=f"运营方-{suffix}"
    )
    owner = create_approved_legal_party(
        db_session, suffix=suffix, name=f"产权方-{suffix}"
    )
    lessor = create_approved_legal_party(
        db_session, suffix=suffix, name=f"出租方-{suffix}"
    )
    lessee = create_approved_legal_party(
        db_session, suffix=suffix, name=f"承租方-{suffix}"
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
        suffix=suffix,
    )
    contract_id = _add_lease_contract(
        authenticated_client,
        csrf_headers,
        group_id=group_id,
        lessor_party_id=lessor.id,
        lessee_party_id=lessee.id,
        suffix=suffix,
    )

    # Group detail exposes the newly created contract summary.
    group_detail = authenticated_client.get(f"/api/v1/contract-groups/{group_id}")
    assert group_detail.status_code == 200
    group_payload = group_detail.json()
    assert group_payload.get("contract_group_id") == group_id
    contract_summaries = group_payload.get("contracts", [])
    assert any(c.get("contract_id") == contract_id for c in contract_summaries)

    # Contract detail round-trips the lease detail and rent terms.
    contract_detail = authenticated_client.get(f"/api/v1/contracts/{contract_id}")
    assert contract_detail.status_code == 200
    detail_payload = contract_detail.json()
    assert detail_payload.get("contract_id") == contract_id
    assert detail_payload.get("group_relation_type") == "上游"
    lease_detail = detail_payload.get("lease_detail")
    assert isinstance(lease_detail, dict)
    # 租户名以承租方主体名称为准（服务层同步 lessee name snapshot）
    assert lease_detail.get("tenant_name") == f"承租方-{suffix}"

    rent_terms = authenticated_client.get(f"/api/v1/contracts/{contract_id}/rent-terms")
    assert rent_terms.status_code == 200
    rent_terms_payload = rent_terms.json()
    assert isinstance(rent_terms_payload, list)
    assert len(rent_terms_payload) == 1
    assert rent_terms_payload[0].get("monthly_rent") == "5000.00"

    # Ledger was generated on activation: 12 monthly entries for 2026.
    contract_ledger = authenticated_client.get(
        f"/api/v1/contracts/{contract_id}/ledger"
    )
    assert contract_ledger.status_code == 200
    ledger_items = contract_ledger.json().get("items", [])
    assert isinstance(ledger_items, list)
    assert len(ledger_items) == 12
    assert all(item.get("contract_id") == contract_id for item in ledger_items)
    assert all(item.get("payment_status") == "unpaid" for item in ledger_items)
    assert {item.get("year_month") for item in ledger_items} == {
        f"2026-{month:02d}" for month in range(1, 13)
    }

    # The aggregated ledger endpoint also serves the contract filter.
    aggregated = authenticated_client.get(
        f"/api/v1/ledger/entries?contract_id={contract_id}"
    )
    assert aggregated.status_code == 200
    assert aggregated.json().get("total") == 12

    # Terminate the contract; the detail reflects the new lifecycle status.
    terminate_response = authenticated_client.post(
        f"/api/v1/contracts/{contract_id}/terminate",
        json={"reason": "e2e 终止验证"},
        headers=csrf_headers,
    )
    assert terminate_response.status_code == 200
    assert terminate_response.json().get("status") == "已终止"

    after_terminate = authenticated_client.get(f"/api/v1/contracts/{contract_id}")
    assert after_terminate.status_code == 200
    assert after_terminate.json().get("status") == "已终止"


def test_contract_mutations_require_csrf_header_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Every contract-family mutating endpoint must reject missing CSRF."""
    suffix = uuid4().hex[:8]
    operator = create_approved_legal_party(
        db_session, suffix=suffix, name=f"CSRF运营方-{suffix}"
    )
    owner = create_approved_legal_party(
        db_session, suffix=suffix, name=f"CSRF产权方-{suffix}"
    )
    lessor = create_approved_legal_party(
        db_session, suffix=suffix, name=f"CSRF出租方-{suffix}"
    )
    lessee = create_approved_legal_party(
        db_session, suffix=suffix, name=f"CSRF承租方-{suffix}"
    )

    project_id = _create_project(
        authenticated_client,
        csrf_headers,
        suffix=f"{suffix}p",
        manager_party_id=operator.id,
    )
    group_id = _create_contract_group(
        authenticated_client,
        csrf_headers,
        project_id=project_id,
        operator_party_id=operator.id,
        owner_party_id=owner.id,
        suffix=f"{suffix}g",
    )

    # POST contract-group without CSRF → 403.
    no_csrf_group = authenticated_client.post(
        "/api/v1/contract-groups",
        json={
            "project_id": project_id,
            "revenue_mode": "lease",
            "operator_party_id": operator.id,
            "owner_party_id": owner.id,
            "effective_from": "2026-01-01",
        },
    )
    assert no_csrf_group.status_code == 403

    # POST contract without CSRF → 403.
    no_csrf_contract = authenticated_client.post(
        f"/api/v1/contract-groups/{group_id}/contracts",
        json={
            "contract_group_id": group_id,
            "contract_number": f"E2E-HT-NOCSRF-{suffix}",
            "contract_direction": "出租",
            "group_relation_type": "上游",
            "lessor_party_id": lessor.id,
            "lessee_party_id": lessee.id,
            "effective_from": "2026-01-01",
        },
    )
    assert no_csrf_contract.status_code == 403

    # Create the contract properly for the termination guard.
    contract_id = _add_lease_contract(
        authenticated_client,
        csrf_headers,
        group_id=group_id,
        lessor_party_id=lessor.id,
        lessee_party_id=lessee.id,
        suffix=f"{suffix}c",
    )

    # POST terminate without CSRF → 403.
    no_csrf_terminate = authenticated_client.post(
        f"/api/v1/contracts/{contract_id}/terminate",
        json={"reason": "e2e"},
    )
    assert no_csrf_terminate.status_code == 403

    # DELETE contract without CSRF → 403.
    no_csrf_delete = authenticated_client.delete(f"/api/v1/contracts/{contract_id}")
    assert no_csrf_delete.status_code == 403


def test_contract_group_rejects_missing_parties_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """A contract group referencing nonexistent parties returns 404."""
    suffix = uuid4().hex[:8]
    operator = create_approved_legal_party(
        db_session, suffix=suffix, name=f"缺员运营方-{suffix}"
    )
    project_id = _create_project(
        authenticated_client,
        csrf_headers,
        suffix=f"{suffix}np",
        manager_party_id=operator.id,
    )

    missing_owner_response = authenticated_client.post(
        "/api/v1/contract-groups",
        json={
            "project_id": project_id,
            "revenue_mode": "lease",
            "operator_party_id": operator.id,
            "owner_party_id": "00000000-0000-0000-0000-000000000000",
            "effective_from": "2026-01-01",
        },
        headers=csrf_headers,
    )
    assert missing_owner_response.status_code == 404
    error = missing_owner_response.json().get("error", {})
    assert error.get("code") == "RESOURCE_NOT_FOUND"


def test_contract_number_must_be_unique_within_project_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """A duplicate contract number inside one project is rejected."""
    suffix = uuid4().hex[:8]
    operator = create_approved_legal_party(
        db_session, suffix=suffix, name=f"重号运营方-{suffix}"
    )
    owner = create_approved_legal_party(
        db_session, suffix=suffix, name=f"重号产权方-{suffix}"
    )
    lessor = create_approved_legal_party(
        db_session, suffix=suffix, name=f"重号出租方-{suffix}"
    )
    lessee = create_approved_legal_party(
        db_session, suffix=suffix, name=f"重号承租方-{suffix}"
    )

    project_id = _create_project(
        authenticated_client,
        csrf_headers,
        suffix=f"{suffix}dup",
        manager_party_id=operator.id,
    )
    group_id = _create_contract_group(
        authenticated_client,
        csrf_headers,
        project_id=project_id,
        operator_party_id=operator.id,
        owner_party_id=owner.id,
        suffix=f"{suffix}dup",
    )

    _add_lease_contract(
        authenticated_client,
        csrf_headers,
        group_id=group_id,
        lessor_party_id=lessor.id,
        lessee_party_id=lessee.id,
        suffix=f"{suffix}dup",
    )

    duplicate_response = authenticated_client.post(
        f"/api/v1/contract-groups/{group_id}/contracts",
        json={
            "contract_group_id": group_id,
            "contract_number": f"E2E-HT-{suffix}dup",
            "contract_direction": "出租",
            "group_relation_type": "上游",
            "lessor_party_id": lessor.id,
            "lessee_party_id": lessee.id,
            "sign_date": "2026-01-01",
            "effective_from": "2026-01-01",
            "effective_to": "2026-12-31",
            "lease_detail": {
                "total_deposit": 10000,
                "rent_amount": 5000,
                "monthly_rent_base": 5000,
            },
            "rent_terms": [
                {
                    "sort_order": 1,
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                    "monthly_rent": 5000,
                }
            ],
        },
        headers=csrf_headers,
    )
    assert duplicate_response.status_code == 409
    error = duplicate_response.json().get("error", {})
    assert error.get("code") == "DUPLICATE_RESOURCE"


def test_contract_correction_workflow_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """start-correction clones a draft, finalize swaps ledgers (REQ-RNT-005)."""
    suffix = uuid4().hex[:8]
    operator = create_approved_legal_party(
        db_session, suffix=suffix, name=f"纠错运营方-{suffix}"
    )
    owner = create_approved_legal_party(
        db_session, suffix=suffix, name=f"纠错产权方-{suffix}"
    )
    lessor = create_approved_legal_party(
        db_session, suffix=suffix, name=f"纠错出租方-{suffix}"
    )
    lessee = create_approved_legal_party(
        db_session, suffix=suffix, name=f"纠错承租方-{suffix}"
    )

    project_id = _create_project(
        authenticated_client,
        csrf_headers,
        suffix=f"{suffix}co",
        manager_party_id=operator.id,
    )
    group_id = _create_contract_group(
        authenticated_client,
        csrf_headers,
        project_id=project_id,
        operator_party_id=operator.id,
        owner_party_id=owner.id,
        suffix=f"{suffix}co",
    )
    source_number = f"E2E-HT-{suffix}co"
    source_contract_id = _add_lease_contract(
        authenticated_client,
        csrf_headers,
        group_id=group_id,
        lessor_party_id=lessor.id,
        lessee_party_id=lessee.id,
        suffix=f"{suffix}co",
    )

    # A blank correction reason is rejected.
    blank_start = authenticated_client.post(
        f"/api/v1/contracts/{source_contract_id}/start-correction",
        json={"reason": "   "},
        headers=csrf_headers,
    )
    assert blank_start.status_code == 400
    blank_error = blank_start.json().get("error", {})
    assert blank_error.get("code") == "INVALID_REQUEST"
    assert blank_error.get("details", {}).get("field") == "reason"

    # Starting correction clones the active contract into a -C01 draft.
    start = authenticated_client.post(
        f"/api/v1/contracts/{source_contract_id}/start-correction",
        json={"reason": "租金条款调整"},
        headers=csrf_headers,
    )
    assert start.status_code == 200, start.text
    draft = start.json()
    draft_contract_id = draft["contract_id"]
    assert draft["contract_number"] == f"{source_number}-C01"
    assert draft["status"] == "草稿"

    # The active source contract keeps its terms frozen.
    frozen_term_update = authenticated_client.put(
        f"/api/v1/contracts/{source_contract_id}/rent-terms/placeholder",
        json={"monthly_rent": "6000.00"},
        headers=csrf_headers,
    )
    assert frozen_term_update.status_code == 400
    assert (
        frozen_term_update.json().get("error", {}).get("code") == "OPERATION_NOT_ALLOWED"
    )

    # Edit the draft's rent term, then finalize the correction.
    draft_terms = authenticated_client.get(
        f"/api/v1/contracts/{draft_contract_id}/rent-terms"
    )
    assert draft_terms.status_code == 200
    terms = draft_terms.json()
    assert isinstance(terms, list) and len(terms) == 1
    rent_term_id = terms[0]["rent_term_id"]

    term_update = authenticated_client.put(
        f"/api/v1/contracts/{draft_contract_id}/rent-terms/{rent_term_id}",
        json={"monthly_rent": "6000.00"},
        headers=csrf_headers,
    )
    assert term_update.status_code == 200, term_update.text

    finalize = authenticated_client.post(
        f"/api/v1/contracts/{draft_contract_id}/finalize-correction",
        json={"reason": "纠错定稿"},
        headers=csrf_headers,
    )
    assert finalize.status_code == 200, finalize.text
    replacement = finalize.json()
    replacement_contract_id = replacement["contract_id"]
    assert replacement_contract_id == draft_contract_id
    assert replacement["status"] == "生效"

    # The source contract terminates and its whole ledger is voided.
    source_detail = authenticated_client.get(
        f"/api/v1/contracts/{source_contract_id}"
    )
    assert source_detail.status_code == 200
    assert source_detail.json().get("status") == "已终止"

    source_ledger = authenticated_client.get(
        f"/api/v1/contracts/{source_contract_id}/ledger"
    )
    assert source_ledger.status_code == 200
    source_items = source_ledger.json().get("items", [])
    assert len(source_items) == 12
    assert all(item.get("payment_status") == "voided" for item in source_items)

    # The finalized draft takes over with the corrected terms.
    replacement_ledger = authenticated_client.get(
        f"/api/v1/contracts/{replacement_contract_id}/ledger"
    )
    assert replacement_ledger.status_code == 200
    replacement_items = replacement_ledger.json().get("items", [])
    assert len(replacement_items) == 12
    assert all(item.get("payment_status") == "unpaid" for item in replacement_items)
    assert {item.get("amount_due") for item in replacement_items} == {"6000.00"}


def _add_ledger_free_contract(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    *,
    group_id: str,
    lessor_party_id: str,
    lessee_party_id: str,
    suffix: str,
) -> str:
    """Create an active contract without rent terms (no ledger generated)."""
    response = authenticated_client.post(
        f"/api/v1/contract-groups/{group_id}/contracts",
        json={
            "contract_group_id": group_id,
            "contract_number": f"E2E-HT-{suffix}",
            "contract_direction": "出租",
            "group_relation_type": "上游",
            "lessor_party_id": lessor_party_id,
            "lessee_party_id": lessee_party_id,
            "sign_date": "2026-01-01",
            "effective_from": "2026-01-01",
            "effective_to": "2026-12-31",
            "payment_cycle": "月付",
            "lease_detail": {
                "total_deposit": 10000,
                "rent_amount": 5000,
                "monthly_rent_base": 5000,
                "payment_cycle": "月付",
                "tenant_name": f"E2E租户-{suffix}",
            },
        },
        headers=csrf_headers,
    )
    assert response.status_code == 201, response.text
    contract_id = response.json().get("contract_id")
    assert isinstance(contract_id, str) and contract_id != ""
    return contract_id


def test_contract_void_workflow_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Voiding requires a terminated contract with no ledger (REQ-RNT-005)."""
    suffix = uuid4().hex[:8]
    operator = create_approved_legal_party(
        db_session, suffix=suffix, name=f"作废运营方-{suffix}"
    )
    owner = create_approved_legal_party(
        db_session, suffix=suffix, name=f"作废产权方-{suffix}"
    )
    lessor = create_approved_legal_party(
        db_session, suffix=suffix, name=f"作废出租方-{suffix}"
    )
    lessee = create_approved_legal_party(
        db_session, suffix=suffix, name=f"作废承租方-{suffix}"
    )

    project_id = _create_project(
        authenticated_client,
        csrf_headers,
        suffix=f"{suffix}vd",
        manager_party_id=operator.id,
    )
    group_id = _create_contract_group(
        authenticated_client,
        csrf_headers,
        project_id=project_id,
        operator_party_id=operator.id,
        owner_party_id=owner.id,
        suffix=f"{suffix}vd",
    )

    clean_contract_id = _add_ledger_free_contract(
        authenticated_client,
        csrf_headers,
        group_id=group_id,
        lessor_party_id=lessor.id,
        lessee_party_id=lessee.id,
        suffix=f"{suffix}vd",
    )
    clean_ledger = authenticated_client.get(
        f"/api/v1/contracts/{clean_contract_id}/ledger"
    )
    assert clean_ledger.status_code == 200
    assert clean_ledger.json().get("total") == 0

    # An active contract must be terminated before it can be voided.
    premature_void = authenticated_client.post(
        f"/api/v1/contracts/{clean_contract_id}/void",
        json={"reason": "直接作废应被拒绝"},
        headers=csrf_headers,
    )
    assert premature_void.status_code == 400
    assert (
        premature_void.json().get("error", {}).get("code") == "OPERATION_NOT_ALLOWED"
    )

    terminate = authenticated_client.post(
        f"/api/v1/contracts/{clean_contract_id}/terminate",
        json={"reason": "e2e 终止后作废"},
        headers=csrf_headers,
    )
    assert terminate.status_code == 200, terminate.text

    # A void without a reason is rejected.
    reasonless_void = authenticated_client.post(
        f"/api/v1/contracts/{clean_contract_id}/void",
        json={"reason": " "},
        headers=csrf_headers,
    )
    assert reasonless_void.status_code == 400
    reasonless_error = reasonless_void.json().get("error", {})
    assert reasonless_error.get("code") == "INVALID_REQUEST"
    assert reasonless_error.get("details", {}).get("field") == "reason"

    void = authenticated_client.post(
        f"/api/v1/contracts/{clean_contract_id}/void",
        json={"reason": "录入错误作废"},
        headers=csrf_headers,
    )
    assert void.status_code == 200, void.text
    voided = void.json()
    assert voided["data_status"] == "已作废"
    # Void flips data_status only; the lifecycle status stays terminated.
    assert voided["status"] == "已终止"

    detail = authenticated_client.get(f"/api/v1/contracts/{clean_contract_id}")
    assert detail.status_code == 200
    assert detail.json().get("data_status") == "已作废"

    # A contract with generated ledger entries cannot be voided.
    ledger_contract_id = _add_lease_contract(
        authenticated_client,
        csrf_headers,
        group_id=group_id,
        lessor_party_id=lessor.id,
        lessee_party_id=lessee.id,
        suffix=f"{suffix}vd2",
    )
    terminate_ledger_contract = authenticated_client.post(
        f"/api/v1/contracts/{ledger_contract_id}/terminate",
        json={"reason": "e2e 终止带台账合同"},
        headers=csrf_headers,
    )
    assert terminate_ledger_contract.status_code == 200

    void_with_ledger = authenticated_client.post(
        f"/api/v1/contracts/{ledger_contract_id}/void",
        json={"reason": "带台账作废应被拒绝"},
        headers=csrf_headers,
    )
    assert void_with_ledger.status_code == 400
    assert (
        void_with_ledger.json().get("error", {}).get("code") == "OPERATION_NOT_ALLOWED"
    )
