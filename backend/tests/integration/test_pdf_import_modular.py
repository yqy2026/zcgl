"""
PDF导入API集成测试

测试模块化的PDF导入功能（真实认证链路）
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def authenticated_client(client: TestClient, test_data) -> TestClient:
    """通过真实登录流程初始化认证 cookie。"""
    admin_user = test_data["admin"]
    response = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "Admin123!@#"},
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


@pytest.fixture
def csrf_headers(authenticated_client: TestClient) -> dict[str, str]:
    """Cookie-only 认证下写操作需要的 CSRF 头。"""
    csrf_token = getattr(authenticated_client, "_csrf_token", None)
    if csrf_token is None:
        return {}
    return {"X-CSRF-Token": csrf_token}


class TestPDFSystemEndpoints:
    """测试 PDF 系统信息端点。"""

    def test_get_system_info(self, authenticated_client: TestClient):
        response = authenticated_client.get("/api/v1/pdf-import/info")
        assert response.status_code == 200

        payload = response.json()
        assert payload["success"] is True
        assert "capabilities" in payload
        assert "extractor_summary" in payload
        assert isinstance(payload["capabilities"]["supported_formats"], list)

    def test_get_health_check(self, authenticated_client: TestClient):
        response = authenticated_client.get("/api/v1/pdf-import/health")
        assert response.status_code == 200

        payload = response.json()
        assert payload["status"] in {"healthy", "degraded"}
        assert "timestamp" in payload


class TestPDFBatchEndpoints:
    """测试 PDF 批处理端点。"""

    def test_batch_health_endpoint(self, authenticated_client: TestClient):
        response = authenticated_client.get("/api/v1/pdf-import/batch/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert "configuration" in payload["data"]

    def test_batch_list_endpoint(self, authenticated_client: TestClient):
        response = authenticated_client.get("/api/v1/pdf-import/batch/list")
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert "batches" in payload["data"]

    def test_batch_status_nonexistent(self, authenticated_client: TestClient):
        response = authenticated_client.get("/api/v1/pdf-import/batch/status/fake-batch")
        assert response.status_code == 404

    def test_batch_cancel_nonexistent(
        self, authenticated_client: TestClient, csrf_headers: dict[str, str]
    ):
        response = authenticated_client.post(
            "/api/v1/pdf-import/batch/cancel/fake-batch",
            headers=csrf_headers,
        )
        assert response.status_code == 404

    def test_batch_cleanup_endpoint(
        self, authenticated_client: TestClient, csrf_headers: dict[str, str]
    ):
        response = authenticated_client.delete(
            "/api/v1/pdf-import/batch/cleanup",
            headers=csrf_headers,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert "cleaned_count" in payload["data"]

    def test_batch_upload_requires_files(
        self, authenticated_client: TestClient, csrf_headers: dict[str, str]
    ):
        response = authenticated_client.post(
            "/api/v1/pdf-import/batch/upload",
            headers=csrf_headers,
        )
        assert response.status_code == 422
        payload = response.json()
        assert payload.get("success") is False
        error = payload.get("error", {})
        assert isinstance(error, dict)
        details = error.get("details", {})
        assert isinstance(details, dict)
        field_errors = details.get("field_errors", {})
        assert isinstance(field_errors, dict)
        assert "body.files" in field_errors


class TestPDFSessionsAndRoutes:
    """测试 PDF 会话与路由注册。"""

    def test_get_sessions(self, authenticated_client: TestClient):
        response = authenticated_client.get("/api/v1/pdf-import/sessions")
        assert response.status_code == 200

        payload = response.json()
        assert payload["success"] is True
        assert "data" in payload

    def test_registered_routes(self, authenticated_client: TestClient):
        response = authenticated_client.get("/openapi.json")
        assert response.status_code == 200

        paths = response.json()["paths"].keys()
        required_paths = [
            "/api/v1/pdf-import/info",
            "/api/v1/pdf-import/health",
            "/api/v1/pdf-import/sessions",
            "/api/v1/pdf-import/upload",
            "/api/v1/pdf-import/batch/upload",
            "/api/v1/pdf-import/batch/status/{batch_id}",
            "/api/v1/pdf-import/batch/list",
            "/api/v1/pdf-import/batch/cancel/{batch_id}",
            "/api/v1/pdf-import/batch/cleanup",
            "/api/v1/pdf-import/batch/health",
        ]
        for route in required_paths:
            assert route in paths

    def test_legacy_unversioned_path_not_found(self, authenticated_client: TestClient):
        response = authenticated_client.get("/api/pdf-import/info")
        assert response.status_code == 404
