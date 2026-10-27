"""API contract tests for terminal-contract termination preview and commit."""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_core import PydanticUndefined

from src.api.v1 import terminal_contracts as module
from src.schemas.asset_operations import (
    ContractLifecycleEventResponse,
    TerminalContractRenewalRequest,
    TerminalContractResponse,
    TerminalContractTerminationCommitRequest,
    TerminalContractTerminationCoverageImpact,
    TerminalContractTerminationPreviewResponse,
    TerminalContractTerminationProposal,
    TerminalContractTerminationReversalProposal,
    TerminalContractUpdate,
)
from src.services.party_scope_resolver import EffectivePartyScope
from tests.fixtures.fake_credentials import fake_identifier


def _scope() -> EffectivePartyScope:
    return EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner-1"],
    )


def _proposal() -> TerminalContractTerminationProposal:
    return TerminalContractTerminationProposal.model_validate(
        {
            "effective_date": "2026-06-30",
            "termination_type": "early",
            "handover_status": "pending",
            "deposit_settlement_status": "pending",
            "reason": "提前退租",
        }
    )


def test_termination_routes_use_asset_ops_write_and_required_idempotency_header() -> (
    None
):
    routes = {route.path: route for route in module.router.routes}
    preview_route = routes["/terminal-contracts/{contract_id}/termination/preview"]
    commit_route = routes["/terminal-contracts/{contract_id}/termination"]

    assert preview_route.methods == {"POST"}
    assert commit_route.methods == {"POST"}
    for route in (preview_route, commit_route):
        authz_dependencies = [
            dependency.call
            for dependency in route.dependant.dependencies
            if type(dependency.call).__name__ == "AuthzPermissionChecker"
        ]
        assert len(authz_dependencies) == 1
        assert authz_dependencies[0].resource_type == "asset_ops"
        assert authz_dependencies[0].action == "write"
        denial = authz_dependencies[0].denial_error_factory()
        assert denial.code == "ASSET_OPS_PERMISSION_DENIED"
        assert denial.status_code == 403

    header_params = {
        param.alias: param for param in commit_route.dependant.header_params
    }
    assert header_params["Idempotency-Key"].default is PydanticUndefined


@pytest.mark.asyncio
async def test_termination_endpoints_bind_path_actor_scope_and_idempotency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = _scope()
    resolver = AsyncMock(return_value=scope)
    preview_response = TerminalContractTerminationPreviewResponse(
        contract_id="terminal-1",
        contract_number="TM-001",
        contract_version=3,
        effective_date=date(2026, 6, 30),
        last_valid_day=date(2026, 6, 29),
        coverage_impact=[
            TerminalContractTerminationCoverageImpact(
                asset_unit_id="unit-1",
                effective_from=date(2026, 1, 1),
                current_effective_to=date(2026, 12, 31),
                new_effective_to=date(2026, 6, 29),
            )
        ],
        warnings=["deposit_unsettled"],
        proposal=_proposal(),
        preview_token=fake_identifier("preview-token"),
        expires_at=datetime(2026, 10, 25, 9, 10, tzinfo=UTC),
    )
    commit_response = ContractLifecycleEventResponse.model_validate(
        {
            "id": "event-1",
            "contract_kind": "terminal",
            "contract_id": "terminal-1",
            "event_type": "terminated",
            "effective_date": date(2026, 6, 30),
            "termination_type": "early",
            "handover_status": "pending",
            "deposit_settlement_status": "pending",
            "reason": "提前退租",
            "created_by": "actor-1",
            "created_at": datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
            "idempotency_key": "terminate-1",
            "idempotent": False,
        }
    )
    service = SimpleNamespace(
        preview_terminal_termination=AsyncMock(return_value=preview_response),
        commit_terminal_termination=AsyncMock(return_value=commit_response),
    )
    monkeypatch.setattr(module.party_scope_resolver, "resolve", resolver)
    monkeypatch.setattr(module, "contract_lifecycle_command_service", service)
    db = MagicMock()
    current_user = SimpleNamespace(id="actor-1")

    preview_result = await module.preview_terminal_contract_termination(
        contract_id="terminal-1",
        payload=_proposal(),
        db=db,
        current_user=current_user,
    )
    commit_result = await module.commit_terminal_contract_termination(
        contract_id="terminal-1",
        payload=TerminalContractTerminationCommitRequest(
            preview_token=preview_result.preview_token,
            expected_version=3,
        ),
        idempotency_key="  terminate-request-1  ",
        db=db,
        current_user=current_user,
    )

    assert commit_result == commit_response
    assert resolver.await_count == 2
    preview_call = service.preview_terminal_termination.await_args
    assert preview_call.kwargs["contract_id"] == "terminal-1"
    assert preview_call.kwargs["actor_id"] == "actor-1"
    assert preview_call.kwargs["scope"] is scope
    assert preview_call.kwargs["proposal"] == _proposal()
    commit_call = service.commit_terminal_termination.await_args
    assert commit_call.kwargs["contract_id"] == "terminal-1"
    assert commit_call.kwargs["actor_id"] == "actor-1"
    assert commit_call.kwargs["scope"] is scope
    assert commit_call.kwargs["idempotency_key"] == "terminate-request-1"


