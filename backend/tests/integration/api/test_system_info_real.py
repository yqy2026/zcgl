"""
System info integration test with real auth/DB dependency path.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient


def _get_auth_headers(client: TestClient, admin_user) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "Admin123!@#"},
    )
    assert response.status_code == 200
    auth_token = response.cookies.get("auth_token")
    csrf_token = response.cookies.get("csrf_token")
    assert auth_token is not None
    assert csrf_token is not None
    client.cookies.set("auth_token", auth_token)
    client.cookies.set("csrf_token", csrf_token)
    return {"X-CSRF-Token": csrf_token}


@pytest.mark.integration
def test_system_info_real_flow(client: TestClient, test_data):
    """真实链路验证：/api/v1/system/info 返回系统状态。"""
    admin_user = test_data["admin"]
    headers = _get_auth_headers(client, admin_user)

    response = client.get("/api/v1/system/info", headers=headers)
    assert response.status_code == 200

    payload = response.json()
    assert payload.get("success") is True
    assert isinstance(payload.get("timestamp"), str)

    data = payload.get("data", {})
    assert isinstance(data.get("version"), str) and data["version"] != ""
    assert data.get("database_status") in {"connected", "disconnected"}
    assert data.get("api_version") == "v1"
    assert isinstance(data.get("build_time"), str) and data["build_time"] != ""
    datetime.strptime(data["build_time"], "%Y-%m-%d %H:%M:%S")
    assert data.get("environment") in {
        "test",
        "development",
        "testing",
        "staging",
        "production",
    }


@pytest.mark.integration
def test_system_info_requires_auth(client: TestClient):
    """未认证访问系统信息应被拒绝。"""
    response = client.get("/api/v1/system/info")
    assert response.status_code == 401


@pytest.mark.integration
def test_system_root_real_flow(client: TestClient, test_data):
    """真实链路验证：/api/v1/system/root 返回路由导航信息。"""
    admin_user = test_data["admin"]
    headers = _get_auth_headers(client, admin_user)

    response = client.get("/api/v1/system/root", headers=headers)
    assert response.status_code == 200

    payload = response.json()
    assert payload.get("success") is True

    data = payload.get("data", {})
    assert isinstance(data.get("version"), str) and data["version"] != ""
    endpoints = data.get("endpoints", {})
    assert isinstance(endpoints, dict)
    assert endpoints.get("auth") == "/api/v1/auth"
    assert endpoints.get("health") == "/api/v1/monitoring/health"
