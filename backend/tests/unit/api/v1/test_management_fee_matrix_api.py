"""Management fee matrix keeps the existing authenticated ledger boundary."""

from types import SimpleNamespace as Row
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from src.api.v1 import rent_ledger_queries as api
from src.crud.management_fee_matrix import management_fee_matrix_repository
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = pytest.mark.unit


def test_fee_matrix_http_dispatches_whole_scope_and_serializes_decimal(monkeypatch):
    app = FastAPI()
    app.include_router(api.router)
    scope = EffectivePartyScope(
        user_id="actor", source="explicit", scope_mode="unrestricted"
    )
    db = MagicMock()
    monkeypatch.setattr(
        api.party_scope_resolver, "resolve", AsyncMock(return_value=scope)
    )
    service = AsyncMock(
        return_value={
            "ledger_type": "management_fee",
            "year": 2026,
            "current_month": 10,
            "rows": [],
            "total_confirmed_amount": "12.34",
        }
    )
    monkeypatch.setattr(api.management_fee_matrix_service, "matrix", service)
    app.dependency_overrides[api.get_async_db] = lambda: db
    app.dependency_overrides[api.get_current_active_user] = lambda: Row(id="actor")
    for route in api.router.routes:
        for dependency in route.dependant.dependencies:
            if type(dependency.call).__name__ == "AuthzPermissionChecker":
                assert dependency.call.resource_type == "asset_ops"
                assert dependency.call.action == "read"
                app.dependency_overrides[dependency.call] = lambda: None
    with TestClient(app) as client:
        response = client.get(
            "/rent-ledgers", params={"ledger_type": "management_fee", "year": 2026}
        )
        assert response.status_code == 200
        assert response.json()["total_confirmed_amount"] == "12.34"
        service.assert_awaited_once_with(db, scope=scope, year=2026)
        assert (
            client.get(
                "/rent-ledgers", params={"ledger_type": "management_fee", "year": 9999}
            ).status_code
            == 422
        )


@pytest.mark.asyncio
async def test_matrix_query_excludes_superseded_and_partial_manager_scope():
    scope = EffectivePartyScope(
        user_id="actor",
        source="explicit",
        scope_mode="manager",
        manager_party_ids=("manager",),
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(all=lambda: []))
    assert (
        await management_fee_matrix_repository.list_year(db, scope=scope, year=2026)
        == ()
    )
    sql = str(
        db.execute.call_args.args[0].compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "2026-01" in sql and "2026-12" in sql
    assert "superseded" in sql
    assert "NOT (EXISTS" in sql
    assert "operator_party_id NOT IN" in sql
    assert "JOIN parties" in sql
