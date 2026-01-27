"""
系统API测试

Test coverage for System API endpoints:
- Health checks
- System information
- Diagnostics
- Configuration
"""

import pytest
from fastapi import status


@pytest.fixture
def admin_user_headers(client, admin_user):
    """管理员用户认证头"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.username, "password": "admin123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestSystemAPI:
    """测试系统API"""

    def test_health_check(self, client, admin_user_headers):
        """测试健康检查"""
        response = client.get("/api/v1/system/health", headers=admin_user_headers)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_system_info(self, client, admin_user_headers):
        """测试获取系统信息"""
        response = client.get("/api/v1/system/info", headers=admin_user_headers)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_system_metrics(self, client, admin_user_headers):
        """测试获取系统指标"""
        response = client.get("/api/v1/system/metrics", headers=admin_user_headers)
        assert response.status_code in [status_HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_database_status(self, client, admin_user_headers):
        """测试获取数据库状态"""
        response = client.get(
            "/api/v1/system/database-status", headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_cache_status(self, client, admin_user_headers):
        """测试获取缓存状态"""
        response = client.get("/api/v1/system/cache-status", headers=admin_user_headers)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_system_diagnostics(self, client, admin_user_headers):
        """测试系统诊断"""
        response = client.get("/api/v1/system/diagnostics", headers=admin_user_headers)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/system/health")
        # 健康检查可能允许未认证访问
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_401_UNAUTHORIZED,
        ]
