"""
Party API integration tests with real DB/auth flow.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _get_auth_headers(client: TestClient, admin_user) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": admin_user.username, "password": "Admin123!@#"},
    )
    assert response.status_code == 200
    csrf_token = response.cookies.get("csrf_token")
    assert csrf_token is not None
    return {"X-CSRF-Token": csrf_token}


@pytest.mark.integration
def test_delete_party_should_be_blocked_when_referenced_by_project(
    client: TestClient,
    db_session: Session,
    test_data: dict[str, object],
) -> None:
    from src.models.party import Party, PartyType
    from src.models.project import Project

    admin_user = test_data["admin"]
    headers = _get_auth_headers(client, admin_user)
    suffix = uuid.uuid4().hex[:8]

    party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Party Delete Guard {suffix}",
        code=f"PTY-DEL-{suffix}",
        external_ref=f"PTY-DEL-EXT-{suffix}",
        status="active",
    )
    db_session.add(party)
    db_session.flush()

    project = Project(
        project_name=f"Party Delete Guard Project {suffix}",
        project_code=f"PRJ-{suffix.upper()}-{uuid.uuid4().int % 1000000:06d}",
        status="planning",
        manager_party_id=party.id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(party)

    response = client.delete(f"/api/v1/parties/{party.id}", headers=headers)

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "OPERATION_NOT_ALLOWED"
    assert "项目引用" in payload["error"]["message"]

    detail_response = client.get(f"/api/v1/parties/{party.id}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == party.id


@pytest.mark.integration
def test_selected_view_headers_should_narrow_party_results(
    client: TestClient,
    db_session: Session,
    test_data: dict[str, object],
) -> None:
    from src.models.abac import ABACPolicy, ABACPolicyRule, ABACRolePolicy
    from src.models.auth import User
    from src.models.party import Party, PartyType
    from src.models.rbac import Role, UserRoleAssignment
    from src.models.user_party_binding import RelationType, UserPartyBinding
    from src.services.core.password_service import PasswordService

    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)

    party_a = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Selected Party A {suffix}",
        code=f"SPARTY-A-{suffix}",
        external_ref=f"SPARTY-A-EXT-{suffix}",
        status="active",
    )
    party_b = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Selected Party B {suffix}",
        code=f"SPARTY-B-{suffix}",
        external_ref=f"SPARTY-B-EXT-{suffix}",
        status="active",
    )
    db_session.add_all([party_a, party_b])
    db_session.flush()

    organization_id = str(getattr(test_data["organization"], "id"))  # type: ignore[index]
    user = User(
        username=f"party_selected_view_user_{suffix}",
        email=f"party_selected_view_user_{suffix}@example.com",
        phone=f"138{uuid.uuid4().int % 10**8:08d}",
        full_name="Party Selected View User",
        password_hash=password_hash,
        is_active=True,
        default_organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add(user)
    db_session.flush()

    db_session.add_all(
        [
            UserPartyBinding(
                user_id=user.id,
                party_id=party_a.id,
                relation_type=RelationType.OWNER,
                is_primary=True,
            ),
            UserPartyBinding(
                user_id=user.id,
                party_id=party_b.id,
                relation_type=RelationType.OWNER,
                is_primary=False,
            ),
        ]
    )

    role = Role(
        name=f"vis_party_reader_{suffix}",
        display_name=f"PR{suffix[:6]}",
        is_system_role=False,
        is_active=True,
        created_by="integration_test",
        updated_by="integration_test",
    )
    policy = ABACPolicy(
        name=f"vis_party_read_policy_{suffix}",
        effect="allow",
        priority=100,
        enabled=True,
    )
    policy.rules.append(
        ABACPolicyRule(
            resource_type="party",
            action="read",
            condition_expr={"==": [1, 1]},
            field_mask=None,
        )
    )
    db_session.add_all([role, policy])
    db_session.flush()
    db_session.add(ABACRolePolicy(role_id=role.id, policy_id=policy.id, enabled=True))
    db_session.add(
        UserRoleAssignment(
            user_id=user.id,
            role_id=role.id,
            assigned_by="integration_test",
            is_active=True,
        )
    )
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={"identifier": user.username, "password": password},
    )
    assert login_response.status_code == 200

    base_response = client.get("/api/v1/parties")
    assert base_response.status_code == 200
    assert {item["id"] for item in base_response.json()} == {party_a.id, party_b.id}

    narrowed_response = client.get(
        "/api/v1/parties",
        headers={
            "X-View-Perspective": "owner",
            "X-View-Party-Id": party_a.id,
        },
    )
    assert narrowed_response.status_code == 200
    assert {item["id"] for item in narrowed_response.json()} == {party_a.id}

    narrowed_detail_ok = client.get(
        f"/api/v1/parties/{party_a.id}",
        headers={
            "X-View-Perspective": "owner",
            "X-View-Party-Id": party_a.id,
        },
    )
    assert narrowed_detail_ok.status_code == 200

    narrowed_detail_other = client.get(
        f"/api/v1/parties/{party_b.id}",
        headers={
            "X-View-Perspective": "owner",
            "X-View-Party-Id": party_a.id,
        },
    )
    assert narrowed_detail_other.status_code == 404
