"""
测试API路由末尾斜杠修复

验证修复后的API路由同时支持带/不带末尾斜杠的路径，
不再产生307重定向问题。
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """创建测试客户端"""
    from src.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.integration
class TestRouteTrailingSlashFix:
    """验证路由同时支持带/不带斜杠的路径"""

    @pytest.mark.parametrize(
        ("route_path", "expected_status"),
        [
            ("/api/v1/notifications", 401),
            ("/api/v1/ownerships", 401),
            ("/api/v1/organizations", 401),
            ("/api/v1/projects", 401),
            ("/api/v1/tasks", 401),
            ("/api/v1/defects", 404),
        ],
    )
    @pytest.mark.parametrize("use_slash", [True, False])
    def test_no_redirect_on_different_formats(
        self,
        client: TestClient,
        route_path: str,
        expected_status: int,
        use_slash: bool,
    ):
        """测试不同路径格式都不产生307重定向"""
        # 测试路由
        test_path = f"{route_path}/" if use_slash else route_path
        response = client.get(test_path, follow_redirects=False)

        # 验证没有307/308重定向
        assert response.status_code not in [
            307,
            308,
        ], f"路由 {test_path} 返回了 {response.status_code} 重定向"
        assert response.status_code == expected_status

    def test_notifications_both_formats_consistent(self, client: TestClient):
        """验证通知列表两种格式返回相同状态码"""
        # 测试无斜杠和有斜杠格式
        r1 = client.get("/api/v1/notifications?limit=5")
        r2 = client.get("/api/v1/notifications/?limit=5")

        # 验证状态码一致
        assert r1.status_code == r2.status_code
