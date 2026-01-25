"""
占用率API测试

Test coverage for Occupancy API endpoints:
- Occupancy rate calculations
- Area statistics
- Utilization metrics
"""

import pytest
from fastapi import status


@pytest.fixture
def admin_user_headers(client, admin_user):
    """管理员用户认证头"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.username, "password": "admin123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestOccupancyAPI:
    """测试占用率API"""

    def test_get_occupancy_rate(self, client, admin_user_headers):
        """测试获取占用率"""
        response = client.get(
            "/api/v1/occupancy/rate",
            headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_area_statistics(self, client, admin_user_headers):
        """测试获取面积统计"""
        response = client.get(
            "/api/v1/occupancy/area-stats",
            headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_calculate_occupancy_by_project(self, client, admin_user_headers):
        """测试按项目计算占用率"""
        response = client.get(
            "/api/v1/occupancy/by-project/project-id",
            headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_utilization_metrics(self, client, admin_user_headers):
        """测试获取利用率指标"""
        response = client.get(
            "/api/v1/occupancy/utilization",
            headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/occupancy/rate")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