def test_reversal_route_uses_asset_ops_write_and_required_idempotency_header() -> (
    None
):
    routes = {route.path: route for route in module.router.routes}
    reversal_route = routes["/terminal-contracts/{contract_id}/termination-reversal"]

    assert reversal_route.methods == {"POST"}
    authz_dependencies = [
        dependency.call
        for dependency in reversal_route.dependant.dependencies
        if type(dependency.call).__name__ == "AuthzPermissionChecker"
    ]
    assert len(authz_dependencies) == 1
    assert authz_dependencies[0].resource_type == "asset_ops"
    assert authz_dependencies[0].action == "write"

    header_params = {
        param.alias: param for param in reversal_route.dependant.header_params
    }
    assert header_params["Idempotency-Key"].default is PydanticUndefined


@pytest.mark.asyncio
async def test_reversal_endpoint_binds_path_actor_scope_and_idempotency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = _scope()
    resolver = AsyncMock(return_value=scope)
    reversal_response = ContractLifecycleEventResponse.model_validate(
        {
            "id": "event-reversal-1",
            "contract_kind": "terminal",
            "contract_id": "terminal-1",
            "event_type": "reversed",
            "effective_date": date(2026, 7, 1),
            "reversed_event_id": "event-1",
            "reason": "终止日期录入错误",
            "created_by": "actor-1",
            "created_at": datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
            "idempotency_key": "reverse-1",
            "idempotent": False,
        }
    )
    service = SimpleNamespace(
        reverse_terminal_termination=AsyncMock(return_value=reversal_response),
    )
    monkeypatch.setattr(module.party_scope_resolver, "resolve", resolver)
    monkeypatch.setattr(module, "contract_lifecycle_command_service", service)
    db = MagicMock()
    current_user = SimpleNamespace(id="actor-1")
    proposal = TerminalContractTerminationReversalProposal.model_validate(
        {
            "target_event_id": "event-1",
            "effective_date": "2026-07-01",
            "reason": "终止日期录入错误",
        }
    )

    result = await module.reverse_terminal_contract_termination(
        contract_id="terminal-1",
        payload=proposal,
        idempotency_key="  reverse-request-1  ",
        db=db,
        current_user=current_user,
    )

    assert result == reversal_response
    assert resolver.await_count == 1
    call = service.reverse_terminal_termination.await_args
    assert call.kwargs["contract_id"] == "terminal-1"
    assert call.kwargs["proposal"] == proposal
    assert call.kwargs["actor_id"] == "actor-1"
    assert call.kwargs["scope"] is scope
    assert call.kwargs["idempotency_key"] == "reverse-request-1"


