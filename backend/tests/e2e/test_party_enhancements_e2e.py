"""
End-to-end party enhancement tests (REQ-PTY-002 / REQ-PTY-003).

Covers batch import with per-item outcomes, contact management, the
lifecycle preview→commit protocol (deactivate/reactivate) with idempotency
and state-machine guards, and the party review-log trail.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.e2e


def _create_party(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    *,
    suffix: str,
    name: str,
) -> dict[str, object]:
    response = authenticated_client.post(
        "/api/v1/parties",
        json={"party_type": "legal_entity", "name": name},
        headers=csrf_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _approve_party(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    party_id: str,
) -> None:
    submit = authenticated_client.post(
        f"/api/v1/parties/{party_id}/submit-review", headers=csrf_headers
    )
    assert submit.status_code == 200, submit.text
    approve = authenticated_client.post(
        f"/api/v1/parties/{party_id}/approve-review", headers=csrf_headers
    )
    assert approve.status_code == 200, approve.text


def test_party_import_and_contacts_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Batch import reports per-item outcomes; contacts round-trip."""
    suffix = uuid4().hex[:8]
    import_response = authenticated_client.post(
        "/api/v1/parties/import",
        json={
            "items": [
                {"party_type": "legal_entity", "name": f"导入法人-{suffix}"},
                {
                    "party_type": "individual",
                    "name": f"导入自然人-{suffix}",
                    "identifier_type": "national_id",
                    "identifier_value": "310101199001011234",
                },
                # Same (type, name) as the first item: per-item duplicate.
                {"party_type": "legal_entity", "name": f"导入法人-{suffix}"},
            ]
        },
        headers=csrf_headers,
    )
    assert import_response.status_code == 200, import_response.text
    result = import_response.json()
    assert result["created_count"] == 2
    assert result["error_count"] == 1
    statuses = [item["status"] for item in result["items"]]
    assert statuses == ["created", "created", "error"]
    assert "主体名称重复" in result["items"][2]["message"]

    # Imported parties land as drafts with auto-generated codes.
    imported_party_id = result["items"][0]["party_id"]
    detail = authenticated_client.get(f"/api/v1/parties/{imported_party_id}")
    assert detail.status_code == 200
    imported = detail.json()
    assert imported["review_status"] == "draft"
    assert imported["status"] == "active"
    assert imported["code"].startswith("LE-")

    # The import is recorded on the review-log trail.
    logs = authenticated_client.get(f"/api/v1/parties/{imported_party_id}/review-logs")
    assert logs.status_code == 200
    log_list = logs.json()
    assert any(
        log["action"] == "import"
        and log["from_status"] == "none"
        and log["to_status"] == "draft"
        for log in log_list
    )

    # Empty import batches are rejected by the schema.
    empty_import = authenticated_client.post(
        "/api/v1/parties/import", json={"items": []}, headers=csrf_headers
    )
    assert empty_import.status_code == 422

    # Contacts: empty list, then create and read back.
    empty_contacts = authenticated_client.get(
        f"/api/v1/parties/{imported_party_id}/contacts"
    )
    assert empty_contacts.status_code == 200
    assert empty_contacts.json() == []

    created_contact = authenticated_client.post(
        f"/api/v1/parties/{imported_party_id}/contacts",
        json={
            "contact_name": f"联系人-{suffix}",
            "contact_phone": "13900001234",
            "position": "经理",
            "is_primary": True,
        },
        headers=csrf_headers,
    )
    assert created_contact.status_code == 200, created_contact.text
    contact = created_contact.json()
    assert contact["contact_name"] == f"联系人-{suffix}"
    assert contact["contact_phone"] == "13900001234"
    assert contact["is_primary"] is True

    contacts = authenticated_client.get(
        f"/api/v1/parties/{imported_party_id}/contacts"
    )
    assert contacts.status_code == 200
    assert len(contacts.json()) == 1

    # Contacts on unknown parties are a 404.
    missing_contacts = authenticated_client.get(
        f"/api/v1/parties/{uuid4()}/contacts"
    )
    assert missing_contacts.status_code == 404
    assert (
        missing_contacts.json().get("error", {}).get("code") == "RESOURCE_NOT_FOUND"
    )


