"""Contact visibility integration tests for non-admin scoped users."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.crud.contact import contact_crud
from src.models.abac import ABACPolicy, ABACPolicyRule, ABACRolePolicy
from src.models.auth import User
from src.models.contact import Contact
from src.models.organization import Organization
from src.models.ownership import Ownership
from src.models.rbac import Role, UserRoleAssignment
from src.models.user_party_binding import RelationType, UserPartyBinding
from src.services.core.password_service import PasswordService


def _login(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": username, "password": password},
    )
    assert response.status_code == 200
    csrf_token = response.cookies.get("csrf_token")
    assert csrf_token is not None
    client.cookies.set("csrf_token", csrf_token)
    return {"X-CSRF-Token": csrf_token}


@pytest.fixture(autouse=True)
def disable_contact_field_encryption(monkeypatch):
    monkeypatch.setattr(
        contact_crud.sensitive_data_handler,
        "encryption_enabled",
        False,
    )


def _owner_scope_condition_expr() -> dict[str, object]:
    return {
        "if": [
            {
                "or": [
                    {"!!": {"var": "resource.owner_party_id"}},
                    {"!!": {"var": "resource.party_id"}},
                ]
            },
            {
                "or": [
                    {
                        "in": [
                            {"var": "resource.owner_party_id"},
                            {"var": "subject.owner_party_ids"},
                        ]
                    },
                    {
                        "in": [
                            {"var": "resource.party_id"},
                            {"var": "subject.owner_party_ids"},
                        ]
                    },
                ]
            },
            {"==": [1, 0]},
        ]
    }


def _bind_contact_policy(db_session: Session, *, suffix: str, user_id: str) -> None:
    role = Role(
        name=f"vis_contact_owner_{suffix}",
        display_name=f"CO{suffix[:6]}",
        is_system_role=False,
        is_active=True,
        created_by="integration_test",
        updated_by="integration_test",
    )

    policy = ABACPolicy(
        name=f"vis_contact_owner_policy_{suffix}",
        effect="allow",
        priority=100,
        enabled=True,
    )
    for action in ("create", "read", "update", "delete"):
        policy.rules.append(
            ABACPolicyRule(
                resource_type="contact",
                action=action,
                condition_expr=_owner_scope_condition_expr(),
                field_mask=None,
            )
        )

    db_session.add_all([role, policy])
    db_session.flush()
    db_session.add(ABACRolePolicy(role_id=role.id, policy_id=policy.id, enabled=True))
    db_session.add(
        UserRoleAssignment(
            user_id=user_id,
            role_id=role.id,
            assigned_by="integration_test",
            is_active=True,
        )
    )


@pytest.mark.integration
def test_non_admin_contact_visibility_isolation(
    client: TestClient,
    db_session: Session,
) -> None:
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)

    org = Organization(
        name=f"Contact Org {suffix}",
        code=f"CONTACT-ORG-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    db_session.add(org)
    db_session.flush()

    ownership_a = Ownership(
        name=f"Contact Ownership A {suffix}",
        code=f"OWN-A-{suffix}",
        created_by="integration_test",
        updated_by="integration_test",
    )
    ownership_b = Ownership(
        name=f"Contact Ownership B {suffix}",
        code=f"OWN-B-{suffix}",
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add_all([ownership_a, ownership_b])
    db_session.flush()

    user = User(
        username=f"contact_scope_user_{suffix}",
        email=f"contact_scope_user_{suffix}@example.com",
        phone=f"135{uuid.uuid4().int % 10**8:08d}",
        full_name="Contact Scope User",
        password_hash=password_hash,
        is_active=True,
        default_organization_id=org.id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add(user)
    db_session.flush()

    db_session.add(
        UserPartyBinding(
            user_id=user.id,
            party_id=ownership_a.id,
            relation_type=RelationType.OWNER,
            is_primary=True,
        )
    )

    contact_a = Contact(
        entity_type="ownership",
        entity_id=ownership_a.id,
        name=f"Scoped Contact {suffix}",
        phone="13800138000",
        is_primary=True,
        created_by="integration_test",
        updated_by="integration_test",
    )
    contact_b = Contact(
        entity_type="ownership",
        entity_id=ownership_b.id,
        name=f"Other Contact {suffix}",
        phone="13900139000",
        is_primary=True,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add_all([contact_a, contact_b])

    _bind_contact_policy(db_session, suffix=suffix, user_id=user.id)
    db_session.commit()

    csrf_headers = _login(client, user.username, password)

    response_list_ok = client.get(f"/api/v1/contacts/entity/ownership/{ownership_a.id}")
    assert response_list_ok.status_code == 200
    payload = response_list_ok.json()["data"]
    assert [item["id"] for item in payload["items"]] == [contact_a.id]

    response_list_other = client.get(f"/api/v1/contacts/entity/ownership/{ownership_b.id}")
    assert response_list_other.status_code == 404

    response_detail_ok = client.get(f"/api/v1/contacts/{contact_a.id}")
    assert response_detail_ok.status_code == 200
    assert response_detail_ok.json()["id"] == contact_a.id

    response_detail_other = client.get(f"/api/v1/contacts/{contact_b.id}")
    assert response_detail_other.status_code == 404

    response_create_ok = client.post(
        "/api/v1/contacts/",
        json={
            "name": f"Created Contact {suffix}",
            "phone": "13700137000",
            "entity_type": "ownership",
            "entity_id": ownership_a.id,
            "is_primary": False,
        },
        headers=csrf_headers,
    )
    assert response_create_ok.status_code == 200
    assert response_create_ok.json()["entity_id"] == ownership_a.id

    response_create_other = client.post(
        "/api/v1/contacts/",
        json={
            "name": f"Blocked Contact {suffix}",
            "phone": "13600136000",
            "entity_type": "ownership",
            "entity_id": ownership_b.id,
            "is_primary": False,
        },
        headers=csrf_headers,
    )
    assert response_create_other.status_code == 403
