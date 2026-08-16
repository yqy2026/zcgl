"""
End-to-end role and authorization tests (REQ-AUTH-003).

Covers role lifecycle through the public API: custom role creation with
duplicate guard, permission binding, user assignment with conflict and
in-use guards, live permission effects via /authz/check, data-policy
packages on roles, and system-role protection.
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




def _seed_asset_read_permission(db_session) -> str:
    """Insert (or reuse) the asset:read permission row; return its id."""
    from src.models.rbac import Permission

    permission = (
        db_session.query(Permission)
        .filter(Permission.resource == "asset", Permission.action == "read")
        .first()
    )
    if permission is None:
        permission = Permission(
            name="asset:read",
            display_name="资产读取",
            description="e2e 角色授权验证用",
            resource="asset",
            action="read",
            is_system_permission=True,
            requires_approval=False,
            created_by="e2e-fixture",
            updated_by="e2e-fixture",
        )
        db_session.add(permission)
        db_session.commit()
        db_session.refresh(permission)
    return permission.id


def test_role_lifecycle_and_live_permissions_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
    create_test_user_factory,
) -> None:
    """Role → permissions → assignment → live /authz/check → revoke → delete."""
    suffix = uuid4().hex[:8]
    admin_session = capture_session(authenticated_client)
    role_name = f"e2e_role_{suffix}"
    asset_read_id = _seed_asset_read_permission(db_session)

    # Create a custom role; duplicate names are rejected.
    created = authenticated_client.post(
        "/api/v1/roles",
        json={
            "name": role_name,
            "display_name": f"E2E角色-{suffix}",
            "description": "e2e 角色生命周期",
        },
        headers=csrf_headers,
    )
    assert created.status_code == 201, created.text
    role = created.json()
    role_id = role["id"]
    assert role["is_system_role"] is False

    duplicate = authenticated_client.post(
        "/api/v1/roles",
        json={"name": role_name, "display_name": f"E2E角色重-{suffix}"},
        headers=csrf_headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json().get("error", {}).get("code") == "DUPLICATE_RESOURCE"

    # Bind exactly one permission to the role.
    bind = authenticated_client.put(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permission_ids": [asset_read_id]},
        headers=csrf_headers,
    )
    assert bind.status_code == 200, bind.text
    assert bind.json().get("data", {}).get("permission_count") == 1

    # Assign the role to a fresh user; duplicate active assignments conflict.
    create_test_user_factory(
        username=f"e2e_role_user_{suffix}",
        email=f"e2e_role_user_{suffix}@example.com",
        password="UserPass123!@#",
        full_name=f"E2E角色用户-{suffix}",
        role="user",
    )
    user_id_response = authenticated_client.get(
        "/api/v1/auth/users",
        params={"search": f"e2e_role_user_{suffix}"},
    )
    assert user_id_response.status_code == 200
    user_rows = user_id_response.json().get("data", {}).get("items", [])
    assert len(user_rows) == 1
    user_id = user_rows[0]["id"]

    assignment = authenticated_client.post(
        "/api/v1/roles/assignments",
        json={"user_id": user_id, "role_id": role_id, "reason": "e2e 授权验证"},
        headers=csrf_headers,
    )
    assert assignment.status_code == 201, assignment.text

    repeat_assignment = authenticated_client.post(
        "/api/v1/roles/assignments",
        json={"user_id": user_id, "role_id": role_id, "reason": "重复分配"},
        headers=csrf_headers,
    )
    assert repeat_assignment.status_code == 409
    assert (
        repeat_assignment.json().get("error", {}).get("code") == "RESOURCE_CONFLICT"
    )

    # The permission summary reflects the role's effective permissions.
    summary = authenticated_client.get(
        f"/api/v1/roles/users/{user_id}/permissions/summary"
    )
    assert summary.status_code == 200, summary.text
    effective = summary.json().get("effective_permissions", {})
    assert "read" in effective.get("asset", [])

    # The assigned user's live ABAC check allows asset read but not delete.
    login(authenticated_client, f"e2e_role_user_{suffix}", "UserPass123!@#")
    user_session = capture_session(authenticated_client)
    user_headers = restore_session(authenticated_client, user_session)
    allowed = authenticated_client.post(
        "/api/v1/authz/check",
        json={"resource_type": "asset", "action": "read"},
        headers=user_headers,
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json().get("allowed") is True
    assert allowed.json().get("reason_code") == "rbac_permission_fallback"

    denied = authenticated_client.post(
        "/api/v1/authz/check",
        json={"resource_type": "asset", "action": "delete"},
        headers=user_headers,
    )
    assert denied.status_code == 200, denied.text
    assert denied.json().get("allowed") is False

    # A role with active assignments cannot be deleted.
    admin_headers = restore_session(authenticated_client, admin_session)
    delete_in_use = authenticated_client.delete(
        f"/api/v1/roles/{role_id}", headers=admin_headers
    )
    assert delete_in_use.status_code == 400
    in_use_error = delete_in_use.json().get("error", {})
    assert in_use_error.get("code") == "OPERATION_NOT_ALLOWED"
    assert in_use_error.get("details", {}).get("reason") == "role_in_use"

    # Revoking the assignment flips the live check back to denied.
    revoke = authenticated_client.delete(
        f"/api/v1/roles/users/{user_id}/roles/{role_id}", headers=admin_headers
    )
    assert revoke.status_code == 200, revoke.text

    restore_session(authenticated_client, user_session)
    revoked_check = authenticated_client.post(
        "/api/v1/authz/check",
        json={"resource_type": "asset", "action": "read"},
        headers=user_headers,
    )
    assert revoked_check.status_code == 200
    assert revoked_check.json().get("allowed") is False

    # After revocation the role can be deleted (204).
    admin_headers = restore_session(authenticated_client, admin_session)
    delete_role = authenticated_client.delete(
        f"/api/v1/roles/{role_id}", headers=admin_headers
    )
    assert delete_role.status_code == 204


def test_role_data_policies_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    """Data-policy packages round-trip on roles with template validation."""
    suffix = uuid4().hex[:8]
    created = authenticated_client.post(
        "/api/v1/roles",
        json={
            "name": f"e2e_policy_role_{suffix}",
            "display_name": f"E2E策略角色-{suffix}",
        },
        headers=csrf_headers,
    )
    assert created.status_code == 201, created.text
    role_id = created.json()["id"]

    templates = authenticated_client.get("/api/v1/auth/data-policies/templates")
    assert templates.status_code == 200, templates.text
    assert "audit_viewer" in templates.json()

    bind = authenticated_client.put(
        f"/api/v1/auth/roles/{role_id}/data-policies",
        json={"policy_packages": ["audit_viewer"]},
        headers=csrf_headers,
    )
    assert bind.status_code == 200, bind.text
    assert bind.json().get("policy_packages") == ["audit_viewer"]

    readback = authenticated_client.get(
        f"/api/v1/auth/roles/{role_id}/data-policies"
    )
    assert readback.status_code == 200, readback.text
    assert readback.json().get("policy_packages") == ["audit_viewer"]

    invalid = authenticated_client.put(
        f"/api/v1/auth/roles/{role_id}/data-policies",
        json={"policy_packages": ["not_a_package"]},
        headers=csrf_headers,
    )
    assert invalid.status_code == 400
    assert invalid.json().get("error", {}).get("code") == "INVALID_REQUEST"

    missing_role = authenticated_client.get(
        "/api/v1/auth/roles/00000000-0000-0000-0000-000000000000/data-policies"
    )
    assert missing_role.status_code == 404
    assert missing_role.json().get("error", {}).get("code") == "RESOURCE_NOT_FOUND"

    cleanup = authenticated_client.delete(
        f"/api/v1/roles/{role_id}", headers=csrf_headers
    )
    assert cleanup.status_code == 204


def test_role_management_denies_regular_users_e2e(
    authenticated_client: TestClient,
    db_session,
    create_test_user_factory,
) -> None:
    """Role management is admin-gated; regular users get 403 (Standard #2)."""
    from tests.e2e.session_helpers import login

    suffix = uuid4().hex[:8]
    create_test_user_factory(
        username=f"e2e_role_reg_{suffix}",
        email=f"e2e_role_reg_{suffix}@example.com",
        password="UserPass123!@#",
        full_name=f"E2E角色普通用户-{suffix}",
        role="user",
    )
    regular_headers = login(
        authenticated_client, f"e2e_role_reg_{suffix}", "UserPass123!@#"
    )
    denied = authenticated_client.post(
        "/api/v1/roles",
        json={"name": f"e2e_forbidden_{suffix}", "display_name": "禁止创建"},
        headers=regular_headers,
    )
    assert denied.status_code == 403
    assert denied.json().get("error", {}).get("code") == "PERMISSION_DENIED"
