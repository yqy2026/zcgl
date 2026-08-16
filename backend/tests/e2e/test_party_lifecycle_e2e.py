"""
End-to-end party lifecycle tests (REQ-PTY-001).

Covers the public Party surface: create (legal entity + individual),
review workflow (submit → approve → reject), review-status scoped
list filtering, update/delete guards on approved parties, and search.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.e2e


def _create_party(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    *,
    name: str,
    party_type: str = "legal_entity",
    identifier_type: str | None = None,
    identifier_value: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "party_type": party_type,
        "name": name,
    }
    if identifier_type is not None:
        payload["identifier_type"] = identifier_type
    if identifier_value is not None:
        payload["identifier_value"] = identifier_value
    response = authenticated_client.post(
        "/api/v1/parties",
        json=payload,
        headers=csrf_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_party_review_workflow_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    """Create → draft → submit (pending) → approve (approved)."""
    suffix = uuid4().hex[:8]
    created = _create_party(
        authenticated_client,
        csrf_headers,
        name=f"E2E主体-{suffix}",
        identifier_type="unified_social_credit_code",
        identifier_value=f"91310000{suffix.upper()}",
    )
    party_id = created.get("id")
    assert isinstance(party_id, str) and party_id != ""
    assert created.get("party_type") == "legal_entity"
    assert created.get("review_status") == "draft"
    assert created.get("code", "").startswith("LE-")
    assert created.get("status") == "active"

    # Update while draft is allowed.
    draft_update = authenticated_client.put(
        f"/api/v1/parties/{party_id}",
        json={"name": f"E2E主体改名-{suffix}"},
        headers=csrf_headers,
    )
    assert draft_update.status_code == 200
    assert draft_update.json().get("name") == f"E2E主体改名-{suffix}"

    # Submit review → pending.
    submit_response = authenticated_client.post(
        f"/api/v1/parties/{party_id}/submit-review",
        headers=csrf_headers,
    )
    assert submit_response.status_code == 200
    assert submit_response.json().get("review_status") == "pending"

    # Approve → approved.
    approve_response = authenticated_client.post(
        f"/api/v1/parties/{party_id}/approve-review",
        headers=csrf_headers,
    )
    assert approve_response.status_code == 200
    approved = approve_response.json()
    assert approved.get("review_status") == "approved"
    assert approved.get("review_by") is not None

    # Approved parties cannot be edited or deleted directly.
    update_blocked = authenticated_client.put(
        f"/api/v1/parties/{party_id}",
        json={"name": "不该成功"},
        headers=csrf_headers,
    )
    assert update_blocked.status_code == 400
    error = update_blocked.json().get("error", {})
    assert error.get("code") == "OPERATION_NOT_ALLOWED"
    assert (
        error.get("details", {}).get("reason")
        == "party_update_forbidden_by_review_status"
    )

    delete_blocked = authenticated_client.delete(
        f"/api/v1/parties/{party_id}",
        headers=csrf_headers,
    )
    assert delete_blocked.status_code == 400
    error = delete_blocked.json().get("error", {})
    assert error.get("code") == "OPERATION_NOT_ALLOWED"
    assert (
        error.get("details", {}).get("reason")
        == "party_delete_forbidden_by_review_status"
    )


def test_party_reject_flow_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    """A pending party can be rejected and returns to a re-editable state."""
    suffix = uuid4().hex[:8]
    created = _create_party(
        authenticated_client,
        csrf_headers,
        name=f"E2E驳回主体-{suffix}",
    )
    party_id = created.get("id")
    assert isinstance(party_id, str)

    authenticated_client.post(
        f"/api/v1/parties/{party_id}/submit-review",
        headers=csrf_headers,
    )

    reject_response = authenticated_client.post(
        f"/api/v1/parties/{party_id}/reject-review",
        json={"reason": "e2e 驳回原因"},
        headers=csrf_headers,
    )
    assert reject_response.status_code == 200
    assert reject_response.json().get("review_status") == "rejected"
    assert reject_response.json().get("review_reason") == "e2e 驳回原因"

    # Rejected parties become editable again (review_status stays rejected;
    # the edit itself is allowed, only pending/approved are blocked).
    re_edit = authenticated_client.put(
        f"/api/v1/parties/{party_id}",
        json={"name": f"E2E驳回后改名-{suffix}"},
        headers=csrf_headers,
    )
    assert re_edit.status_code == 200
    assert re_edit.json().get("name") == f"E2E驳回后改名-{suffix}"
    assert re_edit.json().get("review_status") == "rejected"

    # Resubmit after rejection returns the party to pending.
    resubmit = authenticated_client.post(
        f"/api/v1/parties/{party_id}/submit-review",
        headers=csrf_headers,
    )
    assert resubmit.status_code == 200
    assert resubmit.json().get("review_status") == "pending"


def test_party_list_search_and_filter_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    """List supports search, party_type, and review_status filters."""
    suffix = uuid4().hex[:8]
    legal = _create_party(
        authenticated_client,
        csrf_headers,
        name=f"E2E检索主体-{suffix}",
    )
    legal_id = legal.get("id")
    assert isinstance(legal_id, str)

    individual = _create_party(
        authenticated_client,
        csrf_headers,
        name=f"E2E自然人-{suffix}",
        party_type="individual",
        identifier_type="national_id",
        identifier_value=f"31010119900101{suffix[:4]}",
    )
    individual_id = individual.get("id")
    assert isinstance(individual_id, str)
    assert individual.get("code", "").startswith("NP-")

    # Search by name fragment.
    search_response = authenticated_client.get(f"/api/v1/parties?search={suffix}")
    assert search_response.status_code == 200
    search_items = search_response.json()
    assert isinstance(search_items, list)
    search_ids = {item.get("id") for item in search_items}
    assert {legal_id, individual_id}.issubset(search_ids)

    # Filter by party_type.
    legal_only = authenticated_client.get(
        f"/api/v1/parties?search={suffix}&party_type=legal_entity"
    )
    assert legal_only.status_code == 200
    legal_ids = {item.get("id") for item in legal_only.json()}
    assert legal_id in legal_ids
    assert individual_id not in legal_ids

    # Newly created parties are drafts; filter by review_status=draft.
    draft_only = authenticated_client.get(
        f"/api/v1/parties?search={suffix}&review_status=draft"
    )
    assert draft_only.status_code == 200
    draft_ids = {item.get("id") for item in draft_only.json()}
    assert {legal_id, individual_id}.issubset(draft_ids)

    # approve the legal party → no longer in draft filter.
    authenticated_client.post(
        f"/api/v1/parties/{legal_id}/submit-review",
        headers=csrf_headers,
    )
    authenticated_client.post(
        f"/api/v1/parties/{legal_id}/approve-review",
        headers=csrf_headers,
    )
    draft_after_approve = authenticated_client.get(
        f"/api/v1/parties?search={suffix}&review_status=draft"
    )
    assert draft_after_approve.status_code == 200
    draft_ids_after = {item.get("id") for item in draft_after_approve.json()}
    assert legal_id not in draft_ids_after
    assert individual_id in draft_ids_after


def test_party_identifier_pair_validation_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    """identifier_type without identifier_value is rejected with 422."""
    suffix = uuid4().hex[:8]
    response = authenticated_client.post(
        "/api/v1/parties",
        json={
            "party_type": "legal_entity",
            "name": f"E2E标识校验-{suffix}",
            "identifier_type": "unified_social_credit_code",
        },
        headers=csrf_headers,
    )
    assert response.status_code == 422

    # Individual with a legal-only identifier type is also rejected.
    response = authenticated_client.post(
        "/api/v1/parties",
        json={
            "party_type": "individual",
            "name": f"E2E标识类型-{suffix}",
            "identifier_type": "unified_social_credit_code",
            "identifier_value": f"91310000{suffix.upper()}",
        },
        headers=csrf_headers,
    )
    assert response.status_code == 400


def test_party_review_requires_admin_and_csrf_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
    create_test_user_factory,
) -> None:
    """Review approval is admin-gated: a regular user cannot approve (403),
    and mutations without the CSRF header are rejected (issue #91 行动项 14)."""
    from tests.e2e.session_helpers import capture_session, login, restore_session

    suffix = uuid4().hex[:8]
    admin_session = capture_session(authenticated_client)
    party = _create_party(
        authenticated_client,
        csrf_headers,
        name=f"分离审批主体-{suffix}",
    )
    submit = authenticated_client.post(
        f"/api/v1/parties/{party['id']}/submit-review", headers=csrf_headers
    )
    assert submit.status_code == 200, submit.text

    # CSRF negative branch (E2E Admission Standard #2).
    csrf_missing = authenticated_client.post(
        f"/api/v1/parties/{party['id']}/approve-review"
    )
    assert csrf_missing.status_code == 403

    # Submitter/approver separation: a regular user cannot approve.
    create_test_user_factory(
        username=f"e2e_party_reg_{suffix}",
        email=f"e2e_party_reg_{suffix}@example.com",
        password="UserPass123!@#",
        full_name=f"E2E主体普通用户-{suffix}",
        role="user",
    )
    login(authenticated_client, f"e2e_party_reg_{suffix}", "UserPass123!@#")
    regular_session = capture_session(authenticated_client)
    regular_headers = restore_session(authenticated_client, regular_session)
    denied = authenticated_client.post(
        f"/api/v1/parties/{party['id']}/approve-review",
        headers=regular_headers,
    )
    assert denied.status_code == 403
    assert denied.json().get("error", {}).get("code") == "PERMISSION_DENIED"

    # The admin approval still lands afterwards.
    admin_headers = restore_session(authenticated_client, admin_session)
    approve = authenticated_client.post(
        f"/api/v1/parties/{party['id']}/approve-review",
        headers=admin_headers,
    )
    assert approve.status_code == 200, approve.text
    assert approve.json().get("review_status") == "approved"
