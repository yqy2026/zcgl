"""
Asset visibility integration tests for non-admin scoped users.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.abac import ABACPolicy, ABACPolicyRule, ABACRolePolicy
from src.models.asset import Asset
from src.models.auth import User
from src.models.party import Party, PartyType
from src.models.rbac import Role, UserRoleAssignment
from src.models.user_party_binding import RelationType, UserPartyBinding
from src.services.core.password_service import PasswordService


def _login(client: TestClient, username: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": username, "password": password},
    )
    assert response.status_code == 200


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


def _bind_asset_owner_read_policy(
    db_session: Session,
    *,
    suffix: str,
    user_id: str,
) -> None:
    role = Role(
        name=f"vis_asset_owner_reader_{suffix}",
        display_name=f"AssetReader{suffix[:6]}",
        is_system_role=False,
        is_active=True,
        created_by="integration_test",
        updated_by="integration_test",
    )

    policy = ABACPolicy(
        name=f"vis_asset_owner_read_policy_{suffix}",
        effect="allow",
        priority=100,
        enabled=True,
    )
    policy.rules.append(
        ABACPolicyRule(
            resource_type="asset",
            action="read",
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


def _extract_asset_ids(response_json: dict[str, object]) -> set[str]:
    items = response_json.get("data", {}).get("items", [])  # type: ignore[union-attr]
    if not isinstance(items, list):
        return set()
    return {
        item.get("id")
        for item in items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


@pytest.mark.integration
def test_non_admin_owner_scoped_asset_list_should_not_be_forbidden(
    client: TestClient,
    db_session: Session,
    test_data: dict[str, object],
) -> None:
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)

    scoped_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Scoped Party {suffix}",
        code=f"SCOPED-{suffix}",
        external_ref=f"SCOPED-EXT-{suffix}",
        status="active",
    )
    other_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Other Party {suffix}",
        code=f"OTHER-{suffix}",
        external_ref=f"OTHER-EXT-{suffix}",
        status="active",
    )
    db_session.add_all([scoped_party, other_party])
    db_session.flush()

    organization_id = str(getattr(test_data["organization"], "id"))  # type: ignore[index]
    scoped_user = User(
        username=f"asset_scope_user_{suffix}",
        email=f"asset_scope_user_{suffix}@example.com",
        phone=f"136{uuid.uuid4().int % 10**8:08d}",
        full_name="Asset Scope User",
        password_hash=password_hash,
        is_active=True,
        default_organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add(scoped_user)
    db_session.flush()

    db_session.add(
        UserPartyBinding(
            user_id=scoped_user.id,
            party_id=scoped_party.id,
            relation_type=RelationType.OWNER,
            is_primary=True,
        )
    )

    scoped_asset = Asset(
        asset_name=f"资产作用域命中-{suffix}",
        address=f"作用域地址-A-{suffix}",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        data_status="正常",
        owner_party_id=scoped_party.id,
        organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    other_asset = Asset(
        asset_name=f"资产作用域隔离-{suffix}",
        address=f"作用域地址-B-{suffix}",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        data_status="正常",
        owner_party_id=other_party.id,
        organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add_all([scoped_asset, other_asset])

    _bind_asset_owner_read_policy(
        db_session,
        suffix=suffix,
        user_id=scoped_user.id,
    )
    db_session.commit()

    _login(client, scoped_user.username, password)
    response = client.get(f"/api/v1/assets?page=1&page_size=20&search={suffix}")
    assert response.status_code == 200

    payload = response.json()
    assert payload.get("success") is True
    items = payload.get("data", {}).get("items", [])
    assert isinstance(items, list)

    item_ids = {
        item.get("id")
        for item in items
        if isinstance(item, dict) and item.get("id") is not None
    }
    assert scoped_asset.id in item_ids
    assert other_asset.id not in item_ids


@pytest.mark.integration
def test_selected_view_headers_should_narrow_asset_results(
    client: TestClient,
    db_session: Session,
    test_data: dict[str, object],
) -> None:
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)

    owner_party_a = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Scoped Owner A {suffix}",
        code=f"SCOPED-OWNER-A-{suffix}",
        external_ref=f"SCOPED-OWNER-A-EXT-{suffix}",
        status="active",
    )
    owner_party_b = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Scoped Owner B {suffix}",
        code=f"SCOPED-OWNER-B-{suffix}",
        external_ref=f"SCOPED-OWNER-B-EXT-{suffix}",
        status="active",
    )
    db_session.add_all([owner_party_a, owner_party_b])
    db_session.flush()

    organization_id = str(getattr(test_data["organization"], "id"))  # type: ignore[index]
    scoped_user = User(
        username=f"asset_selected_view_user_{suffix}",
        email=f"asset_selected_view_user_{suffix}@example.com",
        phone=f"137{uuid.uuid4().int % 10**8:08d}",
        full_name="Asset Selected View User",
        password_hash=password_hash,
        is_active=True,
        default_organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add(scoped_user)
    db_session.flush()

    db_session.add_all(
        [
            UserPartyBinding(
                user_id=scoped_user.id,
                party_id=owner_party_a.id,
                relation_type=RelationType.OWNER,
                is_primary=True,
            ),
            UserPartyBinding(
                user_id=scoped_user.id,
                party_id=owner_party_b.id,
                relation_type=RelationType.OWNER,
                is_primary=False,
            ),
        ]
    )

    asset_a = Asset(
        asset_name=f"资产视角命中-A-{suffix}",
        address=f"视角地址-A-{suffix}",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        data_status="正常",
        owner_party_id=owner_party_a.id,
        organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    asset_b = Asset(
        asset_name=f"资产视角命中-B-{suffix}",
        address=f"视角地址-B-{suffix}",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        data_status="正常",
        owner_party_id=owner_party_b.id,
        organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add_all([asset_a, asset_b])

    _bind_asset_owner_read_policy(
        db_session,
        suffix=suffix,
        user_id=scoped_user.id,
    )
    db_session.commit()

    _login(client, scoped_user.username, password)

    base_response = client.get(f"/api/v1/assets?page=1&page_size=20&search={suffix}")
    assert base_response.status_code == 200
    assert _extract_asset_ids(base_response.json()) == {asset_a.id, asset_b.id}

    narrowed_response = client.get(
        f"/api/v1/assets?page=1&page_size=20&search={suffix}",
        headers={
            "X-View-Perspective": "owner",
            "X-View-Party-Id": owner_party_a.id,
        },
    )
    assert narrowed_response.status_code == 200
    assert _extract_asset_ids(narrowed_response.json()) == {asset_a.id}
