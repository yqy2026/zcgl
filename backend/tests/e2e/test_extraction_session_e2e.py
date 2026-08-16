"""
End-to-end document extraction session tests (REQ-DOC-001, backend side).

Covers the unified extraction-session entry point with a real text-layer
PDF (no OCR, LLM disabled by default): contract session confirm creating
the contract, property certificate session confirm creating the
certificate with the staged attachment promoted, cancel semantics, and
the review-validation guards.
"""

from uuid import uuid4

import fitz
import pytest
from fastapi.testclient import TestClient

from tests.e2e.factories import (
    create_approved_legal_party,
    create_scoped_asset_via_api,
)

pytestmark = pytest.mark.e2e


def _text_pdf_bytes(*lines: str) -> bytes:
    """A real one-page PDF whose text layer keeps the pipeline off OCR."""
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line)
        y += 20
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
            "project_name": f"E2E抽取项目-{suffix}",
            "status": "planning",
            "manager_party_id": manager_party_id,
            "data_status": "正常",
        },
        headers=csrf_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_contract_extraction_session_confirm_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """A contract upload confirms into a real contract via manual review."""
    suffix = uuid4().hex[:8]
    operator = create_approved_legal_party(
        db_session, suffix=f"{suffix}op", name=f"抽取运营方-{suffix}"
    )
    owner = create_approved_legal_party(
        db_session, suffix=f"{suffix}ow", name=f"抽取产权方-{suffix}"
    )
    lessor = create_approved_legal_party(
        db_session, suffix=f"{suffix}ls", name=f"抽取出租方-{suffix}"
    )
    lessee = create_approved_legal_party(
        db_session, suffix=f"{suffix}lz", name=f"抽取承租方-{suffix}"
    )
    project_id = _create_project(
        authenticated_client,
        csrf_headers,
        suffix=suffix,
        manager_party_id=operator.id,
    )
    contract_number = f"E2E-EXT-{suffix}"

    session = authenticated_client.post(
        "/api/v1/extraction-sessions",
        data={
            "target_type": "contract",
            "project_id": project_id,
            "revenue_mode": "lease",
            "contract_direction": "出租",
            "group_relation_type": "下游",
        },
        files={
            "file": (
                "contract.pdf",
                _text_pdf_bytes(
                    f"Contract number: {contract_number}",
                    "Effective from: 2026-01-01 to 2026-12-31",
                ),
                "application/pdf",
            )
        },
        headers=csrf_headers,
    )
    assert session.status_code == 201, session.text
    session_payload = session.json()
    session_id = session_payload["session_id"]
    assert session_payload["status"] == "ready_for_review"
    assert session_payload["target_type"] == "contract"
    # English labels do not hit the Chinese rule regexes: no candidates.
    assert session_payload["candidates"]["fields"] == {}

    fetched = authenticated_client.get(f"/api/v1/extraction-sessions/{session_id}")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "ready_for_review"

    # Missing a required manual field is rejected by candidate review.
    incomplete = authenticated_client.post(
        f"/api/v1/extraction-sessions/{session_id}/confirm",
        json={
            "actions": [
                {"field_key": "contract_number", "action": "manual", "value": contract_number},
            ],
            "party_ids": {
                "operator_party_id": operator.id,
                "owner_party_id": owner.id,
                "lessor_party_id": lessor.id,
                "lessee_party_id": lessee.id,
            },
            "asset_ids": [],
        },
        headers=csrf_headers,
    )
    assert incomplete.status_code == 422, incomplete.text

    confirm = authenticated_client.post(
        f"/api/v1/extraction-sessions/{session_id}/confirm",
        json={
            "actions": [
                {"field_key": "contract_number", "action": "manual", "value": contract_number},
                {"field_key": "sign_date", "action": "manual", "value": "2026-01-01"},
                {"field_key": "effective_from", "action": "manual", "value": "2026-01-01"},
                {"field_key": "effective_to", "action": "manual", "value": "2026-12-31"},
                {"field_key": "monthly_rent", "action": "manual", "value": "5000"},
            ],
            "party_ids": {
                "operator_party_id": operator.id,
                "owner_party_id": owner.id,
                "lessor_party_id": lessor.id,
                "lessee_party_id": lessee.id,
            },
            "asset_ids": [],
        },
        headers=csrf_headers,
    )
    assert confirm.status_code == 200, confirm.text
    contract_id = confirm.json()["contract_id"]

    contract_detail = authenticated_client.get(f"/api/v1/contracts/{contract_id}")
    assert contract_detail.status_code == 200, contract_detail.text
    detail = contract_detail.json()
    assert detail["contract_number"] == contract_number
    assert detail["status"] == "生效"

    # The confirmed rent term materializes the monthly ledger.
    ledger = authenticated_client.get(f"/api/v1/contracts/{contract_id}/ledger")
    assert ledger.status_code == 200
    assert ledger.json().get("total") == 12

    # The session is consumed by the confirmation.
    consumed = authenticated_client.get(f"/api/v1/extraction-sessions/{session_id}")
    assert consumed.status_code == 404


