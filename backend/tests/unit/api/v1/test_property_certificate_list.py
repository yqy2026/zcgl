from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_app() -> FastAPI:
    from src.api.v1.assets import property_certificate as module

    app = FastAPI()
    app.include_router(module.router, prefix="/property-certificates")
    app.dependency_overrides[module.get_async_db] = lambda: MagicMock()
    app.dependency_overrides[module.get_current_active_user] = lambda: MagicMock(
        id="user-1"
    )
    list_route = next(
        route
        for route in module.router.routes
        if route.path == "" and "GET" in route.methods
    )
    authz_dependency = next(
        dependency
        for dependency in list_route.dependant.dependencies
        if dependency.name == "_authz_ctx"
    )
    app.dependency_overrides[authz_dependency.call] = lambda: MagicMock()
    return app


def test_list_rejects_blank_asset_id_query() -> None:
    app = _build_app()

    with TestClient(app) as client:
        assert client.get("/property-certificates?asset_id=").status_code == 422
        assert client.get("/property-certificates?asset_id=%20%20").status_code == 422


def test_list_passes_asset_id_to_service() -> None:
    from src.api.v1.assets import property_certificate as module

    service = MagicMock()
    service.list_certificates = AsyncMock(return_value=[])
    app = _build_app()

    with patch.object(module, "PropertyCertificateService", return_value=service):
        with TestClient(app) as client:
            response = client.get(
                "/property-certificates?skip=5&limit=10&asset_id=asset-1"
            )

    assert response.status_code == 200
    service.list_certificates.assert_awaited_once_with(
        skip=5,
        limit=10,
        asset_id="asset-1",
        current_user_id="user-1",
    )
