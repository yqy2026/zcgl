"""
Project visibility integration tests for non-admin users across organizations.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.abac import ABACPolicy, ABACPolicyRule, ABACRolePolicy
from src.models.auth import User
from src.models.organization import Organization
from src.models.party import Party, PartyType
from src.models.project import Project
from src.models.rbac import Role, UserRoleAssignment
from src.models.user_party_binding import RelationType, UserPartyBinding
from src.services.core.password_service import PasswordService


def _build_project_code() -> str:
    segment = uuid.uuid4().hex[:6].upper()
    serial = f"{uuid.uuid4().int % 1000000:06d}"
    return f"PRJ-{segment}-{serial}"


def _login(client: TestClient, username: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": username, "password": password},
    )
    assert response.status_code == 200


def _bind_project_read_policy(
    db_session: Session,
    *,
    suffix: str,
    user_ids: list[str],
) -> None:
    """Seed a non-admin role with project read ABAC policy for target users."""
    role = Role(
        name=f"vis_project_reader_{suffix}",
        display_name=f"VisReader{suffix[:6]}",
        is_system_role=False,
        is_active=True,
        created_by="integration_test",
        updated_by="integration_test",
    )

    policy = ABACPolicy(
        name=f"vis_project_read_policy_{suffix}",
        effect="allow",
        priority=100,
        enabled=True,
    )
    policy.rules.append(
        ABACPolicyRule(
            resource_type="project",
            action="read",
            condition_expr={"==": [1, 1]},
            field_mask=None,
        )
    )

    db_session.add_all([role, policy])
    db_session.flush()

    db_session.add(ABACRolePolicy(role_id=role.id, policy_id=policy.id, enabled=True))
    for user_id in user_ids:
        db_session.add(
            UserRoleAssignment(
                user_id=user_id,
                role_id=role.id,
                assigned_by="integration_test",
                is_active=True,
            )
        )


@pytest.mark.integration
def test_non_admin_project_visibility_isolation(client: TestClient, db_session: Session):
    """真实链路验证：非管理员仅能看到本组织项目。"""
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)

    org_a = Organization(
        name=f"Visibility Org A-{suffix}",
        code=f"VIS-ORG-A-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    org_b = Organization(
        name=f"Visibility Org B-{suffix}",
        code=f"VIS-ORG-B-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    db_session.add_all([org_a, org_b])
    db_session.flush()

    party_a = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Visibility Party A-{suffix}",
        code=f"VIS-PARTY-A-{suffix}",
        external_ref=org_a.id,
        status="active",
    )
    party_b = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Visibility Party B-{suffix}",
        code=f"VIS-PARTY-B-{suffix}",
        external_ref=org_b.id,
        status="active",
    )
    db_session.add_all([party_a, party_b])
    db_session.flush()

    user_a = User(
        username=f"vis_user_a_{suffix}",
        email=f"vis_user_a_{suffix}@example.com",
        phone=f"139{uuid.uuid4().int % 10**8:08d}",
        full_name="Visibility User A",
        password_hash=password_hash,
        is_active=True,
        default_organization_id=org_a.id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    user_b = User(
        username=f"vis_user_b_{suffix}",
        email=f"vis_user_b_{suffix}@example.com",
        phone=f"137{uuid.uuid4().int % 10**8:08d}",
        full_name="Visibility User B",
        password_hash=password_hash,
        is_active=True,
        default_organization_id=org_b.id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add_all([user_a, user_b])
    db_session.flush()

    db_session.add_all(
        [
            UserPartyBinding(
                user_id=user_a.id,
                party_id=party_a.id,
                relation_type=RelationType.MANAGER,
                is_primary=True,
            ),
            UserPartyBinding(
                user_id=user_b.id,
                party_id=party_b.id,
                relation_type=RelationType.MANAGER,
                is_primary=True,
            ),
        ]
    )

    project_a = Project(
        project_name=f"Visibility Project A-{suffix}",
        project_code=_build_project_code(),
        status="active",
        manager_party_id=party_a.id,
        created_by=user_a.id,
    )
    project_b = Project(
        project_name=f"Visibility Project B-{suffix}",
        project_code=_build_project_code(),
        status="active",
        manager_party_id=party_b.id,
        created_by=user_b.id,
    )
    db_session.add_all([project_a, project_b])
    _bind_project_read_policy(
        db_session,
        suffix=suffix,
        user_ids=[user_a.id, user_b.id],
    )
    db_session.commit()

    _login(client, user_a.username, password)
    response_a = client.get("/api/v1/projects/")
    assert response_a.status_code == 200
    items_a = response_a.json()["data"]["items"]
    ids_a = {item["id"] for item in items_a}
    assert project_a.id in ids_a
    assert project_b.id not in ids_a

    client.cookies.clear()
    _login(client, user_b.username, password)
    response_b = client.get("/api/v1/projects/")
    assert response_b.status_code == 200
    items_b = response_b.json()["data"]["items"]
    ids_b = {item["id"] for item in items_b}
    assert project_b.id in ids_b
    assert project_a.id not in ids_b


@pytest.mark.integration
def test_selected_view_headers_should_narrow_project_results(
    client: TestClient,
    db_session: Session,
) -> None:
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)

    org_a = Organization(
        name=f"Selected View Org A-{suffix}",
        code=f"SV-ORG-A-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    org_b = Organization(
        name=f"Selected View Org B-{suffix}",
        code=f"SV-ORG-B-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    db_session.add_all([org_a, org_b])
    db_session.flush()

    party_a = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Selected View Party A-{suffix}",
        code=f"SV-PARTY-A-{suffix}",
        external_ref=org_a.id,
        status="active",
    )
    party_b = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Selected View Party B-{suffix}",
        code=f"SV-PARTY-B-{suffix}",
        external_ref=org_b.id,
        status="active",
    )
    db_session.add_all([party_a, party_b])
    db_session.flush()

    user = User(
        username=f"project_selected_view_user_{suffix}",
        email=f"project_selected_view_user_{suffix}@example.com",
        phone=f"138{uuid.uuid4().int % 10**8:08d}",
        full_name="Project Selected View User",
        password_hash=password_hash,
        is_active=True,
        default_organization_id=org_a.id,
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
                relation_type=RelationType.MANAGER,
                is_primary=True,
            ),
            UserPartyBinding(
                user_id=user.id,
                party_id=party_b.id,
                relation_type=RelationType.MANAGER,
                is_primary=False,
            ),
        ]
    )

    project_a = Project(
        project_name=f"Selected View Project A-{suffix}",
        project_code=_build_project_code(),
        status="active",
        manager_party_id=party_a.id,
        created_by=user.id,
    )
    project_b = Project(
        project_name=f"Selected View Project B-{suffix}",
        project_code=_build_project_code(),
        status="active",
        manager_party_id=party_b.id,
        created_by=user.id,
    )
    db_session.add_all([project_a, project_b])
    _bind_project_read_policy(
        db_session,
        suffix=suffix,
        user_ids=[user.id],
    )
    db_session.commit()

    _login(client, user.username, password)
    base_response = client.get("/api/v1/projects/")
    assert base_response.status_code == 200
    base_ids = {item["id"] for item in base_response.json()["data"]["items"]}
    assert base_ids == {project_a.id, project_b.id}

    narrowed_response = client.get(
        "/api/v1/projects/",
        headers={
            "X-View-Perspective": "manager",
            "X-View-Party-Id": party_a.id,
        },
    )
    assert narrowed_response.status_code == 200
    narrowed_ids = {item["id"] for item in narrowed_response.json()["data"]["items"]}
    assert narrowed_ids == {project_a.id}

    narrowed_detail_ok = client.get(
        f"/api/v1/projects/{project_a.id}",
        headers={
            "X-View-Perspective": "manager",
            "X-View-Party-Id": party_a.id,
        },
    )
    assert narrowed_detail_ok.status_code == 200

    narrowed_detail_other = client.get(
        f"/api/v1/projects/{project_b.id}",
        headers={
            "X-View-Perspective": "manager",
            "X-View-Party-Id": party_a.id,
        },
    )
    assert narrowed_detail_other.status_code == 404
