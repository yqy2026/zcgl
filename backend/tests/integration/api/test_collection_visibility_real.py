"""Collection visibility integration tests for non-admin scoped users."""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.abac import ABACPolicy, ABACPolicyRule, ABACRolePolicy
from src.models.auth import User
from src.models.collection import CollectionMethod, CollectionRecord, CollectionStatus
from src.models.contract_group import (
    Contract,
    ContractDirection,
    ContractGroup,
    ContractLedgerEntry,
    ContractLifecycleStatus,
    ContractReviewStatus,
    GroupRelationType,
    RevenueMode,
)
from src.models.organization import Organization
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


def _bind_collection_read_policy(
    db_session: Session,
    *,
    suffix: str,
    user_ids: list[str],
) -> None:
    role = Role(
        name=f"vis_collection_reader_{suffix}",
        display_name=f"CR{suffix[:6]}",
        is_system_role=False,
        is_active=True,
        created_by="integration_test",
        updated_by="integration_test",
    )

    policy = ABACPolicy(
        name=f"vis_collection_read_policy_{suffix}",
        effect="allow",
        priority=100,
        enabled=True,
    )
    policy.rules.append(
        ABACPolicyRule(
            resource_type="collection",
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


def _settlement_rule() -> dict[str, object]:
    return {
        "version": "v1",
        "cycle": "月付",
        "settlement_mode": "manual",
        "amount_rule": {"basis": "fixed"},
        "payment_rule": {"due_day": 1},
    }


@pytest.mark.integration
def test_non_admin_collection_visibility_isolation(
    client: TestClient,
    db_session: Session,
) -> None:
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)
    now = datetime.now(UTC).replace(tzinfo=None)

    org_a = Organization(
        name=f"Collection Org A-{suffix}",
        code=f"COL-ORG-A-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    org_b = Organization(
        name=f"Collection Org B-{suffix}",
        code=f"COL-ORG-B-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    db_session.add_all([org_a, org_b])
    db_session.flush()

    operator_party_a = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Collection Operator A-{suffix}",
        code=f"COL-OP-A-{suffix}",
        external_ref=org_a.id,
        status="active",
    )
    operator_party_b = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Collection Operator B-{suffix}",
        code=f"COL-OP-B-{suffix}",
        external_ref=org_b.id,
        status="active",
    )
    owner_party_a = Party(
        party_type=PartyType.LEGAL_ENTITY.value,
        name=f"Collection Owner A-{suffix}",
        code=f"COL-OWN-A-{suffix}",
        external_ref=f"COL-OWN-A-EXT-{suffix}",
        status="active",
    )
    owner_party_b = Party(
        party_type=PartyType.LEGAL_ENTITY.value,
        name=f"Collection Owner B-{suffix}",
        code=f"COL-OWN-B-{suffix}",
        external_ref=f"COL-OWN-B-EXT-{suffix}",
        status="active",
    )
    tenant_party_a = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Collection Tenant A-{suffix}",
        code=f"COL-TEN-A-{suffix}",
        external_ref=f"COL-TEN-A-EXT-{suffix}",
        status="active",
    )
    tenant_party_b = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Collection Tenant B-{suffix}",
        code=f"COL-TEN-B-{suffix}",
        external_ref=f"COL-TEN-B-EXT-{suffix}",
        status="active",
    )
    db_session.add_all(
        [
            operator_party_a,
            operator_party_b,
            owner_party_a,
            owner_party_b,
            tenant_party_a,
            tenant_party_b,
        ]
    )
    db_session.flush()

    user_a = User(
        username=f"collection_user_a_{suffix}",
        email=f"collection_user_a_{suffix}@example.com",
        phone=f"136{uuid.uuid4().int % 10**8:08d}",
        full_name="Collection User A",
        password_hash=password_hash,
        is_active=True,
        default_organization_id=org_a.id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    user_b = User(
        username=f"collection_user_b_{suffix}",
        email=f"collection_user_b_{suffix}@example.com",
        phone=f"137{uuid.uuid4().int % 10**8:08d}",
        full_name="Collection User B",
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
                party_id=operator_party_a.id,
                relation_type=RelationType.MANAGER,
                is_primary=True,
            ),
            UserPartyBinding(
                user_id=user_b.id,
                party_id=operator_party_b.id,
                relation_type=RelationType.MANAGER,
                is_primary=True,
            ),
        ]
    )

    group_a = ContractGroup(
        contract_group_id=f"col-group-a-{suffix}",
        group_code=f"GRP-CA{suffix[:4].upper()}-202603-0201",
        revenue_mode=RevenueMode.LEASE,
        operator_party_id=operator_party_a.id,
        owner_party_id=owner_party_a.id,
        effective_from=date(2026, 1, 1),
        settlement_rule=_settlement_rule(),
        data_status="正常",
        created_at=now,
        updated_at=now,
        created_by="integration_test",
        updated_by="integration_test",
    )
    group_b = ContractGroup(
        contract_group_id=f"col-group-b-{suffix}",
        group_code=f"GRP-CB{suffix[:4].upper()}-202603-0202",
        revenue_mode=RevenueMode.LEASE,
        operator_party_id=operator_party_b.id,
        owner_party_id=owner_party_b.id,
        effective_from=date(2026, 1, 1),
        settlement_rule=_settlement_rule(),
        data_status="正常",
        created_at=now,
        updated_at=now,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add_all([group_a, group_b])
    db_session.flush()

    contract_a = Contract(
        contract_id=f"col-contract-a-{suffix}",
        contract_group_id=group_a.contract_group_id,
        contract_number=f"COL-A-{suffix}",
        contract_direction=ContractDirection.LESSOR,
        group_relation_type=GroupRelationType.UPSTREAM,
        lessor_party_id=owner_party_a.id,
        lessee_party_id=tenant_party_a.id,
        sign_date=date(2026, 1, 1),
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        currency_code="CNY",
        is_tax_included=True,
        status=ContractLifecycleStatus.ACTIVE,
        review_status=ContractReviewStatus.APPROVED,
        data_status="正常",
        created_at=now,
        updated_at=now,
        created_by="integration_test",
        updated_by="integration_test",
    )
    contract_b = Contract(
        contract_id=f"col-contract-b-{suffix}",
        contract_group_id=group_b.contract_group_id,
        contract_number=f"COL-B-{suffix}",
        contract_direction=ContractDirection.LESSOR,
        group_relation_type=GroupRelationType.UPSTREAM,
        lessor_party_id=owner_party_b.id,
        lessee_party_id=tenant_party_b.id,
        sign_date=date(2026, 1, 1),
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        currency_code="CNY",
        is_tax_included=True,
        status=ContractLifecycleStatus.ACTIVE,
        review_status=ContractReviewStatus.APPROVED,
        data_status="正常",
        created_at=now,
        updated_at=now,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add_all([contract_a, contract_b])
    db_session.flush()

    ledger_a = ContractLedgerEntry(
        entry_id=f"col-ledger-a-{suffix}",
        contract_id=contract_a.contract_id,
        year_month="2026-01",
        due_date=date.today() - timedelta(days=10),
        amount_due=Decimal("1000.00"),
        currency_code="CNY",
        is_tax_included=True,
        tax_rate=Decimal("0.0900"),
        payment_status="unpaid",
        paid_amount=Decimal("0.00"),
        created_at=now,
        updated_at=now,
    )
    ledger_b = ContractLedgerEntry(
        entry_id=f"col-ledger-b-{suffix}",
        contract_id=contract_b.contract_id,
        year_month="2026-01",
        due_date=date.today() - timedelta(days=10),
        amount_due=Decimal("2000.00"),
        currency_code="CNY",
        is_tax_included=True,
        tax_rate=Decimal("0.0900"),
        payment_status="unpaid",
        paid_amount=Decimal("0.00"),
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([ledger_a, ledger_b])
    db_session.flush()

    record_a = CollectionRecord(
        id=f"col-record-a-{suffix}",
        ledger_id=ledger_a.entry_id,
        contract_id=contract_a.contract_id,
        collection_method=CollectionMethod.PHONE,
        collection_date=date.today(),
        collection_status=CollectionStatus.PENDING,
        operator="operator-a",
        operator_id=str(user_a.id),
        created_at=now,
        updated_at=now,
    )
    record_b = CollectionRecord(
        id=f"col-record-b-{suffix}",
        ledger_id=ledger_b.entry_id,
        contract_id=contract_b.contract_id,
        collection_method=CollectionMethod.PHONE,
        collection_date=date.today(),
        collection_status=CollectionStatus.PENDING,
        operator="operator-b",
        operator_id=str(user_b.id),
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([record_a, record_b])

    _bind_collection_read_policy(
        db_session,
        suffix=suffix,
        user_ids=[user_a.id, user_b.id],
    )
    db_session.commit()

    _login(client, user_a.username, password)
    response_list_a = client.get("/api/v1/collection/records")
    assert response_list_a.status_code == 200
    ids_a = {item["id"] for item in response_list_a.json()["data"]["items"]}
    assert record_a.id in ids_a
    assert record_b.id not in ids_a

    response_summary_a = client.get("/api/v1/collection/summary")
    assert response_summary_a.status_code == 200
    assert response_summary_a.json()["total_overdue_count"] == 1

    response_detail_a = client.get(f"/api/v1/collection/records/{record_a.id}")
    assert response_detail_a.status_code == 200
    assert response_detail_a.json()["id"] == record_a.id

    response_detail_b = client.get(f"/api/v1/collection/records/{record_b.id}")
    assert response_detail_b.status_code == 404

    client.cookies.clear()
    _login(client, user_b.username, password)
    response_list_b = client.get("/api/v1/collection/records")
    assert response_list_b.status_code == 200
    ids_b = {item["id"] for item in response_list_b.json()["data"]["items"]}
    assert record_b.id in ids_b
    assert record_a.id not in ids_b

    response_summary_b = client.get("/api/v1/collection/summary")
    assert response_summary_b.status_code == 200
    assert response_summary_b.json()["total_overdue_count"] == 1


@pytest.mark.integration
def test_selected_view_headers_should_narrow_collection_results(
    client: TestClient,
    db_session: Session,
) -> None:
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)
    now = datetime.now(UTC).replace(tzinfo=None)

    org_a = Organization(
        name=f"Selected Collection Org A-{suffix}",
        code=f"SCL-ORG-A-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    org_b = Organization(
        name=f"Selected Collection Org B-{suffix}",
        code=f"SCL-ORG-B-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    db_session.add_all([org_a, org_b])
    db_session.flush()

    operator_party_a = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Selected Collection Operator A-{suffix}",
        code=f"SCL-OP-A-{suffix}",
        external_ref=org_a.id,
        status="active",
    )
    operator_party_b = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Selected Collection Operator B-{suffix}",
        code=f"SCL-OP-B-{suffix}",
        external_ref=org_b.id,
        status="active",
    )
    owner_party_a = Party(
        party_type=PartyType.LEGAL_ENTITY.value,
        name=f"Selected Collection Owner A-{suffix}",
        code=f"SCL-OWN-A-{suffix}",
        external_ref=f"SCL-OWN-A-EXT-{suffix}",
        status="active",
    )
    owner_party_b = Party(
        party_type=PartyType.LEGAL_ENTITY.value,
        name=f"Selected Collection Owner B-{suffix}",
        code=f"SCL-OWN-B-{suffix}",
        external_ref=f"SCL-OWN-B-EXT-{suffix}",
        status="active",
    )
    tenant_party_a = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Selected Collection Tenant A-{suffix}",
        code=f"SCL-TEN-A-{suffix}",
        external_ref=f"SCL-TEN-A-EXT-{suffix}",
        status="active",
    )
    tenant_party_b = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Selected Collection Tenant B-{suffix}",
        code=f"SCL-TEN-B-{suffix}",
        external_ref=f"SCL-TEN-B-EXT-{suffix}",
        status="active",
    )
    db_session.add_all(
        [
            operator_party_a,
            operator_party_b,
            owner_party_a,
            owner_party_b,
            tenant_party_a,
            tenant_party_b,
        ]
    )
    db_session.flush()

    user = User(
        username=f"collection_selected_view_user_{suffix}",
        email=f"collection_selected_view_user_{suffix}@example.com",
        phone=f"138{uuid.uuid4().int % 10**8:08d}",
        full_name="Collection Selected View User",
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
                party_id=operator_party_a.id,
                relation_type=RelationType.MANAGER,
                is_primary=True,
            ),
            UserPartyBinding(
                user_id=user.id,
                party_id=operator_party_b.id,
                relation_type=RelationType.MANAGER,
                is_primary=False,
            ),
        ]
    )

    group_a = ContractGroup(
        contract_group_id=f"scl-group-a-{suffix}",
        group_code=f"GRP-SCLA{suffix[:4].upper()}-202603-0201",
        revenue_mode=RevenueMode.LEASE,
        operator_party_id=operator_party_a.id,
        owner_party_id=owner_party_a.id,
        effective_from=date(2026, 1, 1),
        settlement_rule=_settlement_rule(),
        data_status="正常",
        created_at=now,
        updated_at=now,
        created_by="integration_test",
        updated_by="integration_test",
    )
    group_b = ContractGroup(
        contract_group_id=f"scl-group-b-{suffix}",
        group_code=f"GRP-SCLB{suffix[:4].upper()}-202603-0202",
        revenue_mode=RevenueMode.LEASE,
        operator_party_id=operator_party_b.id,
        owner_party_id=owner_party_b.id,
        effective_from=date(2026, 1, 1),
        settlement_rule=_settlement_rule(),
        data_status="正常",
        created_at=now,
        updated_at=now,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add_all([group_a, group_b])
    db_session.flush()

    contract_a = Contract(
        contract_id=f"scl-contract-a-{suffix}",
        contract_group_id=group_a.contract_group_id,
        contract_number=f"SCL-A-{suffix}",
        contract_direction=ContractDirection.LESSOR,
        group_relation_type=GroupRelationType.UPSTREAM,
        lessor_party_id=owner_party_a.id,
        lessee_party_id=tenant_party_a.id,
        sign_date=date(2026, 1, 1),
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        currency_code="CNY",
        is_tax_included=True,
        status=ContractLifecycleStatus.ACTIVE,
        review_status=ContractReviewStatus.APPROVED,
        data_status="正常",
        created_at=now,
        updated_at=now,
        created_by="integration_test",
        updated_by="integration_test",
    )
    contract_b = Contract(
        contract_id=f"scl-contract-b-{suffix}",
        contract_group_id=group_b.contract_group_id,
        contract_number=f"SCL-B-{suffix}",
        contract_direction=ContractDirection.LESSOR,
        group_relation_type=GroupRelationType.UPSTREAM,
        lessor_party_id=owner_party_b.id,
        lessee_party_id=tenant_party_b.id,
        sign_date=date(2026, 1, 1),
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        currency_code="CNY",
        is_tax_included=True,
        status=ContractLifecycleStatus.ACTIVE,
        review_status=ContractReviewStatus.APPROVED,
        data_status="正常",
        created_at=now,
        updated_at=now,
        created_by="integration_test",
        updated_by="integration_test",
    )
    db_session.add_all([contract_a, contract_b])
    db_session.flush()

    ledger_a = ContractLedgerEntry(
        entry_id=f"scl-ledger-a-{suffix}",
        contract_id=contract_a.contract_id,
        year_month="2026-01",
        due_date=date.today() - timedelta(days=10),
        amount_due=Decimal("1000.00"),
        currency_code="CNY",
        is_tax_included=True,
        tax_rate=Decimal("0.0900"),
        payment_status="unpaid",
        paid_amount=Decimal("0.00"),
        created_at=now,
        updated_at=now,
    )
    ledger_b = ContractLedgerEntry(
        entry_id=f"scl-ledger-b-{suffix}",
        contract_id=contract_b.contract_id,
        year_month="2026-01",
        due_date=date.today() - timedelta(days=10),
        amount_due=Decimal("2000.00"),
        currency_code="CNY",
        is_tax_included=True,
        tax_rate=Decimal("0.0900"),
        payment_status="unpaid",
        paid_amount=Decimal("0.00"),
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([ledger_a, ledger_b])
    db_session.flush()

    record_a = CollectionRecord(
        id=f"scl-record-a-{suffix}",
        ledger_id=ledger_a.entry_id,
        contract_id=contract_a.contract_id,
        collection_method=CollectionMethod.PHONE,
        collection_date=date.today(),
        collection_status=CollectionStatus.PENDING,
        operator="operator-a",
        operator_id=str(user.id),
        created_at=now,
        updated_at=now,
    )
    record_b = CollectionRecord(
        id=f"scl-record-b-{suffix}",
        ledger_id=ledger_b.entry_id,
        contract_id=contract_b.contract_id,
        collection_method=CollectionMethod.PHONE,
        collection_date=date.today(),
        collection_status=CollectionStatus.PENDING,
        operator="operator-b",
        operator_id=str(user.id),
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([record_a, record_b])

    _bind_collection_read_policy(
        db_session,
        suffix=suffix,
        user_ids=[user.id],
    )
    db_session.commit()

    _login(client, user.username, password)
    base_response = client.get("/api/v1/collection/records")
    assert base_response.status_code == 200
    assert {
        item["id"] for item in base_response.json()["data"]["items"]
    } == {record_a.id, record_b.id}

    narrowed_response = client.get(
        "/api/v1/collection/records",
        headers={
            "X-View-Perspective": "manager",
            "X-View-Party-Id": operator_party_a.id,
        },
    )
    assert narrowed_response.status_code == 200
    assert {
        item["id"] for item in narrowed_response.json()["data"]["items"]
    } == {record_a.id}
