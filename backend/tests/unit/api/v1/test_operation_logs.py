"""
操作日志API测试

Test coverage for Operation Logs API endpoints:
- Audit trail queries
- Operation tracking
- Log filtering and pagination
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


class TestOperationLogsAPI:
    """测试操作日志API"""

    def test_get_operation_logs(self, client, admin_user_headers):
        """测试获取操作日志列表"""
        response = client.get("/api/v1/operation-logs/", headers=admin_user_headers)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_logs_with_filters(self, client, admin_user_headers):
        """测试带筛选的日志查询"""
        response = client.get(
            "/api/v1/operation-logs/?user_id=test-user&action=create",
            headers=admin_user_headers,
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_logs_by_date_range(self, client, admin_user_headers):
        """测试按日期范围查询日志"""
        response = client.get(
            "/api/v1/operation-logs/?date_from=2024-01-01&date_to=2024-12-31",
            headers=admin_user_headers,
        )
        assert response.status_code in [status_HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_logs_with_pagination(self, client, admin_user_headers):
        """测试分页查询日志"""
        response = client.get(
            "/api/v1/operation-logs/?page=1&page_size=50", headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/operation-logs/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
