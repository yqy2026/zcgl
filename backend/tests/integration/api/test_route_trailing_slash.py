"""
测试API路由末尾斜杠收敛契约

列表/创建端点统一为无末尾斜杠的 canonical 路径（`"/"` 与 `""`），
不再双注册 `"/"` 变体；带斜杠请求由 FastAPI 默认 `redirect_slashes=True`
返回 307 重定向到 canonical 路径（0→1 阶段不做兼容操作）。
"""

from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """创建测试客户端"""
    from src.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.integration
class TestRouteTrailingSlashContract:
    """验证收敛后的路由契约：canonical 路径直达，带斜杠变体 307"""

    @pytest.mark.parametrize(
        ("route_path", "expected_status"),
        [
            ("/api/v1/notifications", 401),
            ("/api/v1/organizations", 401),
            ("/api/v1/projects", 401),
            ("/api/v1/tasks", 401),
            ("/api/v1/ownerships", 404),
            ("/api/v1/property-certificates", 401),
            ("/api/v1/defects", 404),
        ],
    )
    def test_canonical_path_returns_expected_status(
        self,
        client: TestClient,
        route_path: str,
        expected_status: int,
    ):
        """canonical（无末尾斜杠）路径直接命中路由，不产生 307 重定向"""
        response = client.get(route_path, follow_redirects=False)

        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "route_path",
        [
            "/api/v1/notifications",
            "/api/v1/organizations",
            "/api/v1/projects",
            "/api/v1/tasks",
            "/api/v1/property-certificates",
        ],
    )
    def test_trailing_slash_redirects_to_canonical(
        self,
        client: TestClient,
        route_path: str,
    ):
        """带末尾斜杠的请求 307 重定向到 canonical 路径（不再双注册兼容）"""
        response = client.get(f"{route_path}/", follow_redirects=False)

        assert response.status_code == 307, (
            f"路由 {route_path}/ 应 307 重定向到 canonical 路径 {route_path}"
        )
        assert urlsplit(response.headers.get("location", "")).path == route_path

    @pytest.mark.parametrize(
        "route_path",
        [
            "/api/v1/projects",
            "/api/v1/organizations",
            "/api/v1/property-certificates",
            "/api/v1/tasks",
        ],
    )
    def test_trailing_slash_post_redirects_to_canonical(
        self,
        client: TestClient,
        route_path: str,
    ):
        """POST 创建端点的带斜杠请求同样 307 到 canonical（不再双注册兼容）"""
        response = client.post(f"{route_path}/", follow_redirects=False)

        assert response.status_code == 307, (
            f"路由 {route_path}/ POST 应 307 重定向到 canonical 路径 {route_path}"
        )
        assert urlsplit(response.headers.get("location", "")).path == route_path