def test_renewal_route_uses_asset_ops_write_and_required_idempotency_header() -> None:
    routes = {route.path: route for route in module.router.routes}
    renewal_route = routes["/terminal-contracts/{contract_id}/renewals"]

    assert renewal_route.methods == {"POST"}
    authz_dependencies = [
        dependency.call
        for dependency in renewal_route.dependant.dependencies
        if type(dependency.call).__name__ == "AuthzPermissionChecker"
    ]
    assert len(authz_dependencies) == 1
    assert authz_dependencies[0].resource_type == "asset_ops"
    assert authz_dependencies[0].action == "write"

    header_params = {
        param.alias: param for param in renewal_route.dependant.header_params
    }
    assert header_params["Idempotency-Key"].default is PydanticUndefined


@pytest.mark.asyncio
async def test_renewal_endpoint_binds_path_actor_scope_and_idempotency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = _scope()
    resolver = AsyncMock(return_value=scope)
    renewal_response = TerminalContractResponse.model_validate(
        {
            "contract_number": "TM-002",
            "contract_mode": "sublease",
            "tenant_party_id": "tenant-1",
            "lessor_party_id": "owner-1",
            "upstream_contract_id": "upstream-2",
            "start_date": date(2027, 1, 1),
            "end_date": date(2027, 12, 31),
            "deposit_amount": "20000",
            "rent_collector": "operator",
            "renewed_from_id": "terminal-1",
            "scan_document_id": fake_identifier("scan"),
            "asset_unit_ids": ["unit-1"],
            "rent_schedules": [],
            "id": "terminal-2",
            "version": 1,
            "created_at": datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
            "updated_at": datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
            "status": "scheduled",
            "warnings": [],
            "idempotent": False,
        }
    )
    service = SimpleNamespace(
        renew_terminal=AsyncMock(return_value=renewal_response),
    )
    monkeypatch.setattr(module.party_scope_resolver, "resolve", resolver)
    monkeypatch.setattr(module, "contract_lifecycle_command_service", service)
    db = MagicMock()
    current_user = SimpleNamespace(id="actor-1")
    proposal = TerminalContractRenewalRequest.model_validate(
        {
            "contract_number": "TM-002",
            "upstream_contract_id": "upstream-2",
            "start_date": "2027-01-01",
            "end_date": "2027-12-31",
            "deposit_amount": "20000",
            "scan_document_id": "scan-new-terminal",
            "scan_owner_id": "intake-session-2",
        }
    )

    result = await module.renew_terminal_contract(
        contract_id="terminal-1",
        payload=proposal,
        idempotency_key="  renew-terminal-request-1  ",
        db=db,
        current_user=current_user,
    )

    assert result == renewal_response
    assert resolver.await_count == 1
    call = service.renew_terminal.await_args
    assert call.kwargs["contract_id"] == "terminal-1"
    assert call.kwargs["request"] == proposal
    assert call.kwargs["actor_id"] == "actor-1"
    assert call.kwargs["scope"] is scope
    assert call.kwargs["idempotency_key"] == "renew-terminal-request-1"


def test_list_and_detail_routes_use_asset_ops_read() -> None:
    routes = {
        (route.path, next(iter(route.methods))): route
        for route in module.router.routes
    }
    list_route = routes[("/terminal-contracts", "GET")]
    detail_route = routes[("/terminal-contracts/{contract_id}", "GET")]

    assert list_route.methods == {"GET"}
    assert detail_route.methods == {"GET"}
    for route in (list_route, detail_route):
        authz_dependencies = [
            dependency.call
            for dependency in route.dependant.dependencies
            if type(dependency.call).__name__ == "AuthzPermissionChecker"
        ]
        assert len(authz_dependencies) == 1
        assert authz_dependencies[0].resource_type == "asset_ops"
        assert authz_dependencies[0].action == "read"


