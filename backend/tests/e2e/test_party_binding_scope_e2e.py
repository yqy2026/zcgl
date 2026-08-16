"""
End-to-end user party-binding scope tests (REQ-AUTH-002).

Covers the preview→commit change protocol for user party bindings: scope
diffs on preview, idempotent commits, one-shot preview tokens, binding
closure, and the batch preview/commit path over multiple users.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.e2e.factories import create_approved_legal_party

pytestmark = pytest.mark.e2e


def _create_regular_user(create_test_user_factory, suffix: str) -> str:
    user = create_test_user_factory(
        username=f"e2e_bind_{suffix}",
        email=f"e2e_bind_{suffix}@example.com",
        password="UserPass123!@#",
        full_name=f"E2E绑定用户-{suffix}",
        role="user",
    )
    return str(user.id)


def test_single_user_party_binding_preview_commit_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
    create_test_user_factory,
) -> None:
    """Preview shows the scope diff; commit is idempotent and one-shot."""
    suffix = uuid4().hex[:8]
    user_id = _create_regular_user(create_test_user_factory, suffix)
    party = create_approved_legal_party(
        db_session, suffix=suffix, name=f"绑定主体-{suffix}"
    )

    preview = authenticated_client.post(
        f"/api/v1/users/{user_id}/party-bindings/preview",
        json={"operation": "create", "party_id": party.id, "relation_type": "owner"},
        headers=csrf_headers,
    )
    assert preview.status_code == 200, preview.text
    preview_payload = preview.json()
    before_scope = preview_payload["before_scope"]
    after_scope = preview_payload["after_scope"]
    assert before_scope["source"] == "none"
    assert after_scope["source"] == "explicit"
    assert party.id in after_scope["owner_party_ids"]
    assert preview_payload["impact"]["scope_changed"] is True
    preview_token = preview_payload["preview_token"]
    assert preview_token

    commit = authenticated_client.post(
        f"/api/v1/users/{user_id}/party-bindings/commit",
        json={
            "preview_token": preview_token,
            "reason": "e2e 绑定产权方视角",
            "idempotency_key": f"e2e-bind-{suffix}",
        },
        headers=csrf_headers,
    )
    assert commit.status_code == 200, commit.text
    commit_payload = commit.json()
    assert commit_payload["idempotent"] is False
    binding = commit_payload["binding"]
    assert binding["relation_type"] == "owner"
    assert binding["party_id"] == party.id

    # Replaying the same commit key is idempotent.
    replay = authenticated_client.post(
        f"/api/v1/users/{user_id}/party-bindings/commit",
        json={
            "preview_token": preview_token,
            "reason": "e2e 绑定产权方视角",
            "idempotency_key": f"e2e-bind-{suffix}",
        },
        headers=csrf_headers,
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotent"] is True

    # The consumed token cannot back a different idempotency key.
    stale = authenticated_client.post(
        f"/api/v1/users/{user_id}/party-bindings/commit",
        json={
            "preview_token": preview_token,
            "reason": "复用已消费令牌",
            "idempotency_key": f"e2e-bind-other-{suffix}",
        },
        headers=csrf_headers,
    )
    assert stale.status_code == 409
    assert (
        stale.json().get("error", {}).get("code") == "SCOPE_CHANGE_PREVIEW_STALE"
    )

    # The binding is listed for the user.
    listing = authenticated_client.get(
        f"/api/v1/users/{user_id}/party-bindings"
    )
    assert listing.status_code == 200, listing.text
    bindings = listing.json()
    assert any(b["party_id"] == party.id for b in bindings)

    # Closing the binding empties the explicit scope.
    close_preview = authenticated_client.post(
        f"/api/v1/users/{user_id}/party-bindings/preview",
        json={"operation": "close", "binding_id": binding["id"]},
        headers=csrf_headers,
    )
    assert close_preview.status_code == 200, close_preview.text
    close_payload = close_preview.json()
    assert close_payload["impact"]["after_current_binding_count"] == 0
    assert close_payload["after_scope"]["source"] == "none"

    close_commit = authenticated_client.post(
        f"/api/v1/users/{user_id}/party-bindings/commit",
        json={
            "preview_token": close_payload["preview_token"],
            "reason": "e2e 关闭绑定",
            "idempotency_key": f"e2e-close-{suffix}",
        },
        headers=csrf_headers,
    )
    assert close_commit.status_code == 200, close_commit.text
    closed_binding = close_commit.json()["binding"]
    assert closed_binding["valid_to"] is not None

    # Guards: unknown user is a 404; single-item batches are rejected.
    unknown_user = authenticated_client.post(
        f"/api/v1/users/{uuid4()}/party-bindings/preview",
        json={"operation": "create", "party_id": party.id, "relation_type": "owner"},
        headers=csrf_headers,
    )
    assert unknown_user.status_code == 404

    single_item = authenticated_client.post(
        "/api/v1/users/party-bindings/batch/preview",
        json={
            "items": [
                {
                    "user_id": user_id,
                    "operation": "create",
                    "party_id": party.id,
                    "relation_type": "owner",
                }
            ]
        },
        headers=csrf_headers,
    )
    assert single_item.status_code == 422


def test_batch_party_binding_preview_commit_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
    create_test_user_factory,
) -> None:
    """Batch preview reports both users' scope diffs; commit lands both."""
    suffix = uuid4().hex[:8]
    user_a = _create_regular_user(create_test_user_factory, f"{suffix}a")
    user_b = _create_regular_user(create_test_user_factory, f"{suffix}b")
    party_a = create_approved_legal_party(
        db_session, suffix=f"{suffix}a", name=f"批量主体A-{suffix}"
    )
    party_b = create_approved_legal_party(
        db_session, suffix=f"{suffix}b", name=f"批量主体B-{suffix}"
    )

    preview = authenticated_client.post(
        "/api/v1/users/party-bindings/batch/preview",
        json={
            "items": [
                {
                    "user_id": user_a,
                    "operation": "create",
                    "party_id": party_a.id,
                    "relation_type": "owner",
                },
                {
                    "user_id": user_b,
                    "operation": "create",
                    "party_id": party_b.id,
                    "relation_type": "manager",
                },
            ]
        },
        headers=csrf_headers,
    )
    assert preview.status_code == 200, preview.text
    preview_payload = preview.json()
    assert len(preview_payload["items"]) == 2
    assert preview_payload["impact"]["user_count"] == 2
    for item in preview_payload["items"]:
        assert item["after_scope"]["source"] == "explicit"

    commit = authenticated_client.post(
        "/api/v1/users/party-bindings/batch/commit",
        json={
            "preview_token": preview_payload["preview_token"],
            "reason": "e2e 批量绑定两个用户",
            "idempotency_key": f"e2e-batch-{suffix}",
        },
        headers=csrf_headers,
    )
    assert commit.status_code == 200, commit.text
    assert commit.json()["idempotent"] is False

    replay = authenticated_client.post(
        "/api/v1/users/party-bindings/batch/commit",
        json={
            "preview_token": preview_payload["preview_token"],
            "reason": "e2e 批量绑定两个用户",
            "idempotency_key": f"e2e-batch-{suffix}",
        },
        headers=csrf_headers,
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotent"] is True

    bindings_a = authenticated_client.get(
        f"/api/v1/users/{user_a}/party-bindings"
    ).json()
    assert any(
        b["party_id"] == party_a.id and b["relation_type"] == "owner"
        for b in bindings_a
    )
    bindings_b = authenticated_client.get(
        f"/api/v1/users/{user_b}/party-bindings"
    ).json()
    assert any(
        b["party_id"] == party_b.id and b["relation_type"] == "manager"
        for b in bindings_b
    )

def test_party_binding_preview_requires_csrf_header_e2e(
    authenticated_client,
) -> None:
    """E2E Admission Standard #2: mutations need the CSRF negative branch."""
    missing_user_id = uuid4()
    response = authenticated_client.post(
        f"/api/v1/users/{missing_user_id}/party-bindings/preview",
        json={
            "operation": "create",
            "party_id": str(missing_user_id),
            "relation_type": "owner",
        },
    )
    assert response.status_code == 403
