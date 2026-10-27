"""API contract tests for upstream-contract exit preview, commit and reversal."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_core import PydanticUndefined

from src.api.v1 import upstream_contracts as module
from src.schemas.asset_operations import (
    ContractLifecycleEventResponse,
    UpstreamContractExitCommitRequest,
    UpstreamContractExitCoverageImpact,
    UpstreamContractExitPreviewResponse,
    UpstreamContractExitProposal,
    UpstreamContractExitReversalProposal,
    UpstreamContractRenewalRequest,
    UpstreamContractResponse,
    UpstreamContractUpdate,
)
from src.services.party_scope_resolver import EffectivePartyScope
from tests.fixtures.fake_credentials import fake_identifier


def _scope() -> EffectivePartyScope:
    return EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="manager",
        manager_party_ids=["operator-1"],
    )


def _proposal() -> UpstreamContractExitProposal:
    return UpstreamContractExitProposal.model_validate(
        {"effective_date": "2026-06-30", "reason": "提前解除承租合同"}
    )


def test_exit_routes_use_asset_ops_write_and_required_idempotency_header() -> None:
    routes = {route.path: route for route in module.router.routes}
    preview_route = routes["/upstream-contracts/{contract_id}/exit/preview"]
    commit_route = routes["/upstream-contracts/{contract_id}/exit"]
    reversal_route = routes["/upstream-contracts/{contract_id}/exit-reversal"]

    assert preview_route.methods == {"POST"}
    assert commit_route.methods == {"POST"}
    assert reversal_route.methods == {"POST"}
    for route in (preview_route, commit_route, reversal_route):
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

    for route in (commit_route, reversal_route):
        header_params = {
            param.alias: param for param in route.dependant.header_params
        }
        assert header_params["Idempotency-Key"].default is PydanticUndefined


@pytest.mark.asyncio
async def test_exit_endpoints_bind_path_actor_scope_and_idempotency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = _scope()
    resolver = AsyncMock(return_value=scope)
    preview_response = UpstreamContractExitPreviewResponse(
        contract_id="upstream-1",
        contract_number="UP-001",
        contract_version=2,
        deposit_amount=Decimal("50000"),
        effective_date=date(2026, 6, 30),
        last_valid_day=date(2026, 6, 29),
        coverage_impact=[
            UpstreamContractExitCoverageImpact(
                asset_unit_id="unit-1",
                effective_from=date(2026, 1, 1),
                current_effective_to=date(2026, 12, 31),
                new_effective_to=date(2026, 6, 29),
            )
        ],
        proposal=_proposal(),
        preview_token=fake_identifier("preview-token"),
        expires_at=datetime(2026, 10, 25, 9, 10, tzinfo=UTC),
    )
    exit_response = ContractLifecycleEventResponse.model_validate(
        {
            "id": "event-exit-1",
            "contract_kind": "upstream",
            "contract_id": "upstream-1",
            "event_type": "exited",
            "effective_date": date(2026, 6, 30),
            "reason": "提前解除承租合同",
            "created_by": "actor-1",
            "created_at": datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
            "idempotency_key": "exit-1",
            "idempotent": False,
        }
    )
    reversal_response = ContractLifecycleEventResponse.model_validate(
        {
            "id": "event-exit-reversal-1",
            "contract_kind": "upstream",
            "contract_id": "upstream-1",
            "event_type": "reversed",
            "effective_date": date(2026, 7, 1),
            "reversed_event_id": "event-exit-1",
            "reason": "退出日期录入错误",
            "created_by": "actor-1",
            "created_at": datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
            "idempotency_key": "exit-reversal-1",
            "idempotent": False,
        }
    )
    service = SimpleNamespace(
        preview_upstream_exit=AsyncMock(return_value=preview_response),
        commit_upstream_exit=AsyncMock(return_value=exit_response),
        reverse_upstream_exit=AsyncMock(return_value=reversal_response),
    )
    monkeypatch.setattr(module.party_scope_resolver, "resolve", resolver)
    monkeypatch.setattr(module, "contract_lifecycle_command_service", service)
    db = MagicMock()
    current_user = SimpleNamespace(id="actor-1")

    preview_result = await module.preview_upstream_contract_exit(
        contract_id="upstream-1",
        payload=_proposal(),
        db=db,
        current_user=current_user,
    )
    exit_result = await module.commit_upstream_contract_exit(
        contract_id="upstream-1",
        payload=UpstreamContractExitCommitRequest(
            preview_token=preview_result.preview_token,
            expected_version=2,
        ),
        idempotency_key="  exit-request-1  ",
        db=db,
        current_user=current_user,
    )
    reversal_result = await module.reverse_upstream_contract_exit(
        contract_id="upstream-1",
        payload=UpstreamContractExitReversalProposal.model_validate(
            {
                "target_event_id": "event-exit-1",
                "effective_date": "2026-07-01",
                "reason": "退出日期录入错误",
            }
        ),
        idempotency_key="  exit-reversal-request-1  ",
        db=db,
        current_user=current_user,
    )

    assert exit_result == exit_response
    assert reversal_result == reversal_response
    assert resolver.await_count == 3
    preview_call = service.preview_upstream_exit.await_args
    assert preview_call.kwargs["contract_id"] == "upstream-1"
    assert preview_call.kwargs["actor_id"] == "actor-1"
    assert preview_call.kwargs["scope"] is scope
    exit_call = service.commit_upstream_exit.await_args
    assert exit_call.kwargs["contract_id"] == "upstream-1"
    assert exit_call.kwargs["scope"] is scope
    assert exit_call.kwargs["idempotency_key"] == "exit-request-1"
    reversal_call = service.reverse_upstream_exit.await_args
    assert reversal_call.kwargs["contract_id"] == "upstream-1"
    assert reversal_call.kwargs["scope"] is scope
    assert reversal_call.kwargs["idempotency_key"] == "exit-reversal-request-1"


def test_renewal_route_uses_asset_ops_write_and_required_idempotency_header() -> None:
    routes = {route.path: route for route in module.router.routes}
    renewal_route = routes["/upstream-contracts/{contract_id}/renewals"]

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
    renewal_response = UpstreamContractResponse.model_validate(
        {
            "contract_number": "UP-002",
            "contract_type": "lease",
            "name": "续签上游合同",
            "owner_party_id": "owner-1",
            "operator_party_id": "operator-1",
            "start_date": date(2027, 1, 1),
            "end_date": date(2029, 12, 31),
            "payment_cycle": "monthly",
            "payment_day": 15,
            "deposit_amount": Decimal("50000"),
            "renewed_from_id": "upstream-1",
            "scan_document_id": fake_identifier("scan"),
            "asset_unit_ids": ["unit-1"],
            "rent_schedules": [],
            "id": "upstream-2",
            "version": 1,
            "created_at": datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
            "updated_at": datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
            "status": "scheduled",
            "warnings": [],
            "idempotent": False,
        }
    )
    service = SimpleNamespace(
        renew_upstream=AsyncMock(return_value=renewal_response),
    )
    monkeypatch.setattr(module.party_scope_resolver, "resolve", resolver)
    monkeypatch.setattr(module, "contract_lifecycle_command_service", service)
    db = MagicMock()
    current_user = SimpleNamespace(id="actor-1")
    proposal = UpstreamContractRenewalRequest.model_validate(
        {
            "contract_number": "UP-002",
            "name": "续签上游合同",
            "start_date": "2027-01-01",
            "end_date": "2029-12-31",
            "payment_cycle": "monthly",
            "payment_day": 15,
            "deposit_amount": "50000",
            "scan_document_id": "scan-new",
            "scan_owner_id": "intake-session-1",
        }
    )

    result = await module.renew_upstream_contract(
        contract_id="upstream-1",
        payload=proposal,
        idempotency_key="  renew-request-1  ",
        db=db,
        current_user=current_user,
    )

    assert result == renewal_response
    assert resolver.await_count == 1
    call = service.renew_upstream.await_args
    assert call.kwargs["contract_id"] == "upstream-1"
    assert call.kwargs["request"] == proposal
    assert call.kwargs["actor_id"] == "actor-1"
    assert call.kwargs["scope"] is scope
    assert call.kwargs["idempotency_key"] == "renew-request-1"


def test_list_and_detail_routes_use_asset_ops_read() -> None:
    routes = {
        (route.path, next(iter(route.methods))): route
        for route in module.router.routes
    }
    list_route = routes[("/upstream-contracts", "GET")]
    detail_route = routes[("/upstream-contracts/{contract_id}", "GET")]

    assert list_route.methods == {"GET"}
    assert detail_route.methods == {"GET"}
    list_authz = [
        dependency.call
        for dependency in list_route.dependant.dependencies
        if type(dependency.call).__name__ == "AuthzPermissionChecker"
    ]
    detail_authz = [
        dependency.call
        for dependency in detail_route.dependant.dependencies
        if type(dependency.call).__name__ == "AuthzPermissionChecker"
    ]
    assert len(list_authz) == 1
    assert list_authz[0].resource_type == "asset_ops"
    assert list_authz[0].action == "read"
    assert len(detail_authz) == 1
    assert detail_authz[0].resource_type == "asset_ops"
    assert detail_authz[0].action == "read"


@pytest.mark.asyncio
async def test_list_and_detail_endpoints_bind_scope_and_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = _scope()
    resolver = AsyncMock(return_value=scope)
    detail_response = UpstreamContractResponse.model_validate(
        {
            "contract_number": "UP-001",
            "contract_type": "lease",
            "name": "上游合同",
            "owner_party_id": "owner-1",
            "operator_party_id": "operator-1",
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 12, 31),
            "payment_cycle": "monthly",
            "payment_day": 15,
            "deposit_amount": "0",
            "scan_document_id": "scan",
            "asset_unit_ids": ["unit-1"],
            "rent_schedules": [],
            "id": "upstream-1",
            "version": 1,
            "created_at": datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
            "updated_at": datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
            "status": "active",
            "warnings": [],
            "idempotent": False,
        }
    )
    query_service = SimpleNamespace(
        list_upstream_contracts=AsyncMock(return_value=([detail_response], 1)),
        get_upstream_contract=AsyncMock(return_value=detail_response),
    )
    monkeypatch.setattr(module.party_scope_resolver, "resolve", resolver)
    monkeypatch.setattr(module, "asset_operations_query_service", query_service)
    db = MagicMock()
    current_user = SimpleNamespace(id="actor-1")

    list_result = await module.list_upstream_contracts(
        contract_type="lease",
        owner_party_id="owner-1",
        q="UP-001",
        offset=0,
        limit=20,
        db=db,
        current_user=current_user,
    )
    detail_result = await module.get_upstream_contract(
        contract_id="upstream-1",
        db=db,
        current_user=current_user,
    )

    assert list_result.total == 1
    assert list_result.items[0].id == "upstream-1"
    assert detail_result.id == "upstream-1"
    list_call = query_service.list_upstream_contracts.await_args
    assert list_call.kwargs["scope"] is scope
    assert list_call.kwargs["contract_type"] == "lease"
    assert list_call.kwargs["owner_party_id"] == "owner-1"
    assert list_call.kwargs["query"] == "UP-001"
    assert list_call.kwargs["offset"] == 0
    assert list_call.kwargs["limit"] == 20
    detail_call = query_service.get_upstream_contract.await_args
    assert detail_call.args == (db, "upstream-1")
    assert detail_call.kwargs["scope"] is scope


def test_update_route_uses_asset_ops_write() -> None:
    routes = {route.path: route for route in module.router.routes}
    update_route = routes["/upstream-contracts/{contract_id}"]

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
    update_response = UpstreamContractResponse.model_validate(
        {
            "contract_number": "UP-001",
            "contract_type": "lease",
            "name": "改名后的上游合同",
            "owner_party_id": "owner-1",
            "operator_party_id": "operator-1",
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 12, 31),
            "payment_cycle": "monthly",
            "payment_day": 15,
            "deposit_amount": "0",
            "scan_document_id": "scan",
            "asset_unit_ids": ["unit-1"],
            "rent_schedules": [],
            "id": "upstream-1",
            "version": 4,
            "created_at": datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
            "updated_at": datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
            "status": "active",
            "warnings": [],
            "idempotent": False,
        }
    )
    command_service = SimpleNamespace(
        update_upstream=AsyncMock(return_value=update_response),
    )
    monkeypatch.setattr(module.party_scope_resolver, "resolve", resolver)
    monkeypatch.setattr(module, "asset_contract_command_service", command_service)
    db = MagicMock()
    current_user = SimpleNamespace(id="actor-1")
    payload = UpstreamContractUpdate.model_validate(
        {"expected_version": 3, "name": "改名后的上游合同"}
    )

    result = await module.update_upstream_contract(
        contract_id="upstream-1",
        payload=payload,
        db=db,
        current_user=current_user,
    )

    assert result == update_response
    call = command_service.update_upstream.await_args
    assert call.kwargs["contract_id"] == "upstream-1"
    assert call.kwargs["request"] == payload
    assert call.kwargs["actor_id"] == "actor-1"
    assert call.kwargs["scope"] is scope
