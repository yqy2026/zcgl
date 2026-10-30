"""Management fee real PostgreSQL/Redis HTTP workflow without database resets.

This module overrides destructive inherited bootstrap fixtures. Its database
sessions retain the existing per-test outer transaction rollback discipline.
"""

import io
import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import inspect
from sqlalchemy.engine import make_url

from src.models.asset_contract import TerminalContract, UpstreamContract
from src.models.asset_ledger import RentLedgerEntry
from src.models.management_fee_statement import ManagementFeeStatement
from tests.e2e.test_asset_contract_lifecycle_e2e import _seed_signed_contracts

pytestmark = pytest.mark.e2e


@pytest.fixture(autouse=True)
def reset_token_blacklist_state(monkeypatch):
    """Override global clearing: isolate and clean only this test's namespace."""
    from src.security.token_blacklist import blacklist_manager

    monkeypatch.setattr(blacklist_manager, "_cache_namespace", f"fee-e2e-{uuid4().hex}")
    monkeypatch.setattr(blacklist_manager, "_blacklisted_tokens", set())
    monkeypatch.setattr(blacklist_manager, "_blacklist_expiry", {})
    monkeypatch.setattr(blacklist_manager, "_revoked_users", {})
    try:
        yield
    finally:
        # monkeypatch restores the original namespace and memory after cleanup.
        blacklist_manager.clear_blacklist()


