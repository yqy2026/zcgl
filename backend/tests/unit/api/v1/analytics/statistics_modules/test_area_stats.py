"""
Area Stats Module 测试 (修复版)
测试面积统计模块的端点 - 匹配实际 API 实现
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.database import get_async_db
from src.main import app
from src.middleware.auth import get_current_active_user
from src.models.auth import User


@pytest.fixture
def mock_db():
    """Mock 数据库会话"""
    return AsyncMock()


@pytest.fixture
def mock_user():
    """Mock 当前用户"""
    user = Mock(spec=User)
    user.id = "test_user_001"
    user.username = "testuser"
    user.is_active = True
    return user


@pytest.fixture
def client(mock_db, mock_user):
    """测试客户端"""

    async def override_get_db():
        yield mock_db

    def override_get_user():
        return mock_user

    app.dependency_overrides[get_async_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


class TestAreaStatistics:
    """面积统计测试 - 修复版"""

    def test_get_area_summary(self, client):
        """
        测试获取面积摘要

        Given: 用户已登录
        When: 调用 GET /api/v1/statistics/area-summary
        Then: 返回面积摘要数据
        """
        # Arrange - Mock AreaService.calculate_summary_with_aggregation
        with patch(
            "src.services.analytics.area_service.AreaService.calculate_summary_with_aggregation"
        ) as mock_calc:
            mock_calc.return_value = {
                "total_land_area": 50000.0,
                "total_rentable_area": 45000.0,
                "total_rented_area": 35000.0,
                "total_unrented_area": 10000.0,
                "overall_occupancy_rate": 77.78,
            }

            # Act
            response = client.get("/api/v1/statistics/area-summary")

            # Assert
            assert response.status_code == 200

    def test_get_area_statistics_direct(self, client):
        """
        测试获取面积统计（直接计算）

        Given: 用户已登录
        When: 调用 GET /api/v1/statistics/area-statistics
        Then: 返回面积统计数据
        """
        # Arrange - Mock asset_crud.get_multi_with_search
        with patch("src.crud.asset.asset_crud.get_multi_with_search_async") as mock_get:
            # 创建模拟资产
            mock_assets = []
            for i in range(10):
                asset = Mock()
                asset.land_area = 5000.0
                asset.rentable_area = 4500.0
                asset.rented_area = 3500.0
                mock_assets.append(asset)

            mock_get.return_value = (mock_assets, 10)

            # Act
            response = client.get("/api/v1/statistics/area-statistics")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data

    def test_area_statistics_with_filters(self, client):
        """
        测试带筛选的面积统计

        Given: 用户提供筛选条件
        When: 调用 GET /api/v1/statistics/area-statistics?ownership_status=confirmed
        Then: 返回筛选后的面积统计
        """
        # Arrange
        with patch("src.crud.asset.asset_crud.get_multi_with_search_async") as mock_get:
            mock_get.return_value = ([Mock()] * 5, 5)

            # Act
            response = client.get(
                "/api/v1/statistics/area-statistics?ownership_status=confirmed"
            )

            # Assert
            assert response.status_code == 200
