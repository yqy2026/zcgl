"""Management fee HTTP boundaries enforce capability and source-only writes."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace as Row
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1 import management_fee_statements as api
from src.core.exception_handler import BaseBusinessError, setup_exception_handlers
from src.schemas.management_fee_responses import (
    ManagementFeeListResponse,
    ManagementFeeStatementResponse,
)
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = pytest.mark.unit


def public_statement():
    return ManagementFeeStatementResponse(
        id="st",
        owner_party_id="owner",
        period="2026-10",
        statement_number="MF-10",
        version=2,
        status="collecting",
        deadline=date(2026, 11, 30),
        upstream_contract_ids=["up"],
        base_amount=Decimal("1234.50"),
        fee_amount=Decimal("123.45"),
        stamped_document_id=None,
        confirmed_at=None,
        confirmed_by=None,
        predecessor_statement_id=None,
        successor_statement_id=None,
        lines=[],
        carried_waiting_hint=False,
        upstream_missing_entry_ids=[],
        upstream_missing_warning=None,
    )


def test_successful_list_exposes_public_status_decimal_and_scope(boundary, monkeypatch):
    client, commands, db, scope, app = boundary
    service = AsyncMock(
        return_value=ManagementFeeListResponse(items=[public_statement()], total=1)
    )
    monkeypatch.setattr(api.management_fee_response_service, "list", service)
    response = client.get("/management-fee-statements", params={"period": "2026-10"})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    item = response.json()["items"][0]
    assert item["status"] == "collecting"
    assert item["base_amount"] == "1234.50"
    assert item["fee_amount"] == "123.45"
    assert item["deadline"] == "2026-11-30"
    service.assert_awaited_once_with(db, period="2026-10", scope=scope)


def test_successful_detail_exposes_public_status_decimal_and_scope(
    boundary, monkeypatch
):
    client, commands, db, scope, app = boundary
    service = AsyncMock(return_value=public_statement())
    monkeypatch.setattr(api.management_fee_response_service, "get", service)
    response = client.get("/management-fee-statements/st")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "st"
    assert body["status"] == "collecting"
    assert body["base_amount"] == "1234.50"
    assert body["fee_amount"] == "123.45"
    assert body["stamped_document_id"] is None
    service.assert_awaited_once_with(db, statement_id="st", scope=scope)


def test_seven_routes_require_matching_capability_and_write_keys():
    assert len(api.router.routes) == 7
    for route in api.router.routes:
        guards = [
            dep.call
            for dep in route.dependant.dependencies
            if type(dep.call).__name__ == "AuthzPermissionChecker"
        ]
        assert len(guards) == 1
        assert guards[0].resource_type == "asset_ops"
        assert guards[0].action == ("read" if route.methods == {"GET"} else "write")
        if route.methods == {"POST"} and not route.path.endswith("/stamped-document"):
            assert "Idempotency-Key" in {
                param.alias for param in route.dependant.header_params
            }


@pytest.fixture
def boundary(monkeypatch):
    app = FastAPI()
    setup_exception_handlers(app)
    app.include_router(api.router)
    db = MagicMock()
    scope = EffectivePartyScope(
        user_id="actor", source="explicit", scope_mode="unrestricted"
    )
    monkeypatch.setattr(
        api.party_scope_resolver, "resolve", AsyncMock(return_value=scope)
    )
    commands = {}
    for name, service, method in (
        ("deferrals", api.management_fee_command_service, "defer_line"),
        ("confirmation", api.management_fee_confirmation_service, "confirm"),
        ("successor", api.management_fee_confirmation_service, "supersede"),
        ("stamped-document", api.management_fee_upload_service, "upload"),
    ):
        result = {"statement_id": "st", "version": 2, "idempotent": False}
        if name == "successor":
            result["successor_statement_id"] = "new"
        if name == "stamped-document":
            result.update(document_id="doc", fee_amount="10.00")
        mock = AsyncMock(return_value=result)
        monkeypatch.setattr(service, method, mock)
        commands[name] = mock
    app.dependency_overrides[api.get_async_db] = lambda: db
    app.dependency_overrides[api.get_current_active_user] = lambda: Row(id="actor")
    for route in api.router.routes:
        for dependency in route.dependant.dependencies:
            if type(dependency.call).__name__ == "AuthzPermissionChecker":
                app.dependency_overrides[dependency.call] = lambda: None
    with TestClient(app) as client:
        yield client, commands, db, scope, app


@pytest.mark.parametrize(
    "command,payload",
    [
        (
            "deferrals",
            {
                "rent_ledger_entry_id": "rent",
                "reason": "下月补齐",
                "expected_version": 1,
            },
        ),
        ("confirmation", {"expected_version": 1}),
        ("successor", {"expected_version": 1, "reason": "有误"}),
    ],
)
def test_commands_forward_actor_scope_and_normalized_key(boundary, command, payload):
    client, commands, db, scope, app = boundary
    response = client.post(
        f"/management-fee-statements/st/{command}",
        json=payload,
        headers={"Idempotency-Key": " key "},
    )
    assert response.status_code == 200
    args = commands[command].await_args
    assert args.args == (db,)
    assert args.kwargs["statement_id"] == "st"
    assert args.kwargs["actor_id"] == "actor"
    assert args.kwargs["scope"] is scope
    assert args.kwargs["idempotency_key"] == "key"


@pytest.mark.parametrize("headers", [{}, {"Idempotency-Key": "  "}])
def test_confirmation_requires_nonblank_key_before_service(boundary, headers):
    client, commands, *_ = boundary
    assert (
        client.post(
            "/management-fee-statements/st/confirmation",
            json={"expected_version": 1},
            headers=headers,
        ).status_code
        == 422
    )
    commands["confirmation"].assert_not_awaited()


def test_derived_amount_is_rejected_before_confirmation(boundary):
    client, commands, *_ = boundary
    response = client.post(
        "/management-fee-statements/st/confirmation",
        json={"expected_version": 1, "fee_amount": 100},
        headers={"Idempotency-Key": "key"},
    )
    assert response.status_code == 422
    commands["confirmation"].assert_not_awaited()


def test_stamp_is_multipart_and_passes_file_and_expected_version(boundary):
    client, commands, db, scope, app = boundary
    response = client.post(
        "/management-fee-statements/st/stamped-document",
        data={"expected_version": "1"},
        files={"file": ("stamp.pdf", b"%PDF-1.7", "application/pdf")},
    )
    assert response.status_code == 200
    args = commands["stamped-document"].await_args
    assert args.kwargs["expected_version"] == 1
    assert args.kwargs["file"].filename == "stamp.pdf"
    assert args.kwargs["scope"] is scope
    assert args.kwargs["actor_id"] == "actor"


def test_invalid_month_preserves_service_business_error(boundary, monkeypatch):
    client, *_ = boundary
    monkeypatch.setattr(
        api.management_fee_response_service,
        "list",
        AsyncMock(
            side_effect=BaseBusinessError(
                message="月份无效", code="INVALID_PERIOD", status_code=400
            )
        ),
    )
    assert (
        client.get(
            "/management-fee-statements", params={"period": "2026-13"}
        ).status_code
        == 400
    )


def test_owner_receipt_uses_rent_record_response_and_fixed_fact_payload(
    boundary, monkeypatch
):
    client, commands, db, scope, app = boundary
    service = AsyncMock(
        return_value={
            "id": "receipt",
            "ledger_entry_id": "rent",
            "record_type": "owner_reported_receipt",
            "amount": "10",
            "occurred_on": "2026-10-29",
            "version": 2,
        }
    )
    monkeypatch.setattr(api.management_fee_owner_receipt_service, "register", service)
    payload = {
        "rent_ledger_entry_id": "rent",
        "amount": "10",
        "occurred_on": "2026-10-29",
        "expected_version": 1,
    }
    response = client.post(
        "/management-fee-statements/st/owner-receipts",
        json=payload,
        headers={"Idempotency-Key": " key "},
    )
    assert response.status_code == 200
    assert service.await_args.kwargs["request"].rent_ledger_entry_id == "rent"
    assert service.await_args.kwargs["scope"] is scope
    assert service.await_args.kwargs["idempotency_key"] == "key"
    payload["record_type"] = "receipt"
    assert (
        client.post(
            "/management-fee-statements/st/owner-receipts",
            json=payload,
            headers={"Idempotency-Key": "key"},
        ).status_code
        == 422
    )
