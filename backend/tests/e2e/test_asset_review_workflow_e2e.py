"""
End-to-end asset review workflow tests (REQ-AST-003).

Covers the two-step review state machine across the public API:
submit → approve / reject, withdraw, reverse review, resubmit, the
review log trail, batch transitions, and the non-admin denial branch.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.models.party import Party, PartyReviewStatus, PartyType
from src.models.user_party_binding import RelationType, UserPartyBinding
from tests.e2e.factories import (
    create_asset_ownership as _create_ownership,
)
from tests.e2e.factories import (
    create_asset_payload as _create_asset_payload,
)

pytestmark = pytest.mark.e2e


def _ensure_asset_party_scope(
    db_session,
    authenticated_client: TestClient,
    *,
    suffix: str,
) -> Party:
    ownership = _create_ownership(db_session, suffix)
    party = (
        db_session.query(Party)
        .filter(
            Party.party_type == PartyType.LEGAL_ENTITY,
            Party.external_ref == ownership.id,
        )
        .one_or_none()
    )
    if party is None:
        party = Party(
            party_type=PartyType.LEGAL_ENTITY,
            name=ownership.name,
            code=f"LE-{uuid4().int % 1_000_000:06d}",
            external_ref=ownership.id,
            status="active",
            review_status=PartyReviewStatus.APPROVED.value,
        )
        db_session.add(party)
        db_session.flush()

    user_id = getattr(authenticated_client, "_user_id", None)
    assert isinstance(user_id, str) and user_id != ""

    binding = (
        db_session.query(UserPartyBinding)
        .filter(
            UserPartyBinding.user_id == user_id,
            UserPartyBinding.party_id == party.id,
            UserPartyBinding.relation_type == RelationType.OWNER,
        )
        .one_or_none()
    )
    if binding is None:
        binding = UserPartyBinding(
            user_id=user_id,
            party_id=party.id,
            relation_type=RelationType.OWNER,
        )
        db_session.add(binding)
        db_session.flush()

    db_session.commit()
    db_session.refresh(party)
    return party


def _create_review_asset(
    db_session,
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    *,
    suffix: str,
) -> str:
    """Create a draft asset through the public API; return its id."""
    party = _ensure_asset_party_scope(
        db_session,
        authenticated_client,
        suffix=suffix,
    )
    payload = _create_asset_payload(
        suffix=suffix,
        ownership_id=party.external_ref or party.id,
    )
    payload["owner_party_id"] = party.id
    payload["manager_party_id"] = party.id
    response = authenticated_client.post(
        "/api/v1/assets",
        json=payload,
        headers=csrf_headers,
    )
    assert response.status_code == 201, response.text
    asset_id = response.json().get("id")
    assert isinstance(asset_id, str) and asset_id != ""
    return asset_id


def test_asset_review_full_workflow_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """draft → pending → approved → reversed → pending → draft with logs."""
    suffix = uuid4().hex[:8]
    asset_id = _create_review_asset(
        db_session, authenticated_client, csrf_headers, suffix=suffix
    )

    submit = authenticated_client.post(
        f"/api/v1/assets/{asset_id}/submit-review", headers=csrf_headers
    )
    assert submit.status_code == 200, submit.text
    assert submit.json().get("review_status") == "pending"

    # A second submit from pending is an illegal transition.
    double_submit = authenticated_client.post(
        f"/api/v1/assets/{asset_id}/submit-review", headers=csrf_headers
    )
    assert double_submit.status_code == 400
    error = double_submit.json().get("error", {})
    assert error.get("code") == "OPERATION_NOT_ALLOWED"
    assert error.get("details", {}).get("reason") == (
        "asset_invalid_review_status_transition"
    )

    approve = authenticated_client.post(
        f"/api/v1/assets/{asset_id}/approve-review", headers=csrf_headers
    )
    assert approve.status_code == 200, approve.text
    approved = approve.json()
    assert approved["review_status"] == "approved"
    assert approved["reviewed_at"] is not None
    assert approved["review_by"]

    # Approved assets freeze business fields and deletion.
    blocked_update = authenticated_client.put(
        f"/api/v1/assets/{asset_id}",
        json={"usage_status": "自用", "updated_by": "e2e_test"},
        headers=csrf_headers,
    )
    assert blocked_update.status_code == 400
    assert (
        blocked_update.json().get("error", {}).get("code") == "OPERATION_NOT_ALLOWED"
    )
    blocked_delete = authenticated_client.delete(
        f"/api/v1/assets/{asset_id}", headers=csrf_headers
    )
    assert blocked_delete.status_code == 400

    reverse = authenticated_client.post(
        f"/api/v1/assets/{asset_id}/reverse-review",
        json={"reason": "e2e 反审核"},
        headers=csrf_headers,
    )
    assert reverse.status_code == 200, reverse.text
    reversed_asset = reverse.json()
    assert reversed_asset["review_status"] == "reversed"
    assert reversed_asset["review_reason"] == "e2e 反审核"

    resubmit = authenticated_client.post(
        f"/api/v1/assets/{asset_id}/resubmit-review", headers=csrf_headers
    )
    assert resubmit.status_code == 200, resubmit.text
    assert resubmit.json().get("review_status") == "pending"

    withdraw = authenticated_client.post(
        f"/api/v1/assets/{asset_id}/withdraw-review",
        json={"reason": "资料需要补充"},
        headers=csrf_headers,
    )
    assert withdraw.status_code == 200, withdraw.text
    assert withdraw.json().get("review_status") == "draft"

    # The review log records the full state-machine chain, latest first.
    logs_response = authenticated_client.get(f"/api/v1/assets/{asset_id}/review-logs")
    assert logs_response.status_code == 200, logs_response.text
    logs = logs_response.json()
    assert isinstance(logs, list) and len(logs) == 5
    expected_chain = [
        ("withdraw", "pending", "draft"),
        ("resubmit", "reversed", "pending"),
        ("reverse", "approved", "reversed"),
        ("approve", "pending", "approved"),
        ("submit", "draft", "pending"),
    ]
    for log, (action, from_status, to_status) in zip(logs, expected_chain):
        assert log["action"] == action
        assert log["from_status"] == from_status
        assert log["to_status"] == to_status
        assert log["operator"]
    reverse_log = next(log for log in logs if log["action"] == "reverse")
    assert reverse_log["reason"] == "e2e 反审核"


def test_asset_review_reject_flow_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Reject returns the asset to draft with the reason recorded."""
    suffix = uuid4().hex[:8]
    asset_id = _create_review_asset(
        db_session, authenticated_client, csrf_headers, suffix=suffix
    )

    submit = authenticated_client.post(
        f"/api/v1/assets/{asset_id}/submit-review", headers=csrf_headers
    )
    assert submit.status_code == 200

    # Blank rejection reasons are rejected by the service layer.
    blank_reject = authenticated_client.post(
        f"/api/v1/assets/{asset_id}/reject-review",
        json={"reason": "   "},
        headers=csrf_headers,
    )
    assert blank_reject.status_code == 422
    assert blank_reject.json().get("error", {}).get("code") == "VALIDATION_ERROR"

    reject = authenticated_client.post(
        f"/api/v1/assets/{asset_id}/reject-review",
        json={"reason": "审核后发现主数据有误"},
        headers=csrf_headers,
    )
    assert reject.status_code == 200, reject.text
    rejected = reject.json()
    assert rejected["review_status"] == "draft"
    assert rejected["review_reason"] == "审核后发现主数据有误"

    # Resubmit only applies to reversed assets, not draft ones.
    premature_resubmit = authenticated_client.post(
        f"/api/v1/assets/{asset_id}/resubmit-review", headers=csrf_headers
    )
    assert premature_resubmit.status_code == 400
    assert (
        premature_resubmit.json().get("error", {}).get("code")
        == "OPERATION_NOT_ALLOWED"
    )

    # A draft asset can be submitted again after the fix.
    resubmitted = authenticated_client.post(
        f"/api/v1/assets/{asset_id}/submit-review", headers=csrf_headers
    )
    assert resubmitted.status_code == 200
    assert resubmitted.json().get("review_status") == "pending"


