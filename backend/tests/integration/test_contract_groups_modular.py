"""
合同组 API 集成烟测

验证新合同组/合同生命周期路由已挂载到真实 app，
且退休的旧合同入口已下线。
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def _retired_contract_routes_path() -> str:
    return "/".join(("", "api", "v1", "-".join(("rental", "contracts"))))


def _build_csrf_headers(client: TestClient) -> dict[str, str]:
    csrf_token = getattr(client, "_csrf_token", None)
    if csrf_token is None:
        return {}
    return {"X-CSRF-Token": csrf_token}


@pytest.fixture
def authenticated_client(client: TestClient, test_data) -> TestClient:
    """通过真实登录流程初始化认证 cookie。"""
    admin_user = test_data["admin"]
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": admin_user.username, "password": "Admin123!@#"},
    )
    assert response.status_code == 200

    auth_token = response.cookies.get("auth_token")
    csrf_token = response.cookies.get("csrf_token")
    assert auth_token is not None
    client.cookies.set("auth_token", auth_token)
    if csrf_token is not None:
        client.cookies.set("csrf_token", csrf_token)
    setattr(client, "_csrf_token", csrf_token)
    return client


class TestContractGroupRoutes:
    def test_registered_routes(self, authenticated_client: TestClient) -> None:
        response = authenticated_client.get("/openapi.json")
        assert response.status_code == 200

        paths = response.json()["paths"].keys()
        required_paths = [
            "/api/v1/contract-groups",
            "/api/v1/contract-groups/{group_id}",
            "/api/v1/contract-groups/{group_id}/contracts",
            "/api/v1/contracts/{contract_id}",
            "/api/v1/contracts/{contract_id}/terminate",
            "/api/v1/contracts/{contract_id}/void",
            "/api/v1/contracts/{contract_id}/rent-terms",
            "/api/v1/contracts/{contract_id}/rent-terms/{rent_term_id}",
            "/api/v1/contracts/{contract_id}/ledger",
        ]

        for route in required_paths:
            assert route in paths
        assert "/api/v1/contracts/{contract_id}/expire" not in paths
        assert "/api/v1/contracts/{contract_id}/ledger/batch-update-status" not in paths

    def test_retired_contract_paths_are_not_registered(
        self, authenticated_client: TestClient
    ) -> None:
        response = authenticated_client.get(_retired_contract_routes_path())
        assert response.status_code == 404

    def test_missing_contract_group_maps_to_404(
        self, authenticated_client: TestClient
    ) -> None:
        response = authenticated_client.get("/api/v1/contract-groups/grp-notexist")
        assert response.status_code == 404
