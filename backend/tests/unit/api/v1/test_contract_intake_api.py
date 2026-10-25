"""HTTP boundary tests for the single signed-contract intake entrypoint."""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic_core import PydanticUndefined

from src.api.v1 import contract_intake_sessions as module
from src.schemas.asset_operations import (
    ContractIntakeSessionResponse,
    UpstreamContractConfirmRequest,
    UpstreamContractResponse,
)
from src.services.party_scope_resolver import EffectivePartyScope


def _session() -> ContractIntakeSessionResponse:
    return ContractIntakeSessionResponse(
        id="session-1",
        document_id="document-1",
        contract_type="upstream_lease",
        status="ready_for_review",
        candidate_fields={},
        warnings=[],
        expires_at=datetime(2026, 10, 24, 5, 0, tzinfo=UTC),
    )


def _upstream_response() -> UpstreamContractResponse:
    return UpstreamContractResponse.model_validate(
        {
            "id": "upstream-1",
            "contract_number": "UP-001",
            "contract_type": "lease",
            "name": "承租合同",
            "owner_party_id": "owner-1",
            "operator_party_id": "operator-1",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "payment_cycle": "monthly",
            "deposit_amount": "0",
            "scan_document_id": "document-1",
            "asset_unit_ids": ["unit-1"],
            "rent_schedules": [],
            "version": 1,
            "created_at": "2026-10-24T04:00:00Z",
            "updated_at": "2026-10-24T04:00:00Z",
            "status": "expiring",
            "warnings": [],
        }
    )


def test_intake_routes_are_self_registered_and_confirm_requires_idempotency() -> None:
    routes = {route.path: route for route in module.router.routes}
    expected = {
        "/contract-intake-sessions",
        "/contract-intake-sessions/{session_id}",
        "/contract-intake-sessions/{session_id}/confirm-upstream",
        "/contract-intake-sessions/{session_id}/confirm-terminal",
        "/contract-intake-sessions/{session_id}/cancel",
    }
    assert expected <= set(routes)
    for path in expected:
        authz_dependencies = [
            dependency.call
            for dependency in routes[path].dependant.dependencies
            if type(dependency.call).__name__ == "AuthzPermissionChecker"
        ]
        assert len(authz_dependencies) == 1
        assert authz_dependencies[0].resource_type == "asset_ops"
        assert authz_dependencies[0].action == "write"

    for path in (
        "/contract-intake-sessions/{session_id}/confirm-upstream",
        "/contract-intake-sessions/{session_id}/confirm-terminal",
    ):
        headers = {param.alias: param for param in routes[path].dependant.header_params}
        assert headers["Idempotency-Key"].default is PydanticUndefined


@pytest.mark.asyncio
async def test_confirm_endpoint_resolves_actor_scope_and_forwards_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner-1"],
    )
    resolver = AsyncMock(return_value=scope)
    service = SimpleNamespace(
        confirm_upstream=AsyncMock(return_value=_upstream_response())
    )
    monkeypatch.setattr(module, "_intake_service", lambda: service)
    monkeypatch.setattr(module.party_scope_resolver, "resolve", resolver)
    request = UpstreamContractConfirmRequest.model_validate(
        {
            "contract_number": "UP-001",
            "name": "承租合同",
            "owner_party_id": "owner-1",
            "operator_party_id": "operator-1",
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 12, 31),
            "payment_cycle": "monthly",
            "asset_unit_ids": ["unit-1"],
        }
    )

    response = await module.confirm_upstream_contract_intake(
        "session-1",
        request,
        "  request-1  ",
        db=SimpleNamespace(),
        current_user=SimpleNamespace(id="actor-1"),
        _authz=None,
    )

    assert response.id == "upstream-1"
    resolver.assert_awaited_once_with(
        service.confirm_upstream.await_args.args[0], user_id="actor-1"
    )
    assert service.confirm_upstream.await_args.kwargs["scope"] is scope
    assert service.confirm_upstream.await_args.kwargs["idempotency_key"] == "request-1"