def test_contract_extraction_session_cancel_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Cancelling consumes the session and cleans it up."""
    suffix = uuid4().hex[:8]
    operator = create_approved_legal_party(
        db_session, suffix=f"{suffix}c", name=f"取消运营方-{suffix}"
    )
    project_id = _create_project(
        authenticated_client,
        csrf_headers,
        suffix=f"{suffix}c",
        manager_party_id=operator.id,
    )

    session = authenticated_client.post(
        "/api/v1/extraction-sessions",
        data={
            "target_type": "contract",
            "project_id": project_id,
            "revenue_mode": "lease",
            "contract_direction": "出租",
            "group_relation_type": "上游",
        },
        files={
            "file": (
                "contract.pdf",
                _text_pdf_bytes("Draft contract for cancellation test"),
                "application/pdf",
            )
        },
        headers=csrf_headers,
    )
    assert session.status_code == 201, session.text
    session_id = session.json()["session_id"]

    cancel = authenticated_client.post(
        f"/api/v1/extraction-sessions/{session_id}/cancel", headers=csrf_headers
    )
    assert cancel.status_code == 204, cancel.text

    gone = authenticated_client.get(f"/api/v1/extraction-sessions/{session_id}")
    assert gone.status_code == 404

    capabilities = authenticated_client.get(
        "/api/v1/document-extraction/capabilities"
    )
    assert capabilities.status_code == 200
    targets = {t["target_type"] for t in capabilities.json()["targets"]}
    assert {"contract", "property_certificate"} <= targets


def test_property_certificate_extraction_session_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """A certificate upload confirms into a certificate with attachment."""
    suffix = uuid4().hex[:8]
    holder = create_approved_legal_party(
        db_session, suffix=suffix, name=f"抽取权利人-{suffix}"
    )
    asset = create_scoped_asset_via_api(
        authenticated_client,
        db_session,
        suffix=suffix,
        holder_party_id=holder.id,
        csrf_headers=csrf_headers,
    )

    # asset_id is required for the certificate branch.
    missing_asset = authenticated_client.post(
        "/api/v1/extraction-sessions",
        data={"target_type": "property_certificate"},
        files={
            "file": (
                "cert.pdf",
                _text_pdf_bytes("Certificate upload without asset context"),
                "application/pdf",
            )
        },
        headers=csrf_headers,
    )
    assert missing_asset.status_code == 422, missing_asset.text

    session = authenticated_client.post(
        "/api/v1/extraction-sessions",
        data={"target_type": "property_certificate", "asset_id": asset["id"]},
        files={
            "file": (
                "cert.pdf",
                _text_pdf_bytes(f"Certificate E2E-BDC-{suffix} placeholder text"),
                "application/pdf",
            )
        },
        headers=csrf_headers,
    )
    assert session.status_code == 201, session.text
    session_id = session.json()["session_id"]

    # Confirm without holders is rejected.
    no_holder = authenticated_client.post(
        f"/api/v1/extraction-sessions/{session_id}/confirm",
        json={
            "actions": [
                {"field_key": "certificate_number", "action": "manual", "value": f"E2E-BDC-{suffix}"},
                {"field_key": "property_address", "action": "manual", "value": f"抽取地址-{suffix}"},
                {"field_key": "registration_date", "action": "manual", "value": "2026-01-01"},
            ],
            "certificate_type": "real_estate",
            "holder_party_ids": [],
        },
        headers=csrf_headers,
    )
    assert no_holder.status_code == 422, no_holder.text

    confirm = authenticated_client.post(
        f"/api/v1/extraction-sessions/{session_id}/confirm",
        json={
            "actions": [
                {"field_key": "certificate_number", "action": "manual", "value": f"E2E-BDC-{suffix}"},
                {"field_key": "property_address", "action": "manual", "value": f"抽取地址-{suffix}"},
                {"field_key": "registration_date", "action": "manual", "value": "2026-01-01"},
            ],
            "certificate_type": "real_estate",
            "holder_party_ids": [holder.id],
        },
        headers=csrf_headers,
    )
    assert confirm.status_code == 200, confirm.text
    certificate_id = confirm.json()["certificate_id"]

    detail = authenticated_client.get(
        f"/api/v1/property-certificates/{certificate_id}"
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["certificate_number"] == f"E2E-BDC-{suffix}"

    consumed = authenticated_client.get(f"/api/v1/extraction-sessions/{session_id}")
    assert consumed.status_code == 404

def test_extraction_session_creation_requires_csrf_header_e2e(
    authenticated_client,
) -> None:
    """E2E Admission Standard #2: mutations need the CSRF negative branch."""
    response = authenticated_client.post(
        "/api/v1/extraction-sessions",
        data={"target_type": "contract"},
        files={"file": ("c.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 403