def test_party_lifecycle_deactivate_reactivate_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """The preview→commit protocol guards the party lifecycle states."""
    suffix = uuid4().hex[:8]
    party = _create_party(
        authenticated_client, csrf_headers, suffix=suffix, name=f"停用主体-{suffix}"
    )
    party_id = party["id"]
    _approve_party(authenticated_client, csrf_headers, party_id)

    # Only approved parties can enter the lifecycle protocol.
    draft_party = _create_party(
        authenticated_client, csrf_headers, suffix=suffix, name=f"草稿主体-{suffix}"
    )
    not_approved = authenticated_client.post(
        f"/api/v1/parties/{draft_party['id']}/status/preview",
        json={"operation": "deactivate"},
        headers=csrf_headers,
    )
    assert not_approved.status_code == 400
    not_approved_error = not_approved.json().get("error", {})
    assert not_approved_error.get("code") == "OPERATION_NOT_ALLOWED"
    assert not_approved_error.get("details", {}).get("reason") == (
        "party_lifecycle_review_not_approved"
    )

    preview = authenticated_client.post(
        f"/api/v1/parties/{party_id}/status/preview",
        json={"operation": "deactivate"},
        headers=csrf_headers,
    )
    assert preview.status_code == 200, preview.text
    preview_payload = preview.json()
    assert preview_payload["before_state"]["status"] == "active"
    assert preview_payload["after_state"]["status"] == "inactive"
    assert preview_payload["after_state"]["available_for_new_references"] is False
    preview_token = preview_payload["preview_token"]

    # Unknown operations are rejected by the schema enum.
    invalid_operation = authenticated_client.post(
        f"/api/v1/parties/{party_id}/status/preview",
        json={"operation": "terminate"},
        headers=csrf_headers,
    )
    assert invalid_operation.status_code == 422
    bad_token = authenticated_client.post(
        f"/api/v1/parties/{party_id}/deactivate",
        json={
            "preview_token": "not-a-real-token",
            "reason": "坏令牌",
            "idempotency_key": f"e2e-bad-{suffix}",
        },
        headers=csrf_headers,
    )
    assert bad_token.status_code == 409

    commit = authenticated_client.post(
        f"/api/v1/parties/{party_id}/deactivate",
        json={
            "preview_token": preview_token,
            "reason": "e2e 停用主体",
            "idempotency_key": f"e2e-deact-{suffix}",
        },
        headers=csrf_headers,
    )
    assert commit.status_code == 200, commit.text
    commit_payload = commit.json()
    assert commit_payload["party"]["status"] == "inactive"
    assert commit_payload["idempotent"] is False

    # Idempotent replay of the same commit key.
    replay = authenticated_client.post(
        f"/api/v1/parties/{party_id}/deactivate",
        json={
            "preview_token": preview_token,
            "reason": "e2e 停用主体",
            "idempotency_key": f"e2e-deact-{suffix}",
        },
        headers=csrf_headers,
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotent"] is True

    # The status filters separate inactive from active parties.
    inactive_list = authenticated_client.get(
        "/api/v1/parties", params={"status": "inactive", "search": f"停用主体-{suffix}"}
    )
    assert inactive_list.status_code == 200
    inactive_items = (
        inactive_list.json().get("items", [])
        if isinstance(inactive_list.json(), dict)
        else inactive_list.json()
    )
    assert any(p.get("id") == party_id for p in inactive_items)

    # Reactivate through the same protocol.
    reactivate_preview = authenticated_client.post(
        f"/api/v1/parties/{party_id}/status/preview",
        json={"operation": "reactivate"},
        headers=csrf_headers,
    )
    assert reactivate_preview.status_code == 200, reactivate_preview.text
    reactivate = authenticated_client.post(
        f"/api/v1/parties/{party_id}/reactivate",
        json={
            "preview_token": reactivate_preview.json()["preview_token"],
            "reason": "e2e 恢复主体",
            "idempotency_key": f"e2e-react-{suffix}",
        },
        headers=csrf_headers,
    )
    assert reactivate.status_code == 200, reactivate.text
    assert reactivate.json()["party"]["status"] == "active"

    # Reactivating an already-active party is an invalid transition.
    active_again_preview = authenticated_client.post(
        f"/api/v1/parties/{party_id}/status/preview",
        json={"operation": "reactivate"},
        headers=csrf_headers,
    )
    assert active_again_preview.status_code == 400
    assert (
        active_again_preview.json().get("error", {}).get("details", {}).get("reason")
        == "party_lifecycle_reactivate_invalid_status"
    )

    # The lifecycle actions are recorded on the review logs.
    logs = authenticated_client.get(f"/api/v1/parties/{party_id}/review-logs")
    assert logs.status_code == 200
    actions = {log["action"] for log in logs.json()}
    assert {"deactivate", "reactivate"} <= actions
    deactivate_log = next(
        log for log in logs.json() if log["action"] == "deactivate"
    )
    assert deactivate_log["from_status"] == "active"
    assert deactivate_log["to_status"] == "inactive"
    assert deactivate_log["reason"] == "e2e 停用主体"

def test_party_creation_requires_csrf_header_e2e(authenticated_client) -> None:
    """E2E Admission Standard #2: mutations need the CSRF negative branch."""
    response = authenticated_client.post(
        "/api/v1/parties",
        json={"party_type": "legal_entity", "name": "CSRF守卫主体"},
    )
    assert response.status_code == 403
