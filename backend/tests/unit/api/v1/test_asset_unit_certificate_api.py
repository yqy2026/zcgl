"""The unit certificate read boundary exposes only scoped certificate facts."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.api.v1 import asset_units as module
from src.core.exception_handler import (
    BaseBusinessError,
    PartyScopeForbiddenError,
    ResourceNotFoundError,
)
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = pytest.mark.unit


def _reader(monkeypatch: pytest.MonkeyPatch, **kwargs: object) -> AsyncMock:
    reader = AsyncMock(**kwargs)
    monkeypatch.setattr(
        module,
        "asset_unit_certificate_service",
        SimpleNamespace(list_for_unit=reader),
    )
    monkeypatch.setattr(
        module.party_scope_resolver,
        "resolve",
        AsyncMock(
            return_value=EffectivePartyScope(
                user_id="test_user_001",
                source="explicit",
                scope_mode="owner",
                owner_party_ids=["owner-1"],
            )
        ),
    )
    return reader


def test_certificate_route_requires_asset_operations_read() -> None:
    route = next(
        route
        for route in module.router.routes
        if route.path == "/asset-units/{unit_id}/property-certificates"
    )
    assert route.methods == {"GET"}
    checker = next(
        dependency.call
        for dependency in route.dependant.dependencies
        if type(dependency.call).__name__ == "AuthzPermissionChecker"
    )
    assert checker.resource_type == "asset_ops"
    assert checker.action == "read"
    assert checker.denial_error_factory().code == "ASSET_OPS_PERMISSION_DENIED"


def test_certificate_http_preserves_registered_text_and_omits_other_units(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = _reader(
        monkeypatch,
        return_value=[
            SimpleNamespace(
                id="certificate-1",
                certificate_number="粤房字 001",
                certificate_type="real_estate",
                property_address="某路一号",
                registration_date=date(2020, 1, 2),
                building_area="共用建筑面积详见附图",
                land_area="00120.00",
                land_use_term_start=None,
                land_use_term_end=date(2070, 1, 1),
                assets=[{"id": "hidden-unit"}],
                party_relations=[{"party_id": "hidden-party"}],
            )
        ],
    )
    result = client.get(
        "/api/v1/asset-units/unit-1/property-certificates?as_of=2026-11-02"
    )
    assert result.status_code == 200
    assert result.json() == {
        "items": [
            {
                "id": "certificate-1",
                "certificate_number": "粤房字 001",
                "certificate_type": "real_estate",
                "property_address": "某路一号",
                "registration_date": "2020-01-02",
                "building_area": "共用建筑面积详见附图",
                "land_area": "00120.00",
                "land_use_term_start": None,
                "land_use_term_end": "2070-01-01",
            }
        ]
    }
    assert reader.await_args.kwargs["unit_id"] == "unit-1"
    assert reader.await_args.kwargs["as_of"] == date(2026, 11, 2)
    assert reader.await_args.kwargs["scope"].owner_party_ids == ["owner-1"]


def test_certificate_date_defaults_to_service_business_clock(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = _reader(monkeypatch, return_value=[])
    response = client.get("/api/v1/asset-units/unit-1/property-certificates")
    assert response.status_code == 200
    assert response.json() == {"items": []}
    assert reader.await_args.kwargs["as_of"] is None


def test_certificate_invalid_date_is_rejected_before_read(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = _reader(monkeypatch, return_value=[])
    assert (
        client.get(
            "/api/v1/asset-units/unit-1/property-certificates?as_of=2026-02-30"
        ).status_code
        == 422
    )
    reader.assert_not_awaited()


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (PartyScopeForbiddenError(), 403),
        (ResourceNotFoundError("AssetUnit", "unit-1"), 404),
    ],
)
def test_certificate_business_errors_keep_status(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status: int,
) -> None:
    _reader(monkeypatch, side_effect=error)
    response = client.get("/api/v1/asset-units/unit-1/property-certificates")
    assert response.status_code == status


def _command_service(
    monkeypatch: pytest.MonkeyPatch, **methods: object
) -> SimpleNamespace:
    service = SimpleNamespace(**methods)
    monkeypatch.setattr(module, "asset_unit_certificate_service", service)
    monkeypatch.setattr(
        module.party_scope_resolver,
        "resolve",
        AsyncMock(
            return_value=EffectivePartyScope(
                user_id="test_user_001",
                source="explicit",
                scope_mode="owner",
                owner_party_ids=["owner-1"],
            )
        ),
    )
    return service


def _registered_route(path: str, methods: set[str]):
    return next(
        route
        for route in module.router.routes
        if route.path == path and route.methods == methods
    )


def test_link_route_requires_asset_operations_write() -> None:
    route = _registered_route("/asset-units/{unit_id}/property-certificates", {"POST"})
    checker = next(
        dependency.call
        for dependency in route.dependant.dependencies
        if type(dependency.call).__name__ == "AuthzPermissionChecker"
    )
    assert checker.resource_type == "asset_ops"
    assert checker.action == "write"
    assert checker.denial_error_factory().code == "ASSET_OPS_PERMISSION_DENIED"


def test_unlink_route_requires_asset_operations_write() -> None:
    route = _registered_route(
        "/asset-units/{unit_id}/property-certificates/{certificate_id}/unlink",
        {"POST"},
    )
    checker = next(
        dependency.call
        for dependency in route.dependant.dependencies
        if type(dependency.call).__name__ == "AuthzPermissionChecker"
    )
    assert checker.action == "write"


def test_link_success_returns_201_with_refreshed_list(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    link = AsyncMock(
        return_value=[
            SimpleNamespace(
                id="certificate-1",
                certificate_number="粤房字 001",
                certificate_type="real_estate",
                property_address=None,
                registration_date=None,
                building_area=None,
                land_area=None,
                land_use_term_start=None,
                land_use_term_end=None,
            )
        ]
    )
    _command_service(monkeypatch, link_certificate=link)
    response = client.post(
        "/api/v1/asset-units/unit-1/property-certificates",
        json={
            "certificate_id": "certificate-1",
            "effective_from": "2026-01-01",
        },
    )
    assert response.status_code == 201
    assert response.json()["items"][0]["certificate_number"] == "粤房字 001"
    kwargs = link.await_args.kwargs
    assert kwargs["certificate_id"] == "certificate-1"
    assert kwargs["effective_from"] == date(2026, 1, 1)
    assert kwargs["effective_to"] is None
    assert kwargs["actor_id"]


def test_unlink_success_returns_200_with_refreshed_list(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    unlink = AsyncMock(return_value=[])
    _command_service(monkeypatch, unlink_certificate=unlink)
    response = client.post(
        "/api/v1/asset-units/unit-1/property-certificates/certificate-1/unlink",
        json={"effective_from": "2026-06-01"},
    )
    assert response.status_code == 200
    assert response.json() == {"items": []}
    assert unlink.await_args.kwargs["effective_from"] == date(2026, 6, 1)


def test_link_rejects_missing_certificate_or_dates(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _command_service(monkeypatch, link_certificate=AsyncMock())
    response = client.post("/api/v1/asset-units/unit-1/property-certificates", json={})
    assert response.status_code == 422
    service.link_certificate.assert_not_awaited()


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (PartyScopeForbiddenError(), 403),
        (ResourceNotFoundError("PropertyCertificate", "certificate-1"), 404),
        (
            BaseBusinessError(
                "区间重叠", code="CERTIFICATE_LINK_OVERLAP", status_code=409
            ),
            409,
        ),
    ],
)
def test_link_business_errors_keep_status(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status: int,
) -> None:
    _command_service(monkeypatch, link_certificate=AsyncMock(side_effect=error))
    response = client.post(
        "/api/v1/asset-units/unit-1/property-certificates",
        json={
            "certificate_id": "certificate-1",
            "effective_from": "2026-01-01",
        },
    )
    assert response.status_code == status
    assert response.json()["error"]["code"] == error.code
