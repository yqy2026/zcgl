"""
Property certificate visibility integration tests for non-admin scoped users.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.abac import ABACPolicy, ABACPolicyRule, ABACRolePolicy
from src.models.auth import User
from src.models.certificate_party_relation import (
    CertificatePartyRelation,
    CertificateRelationRole,
)
from src.models.organization import Organization
from src.models.party import Party, PartyType
from src.models.property_certificate import CertificateType, PropertyCertificate
from src.models.rbac import Role, UserRoleAssignment
from src.models.user_party_binding import RelationType, UserPartyBinding
from src.services.core.password_service import PasswordService


def _login(client: TestClient, username: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": username, "password": password},
    )
    assert response.status_code == 200


def _bind_property_certificate_read_policy(
    db_session: Session,
    *,
    suffix: str,
    user_ids: list[str],
) -> None:
    role = Role(
        name=f"vis_property_cert_reader_{suffix}",
        display_name=f"PCR{suffix[:6]}",
        is_system_role=False,
        is_active=True,
        created_by="integration_test",
        updated_by="integration_test",
    )

    policy = ABACPolicy(
        name=f"vis_property_cert_read_policy_{suffix}",
        effect="allow",
        priority=100,
        enabled=True,
    )
    policy.rules.append(
        ABACPolicyRule(
            resource_type="property_certificate",
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
def test_non_admin_property_certificate_visibility_isolation(
    client: TestClient,
    db_session: Session,
) -> None:
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)

    org_a = Organization(
        name=f"Certificate Visibility Org A-{suffix}",
        code=f"PC-ORG-A-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    org_b = Organization(
        name=f"Certificate Visibility Org B-{suffix}",
        code=f"PC-ORG-B-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    db_session.add_all([org_a, org_b])
    db_session.flush()

    party_a = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Certificate Party A-{suffix}",
        code=f"PC-PARTY-A-{suffix}",
        external_ref=org_a.id,
        status="active",
    )
    party_b = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Certificate Party B-{suffix}",
        code=f"PC-PARTY-B-{suffix}",
        external_ref=org_b.id,
        status="active",
    )
    db_session.add_all([party_a, party_b])
    db_session.flush()

    user_a = User(
        username=f"property_cert_user_a_{suffix}",
        email=f"property_cert_user_a_{suffix}@example.com",
        phone=f"136{uuid.uuid4().int % 10**8:08d}",
        full_name="Property Certificate User A",
        password_hash=password_hash,
        is_active=True,
        default_organization_id=org_a.id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    user_b = User(
        username=f"property_cert_user_b_{suffix}",
        email=f"property_cert_user_b_{suffix}@example.com",
        phone=f"137{uuid.uuid4().int % 10**8:08d}",
        full_name="Property Certificate User B",
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

    cert_a = PropertyCertificate(
        certificate_number=f"PC-A-{suffix}",
        certificate_type=CertificateType.OTHER,
        property_address=f"证书地址-A-{suffix}",
        extraction_source="manual",
        is_verified=False,
        created_by="integration_test",
    )
    cert_b = PropertyCertificate(
        certificate_number=f"PC-B-{suffix}",
        certificate_type=CertificateType.OTHER,
        property_address=f"证书地址-B-{suffix}",
        extraction_source="manual",
        is_verified=False,
        created_by="integration_test",
    )
    db_session.add_all([cert_a, cert_b])
    db_session.flush()

    db_session.add_all(
        [
            CertificatePartyRelation(
                certificate_id=cert_a.id,
                party_id=party_a.id,
                relation_role=CertificateRelationRole.OWNER,
                is_primary=True,
            ),
            CertificatePartyRelation(
                certificate_id=cert_b.id,
                party_id=party_b.id,
                relation_role=CertificateRelationRole.OWNER,
                is_primary=True,
            ),
        ]
    )

    _bind_property_certificate_read_policy(
        db_session,
        suffix=suffix,
        user_ids=[user_a.id, user_b.id],
    )
    db_session.commit()

    _login(client, user_a.username, password)
    response_a = client.get("/api/v1/property-certificates/")
    assert response_a.status_code == 200
    ids_a = {item["id"] for item in response_a.json()}
    assert cert_a.id in ids_a
    assert cert_b.id not in ids_a

    response_a_detail = client.get(f"/api/v1/property-certificates/{cert_a.id}")
    assert response_a_detail.status_code == 200
    assert response_a_detail.json()["id"] == cert_a.id

    response_b_detail = client.get(f"/api/v1/property-certificates/{cert_b.id}")
    assert response_b_detail.status_code == 404

    client.cookies.clear()
    _login(client, user_b.username, password)
    response_b = client.get("/api/v1/property-certificates/")
    assert response_b.status_code == 200
    ids_b = {item["id"] for item in response_b.json()}
    assert cert_b.id in ids_b
    assert cert_a.id not in ids_b


@pytest.mark.integration
def test_selected_view_headers_should_narrow_property_certificate_results(
    client: TestClient,
    db_session: Session,
) -> None:
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)

    org_a = Organization(
        name=f"Selected Cert Org A-{suffix}",
        code=f"SPC-ORG-A-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    org_b = Organization(
        name=f"Selected Cert Org B-{suffix}",
        code=f"SPC-ORG-B-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    db_session.add_all([org_a, org_b])
    db_session.flush()

    party_a = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Selected Cert Party A-{suffix}",
        code=f"SPC-PARTY-A-{suffix}",
        external_ref=org_a.id,
        status="active",
    )
    party_b = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Selected Cert Party B-{suffix}",
        code=f"SPC-PARTY-B-{suffix}",
        external_ref=org_b.id,
        status="active",
    )
    db_session.add_all([party_a, party_b])
    db_session.flush()

    user = User(
        username=f"property_cert_selected_view_user_{suffix}",
        email=f"property_cert_selected_view_user_{suffix}@example.com",
        phone=f"138{uuid.uuid4().int % 10**8:08d}",
        full_name="Property Cert Selected View User",
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

    cert_a = PropertyCertificate(
        certificate_number=f"SPC-A-{suffix}",
        certificate_type=CertificateType.OTHER,
        property_address=f"selected-cert-address-A-{suffix}",
        extraction_source="manual",
        is_verified=False,
        created_by="integration_test",
    )
    cert_b = PropertyCertificate(
        certificate_number=f"SPC-B-{suffix}",
        certificate_type=CertificateType.OTHER,
        property_address=f"selected-cert-address-B-{suffix}",
        extraction_source="manual",
        is_verified=False,
        created_by="integration_test",
    )
    db_session.add_all([cert_a, cert_b])
    db_session.flush()

    db_session.add_all(
        [
            CertificatePartyRelation(
                certificate_id=cert_a.id,
                party_id=party_a.id,
                relation_role=CertificateRelationRole.OWNER,
                is_primary=True,
            ),
            CertificatePartyRelation(
                certificate_id=cert_b.id,
                party_id=party_b.id,
                relation_role=CertificateRelationRole.OWNER,
                is_primary=True,
            ),
        ]
    )

    _bind_property_certificate_read_policy(
        db_session,
        suffix=suffix,
        user_ids=[user.id],
    )
    db_session.commit()

    _login(client, user.username, password)
    base_response = client.get("/api/v1/property-certificates/")
    assert base_response.status_code == 200
    assert {item["id"] for item in base_response.json()} == {cert_a.id, cert_b.id}

    narrowed_response = client.get(
        "/api/v1/property-certificates/",
        headers={
            "X-View-Perspective": "manager",
            "X-View-Party-Id": party_a.id,
        },
    )
    assert narrowed_response.status_code == 200
    assert {item["id"] for item in narrowed_response.json()} == {cert_a.id}
