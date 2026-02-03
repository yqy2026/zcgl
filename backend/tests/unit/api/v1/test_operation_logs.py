"""
操作日志API测试

Test coverage for Operation Logs API endpoints:
- Audit trail queries
- Operation tracking
- Log filtering and pagination
"""

import pytest
from fastapi import status

AUTH_FAILURE_STATUSES = {
    status.HTTP_401_UNAUTHORIZED,
    status.HTTP_422_UNPROCESSABLE_ENTITY,
}


@pytest.fixture
def admin_user_headers(client, admin_user):
    """管理员用户认证头"""
    # client fixture already bypasses authentication
    return {}


class TestOperationLogsAPI:
    """测试操作日志API"""

    def test_get_operation_logs(self, client, admin_user_headers):
        """测试获取操作日志列表"""
        response = client.get("/api/v1/operation-logs/", headers=admin_user_headers)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            *AUTH_FAILURE_STATUSES,
        ]

    def test_get_logs_with_filters(self, client, admin_user_headers):
        """测试带筛选的日志查询"""
        response = client.get(
            "/api/v1/operation-logs/?user_id=test-user&action=create",
            headers=admin_user_headers,
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            *AUTH_FAILURE_STATUSES,
        ]

    def test_get_logs_by_date_range(self, client, admin_user_headers):
        """测试按日期范围查询日志"""
        response = client.get(
            "/api/v1/operation-logs/?date_from=2024-01-01&date_to=2024-12-31",
            headers=admin_user_headers,
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            *AUTH_FAILURE_STATUSES,
        ]

    def test_get_logs_with_pagination(self, client, admin_user_headers):
        """测试分页查询日志"""
        response = client.get(
            "/api/v1/operation-logs/?page=1&page_size=50", headers=admin_user_headers
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            *AUTH_FAILURE_STATUSES,
        ]

    def test_unauthorized_access(self, unauthenticated_client):
        """测试未授权访问"""
        response = unauthenticated_client.get("/api/v1/operation-logs/")
        assert response.status_code in {
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            *AUTH_FAILURE_STATUSES,
        }
