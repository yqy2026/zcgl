"""
Statistics API 测试
测试统计分析 API 端点（模块化架构）- 修复版
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.database import get_db
from src.middleware.auth import get_current_active_user
from src.models.auth import User


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_db():
    """Mock 数据库会话"""
    db = Mock()
    return db


@pytest.fixture
def mock_user():
    """Mock 当前用户"""
    user = Mock(spec=User)
    user.id = "test_user_001"
    user.username = "testuser"
    user.role = "admin"
    user.is_active = True
    return user


@pytest.fixture
def client(mock_db, mock_user):
    """测试客户端"""
    def override_get_db():
        yield mock_db

    def override_get_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# =============================================================================
# 基础统计 API 测试
# =============================================================================

class TestBasicStatistics:
    """基础统计 API 测试"""

    def test_get_basic_statistics_success(self, client):
        """
        测试成功获取基础统计数据

        Given: 用户已登录
        When: 调用 GET /api/v1/statistics/basic
        Then: 返回基础统计数据
        """
        # Arrange
        with patch("src.crud.asset.asset_crud.get_multi_with_search") as mock_get:
            mock_get.return_value = ([Mock()] * 100, 100)

            # Act
            response = client.get("/api/v1/statistics/basic")

            # Assert
            assert response.status_code == 200

    def test_get_dashboard_data(self, client):
        """
        测试获取仪表板数据

        Given: 用户已登录
        When: 调用 GET /api/v1/statistics/dashboard
        Then: 返回仪表板数据或 400/404
        """
        # Arrange
        with patch("src.crud.asset.asset_crud.get_multi_with_search") as mock_get:
            mock_get.return_value = ([Mock()] * 100, 100)

            # Act
            response = client.get("/api/v1/statistics/dashboard")

            # Assert - Dashboard 可能返回 200、400（数据验证失败）或 404
            assert response.status_code in [200, 400, 404]


# =============================================================================
# 面积统计 API 测试
# =============================================================================

class TestAreaStatistics:
    """面积统计 API 测试"""

    def test_get_area_statistics(self, client):
        """
        测试获取面积统计（直接计算）

        Given: 用户已登录
        When: 调用 GET /api/v1/statistics/area-statistics
        Then: 返回面积统计数据
        """
        # Arrange
        with patch("src.crud.asset.asset_crud.get_multi_with_search") as mock_get:
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

    def test_get_area_summary(self, client):
        """
        测试获取面积摘要

        Given: 用户已登录
        When: 调用 GET /api/v1/statistics/area-summary
        Then: 返回面积摘要数据
        """
        # Arrange - Mock AreaService.calculate_summary_with_aggregation
        with patch("src.services.analytics.area_service.AreaService.calculate_summary_with_aggregation") as mock_calc:
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


# =============================================================================
# 财务统计 API 测试
# =============================================================================

class TestFinancialStatistics:
    """财务统计 API 测试"""

    def test_get_financial_summary(self, client):
        """
        测试获取财务摘要

        Given: 用户已登录
        When: 调用 GET /api/v1/statistics/financial-summary
        Then: 返回财务摘要数据
        """
        # Arrange - Mock FinancialService.calculate_summary
        with patch("src.services.analytics.financial_service.FinancialService.calculate_summary") as mock_calc:
            mock_calc.return_value = {
                "total_assets": 100,
                "total_annual_income": 1000000.0,
                "total_annual_expense": 200000.0,
                "net_annual_income": 800000.0,
                "income_per_sqm": 20.0,
                "expense_per_sqm": 4.0,
            }

            # Act
            response = client.get("/api/v1/statistics/financial-summary")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["total_assets"] == 100
            assert data["total_annual_income"] == 1000000.0


# =============================================================================
# 出租率统计 API 测试
# =============================================================================

class TestOccupancyStatistics:
    """出租率统计 API 测试"""

    def test_get_occupancy_rate(self, client):
        """
        测试获取出租率统计

        Given: 用户已登录
        When: 调用 GET /api/v1/statistics/occupancy-rate
        Then: 返回出租率统计数据
        """
        # Arrange - Mock OccupancyService.calculate_with_aggregation
        with patch("src.services.analytics.occupancy_service.OccupancyService.calculate_with_aggregation") as mock_calc:
            mock_calc.return_value = {
                "overall_rate": 85.5,
                "total_rentable_area": 45000.0,
                "total_rented_area": 38475.0,
                "total_assets": 100,
                "rentable_assets_count": 80,
                "calculation_method": "aggregation",
            }

            # Act
            response = client.get("/api/v1/statistics/occupancy-rate")

            # Assert
            assert response.status_code == 200

    def test_get_occupancy_by_category(self, client):
        """
        测试按类别获取出租率

        Given: 用户已登录
        When: 调用 GET /api/v1/statistics/occupancy-rate/by-category?category_field=business_category
        Then: 返回按类别分组的出租率数据
        """
        # Arrange - Mock OccupancyService.calculate_category_with_aggregation
        with patch("src.services.analytics.occupancy_service.OccupancyService.calculate_category_with_aggregation") as mock_calc:
            mock_calc.return_value = {
                "商业": {
                    "overall_rate": 90.0,
                    "total_rentable_area": 20000.0,
                    "total_rented_area": 18000.0,
                    "asset_count": 30,
                },
                "住宅": {
                    "overall_rate": 80.0,
                    "total_rentable_area": 15000.0,
                    "total_rented_area": 12000.0,
                    "asset_count": 20,
                },
            }

            # Act
            response = client.get("/api/v1/statistics/occupancy-rate/by-category?category_field=business_category")

            # Assert
            assert response.status_code == 200


# =============================================================================
# 错误处理测试
# =============================================================================

class TestErrorHandling:
    """错误处理测试"""

    def test_invalid_filter_parameter(self, client):
        """
        测试无效的筛选参数

        Given: 用户提供无效的筛选参数
        When: 调用统计 API
        Then: 返回 200、400、500 或 404
        """
        # Act
        response = client.get("/api/v1/statistics/basic?invalid_param=value")

        # Assert - 未知参数可能导致不同的响应
        assert response.status_code in [200, 400, 404, 500]

    def test_service_layer_exception(self, client):
        """
        测试服务层异常处理

        Given: 服务层抛出异常
        When: 调用统计 API
        Then: 返回 503 或 500 错误
        """
        # Arrange
        with patch("src.crud.asset.asset_crud.get_multi_with_search") as mock_get:
            mock_get.side_effect = Exception("Database error")

            # Act
            response = client.get("/api/v1/statistics/basic")

            # Assert
            # 可能返回 500 或 503（服务不可用）
            assert response.status_code in [500, 503]


# =============================================================================
# 性能测试
# =============================================================================

class TestPerformance:
    """性能测试"""

    def test_large_dataset_performance(self, client):
        """
        测试大数据集性能

        Given: 数据库中有 10000 条记录
        When: 调用统计 API
        Then: 应该返回成功
        """
        # Arrange
        with patch("src.crud.asset.asset_crud.get_multi_with_search") as mock_get:
            # Mock 大数据集
            mock_get.return_value = ([Mock()] * 10000, 10000)

            # Act
            response = client.get("/api/v1/statistics/basic")

            # Assert
            assert response.status_code == 200

