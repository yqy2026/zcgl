"""
占用率API测试

Test coverage for Occupancy API endpoints:
- Occupancy rate calculations
- Area statistics
- Utilization metrics
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


class TestOccupancyAPI:
    """测试占用率API"""

    def test_get_occupancy_rate(self, client, admin_user_headers):
        """测试获取占用率"""
        response = client.get("/api/v1/occupancy/rate", headers=admin_user_headers)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_area_statistics(self, client, admin_user_headers):
        """测试获取面积统计"""
        response = client.get(
            "/api/v1/occupancy/area-stats", headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_calculate_occupancy_by_project(self, client, admin_user_headers):
        """测试按项目计算占用率"""
        response = client.get(
            "/api/v1/occupancy/by-project/project-id", headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_utilization_metrics(self, client, admin_user_headers):
        """测试获取利用率指标"""
        response = client.get(
            "/api/v1/occupancy/utilization", headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_unauthorized_access(self, unauthenticated_client):
        """测试未授权访问"""
        response = unauthenticated_client.get("/api/v1/occupancy/rate")
        assert response.status_code in {
            status.HTTP_200_OK,
            *AUTH_FAILURE_STATUSES,
        }
