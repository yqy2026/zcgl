"""API contract tests for asset-unit split preview and commit."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic_core import PydanticUndefined

from src.api.v1 import asset_units as module
from src.schemas.asset_operations import (
    AssetUnitBoundaryCommitResponse,
    AssetUnitBoundaryImpact,
    AssetUnitBoundaryPreviewResponse,
    AssetUnitMergeCommitRequest,
    AssetUnitMergePreviewRequest,
    AssetUnitMergeResultInput,
    AssetUnitSplitCommitRequest,
    AssetUnitSplitPartInput,
    AssetUnitSplitPreviewRequest,
    AssetUnitUpdate,
    AssetUnitVacancyNoteUpdate,
)
from src.services.party_scope_resolver import EffectivePartyScope
from tests.fixtures.fake_credentials import fake_identifier


def _parts() -> list[AssetUnitSplitPartInput]:
    return [
        AssetUnitSplitPartInput(
            unit_code="U-001-A",
            name="一号商铺 A",
            land_area=Decimal("8.00"),
            building_area=Decimal("40.00"),
            rentable_area=Decimal("30.00"),
        ),
        AssetUnitSplitPartInput(
            unit_code="U-001-B",
            name="一号商铺 B",
            land_area=Decimal("12.00"),
            building_area=Decimal("60.00"),
            rentable_area=Decimal("50.00"),
        ),
    ]


def _scope() -> EffectivePartyScope:
    return EffectivePartyScope(
        user_id="actor-1",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner-1"],
    )


def test_split_routes_use_asset_ops_write_and_required_idempotency_header() -> None:
    routes = {route.path: route for route in module.router.routes}
    preview_route = routes["/asset-units/{unit_id}/split/preview"]
    commit_route = routes["/asset-units/{unit_id}/split"]

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


def test_merge_routes_use_asset_ops_write_and_required_idempotency_header() -> None:
    routes = {route.path: route for route in module.router.routes}
    preview_route = routes["/asset-units/merge/preview"]
    commit_route = routes["/asset-units/merge"]

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
        assert authz_dependencies[0].denial_error_factory().code == (
            "ASSET_OPS_PERMISSION_DENIED"
        )

    header_params = {
        param.alias: param for param in commit_route.dependant.header_params
    }
    assert header_params["Idempotency-Key"].default is PydanticUndefined


@pytest.mark.asyncio
async def test_split_endpoints_bind_path_actor_scope_and_idempotency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = _scope()
    resolver = AsyncMock(return_value=scope)
    preview_response = AssetUnitBoundaryPreviewResponse(
        change_type="split",
        source_unit_ids=["unit-1"],
        results=_parts(),
        area_check={
            "source": {
                "land_area": "20.00",
                "building_area": "100.00",
                "rentable_area": "80.00",
            },
            "result": {
                "land_area": "20.00",
                "building_area": "100.00",
                "rentable_area": "80.00",
            },
        },
        impact=AssetUnitBoundaryImpact(
            source_units_stop_on=date(2026, 10, 31),
            result_units_start_on=date(2026, 11, 1),
            unit_count_delta=1,
        ),
        versions={"unit-1": 3},
        preview_token=fake_identifier("preview-token"),
        expires_at=datetime(2026, 10, 24, 9, 10, tzinfo=UTC),
    )
    commit_response = AssetUnitBoundaryCommitResponse(
        boundary_change_id="change-1",
        change_type="split",
        source_unit_ids=["unit-1"],
        result_unit_ids=["unit-a", "unit-b"],
        effective_date=date(2026, 11, 1),
        committed_at=datetime(2026, 10, 24, 9, 0, tzinfo=UTC),
        idempotent=False,
    )
    service = SimpleNamespace(
        preview=AsyncMock(return_value=preview_response),
        commit=AsyncMock(return_value=commit_response),
    )
    monkeypatch.setattr(module.party_scope_resolver, "resolve", resolver)
    monkeypatch.setattr(module, "asset_unit_boundary_command_service", service)
    db = MagicMock()
    current_user = SimpleNamespace(id="actor-1")

    preview_result = await module.preview_asset_unit_split(
        unit_id="unit-1",
        payload=AssetUnitSplitPreviewRequest(
            effective_date=date(2026, 11, 1),
            parts=_parts(),
        ),
        db=db,
        current_user=current_user,
    )
    commit_request = AssetUnitSplitCommitRequest(
        preview_token=preview_result.preview_token,
        reason="按楼层拆分",
        expected_version=3,
    )
    commit_result = await module.commit_asset_unit_split(
        unit_id="unit-1",
        payload=commit_request,
        idempotency_key="  split-request-1  ",
        db=db,
        current_user=current_user,
    )

    assert commit_result == commit_response
    assert resolver.await_count == 2
    preview_call = service.preview.await_args
    assert preview_call.kwargs["proposal"].source_unit_id == "unit-1"
    assert preview_call.kwargs["actor_id"] == "actor-1"
    assert preview_call.kwargs["scope"] is scope
    commit_call = service.commit.await_args
    assert commit_call.kwargs["source_unit_id"] == "unit-1"
    assert commit_call.kwargs["actor_id"] == "actor-1"
    assert commit_call.kwargs["scope"] is scope
    assert commit_call.kwargs["idempotency_key"] == "split-request-1"


@pytest.mark.asyncio
async def test_merge_endpoints_bind_actor_scope_versions_and_idempotency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = _scope()
    resolver = AsyncMock(return_value=scope)
    result = AssetUnitSplitPartInput(
        unit_code="U-001+002",
        name="一二号合并商铺",
        land_area=Decimal("20.00"),
        building_area=Decimal("100.00"),
        rentable_area=Decimal("80.00"),
    )
    preview_response = AssetUnitBoundaryPreviewResponse(
        change_type="merge",
        source_unit_ids=["unit-1", "unit-2"],
        results=[result],
        area_check={"source": {}, "result": {}},
        impact=AssetUnitBoundaryImpact(
            source_units_stop_on=date(2026, 10, 31),
            result_units_start_on=date(2026, 11, 1),
            unit_count_delta=-1,
        ),
        versions={"unit-1": 2, "unit-2": 3},
        preview_token=fake_identifier("merge-preview-token"),
        expires_at=datetime(2026, 10, 24, 9, 10, tzinfo=UTC),
    )
    commit_response = AssetUnitBoundaryCommitResponse(
        boundary_change_id="merge-change-1",
        change_type="merge",
        source_unit_ids=["unit-1", "unit-2"],
        result_unit_ids=["unit-merged"],
        effective_date=date(2026, 11, 1),
        committed_at=datetime(2026, 10, 24, 9, 0, tzinfo=UTC),
    )
    service = SimpleNamespace(
        preview_merge=AsyncMock(return_value=preview_response),
        commit_merge=AsyncMock(return_value=commit_response),
    )
    monkeypatch.setattr(module.party_scope_resolver, "resolve", resolver)
    monkeypatch.setattr(module, "asset_unit_boundary_command_service", service)
    db = MagicMock()
    current_user = SimpleNamespace(id="actor-1")
    payload = AssetUnitMergePreviewRequest(
        source_unit_ids=["unit-2", "unit-1"],
        effective_date=date(2026, 11, 1),
        result=AssetUnitMergeResultInput(
            unit_code="U-001+002",
            name="一二号合并商铺",
        ),
    )

    preview_result = await module.preview_asset_unit_merge(
        payload=payload,
        db=db,
        current_user=current_user,
    )
    committed = await module.commit_asset_unit_merge(
        payload=AssetUnitMergeCommitRequest(
            preview_token=preview_result.preview_token,
            reason="恢复完整经营边界",
            expected_versions=preview_result.versions,
        ),
        idempotency_key="  merge-request-1  ",
        db=db,
        current_user=current_user,
    )

    assert committed == commit_response
    preview_call = service.preview_merge.await_args
    assert preview_call.kwargs["proposal"].source_unit_ids == ["unit-1", "unit-2"]
    assert preview_call.kwargs["actor_id"] == "actor-1"
    assert preview_call.kwargs["scope"] is scope
    commit_call = service.commit_merge.await_args
    assert commit_call.kwargs["request"].expected_versions == {
        "unit-1": 2,
        "unit-2": 3,
    }
    assert commit_call.kwargs["idempotency_key"] == "merge-request-1"


def test_registered_split_routes_validate_header_and_return_service_contract(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = EffectivePartyScope(
        user_id="test_user_001",
        source="unrestricted",
        scope_mode="unrestricted",
    )
    preview_token = fake_identifier("preview-token")
    preview_response = AssetUnitBoundaryPreviewResponse(
        change_type="split",
        source_unit_ids=["unit-1"],
        results=_parts(),
        area_check={"source": {}, "result": {}},
        impact=AssetUnitBoundaryImpact(
            source_units_stop_on=date(2026, 10, 31),
            result_units_start_on=date(2026, 11, 1),
            unit_count_delta=1,
        ),
        versions={"unit-1": 3},
        preview_token=preview_token,
        expires_at=datetime(2026, 10, 24, 9, 10, tzinfo=UTC),
    )
    commit_response = AssetUnitBoundaryCommitResponse(
        boundary_change_id="change-1",
        change_type="split",
        source_unit_ids=["unit-1"],
        result_unit_ids=["unit-a", "unit-b"],
        effective_date=date(2026, 11, 1),
        committed_at=datetime(2026, 10, 24, 9, 0, tzinfo=UTC),
        idempotent=False,
    )
    service = SimpleNamespace(
        preview=AsyncMock(return_value=preview_response),
        commit=AsyncMock(return_value=commit_response),
    )
    monkeypatch.setattr(
        module.party_scope_resolver,
        "resolve",
        AsyncMock(return_value=scope),
    )
    monkeypatch.setattr(module, "asset_unit_boundary_command_service", service)
    preview_payload = {
        "effective_date": "2026-11-01",
        "parts": [part.model_dump(mode="json") for part in _parts()],
    }

    preview_http = client.post(
        "/api/v1/asset-units/unit-1/split/preview",
        json=preview_payload,
    )
    missing_header = client.post(
        "/api/v1/asset-units/unit-1/split",
        json={
            "preview_token": preview_token,
            "reason": "按楼层拆分",
            "expected_version": 3,
        },
    )
    commit_http = client.post(
        "/api/v1/asset-units/unit-1/split",
        headers={"Idempotency-Key": "split-request-1"},
        json={
            "preview_token": preview_token,
            "reason": "按楼层拆分",
            "expected_version": 3,
        },
    )

    assert preview_http.status_code == 200
    assert preview_http.json()["source_unit_ids"] == ["unit-1"]
    assert missing_header.status_code == 422
    assert commit_http.status_code == 200
    assert commit_http.json()["boundary_change_id"] == "change-1"
    service.commit.assert_awaited_once()


def test_registered_merge_routes_validate_header_and_return_service_contract(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = EffectivePartyScope(
        user_id="test_user_001",
        source="unrestricted",
        scope_mode="unrestricted",
    )
    preview_token = fake_identifier("merge-preview-token")
    preview_response = AssetUnitBoundaryPreviewResponse(
        change_type="merge",
        source_unit_ids=["unit-1", "unit-2"],
        results=[
            AssetUnitSplitPartInput(
                unit_code="U-001+002",
                name="一二号合并商铺",
                land_area=Decimal("20.00"),
                building_area=Decimal("100.00"),
                rentable_area=Decimal("80.00"),
            )
        ],
        area_check={"source": {}, "result": {}},
        impact=AssetUnitBoundaryImpact(
            source_units_stop_on=date(2026, 10, 31),
            result_units_start_on=date(2026, 11, 1),
            unit_count_delta=-1,
        ),
        versions={"unit-1": 2, "unit-2": 3},
        preview_token=preview_token,
        expires_at=datetime(2026, 10, 24, 9, 10, tzinfo=UTC),
    )
    commit_response = AssetUnitBoundaryCommitResponse(
        boundary_change_id="merge-change-1",
        change_type="merge",
        source_unit_ids=["unit-1", "unit-2"],
        result_unit_ids=["unit-merged"],
        effective_date=date(2026, 11, 1),
        committed_at=datetime(2026, 10, 24, 9, 0, tzinfo=UTC),
    )
    service = SimpleNamespace(
        preview_merge=AsyncMock(return_value=preview_response),
        commit_merge=AsyncMock(return_value=commit_response),
    )
    monkeypatch.setattr(
        module.party_scope_resolver,
        "resolve",
        AsyncMock(return_value=scope),
    )
    monkeypatch.setattr(module, "asset_unit_boundary_command_service", service)
    preview_payload = {
        "source_unit_ids": ["unit-2", "unit-1"],
        "effective_date": "2026-11-01",
        "result": {"unit_code": "U-001+002", "name": "一二号合并商铺"},
    }

    preview_http = client.post(
        "/api/v1/asset-units/merge/preview",
        json=preview_payload,
    )
    missing_header = client.post(
        "/api/v1/asset-units/merge",
        json={
            "preview_token": preview_token,
            "reason": "恢复完整经营边界",
            "expected_versions": {"unit-1": 2, "unit-2": 3},
        },
    )
    commit_http = client.post(
        "/api/v1/asset-units/merge",
        headers={"Idempotency-Key": "merge-request-1"},
        json={
            "preview_token": preview_token,
            "reason": "恢复完整经营边界",
            "expected_versions": {"unit-1": 2, "unit-2": 3},
        },
    )

    assert preview_http.status_code == 200
    assert preview_http.json()["source_unit_ids"] == ["unit-1", "unit-2"]
    assert missing_header.status_code == 422
    assert commit_http.status_code == 200
    assert commit_http.json()["boundary_change_id"] == "merge-change-1"
    service.commit_merge.assert_awaited_once()


def test_unit_read_and_update_routes_use_asset_ops_guard() -> None:
    routes = {
        (route.path, next(iter(route.methods))): route
        for route in module.router.routes
    }
    list_route = routes[("/asset-units", "GET")]
    detail_route = routes[("/asset-units/{unit_id}", "GET")]
    update_route = routes[("/asset-units/{unit_id}", "PATCH")]
    note_route = routes[("/asset-units/{unit_id}/vacancy-note", "PUT")]

    assert detail_route.methods == {"GET"}
    assert update_route.methods == {"PATCH"}
    assert note_route.methods == {"PUT"}
    assert list_route.methods == {"GET"}
    for route in (list_route, detail_route):
        authz = [
            d.call
            for d in route.dependant.dependencies
            if type(d.call).__name__ == "AuthzPermissionChecker"
        ]
        assert len(authz) == 1 and authz[0].action == "read"
    for route in (update_route, note_route):
        authz = [
            d.call
            for d in route.dependant.dependencies
            if type(d.call).__name__ == "AuthzPermissionChecker"
        ]
        assert len(authz) == 1 and authz[0].action == "write"


@pytest.mark.asyncio
async def test_unit_read_and_update_endpoints_bind_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.schemas.asset_operations import (
        AssetUnitDetail,
        AssetUnitResponse,
    )

    scope = _scope()
    resolver = AsyncMock(return_value=scope)
    detail = AssetUnitDetail.model_validate(
        {
            "unit_code": "U-001",
            "name": "一号商铺",
            "project_id": "project-1",
            "owner_party_id": "owner-1",
            "address": "地址",
            "usage_type": "commercial",
            "acquisition_mode": "leased",
            "is_operating": True,
            "building_area": "100",
            "rentable_area": "80",
            "managed_from": date(2026, 1, 1),
            "predecessor_unit_ids": [],
            "id": "unit-1",
            "version": 2,
            "created_at": datetime(2026, 1, 1, tzinfo=UTC),
            "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
            "rental_status": "rented",
            "rented_area": "80",
            "occupancy_rate": "1",
            "warnings": [],
            "terminal_contract_ids": ["terminal-1"],
        }
    )
    update_response = AssetUnitResponse.model_validate(
        {
            "unit_code": "U-001",
            "name": "改名后的商铺",
            "project_id": "project-1",
            "owner_party_id": "owner-1",
            "address": "地址",
            "usage_type": "commercial",
            "acquisition_mode": "leased",
            "is_operating": True,
            "building_area": "100",
            "rentable_area": "80",
            "managed_from": date(2026, 1, 1),
            "predecessor_unit_ids": [],
            "id": "unit-1",
            "version": 3,
            "created_at": datetime(2026, 1, 1, tzinfo=UTC),
            "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
            "rental_status": "rented",
            "rented_area": "80",
            "occupancy_rate": "1",
            "warnings": [],
        }
    )
    query_service = SimpleNamespace(
        list_asset_units=AsyncMock(return_value=([detail], 1)),
        get_asset_unit_detail=AsyncMock(return_value=detail),
    )
    command_service = SimpleNamespace(
        update_asset_unit=AsyncMock(return_value=update_response),
        update_vacancy_note=AsyncMock(return_value=update_response),
    )
    monkeypatch.setattr(module.party_scope_resolver, "resolve", resolver)
    monkeypatch.setattr(module, "asset_operations_query_service", query_service)
    monkeypatch.setattr(module, "asset_unit_command_service", command_service)
    db = MagicMock()
    current_user = SimpleNamespace(id="actor-1")

    listing = await module.list_asset_units(
        project_id=None,
        owner_party_id=None,
        usage_type=None,
        q=None,
        filter="non_rentable",
        offset=0,
        limit=20,
        db=db,
        current_user=current_user,
    )
    got = await module.get_asset_unit(
        unit_id="unit-1", db=db, current_user=current_user
    )
    updated = await module.update_asset_unit(
        unit_id="unit-1",
        payload=AssetUnitUpdate.model_validate(
            {"expected_version": 2, "name": "改名后的商铺"}
        ),
        db=db,
        current_user=current_user,
    )
    noted = await module.update_asset_unit_vacancy_note(
        unit_id="unit-1",
        payload=AssetUnitVacancyNoteUpdate.model_validate(
            {"expected_version": 2, "vacancy_reason": "renovation"}
        ),
        db=db,
        current_user=current_user,
    )

    assert listing.total == 1
    assert got.terminal_contract_ids == ["terminal-1"]
    assert updated.name == "改名后的商铺"
    assert noted == update_response
    list_call = query_service.list_asset_units.await_args
    assert list_call.kwargs["filter"] == "non_rentable"
    assert list_call.kwargs["scope"] is scope
    update_call = command_service.update_asset_unit.await_args
    assert update_call.kwargs["unit_id"] == "unit-1"
    assert update_call.kwargs["scope"] is scope
