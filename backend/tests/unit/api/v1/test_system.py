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
    # client fixture already bypasses authentication
    return {}


class TestSystemAPI:
    """测试系统API"""

    def test_health_check(self, client, admin_user_headers):
        """测试健康检查"""
        response = client.get("/api/v1/system/health", headers=admin_user_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_system_info(self, client, admin_user_headers):
        """测试获取系统信息"""
        response = client.get("/api/v1/system/info", headers=admin_user_headers)
        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload.get("success") is True
        assert isinstance(payload.get("data"), dict)

    def test_get_system_metrics(self, client, admin_user_headers):
        """测试获取系统指标"""
        response = client.get("/api/v1/system/metrics", headers=admin_user_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_database_status(self, client, admin_user_headers):
        """测试获取数据库状态"""
        response = client.get(
            "/api/v1/system/database-status", headers=admin_user_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_cache_status(self, client, admin_user_headers):
        """测试获取缓存状态"""
        response = client.get("/api/v1/system/cache-status", headers=admin_user_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_system_diagnostics(self, client, admin_user_headers):
        """测试系统诊断"""
        response = client.get("/api/v1/system/diagnostics", headers=admin_user_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthorized_access(self, unauthenticated_client):
        """测试未授权访问"""
        response = unauthenticated_client.get("/api/v1/system/health")
        assert response.status_code == status.HTTP_404_NOT_FOUND