@pytest.mark.asyncio
async def test_list_and_detail_endpoints_bind_scope_and_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = _scope()
    resolver = AsyncMock(return_value=scope)
    detail_response = TerminalContractResponse.model_validate(
        {
            "contract_number": "TM-001",
            "contract_mode": "sublease",
            "tenant_party_id": "tenant-1",
            "lessor_party_id": "owner-1",
            "upstream_contract_id": None,
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 12, 31),
            "deposit_amount": "0",
            "rent_collector": "operator",
            "scan_document_id": "scan",
            "asset_unit_ids": ["unit-1"],
            "rent_schedules": [],
            "id": "terminal-1",
            "version": 1,
            "created_at": datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
            "updated_at": datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
            "status": "active",
            "warnings": [],
            "idempotent": False,
        }
    )
    query_service = SimpleNamespace(
        list_terminal_contracts=AsyncMock(return_value=([detail_response], 1)),
        get_terminal_contract=AsyncMock(return_value=detail_response),
    )
    monkeypatch.setattr(module.party_scope_resolver, "resolve", resolver)
    monkeypatch.setattr(module, "asset_operations_query_service", query_service)
    db = MagicMock()
    current_user = SimpleNamespace(id="actor-1")

    list_result = await module.list_terminal_contracts(
        contract_mode="sublease",
        upstream_contract_id=None,
        q="TM-001",
        offset=0,
        limit=20,
        db=db,
        current_user=current_user,
    )
    detail_result = await module.get_terminal_contract(
        contract_id="terminal-1",
        db=db,
        current_user=current_user,
    )

    assert list_result.total == 1
    assert list_result.items[0].id == "terminal-1"
    assert detail_result.id == "terminal-1"
    list_call = query_service.list_terminal_contracts.await_args
    assert list_call.kwargs["scope"] is scope
    assert list_call.kwargs["contract_mode"] == "sublease"
    assert list_call.kwargs["query"] == "TM-001"
    detail_call = query_service.get_terminal_contract.await_args
    assert detail_call.args == (db, "terminal-1")
    assert detail_call.kwargs["scope"] is scope


def test_update_route_uses_asset_ops_write() -> None:
    routes = {route.path: route for route in module.router.routes}
    update_route = routes["/terminal-contracts/{contract_id}"]

    assert update_route.methods == {"PATCH"}
    authz_dependencies = [
        dependency.call
        for dependency in update_route.dependant.dependencies
        if type(dependency.call).__name__ == "AuthzPermissionChecker"
    ]
    assert len(authz_dependencies) == 1
    assert authz_dependencies[0].resource_type == "asset_ops"
    assert authz_dependencies[0].action == "write"


@pytest.mark.asyncio
async def test_update_endpoint_binds_path_actor_and_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = _scope()
    resolver = AsyncMock(return_value=scope)
    update_response = TerminalContractResponse.model_validate(
        {
            "contract_number": "TM-001",
            "contract_mode": "sublease",
            "tenant_party_id": "tenant-1",
            "lessor_party_id": "owner-1",
            "upstream_contract_id": "upstream-1",
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 12, 31),
            "deposit_amount": "0",
            "rent_collector": "operator",
            "scan_document_id": "scan",
            "asset_unit_ids": ["unit-1"],
            "rent_schedules": [],
            "id": "terminal-1",
            "version": 3,
            "created_at": datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
            "updated_at": datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
            "status": "active",
            "warnings": [],
            "idempotent": False,
        }
    )
    command_service = SimpleNamespace(
        update_terminal=AsyncMock(return_value=update_response),
    )
    monkeypatch.setattr(module.party_scope_resolver, "resolve", resolver)
    monkeypatch.setattr(module, "asset_contract_command_service", command_service)
    db = MagicMock()
    current_user = SimpleNamespace(id="actor-1")
    payload = TerminalContractUpdate.model_validate(
        {"expected_version": 2, "end_date": "2026-12-31"}
    )

    result = await module.update_terminal_contract(
        contract_id="terminal-1",
        payload=payload,
        db=db,
        current_user=current_user,
    )

    assert result == update_response
    call = command_service.update_terminal.await_args
    assert call.kwargs["contract_id"] == "terminal-1"
    assert call.kwargs["request"] == payload
    assert call.kwargs["actor_id"] == "actor-1"
    assert call.kwargs["scope"] is scope
