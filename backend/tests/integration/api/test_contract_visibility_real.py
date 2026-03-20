"""
Contract visibility integration tests for non-admin scoped users.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.abac import ABACPolicy, ABACPolicyRule, ABACRolePolicy
from src.models.auth import User
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


def _bind_contract_read_policy(
    db_session: Session,
    *,
    suffix: str,
    user_ids: list[str],
) -> None:
    role = Role(
        name=f"vis_contract_reader_{suffix}",
        display_name=f"ContractReader{suffix[:6]}",
        is_system_role=False,
        is_active=True,
        created_by="integration_test",
        updated_by="integration_test",
    )

    policy = ABACPolicy(
        name=f"vis_contract_read_policy_{suffix}",
        effect="allow",
        priority=100,
        enabled=True,
    )
    policy.rules.extend(
        [
            ABACPolicyRule(
                resource_type="contract_group",
                action="read",
                condition_expr={"==": [1, 1]},
                field_mask=None,
            ),
            ABACPolicyRule(
                resource_type="contract",
                action="read",
                condition_expr={"==": [1, 1]},
                field_mask=None,
            ),
        ]
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
def test_non_admin_contract_group_and_ledger_visibility_isolation(
    client: TestClient,
    db_session: Session,
) -> None:
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)
    now = datetime.now(UTC).replace(tzinfo=None)

    org_a = Organization(
        name=f"Contract Visibility Org A-{suffix}",
        code=f"CT-ORG-A-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    org_b = Organization(
        name=f"Contract Visibility Org B-{suffix}",
        code=f"CT-ORG-B-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    db_session.add_all([org_a, org_b])
    db_session.flush()

    operator_party_a = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Operator Party A-{suffix}",
        code=f"CT-OP-A-{suffix}",
        external_ref=org_a.id,
        status="active",
    )
    operator_party_b = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Operator Party B-{suffix}",
        code=f"CT-OP-B-{suffix}",
        external_ref=org_b.id,
        status="active",
    )
    owner_party_a = Party(
        party_type=PartyType.LEGAL_ENTITY.value,
        name=f"Owner Party A-{suffix}",
        code=f"CT-OWN-A-{suffix}",
        external_ref=f"CT-OWN-A-EXT-{suffix}",
        status="active",
    )
    owner_party_b = Party(
        party_type=PartyType.LEGAL_ENTITY.value,
        name=f"Owner Party B-{suffix}",
        code=f"CT-OWN-B-{suffix}",
        external_ref=f"CT-OWN-B-EXT-{suffix}",
        status="active",
    )
    tenant_party_a = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Tenant Party A-{suffix}",
        code=f"CT-TEN-A-{suffix}",
        external_ref=f"CT-TEN-A-EXT-{suffix}",
        status="active",
    )
    tenant_party_b = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Tenant Party B-{suffix}",
        code=f"CT-TEN-B-{suffix}",
        external_ref=f"CT-TEN-B-EXT-{suffix}",
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
        username=f"contract_vis_user_a_{suffix}",
        email=f"contract_vis_user_a_{suffix}@example.com",
        phone=f"136{uuid.uuid4().int % 10**8:08d}",
        full_name="Contract Visibility User A",
        password_hash=password_hash,
        is_active=True,
        default_organization_id=org_a.id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    user_b = User(
        username=f"contract_vis_user_b_{suffix}",
        email=f"contract_vis_user_b_{suffix}@example.com",
        phone=f"137{uuid.uuid4().int % 10**8:08d}",
        full_name="Contract Visibility User B",
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
        contract_group_id=f"ct-group-a-{suffix}",
        group_code=f"GRP-CTA{suffix[:4].upper()}-202603-0001",
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
        contract_group_id=f"ct-group-b-{suffix}",
        group_code=f"GRP-CTB{suffix[:4].upper()}-202603-0002",
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
        contract_id=f"ct-contract-a-{suffix}",
        contract_group_id=group_a.contract_group_id,
        contract_number=f"CT-A-{suffix}",
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
        contract_id=f"ct-contract-b-{suffix}",
        contract_group_id=group_b.contract_group_id,
        contract_number=f"CT-B-{suffix}",
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
        entry_id=f"ct-ledger-a-{suffix}",
        contract_id=contract_a.contract_id,
        year_month="2026-01",
        due_date=date(2026, 1, 1),
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
        entry_id=f"ct-ledger-b-{suffix}",
        contract_id=contract_b.contract_id,
        year_month="2026-01",
        due_date=date(2026, 1, 1),
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

    _bind_contract_read_policy(
        db_session,
        suffix=suffix,
        user_ids=[user_a.id, user_b.id],
    )
    db_session.commit()

    _login(client, user_a.username, password)
    response_group_a = client.get("/api/v1/contract-groups")
    assert response_group_a.status_code == 200
    items_group_a = response_group_a.json()["items"]
    ids_group_a = {item["contract_group_id"] for item in items_group_a}
    assert group_a.contract_group_id in ids_group_a
    assert group_b.contract_group_id not in ids_group_a

    response_ledger_a = client.get(
        "/api/v1/ledger/entries",
        params={"year_month_start": "2026-01"},
    )
    assert response_ledger_a.status_code == 200
    items_ledger_a = response_ledger_a.json()["items"]
    contract_ids_a = {item["contract_id"] for item in items_ledger_a}
    assert contract_a.contract_id in contract_ids_a
    assert contract_b.contract_id not in contract_ids_a

    response_ledger_a_broaden = client.get(
        "/api/v1/ledger/entries",
        params={
            "year_month_start": "2026-01",
            "party_id": operator_party_b.id,
        },
    )
    assert response_ledger_a_broaden.status_code == 200
    assert response_ledger_a_broaden.json()["items"] == []

    client.cookies.clear()
    _login(client, user_b.username, password)
    response_group_b = client.get("/api/v1/contract-groups")
    assert response_group_b.status_code == 200
    items_group_b = response_group_b.json()["items"]
    ids_group_b = {item["contract_group_id"] for item in items_group_b}
    assert group_b.contract_group_id in ids_group_b
    assert group_a.contract_group_id not in ids_group_b

    response_ledger_b = client.get(
        "/api/v1/ledger/entries",
        params={"year_month_start": "2026-01"},
    )
    assert response_ledger_b.status_code == 200
    items_ledger_b = response_ledger_b.json()["items"]
    contract_ids_b = {item["contract_id"] for item in items_ledger_b}
    assert contract_b.contract_id in contract_ids_b
    assert contract_a.contract_id not in contract_ids_b


@pytest.mark.integration
def test_non_admin_contract_resource_endpoints_should_not_cross_party_scope(
    client: TestClient,
    db_session: Session,
) -> None:
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)
    now = datetime.now(UTC).replace(tzinfo=None)

    org_a = Organization(
        name=f"Contract Resource Org A-{suffix}",
        code=f"CTR-ORG-A-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    org_b = Organization(
        name=f"Contract Resource Org B-{suffix}",
        code=f"CTR-ORG-B-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    db_session.add_all([org_a, org_b])
    db_session.flush()

    operator_party_a = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Resource Operator A-{suffix}",
        code=f"CTR-OP-A-{suffix}",
        external_ref=org_a.id,
        status="active",
    )
    operator_party_b = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Resource Operator B-{suffix}",
        code=f"CTR-OP-B-{suffix}",
        external_ref=org_b.id,
        status="active",
    )
    owner_party_a = Party(
        party_type=PartyType.LEGAL_ENTITY.value,
        name=f"Resource Owner A-{suffix}",
        code=f"CTR-OWN-A-{suffix}",
        external_ref=f"CTR-OWN-A-EXT-{suffix}",
        status="active",
    )
    owner_party_b = Party(
        party_type=PartyType.LEGAL_ENTITY.value,
        name=f"Resource Owner B-{suffix}",
        code=f"CTR-OWN-B-{suffix}",
        external_ref=f"CTR-OWN-B-EXT-{suffix}",
        status="active",
    )
    tenant_party_a = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Resource Tenant A-{suffix}",
        code=f"CTR-TEN-A-{suffix}",
        external_ref=f"CTR-TEN-A-EXT-{suffix}",
        status="active",
    )
    tenant_party_b = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Resource Tenant B-{suffix}",
        code=f"CTR-TEN-B-{suffix}",
        external_ref=f"CTR-TEN-B-EXT-{suffix}",
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
        username=f"contract_res_user_a_{suffix}",
        email=f"contract_res_user_a_{suffix}@example.com",
        phone=f"138{uuid.uuid4().int % 10**8:08d}",
        full_name="Contract Resource User A",
        password_hash=password_hash,
        is_active=True,
        default_organization_id=org_a.id,
        created_by="integration_test",
        updated_by="integration_test",
    )
    user_b = User(
        username=f"contract_res_user_b_{suffix}",
        email=f"contract_res_user_b_{suffix}@example.com",
        phone=f"139{uuid.uuid4().int % 10**8:08d}",
        full_name="Contract Resource User B",
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
        contract_group_id=f"ctr-group-a-{suffix}",
        group_code=f"GRP-RA{suffix[:4].upper()}-202603-0101",
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
        contract_group_id=f"ctr-group-b-{suffix}",
        group_code=f"GRP-RB{suffix[:4].upper()}-202603-0102",
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
        contract_id=f"ctr-contract-a-{suffix}",
        contract_group_id=group_a.contract_group_id,
        contract_number=f"CTR-A-{suffix}",
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
        contract_id=f"ctr-contract-b-{suffix}",
        contract_group_id=group_b.contract_group_id,
        contract_number=f"CTR-B-{suffix}",
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
        entry_id=f"ctr-ledger-a-{suffix}",
        contract_id=contract_a.contract_id,
        year_month="2026-01",
        due_date=date(2026, 1, 1),
        amount_due=Decimal("1500.00"),
        currency_code="CNY",
        is_tax_included=True,
        tax_rate=Decimal("0.0900"),
        payment_status="unpaid",
        paid_amount=Decimal("0.00"),
        created_at=now,
        updated_at=now,
    )
    ledger_b = ContractLedgerEntry(
        entry_id=f"ctr-ledger-b-{suffix}",
        contract_id=contract_b.contract_id,
        year_month="2026-01",
        due_date=date(2026, 1, 1),
        amount_due=Decimal("2500.00"),
        currency_code="CNY",
        is_tax_included=True,
        tax_rate=Decimal("0.0900"),
        payment_status="unpaid",
        paid_amount=Decimal("0.00"),
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([ledger_a, ledger_b])

    _bind_contract_read_policy(
        db_session,
        suffix=f"res-{suffix}",
        user_ids=[user_a.id, user_b.id],
    )
    db_session.commit()

    _login(client, user_a.username, password)

    response_group_a_contracts = client.get(
        f"/api/v1/contract-groups/{group_a.contract_group_id}/contracts"
    )
    assert response_group_a_contracts.status_code == 200
    ids_group_a_contracts = {item["contract_id"] for item in response_group_a_contracts.json()}
    assert contract_a.contract_id in ids_group_a_contracts

    response_group_b_contracts = client.get(
        f"/api/v1/contract-groups/{group_b.contract_group_id}/contracts"
    )
    assert response_group_b_contracts.status_code == 404

    response_contract_a_terms = client.get(
        f"/api/v1/contracts/{contract_a.contract_id}/rent-terms"
    )
    assert response_contract_a_terms.status_code == 200
    assert response_contract_a_terms.json() == []

    response_contract_b_terms = client.get(
        f"/api/v1/contracts/{contract_b.contract_id}/rent-terms"
    )
    assert response_contract_b_terms.status_code == 404

    response_contract_a_ledger = client.get(
        f"/api/v1/contracts/{contract_a.contract_id}/ledger"
    )
    assert response_contract_a_ledger.status_code == 200
    ledger_contract_ids = {item["contract_id"] for item in response_contract_a_ledger.json()["items"]}
    assert contract_a.contract_id in ledger_contract_ids

    response_contract_b_ledger = client.get(
        f"/api/v1/contracts/{contract_b.contract_id}/ledger"
    )
    assert response_contract_b_ledger.status_code == 404


@pytest.mark.integration
def test_selected_view_headers_should_narrow_contract_results(
    client: TestClient,
    db_session: Session,
) -> None:
    suffix = uuid.uuid4().hex[:8]
    password = "User123!@#"
    password_hash = PasswordService().get_password_hash(password)
    now = datetime.now(UTC).replace(tzinfo=None)

    org_a = Organization(
        name=f"Selected Contract Org A-{suffix}",
        code=f"SC-ORG-A-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    org_b = Organization(
        name=f"Selected Contract Org B-{suffix}",
        code=f"SC-ORG-B-{suffix}",
        level=1,
        type="department",
        status="active",
    )
    db_session.add_all([org_a, org_b])
    db_session.flush()

    operator_party_a = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Selected Contract Operator A-{suffix}",
        code=f"SC-OP-A-{suffix}",
        external_ref=org_a.id,
        status="active",
    )
    operator_party_b = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Selected Contract Operator B-{suffix}",
        code=f"SC-OP-B-{suffix}",
        external_ref=org_b.id,
        status="active",
    )
    owner_party_a = Party(
        party_type=PartyType.LEGAL_ENTITY.value,
        name=f"Selected Contract Owner A-{suffix}",
        code=f"SC-OWN-A-{suffix}",
        external_ref=f"SC-OWN-A-EXT-{suffix}",
        status="active",
    )
    owner_party_b = Party(
        party_type=PartyType.LEGAL_ENTITY.value,
        name=f"Selected Contract Owner B-{suffix}",
        code=f"SC-OWN-B-{suffix}",
        external_ref=f"SC-OWN-B-EXT-{suffix}",
        status="active",
    )
    tenant_party_a = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Selected Contract Tenant A-{suffix}",
        code=f"SC-TEN-A-{suffix}",
        external_ref=f"SC-TEN-A-EXT-{suffix}",
        status="active",
    )
    tenant_party_b = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Selected Contract Tenant B-{suffix}",
        code=f"SC-TEN-B-{suffix}",
        external_ref=f"SC-TEN-B-EXT-{suffix}",
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
        username=f"contract_selected_view_user_{suffix}",
        email=f"contract_selected_view_user_{suffix}@example.com",
        phone=f"138{uuid.uuid4().int % 10**8:08d}",
        full_name="Contract Selected View User",
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
        contract_group_id=f"sc-group-a-{suffix}",
        group_code=f"GRP-SCA{suffix[:4].upper()}-202603-0101",
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
        contract_group_id=f"sc-group-b-{suffix}",
        group_code=f"GRP-SCB{suffix[:4].upper()}-202603-0102",
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
        contract_id=f"sc-contract-a-{suffix}",
        contract_group_id=group_a.contract_group_id,
        contract_number=f"SC-A-{suffix}",
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
        contract_id=f"sc-contract-b-{suffix}",
        contract_group_id=group_b.contract_group_id,
        contract_number=f"SC-B-{suffix}",
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
        entry_id=f"sc-ledger-a-{suffix}",
        contract_id=contract_a.contract_id,
        year_month="2026-01",
        due_date=date(2026, 1, 1),
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
        entry_id=f"sc-ledger-b-{suffix}",
        contract_id=contract_b.contract_id,
        year_month="2026-01",
        due_date=date(2026, 1, 1),
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

    _bind_contract_read_policy(
        db_session,
        suffix=suffix,
        user_ids=[user.id],
    )
    db_session.commit()

    _login(client, user.username, password)
    base_group_response = client.get("/api/v1/contract-groups")
    assert base_group_response.status_code == 200
    assert {
        item["contract_group_id"] for item in base_group_response.json()["items"]
    } == {group_a.contract_group_id, group_b.contract_group_id}

    narrowed_group_response = client.get(
        "/api/v1/contract-groups",
        headers={
            "X-View-Perspective": "manager",
            "X-View-Party-Id": operator_party_a.id,
        },
    )
    assert narrowed_group_response.status_code == 200
    assert {
        item["contract_group_id"] for item in narrowed_group_response.json()["items"]
    } == {group_a.contract_group_id}

    narrowed_ledger_response = client.get(
        "/api/v1/ledger/entries",
        params={"year_month_start": "2026-01"},
        headers={
            "X-View-Perspective": "manager",
            "X-View-Party-Id": operator_party_a.id,
        },
    )
    assert narrowed_ledger_response.status_code == 200
    assert {
        item["contract_id"] for item in narrowed_ledger_response.json()["items"]
    } == {contract_a.contract_id}

    hidden_group_response = client.get(
        f"/api/v1/contract-groups/{group_b.contract_group_id}",
        headers={
            "X-View-Perspective": "manager",
            "X-View-Party-Id": operator_party_a.id,
        },
    )
    assert hidden_group_response.status_code == 404
