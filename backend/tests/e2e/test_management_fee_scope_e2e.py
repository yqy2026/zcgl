"""Management fees through real human authentication and Party scope resolution."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from src.models.asset_contract import UpstreamContract
from src.models.attachment import Attachment
from src.models.organization import Organization
from src.models.rbac import Permission, Role
from src.models.user_party_binding import UserPartyBinding
from tests.e2e.test_management_fee_e2e import _seed_fee_sources
from tests.e2e.test_management_fee_e2e import fee_schema_ready as fee_schema_ready
from tests.e2e.test_management_fee_e2e import require_redis as require_redis
from tests.e2e.test_management_fee_e2e import (
    reset_token_blacklist_state as reset_token_blacklist_state,
)
from tests.e2e.test_management_fee_e2e import setup_test_database as setup_test_database

pytestmark = pytest.mark.e2e


def _operator(client, factory, db):
    suffix = uuid4().hex
    role_name = f"fee-scope-{suffix}"
    user = factory(
        username=f"fee-{suffix}",
        email=f"{suffix}@example.com",
        password="FeeScope123!@#",
        full_name="管理费普通操作员",
        role=role_name,
    )
    organization = Organization(
        id=str(uuid4()),
        name="无默认范围组织",
        code=f"FEE-{suffix}",
        level=1,
        sort_order=0,
        type="总部",
        status="active",
        path=f"/FEE-{suffix}",
        is_deleted=False,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(organization)
    db.flush()
    user.organization_id = organization.id
    role = db.query(Role).filter_by(name=role_name).one()
    for action in ("read", "write"):
        permission = (
            db.query(Permission).filter_by(resource="asset_ops", action=action).first()
        )
        if permission is None:
            permission = Permission(
                name=f"asset_ops:{action}",
                display_name=f"资产运营{action}",
                resource="asset_ops",
                action=action,
                requires_approval=False,
                created_by=user.id,
                updated_by=user.id,
            )
            db.add(permission)
        role.permissions.append(permission)
    db.commit()
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": user.username, "password": "FeeScope123!@#"},
    )
    assert response.status_code == 200, response.text
    assert role.name not in {"admin", "system_admin"}
    csrf = response.cookies.get("csrf_token")
    return user, {"X-CSRF-Token": csrf} if csrf is not None else {}


def _bind(db, user, party_id, perspective):
    binding = UserPartyBinding(
        user_id=user.id,
        party_id=party_id,
        relation_type=perspective,
        valid_from=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1),
    )
    db.add(binding)
    db.commit()
    return binding


def _reads(client, facts):
    period = facts["effective_date"][:7]
    return (
        client.get("/api/v1/management-fee-statements", params={"period": period}),
        client.get(f"/api/v1/management-fee-statements/{facts['statement_id']}"),
        client.get(
            "/api/v1/rent-ledgers",
            params={"ledger_type": "management_fee", "year": int(period[:4])},
        ),
    )


def test_real_owner_binding_missing_visible_hidden_and_invalid_party(
    client, create_test_user_factory, db_session
):
    user, headers = _operator(client, create_test_user_factory, db_session)
    visible = _seed_fee_sources(db_session, user.id)
    hidden = _seed_fee_sources(db_session, user.id)
    for response in _reads(client, visible):
        assert response.status_code == 403, response.text
        assert response.json()["error"]["code"] == "PARTY_SCOPE_MISSING"
    _bind(db_session, user, visible["owner_id"], "owner")
    listed, detail, matrix = _reads(client, visible)
    assert listed.status_code == detail.status_code == matrix.status_code == 200
    assert {item["id"] for item in listed.json()["items"]} == {visible["statement_id"]}
    assert {row["owner_party_id"] for row in matrix.json()["rows"]} == {
        visible["owner_id"]
    }
    hidden_path = f"/api/v1/management-fee-statements/{hidden['statement_id']}"
    assert client.get(hidden_path).status_code == 404
    denied = client.post(
        f"{hidden_path}/deferrals",
        json={
            "rent_ledger_entry_id": hidden["entry_id"],
            "reason": "越界请求",
            "expected_version": 1,
        },
        headers=headers | {"Idempotency-Key": str(uuid4())},
    )
    assert denied.status_code == 404, denied.text
    from src.models.party import Party

    db_session.get(Party, visible["owner_id"]).status = "inactive"
    db_session.commit()
    for response in _reads(client, visible):
        assert response.status_code == 403, response.text
        assert response.json()["error"]["code"] == "PARTY_SCOPE_INVALID_BINDING"


def test_real_manager_bindings_require_all_agreements(
    client, create_test_user_factory, db_session
):
    user, _ = _operator(client, create_test_user_factory, db_session)
    facts = _seed_fee_sources(db_session, user.id)
    other = _seed_fee_sources(db_session, user.id)
    agreement = db_session.get(UpstreamContract, facts["upstream_id"])
    values = {
        column.key: getattr(agreement, column.key)
        for column in UpstreamContract.__table__.columns
    }
    agreement_id, document_id = str(uuid4()), str(uuid4())
    db_session.add(
        Attachment(
            id=document_id,
            owner_type="contract",
            owner_id=agreement_id,
            file_name="scope.pdf",
            file_type="pdf",
            file_size=1,
            storage_key=f"e2e/fee-scope/{document_id}.pdf",
            created_by=user.id,
        )
    )
    db_session.flush()
    values.update(
        id=agreement_id,
        contract_number=f"FEE-SCOPE-{uuid4().hex}",
        operator_party_id=other["owner_id"],
        scan_document_id=document_id,
        management_fee_rate=Decimal("0.1"),
    )
    db_session.add(UpstreamContract(**values))
    db_session.commit()
    _bind(db_session, user, agreement.operator_party_id, "manager")
    listed, detail, matrix = _reads(client, facts)
    assert detail.status_code == 404, detail.text
    assert listed.status_code == matrix.status_code == 200
    assert facts["statement_id"] not in {item["id"] for item in listed.json()["items"]}
    assert facts["owner_id"] not in {
        row["owner_party_id"] for row in matrix.json()["rows"]
    }
    _bind(db_session, user, other["owner_id"], "manager")
    listed, detail, matrix = _reads(client, facts)
    assert listed.status_code == detail.status_code == matrix.status_code == 200
    assert facts["statement_id"] in {item["id"] for item in listed.json()["items"]}
    assert facts["owner_id"] in {row["owner_party_id"] for row in matrix.json()["rows"]}
