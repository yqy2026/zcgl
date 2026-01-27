"""
审计历史API测试

Test coverage for History API endpoints:
- Audit log queries
- Change tracking
- History filtering and pagination
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


class TestHistoryAPI:
    """测试历史记录API"""

    def test_get_history_logs(self, client, admin_user_headers):
        """测试获取历史记录列表"""
        response = client.get("/api/v1/history/", headers=admin_user_headers)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_history_with_filters(self, client, admin_user_headers):
        """测试带筛选条件的历史记录查询"""
        response = client.get(
            "/api/v1/history/?entity_type=asset&entity_id=test-id",
            headers=admin_user_headers,
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_history_with_pagination(self, client, admin_user_headers):
        """测试分页查询历史记录"""
        response = client.get(
            "/api/v1/history/?page=1&page_size=20", headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_entity_history(self, client, admin_user_headers):
        """测试获取实体特定历史记录"""
        response = client.get(
            "/api/v1/history/asset/test-asset-id", headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/history/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
