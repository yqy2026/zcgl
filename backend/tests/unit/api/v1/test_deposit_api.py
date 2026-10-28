"""Deposit HTTP boundaries keep capabilities, scope and source-only writes."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic_core import PydanticUndefined

from src.api.v1 import deposits
from src.core.exception_handler import setup_exception_handlers
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = pytest.mark.unit


def test_all_four_routes_require_matching_asset_operations_capability():
    assert len(deposits.router.routes) == 4
    for route in deposits.router.routes:
        guards = [
            dependency.call
            for dependency in route.dependant.dependencies
            if type(dependency.call).__name__ == "AuthzPermissionChecker"
        ]
        assert len(guards) == 1
        assert guards[0].resource_type == "asset_ops"
        assert guards[0].action == ("read" if route.methods == {"GET"} else "write")
        if route.methods == {"POST"}:
            headers = {param.alias: param for param in route.dependant.header_params}
            assert headers["Idempotency-Key"].default is PydanticUndefined


@pytest.fixture
def boundary(monkeypatch):
    app = FastAPI()
    setup_exception_handlers(app)
    app.include_router(deposits.router)
    db = MagicMock()
    scope = EffectivePartyScope(
        user_id="actor", source="explicit", scope_mode="unrestricted"
    )
    resolver = AsyncMock(return_value=scope)
    monkeypatch.setattr(deposits.party_scope_resolver, "resolve", resolver)
    services = SimpleNamespace(
        list=AsyncMock(
            return_value={"items": [], "total": 0, "page": 1, "page_size": 20}
        ),
        get=AsyncMock(
            return_value={
                "id": "deposit",
                "contract_kind": "terminal",
                "contract_id": "contract",
                "collector": "operator",
                "agreed_amount": "100",
                "held_amount": "0",
                "carried_in_amount": "0",
                "carried_out_amount": "0",
                "direction": "receivable",
                "outstanding_amount": "100",
                "status": "receivable_uncollected",
                "version": 1,
                "ended": False,
                "read_only": False,
            }
        ),
        register=AsyncMock(
            return_value={
                "id": "record",
                "deposit_entry_id": "deposit",
                "record_type": "collect",
                "amount": "10",
                "occurred_on": "2026-10-28",
                "created_by": "actor",
                "created_at": datetime.now(UTC),
                "version": 2,
            }
        ),
        reverse=AsyncMock(
            return_value={
                "id": "undo",
                "deposit_entry_id": "deposit",
                "record_type": "reversal",
                "amount": "10",
                "occurred_on": "2026-10-28",
                "created_by": "actor",
                "created_at": datetime.now(UTC),
                "version": 3,
                "reverses_record_id": "record",
            }
        ),
    )
    for name in ("list", "get"):
        monkeypatch.setattr(
            deposits.deposit_query_service, name, getattr(services, name)
        )
    for name in ("register", "reverse"):
        monkeypatch.setattr(
            deposits.deposit_command_service, name, getattr(services, name)
        )
    app.dependency_overrides[deposits.get_async_db] = lambda: db
    app.dependency_overrides[deposits.get_current_active_user] = (
        lambda: SimpleNamespace(id="actor")
    )
    for route in deposits.router.routes:
        for dependency in route.dependant.dependencies:
            if type(dependency.call).__name__ == "AuthzPermissionChecker":
                app.dependency_overrides[dependency.call] = lambda: None
    with TestClient(app) as client:
        yield client, services, resolver, db, scope


def test_read_routes_pass_resolved_scope_and_filters(boundary):
    client, services, resolver, db, scope = boundary
    assert (
        client.get(
            "/deposits",
            params={
                "status": "settled",
                "contract_kind": "terminal",
                "contract_id": "contract",
                "party_id": "party",
                "project_id": "project",
            },
        ).status_code
        == 200
    )
    services.list.assert_awaited_once_with(
        db,
        scope=scope,
        status="settled",
        contract_kind="terminal",
        contract_id="contract",
        party_id="party",
        project_id="project",
        page=1,
        page_size=20,
    )
    assert client.get("/deposits/deposit").status_code == 200
    services.get.assert_awaited_once_with(db, entry_id="deposit", scope=scope)
    assert resolver.await_count == 2


@pytest.mark.parametrize("reverse", [False, True])
def test_write_routes_pass_scope_actor_and_normalized_idempotency_key(
    boundary, reverse
):
    client, services, resolver, db, scope = boundary
    path = (
        "/deposit-records/record/reversal" if reverse else "/deposits/deposit/records"
    )
    payload = (
        {"reason": "撤销误录", "expected_version": 2}
        if reverse
        else {
            "record_type": "collect",
            "amount": "10",
            "occurred_on": "2026-10-28",
            "expected_version": 1,
        }
    )
    assert (
        client.post(
            path, json=payload, headers={"Idempotency-Key": "  request-key  "}
        ).status_code
        == 200
    )
    service = services.reverse if reverse else services.register
    args = service.await_args
    assert args.args == (db,)
    assert args.kwargs["scope"] is scope
    assert args.kwargs["actor_id"] == "actor"
    assert args.kwargs["idempotency_key"] == "request-key"
    assert args.kwargs["record_id" if reverse else "entry_id"] == (
        "record" if reverse else "deposit"
    )
    resolver.assert_awaited_once_with(db, user_id="actor")


@pytest.mark.parametrize("headers", [{}, {"Idempotency-Key": "   "}])
@pytest.mark.parametrize("reverse", [False, True])
def test_missing_or_blank_request_key_is_rejected_before_service(
    boundary, headers, reverse
):
    client, services, *_ = boundary
    path = (
        "/deposit-records/record/reversal" if reverse else "/deposits/deposit/records"
    )
    payload = (
        {"reason": "误录", "expected_version": 1}
        if reverse
        else {
            "record_type": "collect",
            "amount": "10",
            "occurred_on": "2026-10-28",
            "expected_version": 1,
        }
    )
    assert client.post(path, json=payload, headers=headers).status_code == 422
    services.register.assert_not_awaited()
    services.reverse.assert_not_awaited()


@pytest.mark.parametrize("reverse", [False, True])
def test_derived_balance_cannot_be_written_through_either_command(boundary, reverse):
    client, services, *_ = boundary
    path = (
        "/deposit-records/record/reversal" if reverse else "/deposits/deposit/records"
    )
    payload = {"expected_version": 1, "held_amount": "999"}
    if reverse:
        payload["reason"] = "误录"
    else:
        payload.update(record_type="collect", amount="10", occurred_on="2026-10-28")
    response = client.post(path, json=payload, headers={"Idempotency-Key": "derived"})
    assert response.status_code == 422
    assert "DERIVED_FIELD_NOT_WRITABLE" in response.text
    services.register.assert_not_awaited()
    services.reverse.assert_not_awaited()