def test_asset_batch_review_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Batch submit/approve transitions report per-item outcomes."""
    suffix = uuid4().hex[:8]
    asset_ids = [
        _create_review_asset(
            db_session, authenticated_client, csrf_headers, suffix=f"{suffix}{i}"
        )
        for i in range(3)
    ]
    missing_id = "00000000-0000-0000-0000-000000000000"

    batch_submit = authenticated_client.post(
        "/api/v1/assets/batch-submit-review",
        json={"asset_ids": [*asset_ids, missing_id]},
        headers=csrf_headers,
    )
    assert batch_submit.status_code == 200, batch_submit.text
    submit_result = batch_submit.json()
    assert submit_result["success_count"] == 3
    assert submit_result["failed_count"] == 1
    assert submit_result["total_count"] == 4
    assert set(submit_result["reviewed_assets"]) == set(asset_ids)
    assert len(submit_result["errors"]) == 1
    assert submit_result["errors"][0]["id"] == missing_id
    assert submit_result["errors"][0]["code"] == "NOT_FOUND"

    # Re-submitting already-pending assets is idempotent (counted as success).
    idempotent_submit = authenticated_client.post(
        "/api/v1/assets/batch-submit-review",
        json={"asset_ids": asset_ids[:1]},
        headers=csrf_headers,
    )
    assert idempotent_submit.status_code == 200
    assert idempotent_submit.json()["success_count"] == 1
    assert idempotent_submit.json()["failed_count"] == 0

    batch_approve = authenticated_client.post(
        "/api/v1/assets/batch-approve-review",
        json={"asset_ids": asset_ids[:2]},
        headers=csrf_headers,
    )
    assert batch_approve.status_code == 200, batch_approve.text
    assert batch_approve.json()["success_count"] == 2

    approved_detail = authenticated_client.get(f"/api/v1/assets/{asset_ids[1]}")
    assert approved_detail.status_code == 200
    assert approved_detail.json().get("review_status") == "approved"

    pending_detail = authenticated_client.get(f"/api/v1/assets/{asset_ids[2]}")
    assert pending_detail.status_code == 200
    assert pending_detail.json().get("review_status") == "pending"


def test_asset_review_requires_permission_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
    client: TestClient,
    create_test_user_factory,
) -> None:
    """A regular user without asset-update rights cannot drive the review."""
    suffix = uuid4().hex[:8]
    asset_id = _create_review_asset(
        db_session, authenticated_client, csrf_headers, suffix=suffix
    )

    create_test_user_factory(
        username="e2e_review_regular",
        email="e2e_review_regular@example.com",
        password="UserPass123!@#",
        full_name="E2E Review Regular",
        role="user",
    )

    # Re-login the shared client as the regular user (same TestClient);
    # clear the admin cookies first to avoid duplicate csrf_token cookies.
    client.cookies.clear()
    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "e2e_review_regular", "password": "UserPass123!@#"},
    )
    assert login.status_code == 200, login.text
    regular_csrf = login.cookies.get("csrf_token")
    assert regular_csrf

    denied = client.post(
        f"/api/v1/assets/{asset_id}/submit-review",
        headers={"X-CSRF-Token": regular_csrf},
    )
    assert denied.status_code == 403
    assert denied.json().get("error", {}).get("code") == "PERMISSION_DENIED"
