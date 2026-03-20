"""History visibility integration tests for non-admin scoped users."""

import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.abac import ABACPolicy, ABACPolicyRule, ABACRolePolicy
from src.models.asset import Asset
from src.models.asset_history import AssetHistory
from src.models.auth import User
from src.models.party import Party, PartyHierarchy, PartyType
from src.models.rbac import Role, UserRoleAssignment
from src.models.user_party_binding import RelationType, UserPartyBinding
from src.services.core.password_service import PasswordService


def _login(client: TestClient, username: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": username, "password": password},
    )
    assert response.status_code == 200


def _bind_history_read_policy(db_session: Session, *, suffix: str, user_id: str) -> None:
    role = Role(
        name=f"vis_history_reader_{suffix}",
        display_name=f"HR{suffix[:6]}",
        is_system_role=False,
        is_active=True,
        created_by="integration_test",
        updated_by="integration_test",
    )

    policy = ABACPolicy(
        name=f"vis_history_read_policy_{suffix}",
        effect="allow",
        priority=100,
        enabled=True,
    )
    policy.rules.append(
        ABACPolicyRule(
            resource_type="history",
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
            user_id=user_id,
            role_id=role.id,
            assigned_by="integration_test",
            is_active=True,
        )
    )


@pytest.mark.integration
def test_non_admin_history_visibility_isolation(
    client: TestClient,
    db_session: Session,
    test_data: dict[str, object],
) -> None:
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)

    scoped_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"History Scoped Party {suffix}",
        code=f"HIS-SCOPED-{suffix}",
        external_ref=f"HIS-SCOPED-EXT-{suffix}",
        status="active",
    )
    other_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"History Other Party {suffix}",
        code=f"HIS-OTHER-{suffix}",
        external_ref=f"HIS-OTHER-EXT-{suffix}",
        status="active",
    )
    db_session.add_all([scoped_party, other_party])
    db_session.flush()

    organization_id = str(getattr(test_data["organization"], "id"))  # type: ignore[index]
    user = User(
        username=f"history_scope_user_{suffix}",
        email=f"history_scope_user_{suffix}@example.com",
        phone=f"136{uuid.uuid4().int % 10**8:08d}",
        full_name="History Scope User",
        password_hash=password_hash,
        is_active=True,
        default_organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add(user)
    db_session.flush()

    db_session.add(
        UserPartyBinding(
            user_id=user.id,
            party_id=scoped_party.id,
            relation_type=RelationType.OWNER,
            is_primary=True,
        )
    )

    scoped_asset = Asset(
        asset_name=f"历史命中资产-{suffix}",
        address=f"历史地址-A-{suffix}",
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
        asset_name=f"历史隔离资产-{suffix}",
        address=f"历史地址-B-{suffix}",
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
    db_session.flush()

    scoped_history = AssetHistory(
        asset_id=scoped_asset.id,
        operation_type="update",
        field_name="asset_name",
        old_value="旧值",
        new_value="新值",
        operator="tester",
        description="作用域内历史记录",
    )
    other_history = AssetHistory(
        asset_id=other_asset.id,
        operation_type="update",
        field_name="asset_name",
        old_value="旧值",
        new_value="新值",
        operator="tester",
        description="作用域外历史记录",
    )
    db_session.add_all([scoped_history, other_history])

    _bind_history_read_policy(db_session, suffix=suffix, user_id=user.id)
    db_session.commit()

    _login(client, user.username, password)

    response_list_all = client.get("/api/v1/history/")
    assert response_list_all.status_code == 200
    all_items = response_list_all.json()["data"]["items"]
    all_ids = {item["id"] for item in all_items}
    assert scoped_history.id in all_ids
    assert other_history.id not in all_ids

    response_list = client.get("/api/v1/history/", params={"asset_id": scoped_asset.id})
    assert response_list.status_code == 200
    ids = {item["id"] for item in response_list.json()["data"]["items"]}
    assert scoped_history.id in ids

    response_detail_ok = client.get(f"/api/v1/history/{scoped_history.id}")
    assert response_detail_ok.status_code == 200
    assert response_detail_ok.json()["id"] == scoped_history.id

    response_detail_other = client.get(f"/api/v1/history/{other_history.id}")
    assert response_detail_other.status_code == 404


@pytest.mark.integration
def test_non_admin_history_list_should_merge_multi_party_scope_and_filter_total(
    client: TestClient,
    db_session: Session,
    test_data: dict[str, object],
) -> None:
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)

    first_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"History Multi Party A {suffix}",
        code=f"HIS-MULTI-A-{suffix}",
        external_ref=f"HIS-MULTI-A-EXT-{suffix}",
        status="active",
    )
    second_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"History Multi Party B {suffix}",
        code=f"HIS-MULTI-B-{suffix}",
        external_ref=f"HIS-MULTI-B-EXT-{suffix}",
        status="active",
    )
    other_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"History Multi Party C {suffix}",
        code=f"HIS-MULTI-C-{suffix}",
        external_ref=f"HIS-MULTI-C-EXT-{suffix}",
        status="active",
    )
    db_session.add_all([first_party, second_party, other_party])
    db_session.flush()

    organization_id = str(getattr(test_data["organization"], "id"))  # type: ignore[index]
    user = User(
        username=f"history_multi_scope_user_{suffix}",
        email=f"history_multi_scope_user_{suffix}@example.com",
        phone=f"137{uuid.uuid4().int % 10**8:08d}",
        full_name="History Multi Scope User",
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
                party_id=first_party.id,
                relation_type=RelationType.OWNER,
                is_primary=True,
            ),
            UserPartyBinding(
                user_id=user.id,
                party_id=second_party.id,
                relation_type=RelationType.MANAGER,
                is_primary=False,
            ),
        ]
    )

    first_asset = Asset(
        asset_name=f"历史多主体资产-A-{suffix}",
        address=f"历史多主体地址-A-{suffix}",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        data_status="正常",
        owner_party_id=first_party.id,
        organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    second_asset = Asset(
        asset_name=f"历史多主体资产-B-{suffix}",
        address=f"历史多主体地址-B-{suffix}",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        data_status="正常",
        owner_party_id=other_party.id,
        manager_party_id=second_party.id,
        organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    other_asset = Asset(
        asset_name=f"历史多主体资产-C-{suffix}",
        address=f"历史多主体地址-C-{suffix}",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        data_status="正常",
        owner_party_id=other_party.id,
        organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add_all([first_asset, second_asset, other_asset])
    db_session.flush()

    first_history = AssetHistory(
        asset_id=first_asset.id,
        operation_type="update",
        field_name="asset_name",
        old_value="旧值-A",
        new_value="新值-A",
        operator="tester",
        description="多主体作用域命中-A",
        operation_time=datetime(2026, 3, 16, 9, 0, 0),
    )
    second_history = AssetHistory(
        asset_id=second_asset.id,
        operation_type="update",
        field_name="asset_name",
        old_value="旧值-B",
        new_value="新值-B",
        operator="tester",
        description="多主体作用域命中-B",
        operation_time=datetime(2026, 3, 16, 10, 0, 0),
    )
    other_history = AssetHistory(
        asset_id=other_asset.id,
        operation_type="update",
        field_name="asset_name",
        old_value="旧值-C",
        new_value="新值-C",
        operator="tester",
        description="多主体作用域外-C",
        operation_time=datetime(2026, 3, 16, 11, 0, 0),
    )
    db_session.add_all([first_history, second_history, other_history])

    _bind_history_read_policy(db_session, suffix=suffix, user_id=user.id)
    db_session.commit()

    _login(client, user.username, password)

    response_page_one = client.get("/api/v1/history/", params={"page": 1, "page_size": 1})
    assert response_page_one.status_code == 200
    page_one_payload = response_page_one.json()["data"]
    assert page_one_payload["pagination"]["total"] == 2
    assert [item["id"] for item in page_one_payload["items"]] == [second_history.id]

    response_page_two = client.get("/api/v1/history/", params={"page": 2, "page_size": 1})
    assert response_page_two.status_code == 200
    page_two_payload = response_page_two.json()["data"]
    assert page_two_payload["pagination"]["total"] == 2
    assert [item["id"] for item in page_two_payload["items"]] == [first_history.id]

    response_page_three = client.get("/api/v1/history/", params={"page": 3, "page_size": 1})
    assert response_page_three.status_code == 200
    page_three_payload = response_page_three.json()["data"]
    assert page_three_payload["pagination"]["total"] == 2
    assert page_three_payload["items"] == []
    assert other_history.id not in {
        item["id"] for item in page_one_payload["items"] + page_two_payload["items"]
    }


@pytest.mark.integration
def test_admin_history_list_without_asset_id_should_see_all_records(
    client: TestClient,
    db_session: Session,
    test_data: dict[str, object],
) -> None:
    suffix = uuid.uuid4().hex[:8]
    organization_id = str(getattr(test_data["organization"], "id"))  # type: ignore[index]

    first_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"History Admin Party A {suffix}",
        code=f"HIS-ADMIN-A-{suffix}",
        external_ref=f"HIS-ADMIN-A-EXT-{suffix}",
        status="active",
    )
    second_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"History Admin Party B {suffix}",
        code=f"HIS-ADMIN-B-{suffix}",
        external_ref=f"HIS-ADMIN-B-EXT-{suffix}",
        status="active",
    )
    db_session.add_all([first_party, second_party])
    db_session.flush()

    first_asset = Asset(
        asset_name=f"历史管理员资产-A-{suffix}",
        address=f"历史管理员地址-A-{suffix}",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        data_status="正常",
        owner_party_id=first_party.id,
        organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    second_asset = Asset(
        asset_name=f"历史管理员资产-B-{suffix}",
        address=f"历史管理员地址-B-{suffix}",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        data_status="正常",
        owner_party_id=second_party.id,
        organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add_all([first_asset, second_asset])
    db_session.flush()

    first_history = AssetHistory(
        asset_id=first_asset.id,
        operation_type="update",
        field_name="asset_name",
        old_value="旧值-admin-A",
        new_value="新值-admin-A",
        operator="tester",
        description="管理员全量历史-A",
        operation_time=datetime(2099, 1, 1, 0, 0, 0),
    )
    second_history = AssetHistory(
        asset_id=second_asset.id,
        operation_type="update",
        field_name="asset_name",
        old_value="旧值-admin-B",
        new_value="新值-admin-B",
        operator="tester",
        description="管理员全量历史-B",
        operation_time=datetime(2099, 1, 2, 0, 0, 0),
    )
    db_session.add_all([first_history, second_history])
    db_session.commit()

    admin_user = test_data["admin"]  # type: ignore[index]
    _login(client, admin_user.username, "Admin123!@#")  # type: ignore[union-attr]

    response = client.get("/api/v1/history/", params={"page": 1, "page_size": 10})
    assert response.status_code == 200
    payload = response.json()["data"]
    ids = {item["id"] for item in payload["items"]}
    assert second_history.id in ids
    assert first_history.id in ids


@pytest.mark.integration
def test_headquarters_history_list_should_expand_descendant_manager_scope(
    client: TestClient,
    db_session: Session,
    test_data: dict[str, object],
) -> None:
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)

    headquarters_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"History HQ Party {suffix}",
        code=f"HIS-HQ-{suffix}",
        external_ref=f"HIS-HQ-EXT-{suffix}",
        status="active",
    )
    child_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"History HQ Child {suffix}",
        code=f"HIS-HQ-CHILD-{suffix}",
        external_ref=f"HIS-HQ-CHILD-EXT-{suffix}",
        status="active",
    )
    other_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"History HQ Other {suffix}",
        code=f"HIS-HQ-OTHER-{suffix}",
        external_ref=f"HIS-HQ-OTHER-EXT-{suffix}",
        status="active",
    )
    db_session.add_all([headquarters_party, child_party, other_party])
    db_session.flush()
    db_session.add(
        PartyHierarchy(
            parent_party_id=headquarters_party.id,
            child_party_id=child_party.id,
        )
    )

    organization_id = str(getattr(test_data["organization"], "id"))  # type: ignore[index]
    user = User(
        username=f"history_hq_scope_user_{suffix}",
        email=f"history_hq_scope_user_{suffix}@example.com",
        phone=f"138{uuid.uuid4().int % 10**8:08d}",
        full_name="History HQ Scope User",
        password_hash=password_hash,
        is_active=True,
        default_organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(
        UserPartyBinding(
            user_id=user.id,
            party_id=headquarters_party.id,
            relation_type=RelationType.HEADQUARTERS,
            is_primary=True,
        )
    )

    headquarters_asset = Asset(
        asset_name=f"历史总部资产-A-{suffix}",
        address=f"历史总部地址-A-{suffix}",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        data_status="正常",
        owner_party_id=other_party.id,
        manager_party_id=headquarters_party.id,
        organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    child_asset = Asset(
        asset_name=f"历史总部资产-B-{suffix}",
        address=f"历史总部地址-B-{suffix}",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        data_status="正常",
        owner_party_id=other_party.id,
        manager_party_id=child_party.id,
        organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    other_asset = Asset(
        asset_name=f"历史总部资产-C-{suffix}",
        address=f"历史总部地址-C-{suffix}",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        data_status="正常",
        owner_party_id=other_party.id,
        manager_party_id=other_party.id,
        organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add_all([headquarters_asset, child_asset, other_asset])
    db_session.flush()

    headquarters_history = AssetHistory(
        asset_id=headquarters_asset.id,
        operation_type="update",
        field_name="asset_name",
        old_value="旧值-hq",
        new_value="新值-hq",
        operator="tester",
        description="总部自身管理范围历史",
        operation_time=datetime(2026, 3, 16, 12, 0, 0),
    )
    child_history = AssetHistory(
        asset_id=child_asset.id,
        operation_type="update",
        field_name="asset_name",
        old_value="旧值-child",
        new_value="新值-child",
        operator="tester",
        description="总部子主体管理范围历史",
        operation_time=datetime(2026, 3, 16, 13, 0, 0),
    )
    other_history = AssetHistory(
        asset_id=other_asset.id,
        operation_type="update",
        field_name="asset_name",
        old_value="旧值-other",
        new_value="新值-other",
        operator="tester",
        description="总部范围外历史",
        operation_time=datetime(2026, 3, 16, 14, 0, 0),
    )
    db_session.add_all([headquarters_history, child_history, other_history])

    _bind_history_read_policy(db_session, suffix=suffix, user_id=user.id)
    db_session.commit()

    _login(client, user.username, password)

    response = client.get("/api/v1/history/", params={"page": 1, "page_size": 10})
    assert response.status_code == 200
    payload = response.json()["data"]
    ids = [item["id"] for item in payload["items"]]
    assert payload["pagination"]["total"] == 2
    assert ids == [child_history.id, headquarters_history.id]
    assert other_history.id not in ids


@pytest.mark.integration
def test_history_list_should_not_duplicate_asset_matching_owner_and_manager_scope(
    client: TestClient,
    db_session: Session,
    test_data: dict[str, object],
) -> None:
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)

    owner_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"History Dual Scope Owner {suffix}",
        code=f"HIS-DUAL-OWNER-{suffix}",
        external_ref=f"HIS-DUAL-OWNER-EXT-{suffix}",
        status="active",
    )
    manager_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"History Dual Scope Manager {suffix}",
        code=f"HIS-DUAL-MANAGER-{suffix}",
        external_ref=f"HIS-DUAL-MANAGER-EXT-{suffix}",
        status="active",
    )
    other_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"History Dual Scope Other {suffix}",
        code=f"HIS-DUAL-OTHER-{suffix}",
        external_ref=f"HIS-DUAL-OTHER-EXT-{suffix}",
        status="active",
    )
    db_session.add_all([owner_party, manager_party, other_party])
    db_session.flush()

    organization_id = str(getattr(test_data["organization"], "id"))  # type: ignore[index]
    user = User(
        username=f"history_dual_scope_user_{suffix}",
        email=f"history_dual_scope_user_{suffix}@example.com",
        phone=f"139{uuid.uuid4().int % 10**8:08d}",
        full_name="History Dual Scope User",
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
                party_id=owner_party.id,
                relation_type=RelationType.OWNER,
                is_primary=True,
            ),
            UserPartyBinding(
                user_id=user.id,
                party_id=manager_party.id,
                relation_type=RelationType.MANAGER,
                is_primary=False,
            ),
        ]
    )

    dual_scope_asset = Asset(
        asset_name=f"历史双命中资产-A-{suffix}",
        address=f"历史双命中地址-A-{suffix}",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        data_status="正常",
        owner_party_id=owner_party.id,
        manager_party_id=manager_party.id,
        organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    owner_only_asset = Asset(
        asset_name=f"历史双命中资产-B-{suffix}",
        address=f"历史双命中地址-B-{suffix}",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        data_status="正常",
        owner_party_id=owner_party.id,
        manager_party_id=other_party.id,
        organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    other_asset = Asset(
        asset_name=f"历史双命中资产-C-{suffix}",
        address=f"历史双命中地址-C-{suffix}",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        data_status="正常",
        owner_party_id=other_party.id,
        manager_party_id=other_party.id,
        organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add_all([dual_scope_asset, owner_only_asset, other_asset])
    db_session.flush()

    dual_scope_history = AssetHistory(
        asset_id=dual_scope_asset.id,
        operation_type="update",
        field_name="asset_name",
        old_value="旧值-dual",
        new_value="新值-dual",
        operator="tester",
        description="owner/manager 双命中历史",
        operation_time=datetime(2026, 3, 16, 15, 0, 0),
    )
    owner_only_history = AssetHistory(
        asset_id=owner_only_asset.id,
        operation_type="update",
        field_name="asset_name",
        old_value="旧值-owner",
        new_value="新值-owner",
        operator="tester",
        description="仅 owner 命中历史",
        operation_time=datetime(2026, 3, 16, 14, 0, 0),
    )
    other_history = AssetHistory(
        asset_id=other_asset.id,
        operation_type="update",
        field_name="asset_name",
        old_value="旧值-other",
        new_value="新值-other",
        operator="tester",
        description="范围外历史",
        operation_time=datetime(2026, 3, 16, 16, 0, 0),
    )
    db_session.add_all([dual_scope_history, owner_only_history, other_history])

    _bind_history_read_policy(db_session, suffix=suffix, user_id=user.id)
    db_session.commit()

    _login(client, user.username, password)

    response = client.get("/api/v1/history/", params={"page": 1, "page_size": 10})
    assert response.status_code == 200
    payload = response.json()["data"]
    ids = [item["id"] for item in payload["items"]]
    assert payload["pagination"]["total"] == 2
    assert ids == [dual_scope_history.id, owner_only_history.id]
    assert len(ids) == len(set(ids)) == 2
    assert other_history.id not in ids


@pytest.mark.integration
def test_selected_view_headers_should_narrow_history_results(
    client: TestClient,
    db_session: Session,
    test_data: dict[str, object],
) -> None:
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)

    first_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"History Selected Party A {suffix}",
        code=f"HIS-SV-A-{suffix}",
        external_ref=f"HIS-SV-A-EXT-{suffix}",
        status="active",
    )
    second_party = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"History Selected Party B {suffix}",
        code=f"HIS-SV-B-{suffix}",
        external_ref=f"HIS-SV-B-EXT-{suffix}",
        status="active",
    )
    db_session.add_all([first_party, second_party])
    db_session.flush()

    organization_id = str(getattr(test_data["organization"], "id"))  # type: ignore[index]
    user = User(
        username=f"history_selected_view_user_{suffix}",
        email=f"history_selected_view_user_{suffix}@example.com",
        phone=f"138{uuid.uuid4().int % 10**8:08d}",
        full_name="History Selected View User",
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
                party_id=first_party.id,
                relation_type=RelationType.OWNER,
                is_primary=True,
            ),
            UserPartyBinding(
                user_id=user.id,
                party_id=second_party.id,
                relation_type=RelationType.OWNER,
                is_primary=False,
            ),
        ]
    )

    first_asset = Asset(
        asset_name=f"历史视角资产-A-{suffix}",
        address=f"历史视角地址-A-{suffix}",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        data_status="正常",
        owner_party_id=first_party.id,
        organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    second_asset = Asset(
        asset_name=f"历史视角资产-B-{suffix}",
        address=f"历史视角地址-B-{suffix}",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        data_status="正常",
        owner_party_id=second_party.id,
        organization_id=organization_id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add_all([first_asset, second_asset])
    db_session.flush()

    first_history = AssetHistory(
        asset_id=first_asset.id,
        operation_type="update",
        field_name="asset_name",
        old_value="旧值-A",
        new_value="新值-A",
        operator="tester",
        description="selected-view 命中历史-A",
    )
    second_history = AssetHistory(
        asset_id=second_asset.id,
        operation_type="update",
        field_name="asset_name",
        old_value="旧值-B",
        new_value="新值-B",
        operator="tester",
        description="selected-view 命中历史-B",
    )
    db_session.add_all([first_history, second_history])

    _bind_history_read_policy(db_session, suffix=suffix, user_id=user.id)
    db_session.commit()

    _login(client, user.username, password)
    base_response = client.get("/api/v1/history/")
    assert base_response.status_code == 200
    assert {
        item["id"] for item in base_response.json()["data"]["items"]
    } == {first_history.id, second_history.id}

    narrowed_response = client.get(
        "/api/v1/history/",
        headers={
            "X-View-Perspective": "owner",
            "X-View-Party-Id": first_party.id,
        },
    )
    assert narrowed_response.status_code == 200
    assert {
        item["id"] for item in narrowed_response.json()["data"]["items"]
    } == {first_history.id}