@pytest.fixture(scope="session", autouse=True)
def hide_env_file():
    """Override root fixture: never move or read local secret files."""
    yield


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Override root fixture: require an existing test schema, never reset it."""
    target = os.environ.get("E2E_TEST_DATABASE_URL") or os.environ.get(
        "TEST_DATABASE_URL"
    )
    assert target is not None, "Explicit E2E_TEST_DATABASE_URL is required"
    parsed = make_url(target)
    assert parsed.drivername.startswith("postgresql")
    assert "test" in (parsed.database or "").lower(), "Dedicated test database required"
    yield


@pytest.fixture(scope="session")
def require_redis(test_database_url):
    """Override inherited flushdb: ping the dedicated cache without deleting keys."""
    import redis

    from src.core.config import settings

    assert test_database_url is not None
    assert settings.REDIS_ENABLED and settings.REDIS_DB == 15
    cache = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=15,
        password=settings.REDIS_PASSWORD,
        socket_connect_timeout=3,
        socket_timeout=3,
    )
    try:
        assert cache.ping() is True
    finally:
        cache.close()
    from src.core.cache_manager import cache_manager

    assert type(cache_manager.backend).__name__ == "RedisCache"
    yield


@pytest.fixture(autouse=True)
def fee_schema_ready(engine):
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {
        "management_fee_statements",
        "management_fee_statement_lines",
        "management_fee_deferrals",
    } <= tables, (
        "Management fee migrations are missing in the test database; apply them explicitly before running"
    )
    from src.models.management_fee_deferral import ManagementFeeDeferral
    from src.models.management_fee_statement import ManagementFeeStatementLine

    for model in (
        ManagementFeeStatement,
        ManagementFeeStatementLine,
        ManagementFeeDeferral,
    ):
        actual = {
            column["name"] for column in inspector.get_columns(model.__tablename__)
        }
        expected = {column.name for column in model.__table__.columns}
        assert expected <= actual, (
            "Management fee test schema columns are stale; apply migrations explicitly"
        )


def _seed_fee_sources(db, actor_id):
    facts = _seed_signed_contracts(db, actor_id)
    agreement = db.get(UpstreamContract, facts["upstream_id"])
    agreement.contract_type = "management_agreement"
    agreement.payment_cycle = None
    agreement.payment_day = None
    agreement.deposit_amount = Decimal("0")
    agreement.management_fee_rate = Decimal("0.10")
    contract = db.get(TerminalContract, facts["terminal_id"])
    contract.contract_mode = "direct_lease"
    contract.rent_collector = "owner"
    today = date.fromisoformat(facts["effective_date"])
    entry = RentLedgerEntry(
        id=str(uuid4()),
        contract_kind="terminal",
        contract_id=contract.id,
        entry_type="owner_receipt_expected",
        period=today.strftime("%Y-%m"),
        period_start=today.replace(day=1),
        period_end=today,
        due_date=today,
        due_amount=Decimal("100.00"),
        origin="manual",
        basis_note="管理费真实HTTP测试租金义务",
        version=1,
    )
    statement = ManagementFeeStatement(
        id=str(uuid4()),
        owner_party_id=agreement.owner_party_id,
        period=entry.period,
        statement_number=f"MF-E2E-{uuid4().hex}",
        version=1,
    )
    db.add_all([entry, statement])
    db.commit()
    return facts | {
        "entry_id": entry.id,
        "statement_id": statement.id,
        "owner_id": agreement.owner_party_id,
    }


def _png():
    content = io.BytesIO()
    Image.new("RGB", (24, 24), "white").save(content, format="PNG")
    return content.getvalue()


def test_fee_receipt_deferral_stamp_confirmation_and_correction_http(
    authenticated_client,
    csrf_headers,
    db_session,
    tmp_path,
    monkeypatch,
):
    from src.services.asset_operations.management_fee_upload_service import (
        management_fee_upload_service,
    )

    monkeypatch.setattr(management_fee_upload_service, "uploads_root", tmp_path)
    client = authenticated_client
    facts = _seed_fee_sources(db_session, client._user_id)
    path = f"/api/v1/management-fee-statements/{facts['statement_id']}"
    initial = client.get(path)
    assert initial.status_code == 200, initial.text
    assert initial.json()["status"] == "collecting"
    assert Decimal(initial.json()["lines"][0]["scheduled_rent"]) == 100

    receipt = {
        "rent_ledger_entry_id": facts["entry_id"],
        "amount": "40.00",
        "occurred_on": facts["effective_date"],
        "expected_version": 1,
    }
    headers = csrf_headers | {"Idempotency-Key": str(uuid4())}
    recorded = client.post(f"{path}/owner-receipts", json=receipt, headers=headers)
    assert recorded.status_code == 200, recorded.text
    replay = client.post(f"{path}/owner-receipts", json=receipt, headers=headers)
    assert replay.status_code == 200 and replay.json()["idempotent"], replay.text
    assert replay.json()["id"] == recorded.json()["id"]
    conflict = client.post(
        f"{path}/owner-receipts", json=receipt | {"amount": "41.00"}, headers=headers
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"

    view = client.get(path).json()
    assert Decimal(view["fee_amount"]) == Decimal("4.00")
    deferred = client.post(
        f"{path}/deferrals",
        json={
            "rent_ledger_entry_id": facts["entry_id"],
            "reason": "余款下月核对",
            "expected_version": view["version"],
        },
        headers=csrf_headers | {"Idempotency-Key": str(uuid4())},
    )
    assert deferred.status_code == 200, deferred.text
    view = client.get(path).json()
    assert view["status"] == "pending_stamp"
    assert Decimal(view["lines"][0]["deferred_amount"]) == Decimal("60.00")
    uploaded = client.post(
        f"{path}/stamped-document",
        data={"expected_version": str(view["version"])},
        files={"file": ("盖章.png", _png(), "image/png")},
        headers=csrf_headers,
    )
    assert uploaded.status_code == 200, uploaded.text
    assert list(tmp_path.rglob("*.png"))
    confirm_payload = {"expected_version": uploaded.json()["version"]}
    confirm_headers = csrf_headers | {"Idempotency-Key": str(uuid4())}
    confirmed = client.post(
        f"{path}/confirmation", json=confirm_payload, headers=confirm_headers
    )
    assert confirmed.status_code == 200, confirmed.text
    confirm_replay = client.post(
        f"{path}/confirmation", json=confirm_payload, headers=confirm_headers
    )
    assert confirm_replay.status_code == 200 and confirm_replay.json()["idempotent"], (
        confirm_replay.text
    )
    frozen = client.get(path).json()
    assert frozen["status"] == "confirmed"
    assert Decimal(frozen["fee_amount"]) == Decimal("4.00")

    year = int(frozen["period"][:4])
    annual = client.get(
        "/api/v1/rent-ledgers", params={"ledger_type": "management_fee", "year": year}
    )
    assert annual.status_code == 200, annual.text
    owner = next(
        row
        for row in annual.json()["rows"]
        if row["owner_party_id"] == facts["owner_id"]
    )
    assert Decimal(owner["total_confirmed_amount"]) == Decimal("4.00")

    db_session.expire_all()
    agreement = db_session.get(UpstreamContract, facts["upstream_id"])
    agreement.management_fee_rate = Decimal("0.20")
    db_session.commit()
    assert client.get(path).json()["lines"] == frozen["lines"]
    next_statement = (
        db_session.query(ManagementFeeStatement)
        .filter(
            ManagementFeeStatement.owner_party_id == facts["owner_id"],
            ManagementFeeStatement.period > frozen["period"],
        )
        .one()
    )
    next_view = client.get(f"/api/v1/management-fee-statements/{next_statement.id}")
    assert next_view.status_code == 200, next_view.text
    assert Decimal(next_view.json()["lines"][0]["deferred_amount"]) == Decimal("60.00")

    corrected = client.post(
        f"{path}/successor",
        json={"expected_version": frozen["version"], "reason": "重新核对比例"},
        headers=csrf_headers | {"Idempotency-Key": str(uuid4())},
    )
    assert corrected.status_code == 200, corrected.text
    original = client.get(path).json()
    assert original["status"] == "superseded"
    assert original["lines"] == frozen["lines"]
    successor = client.get(
        f"/api/v1/management-fee-statements/{corrected.json()['successor_statement_id']}"
    )
    assert successor.status_code == 200, successor.text
    assert successor.json()["stamped_document_id"] is None
    annual_after = client.get(
        "/api/v1/rent-ledgers", params={"ledger_type": "management_fee", "year": year}
    )
    assert annual_after.status_code == 200, annual_after.text
    owner_after = next(
        row
        for row in annual_after.json()["rows"]
        if row["owner_party_id"] == facts["owner_id"]
    )
    assert Decimal(owner_after["total_confirmed_amount"]) == 0


def test_fee_whole_owner_scope_filters_real_database_queries(
    authenticated_client,
    csrf_headers,
    db_session,
    monkeypatch,
):
    """Supply a restricted scope at the resolver seam; keep real auth/CRUD/HTTP."""
    from src.services.party_scope_resolver import (
        EffectivePartyScope,
        party_scope_resolver,
    )

    client = authenticated_client
    visible = _seed_fee_sources(db_session, client._user_id)
    hidden = _seed_fee_sources(db_session, client._user_id)
    scope = EffectivePartyScope(
        user_id=client._user_id,
        source="explicit",
        scope_mode="owner",
        owner_party_ids=(visible["owner_id"],),
    )

    async def restricted_scope(db, *, user_id):
        assert user_id == client._user_id
        return scope

    monkeypatch.setattr(party_scope_resolver, "resolve", restricted_scope)
    period = visible["effective_date"][:7]
    listed = client.get("/api/v1/management-fee-statements", params={"period": period})
    assert listed.status_code == 200, listed.text
    assert {item["id"] for item in listed.json()["items"]} == {visible["statement_id"]}
    hidden_path = f"/api/v1/management-fee-statements/{hidden['statement_id']}"
    assert client.get(hidden_path).status_code == 404
    denied = client.post(
        f"{hidden_path}/deferrals",
        json={
            "rent_ledger_entry_id": hidden["entry_id"],
            "reason": "不可见单据",
            "expected_version": 1,
        },
        headers=csrf_headers | {"Idempotency-Key": str(uuid4())},
    )
    assert denied.status_code == 404, denied.text
    matrix = client.get(
        "/api/v1/rent-ledgers",
        params={"ledger_type": "management_fee", "year": int(period[:4])},
    )
    assert matrix.status_code == 200, matrix.text
    assert {row["owner_party_id"] for row in matrix.json()["rows"]} == {
        visible["owner_id"]
    }


def test_partial_manager_scope_cannot_read_a_whole_owner_statement(
    authenticated_client, db_session, monkeypatch
):
    """Exercise the whole-owner NOT EXISTS guard with actual PostgreSQL facts."""
    from src.models.attachment import Attachment
    from src.services.party_scope_resolver import (
        EffectivePartyScope,
        party_scope_resolver,
    )

    client = authenticated_client
    facts = _seed_fee_sources(db_session, client._user_id)
    other = _seed_fee_sources(db_session, client._user_id)
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
            created_by=client._user_id,
        )
    )
    db_session.flush()
    values.update(
        id=agreement_id,
        contract_number=f"MF-SCOPE-{uuid4().hex}",
        operator_party_id=other["owner_id"],
        scan_document_id=document_id,
    )
    db_session.add(UpstreamContract(**values))
    db_session.commit()
    manager_ids = (agreement.operator_party_id,)

    async def manager_scope(db, *, user_id):
        return EffectivePartyScope(
            user_id=user_id,
            source="explicit",
            scope_mode="manager",
            manager_party_ids=manager_ids,
        )

    monkeypatch.setattr(party_scope_resolver, "resolve", manager_scope)
    path = f"/api/v1/management-fee-statements/{facts['statement_id']}"
    assert client.get(path).status_code == 404
    params = {"ledger_type": "management_fee", "year": int(facts["effective_date"][:4])}
    denied = client.get("/api/v1/rent-ledgers", params=params)
    assert denied.status_code == 200, denied.text
    assert facts["owner_id"] not in {
        row["owner_party_id"] for row in denied.json()["rows"]
    }
    manager_ids = (agreement.operator_party_id, other["owner_id"])
    assert client.get(path).status_code == 200
    allowed = client.get("/api/v1/rent-ledgers", params=params)
    assert allowed.status_code == 200, allowed.text
    assert facts["owner_id"] in {
        row["owner_party_id"] for row in allowed.json()["rows"]
    }
