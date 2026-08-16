"""
End-to-end user lifecycle tests (REQ-AUTH-001 / REQ-SYS-001).

Covers user management through the public API: creation (inactive by
default) with activation, lock/unlock with session and login effects,
password change with global session revocation, admin password reset,
deactivate/activate, deletion, and session revocation blocking refresh.

The admin and the managed user share one TestClient; sessions are swapped
by saving/restoring the cookie jar (a second TestClient on the same app
deadlocks on Windows event-loop teardown).
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.e2e.session_helpers import (
    capture_session,
    login,
    restore_session,
)

pytestmark = pytest.mark.e2e




def _ensure_organization(db_session) -> str:
    """Return an active root organization id (activation requires the chain).

    The organization must resolve to an effective Party scope, i.e. carry a
    represented_party_id pointing at an approved party.
    """
    from src.models.organization import Organization
    from tests.e2e.factories import create_approved_legal_party

    organization = (
        db_session.query(Organization)
        .filter(Organization.is_deleted.is_(False), Organization.status == "active")
        .first()
    )
    if organization is None:
        organization = Organization(
            name="E2E用户生命周期组织",
            code=f"E2E-UL-{uuid4().hex[:6]}",
            level=1,
            sort_order=0,
            type="总部",
            status="active",
            path="/",
            is_deleted=False,
            created_by="e2e-fixture",
            updated_by="e2e-fixture",
        )
        db_session.add(organization)
        db_session.flush()
    if not organization.represented_party_id:
        party = create_approved_legal_party(
            db_session, suffix=uuid4().hex[:6], name="E2E组织代表主体"
        )
        organization.represented_party_id = party.id
        organization.represented_party_perspective = "owner"
    db_session.commit()
    db_session.refresh(organization)
    return organization.id


def test_user_lifecycle_management_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Create → activate → lock → unlock → passwords → deactivate → delete."""
    suffix = uuid4().hex[:8]
    admin_session = capture_session(authenticated_client)

    # API-created users start inactive (secure default) until activated.
    created = authenticated_client.post(
        "/api/v1/auth/users",
        json={
            "username": f"e2e_user_{suffix}",
            "phone": f"138{uuid4().int % 10**8:08d}",
            "full_name": f"E2E用户-{suffix}",
            "password": "ValidPass123!",
        },
        headers=csrf_headers,
    )
    assert created.status_code == 200, created.text
    user = created.json()
    user_id = user["id"]
    assert user["username"] == f"e2e_user_{suffix}"
    assert user["is_active"] is False

    # Activation requires an active organization chain: transfer first.
    organization_id = _ensure_organization(db_session)
    org_preview = authenticated_client.post(
        f"/api/v1/auth/users/{user_id}/organization/preview",
        json={"organization_id": organization_id},
        headers=csrf_headers,
    )
    assert org_preview.status_code == 200, org_preview.text
    org_commit = authenticated_client.put(
        f"/api/v1/auth/users/{user_id}/organization",
        json={
            "preview_token": org_preview.json()["preview_token"],
            "reason": "e2e 激活前挂组织",
            "idempotency_key": f"e2e-org-{suffix}",
        },
        headers=csrf_headers,
    )
    assert org_commit.status_code == 200, org_commit.text

    activate = authenticated_client.post(
        f"/api/v1/auth/users/{user_id}/activate", headers=csrf_headers
    )
    assert activate.status_code == 200, activate.text

    # The user can read their own record.
    login(authenticated_client, f"e2e_user_{suffix}", "ValidPass123!")
    user_session = capture_session(authenticated_client)
    user_headers = restore_session(authenticated_client, user_session)
    own_detail = authenticated_client.get(f"/api/v1/auth/users/{user_id}")
    assert own_detail.status_code == 200, own_detail.text
    assert own_detail.json()["id"] == user_id

    # Admin profile update round-trips.
    admin_headers = restore_session(authenticated_client, admin_session)
    updated = authenticated_client.put(
        f"/api/v1/auth/users/{user_id}",
        json={"full_name": f"E2E用户改-{suffix}"},
        headers=admin_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["full_name"] == f"E2E用户改-{suffix}"

    # Locking the account blocks both the live session and login (a
    # flag-only admin lock is a permanent lock).
    lock = authenticated_client.post(
        f"/api/v1/auth/users/{user_id}/lock", headers=admin_headers
    )
    assert lock.status_code == 200, lock.text
    user_headers = restore_session(authenticated_client, user_session)
    locked_me = authenticated_client.get("/api/v1/auth/me")
    assert locked_me.status_code == 401
    locked_login = authenticated_client.post(
        "/api/v1/auth/login",
        json={"identifier": f"e2e_user_{suffix}", "password": "ValidPass123!"},
    )
    assert locked_login.status_code == 400
    assert locked_login.json().get("error", {}).get("code") == "INVALID_REQUEST"

    admin_headers = restore_session(authenticated_client, admin_session)
    unlock = authenticated_client.post(
        f"/api/v1/auth/users/{user_id}/unlock", headers=admin_headers
    )
    assert unlock.status_code == 200, unlock.text

    # Changing the password revokes every existing session of the user.
    login(authenticated_client, f"e2e_user_{suffix}", "ValidPass123!")
    user_session = capture_session(authenticated_client)
    user_headers = restore_session(authenticated_client, user_session)
    change = authenticated_client.post(
        f"/api/v1/auth/users/{user_id}/change-password",
        json={"current_password": "ValidPass123!", "new_password": "NewPass456!"},
        headers=user_headers,
    )
    assert change.status_code == 200, change.text
    revoked_me = authenticated_client.get("/api/v1/auth/me")
    assert revoked_me.status_code == 401
    old_password_login = authenticated_client.post(
        "/api/v1/auth/login",
        json={"identifier": f"e2e_user_{suffix}", "password": "ValidPass123!"},
    )
    assert old_password_login.status_code == 401
    login(authenticated_client, f"e2e_user_{suffix}", "NewPass456!")

    # Admin reset (explicit new password).
    admin_headers = restore_session(authenticated_client, admin_session)
    reset = authenticated_client.post(
        f"/api/v1/auth/users/{user_id}/reset-password",
        json={"new_password": "ResetPass789!", "reason": "e2e 重置"},
        headers=admin_headers,
    )
    assert reset.status_code == 200, reset.text
    login(authenticated_client, f"e2e_user_{suffix}", "ResetPass789!")
    user_session = capture_session(authenticated_client)

    # Deactivation immediately invalidates the session and login.
    admin_headers = restore_session(authenticated_client, admin_session)
    deactivate = authenticated_client.post(
        f"/api/v1/auth/users/{user_id}/deactivate", headers=admin_headers
    )
    assert deactivate.status_code == 200, deactivate.text
    user_headers = restore_session(authenticated_client, user_session)
    deactivated_me = authenticated_client.get("/api/v1/auth/me")
    assert deactivated_me.status_code == 401
    deactivated_login = authenticated_client.post(
        "/api/v1/auth/login",
        json={"identifier": f"e2e_user_{suffix}", "password": "ResetPass789!"},
    )
    assert deactivated_login.status_code in (400, 401)

    admin_headers = restore_session(authenticated_client, admin_session)
    activate_again = authenticated_client.post(
        f"/api/v1/auth/users/{user_id}/activate", headers=admin_headers
    )
    assert activate_again.status_code == 200, activate_again.text
    reactivated_login = authenticated_client.post(
        "/api/v1/auth/login",
        json={"identifier": f"e2e_user_{suffix}", "password": "ResetPass789!"},
    )
    assert reactivated_login.status_code == 200, reactivated_login.text

    # Weak passwords are rejected by the schema; deletion removes the record.
    admin_headers = restore_session(authenticated_client, admin_session)
    weak_password = authenticated_client.post(
        "/api/v1/auth/users",
        json={
            "username": f"e2e_weak_{suffix}",
            "phone": f"139{uuid4().int % 10**8:08d}",
            "full_name": f"E2E弱密码-{suffix}",
            "password": "weakpass",
        },
        headers=admin_headers,
    )
    assert weak_password.status_code == 422

    # DELETE is the soft path (same implementation as deactivate): the
    # record stays, but the account is inactive.
    deleted = authenticated_client.delete(
        f"/api/v1/auth/users/{user_id}", headers=admin_headers
    )
    assert deleted.status_code == 200, deleted.text
    detail_after_delete = authenticated_client.get(f"/api/v1/auth/users/{user_id}")
    assert detail_after_delete.status_code == 200
    assert detail_after_delete.json()["is_active"] is False

    # Unknown user ids are a clean 404.
    missing_detail = authenticated_client.get(
        f"/api/v1/auth/users/{uuid4()}"
    )
    assert missing_detail.status_code == 404
    assert (
        missing_detail.json().get("error", {}).get("code") == "RESOURCE_NOT_FOUND"
    )


def test_user_session_revocation_blocks_refresh_e2e(
    authenticated_client: TestClient,
    db_session,
    create_test_user_factory,
) -> None:
    """Revoking a session blacklists its refresh token."""
    suffix = uuid4().hex[:8]
    admin_session = capture_session(authenticated_client)
    create_test_user_factory(
        username=f"e2e_sess_{suffix}",
        email=f"e2e_sess_{suffix}@example.com",
        password="UserPass123!@#",
        full_name=f"E2E会话-{suffix}",
        role="user",
    )
    user_headers = login(
        authenticated_client, f"e2e_sess_{suffix}", "UserPass123!@#"
    )
    user_session = capture_session(authenticated_client)

    sessions = authenticated_client.get("/api/v1/auth/sessions")
    assert sessions.status_code == 200, sessions.text
    session_list = sessions.json()
    assert isinstance(session_list, list) and len(session_list) >= 1
    session_id = session_list[0]["id"]
    assert session_list[0]["is_active"] is True

    # Unknown session ids are a 404 (no existence leak) for permitted callers.
    admin_headers = restore_session(authenticated_client, admin_session)
    foreign_revoke = authenticated_client.delete(
        f"/api/v1/auth/sessions/{uuid4()}", headers=admin_headers
    )
    assert foreign_revoke.status_code == 404

    user_headers = restore_session(authenticated_client, user_session)
    revoke = authenticated_client.delete(
        f"/api/v1/auth/sessions/{session_id}", headers=user_headers
    )
    assert revoke.status_code == 200, revoke.text

    refresh = authenticated_client.post("/api/v1/auth/refresh", headers=user_headers)
    assert refresh.status_code == 401, refresh.text

def test_user_creation_requires_csrf_header_e2e(
    authenticated_client,
) -> None:
    """E2E Admission Standard #2: mutations need the CSRF negative branch."""
    response = authenticated_client.post(
        "/api/v1/auth/users",
        json={
            "username": "csrf_guard",
            "phone": "13800009999",
            "full_name": "CSRF Guard",
            "password": "ValidPass123!",
        },
    )
    assert response.status_code == 403
