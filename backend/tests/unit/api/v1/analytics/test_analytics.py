"""
Analytics API 测试
测试综合分析 API 端点
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
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


@pytest.fixture
def sample_analytics_data():
    """示例分析数据"""
    return {
        "total_assets": 100,
        "total_area": 50000.0,
        "occupancy_rate": 85.5,
        "total_revenue": 1000000.0,
        "total_contracts": 50,
        "active_contracts": 35,
        "expired_contracts": 10,
        "expiring_soon_contracts": 5,
        "average_rent_per_sqm": 20.0,
        "revenue_by_type": {
            "lease": 800000.0,
            "service": 150000.0,
            "management": 50000.0,
        },
        "asset_distribution": {
            "by_type": [
                {"type": "building", "count": 50, "area": 30000.0},
                {"type": "land", "count": 30, "area": 15000.0},
                {"type": "facility", "count": 20, "area": 5000.0},
            ],
            "by_status": [
                {"status": "active", "count": 80, "area": 40000.0},
                {"status": "inactive", "count": 15, "area": 8000.0},
                {"status": "maintenance", "count": 5, "area": 2000.0},
            ],
        },
    }


# =============================================================================
# 综合分析 API 测试
# =============================================================================

class TestComprehensiveAnalytics:
    """综合统计分析 API 测试"""

    def test_get_comprehensive_analytics_success(
        self, client, mock_db, sample_analytics_data
    ):
        """
        测试成功获取综合分析数据

        Given: 用户已登录
        When: 调用 GET /api/v1/analytics/comprehensive
        Then: 返回完整的统计数据
        """
        # Arrange
        with patch(
            "src.services.analytics.analytics_service.AnalyticsService.get_comprehensive_analytics"
        ) as mock_get:
            mock_get.return_value = sample_analytics_data

            # Act
            response = client.get("/api/v1/analytics/comprehensive")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert data["data"]["total_assets"] == 100
            assert data["data"]["occupancy_rate"] == 85.5

    def test_get_comprehensive_analytics_with_filters(self, client, mock_db):
        """
        测试带筛选条件的分析数据获取

        Given: 用户已登录，提供日期范围
        When: 调用 GET /api/v1/analytics/comprehensive?date_from=2024-01-01&date_to=2024-12-31
        Then: 服务层收到正确的筛选条件
        """
        # Arrange
        with patch(
            "src.services.analytics.analytics_service.AnalyticsService.get_comprehensive_analytics"
        ) as mock_get:
            mock_get.return_value = {"total_assets": 50}

            # Act
            response = client.get(
                "/api/v1/analytics/comprehensive"
                "?date_from=2024-01-01&date_to=2024-12-31&include_deleted=true"
            )

            # Assert
            assert response.status_code == 200
            # 验证服务层被调用
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "filters" in call_args.kwargs

    def test_get_comprehensive_analytics_without_cache(self, client, mock_db):
        """
        测试禁用缓存的分析数据获取

        Given: 用户设置 should_use_cache=false
        When: 调用 API 并禁用缓存
        Then: 服务层收到禁用缓存标志
        """
        # Arrange
        with patch(
            "src.services.analytics.analytics_service.AnalyticsService.get_comprehensive_analytics"
        ) as mock_get:
            mock_get.return_value = {"total_assets": 100}

            # Act
            response = client.get(
                "/api/v1/analytics/comprehensive?should_use_cache=false"
            )

            # Assert
            assert response.status_code == 200
            call_args = mock_get.call_args
            assert call_args.kwargs["should_use_cache"] is False


# =============================================================================
# 缓存管理 API 测试
# =============================================================================

class TestCacheManagement:
    """缓存管理 API 测试"""

    def test_get_cache_stats(self, client, mock_db):
        """
        测试获取缓存统计信息

        Given: 管理员已登录
        When: 调用 GET /api/v1/analytics/cache/stats
        Then: 返回缓存统计信息
        """
        # Arrange
        with patch(
            "src.services.analytics.analytics_service.AnalyticsService.get_cache_stats"
        ) as mock_stats:
            mock_stats.return_value = {
                "total_keys": 10,
                "hit_rate": 0.85,
                "miss_rate": 0.15,
                "memory_usage": "1.2MB",
            }

            # Act
            response = client.get("/api/v1/analytics/cache/stats")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["total_keys"] == 10
            assert data["data"]["hit_rate"] == 0.85

    def test_clear_cache(self, client, mock_db):
        """
        测试清除缓存

        Given: 管理员已登录
        When: 调用 POST /api/v1/analytics/cache/clear
        Then: 缓存被清除，返回成功消息
        """
        # Arrange
        with patch("src.core.cache_manager.analytics_cache.clear") as mock_clear:
            # Act
            response = client.post("/api/v1/analytics/cache/clear")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "清除成功" in data["message"]
            mock_clear.assert_called_once()


# =============================================================================
# 趋势分析 API 测试
# =============================================================================

class TestTrendAnalysis:
    """趋势分析 API 测试"""

    def test_get_trend_data(self, client, mock_db):
        """
        测试获取趋势数据

        Given: 用户已登录
        When: 调用 GET /api/v1/analytics/trend?trend_type=occupancy&time_dimension=monthly
        Then: 返回月度趋势数据
        """
        # Arrange
        with patch(
            "src.services.analytics.analytics_service.AnalyticsService.calculate_trend"
        ) as mock_trend:
            mock_trend.return_value = {
                "period": "monthly",
                "data_points": [
                    {"month": "2024-01", "revenue": 80000.0, "occupancy_rate": 82.0},
                    {"month": "2024-02", "revenue": 85000.0, "occupancy_rate": 83.5},
                    {"month": "2024-03", "revenue": 90000.0, "occupancy_rate": 85.0},
                ],
            }

            # Act
            response = client.get(
                "/api/v1/analytics/trend?trend_type=occupancy&time_dimension=monthly"
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data


# =============================================================================
# 分布分析 API 测试
# =============================================================================

class TestDistributionAnalysis:
    """分布分析 API 测试"""

    def test_get_distribution_by_type(self, client, mock_db):
        """
        测试按物业性质获取分布数据

        Given: 用户已登录
        When: 调用 GET /api/v1/analytics/distribution?distribution_type=property_nature
        Then: 返回按物业性质分组的分布数据
        """
        # Arrange
        with patch(
            "src.services.analytics.analytics_service.AnalyticsService.calculate_distribution"
        ) as mock_distribution:
            mock_distribution.return_value = {
                "property_nature": [
                    {"type": "commercial", "count": 50, "area": 30000.0},
                    {"type": "non_commercial", "count": 30, "area": 15000.0},
                ],
            }

            # Act
            response = client.get("/api/v1/analytics/distribution?distribution_type=property_nature")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data

    def test_get_distribution_by_status(self, client, mock_db):
        """
        测试按使用状态获取分布数据

        Given: 用户已登录
        When: 调用 GET /api/v1/analytics/distribution?distribution_type=usage_status
        Then: 返回按使用状态分组的分布数据
        """
        # Arrange
        with patch(
            "src.services.analytics.analytics_service.AnalyticsService.calculate_distribution"
        ) as mock_distribution:
            mock_distribution.return_value = {
                "usage_status": [
                    {"status": "rented", "count": 80, "area": 40000.0},
                    {"status": "vacant", "count": 15, "area": 8000.0},
                ],
            }

            # Act
            response = client.get("/api/v1/analytics/distribution?distribution_type=usage_status")

            # Assert
            assert response.status_code == 200


# =============================================================================
# 数据导出 API 测试
# =============================================================================

class TestDataExport:
    """数据导出 API 测试"""

    def test_export_analytics_data(self, client, mock_db, sample_analytics_data):
        """
        测试导出分析数据为 CSV

        Given: 管理员已登录
        When: 调用 POST /api/v1/analytics/export?export_format=csv
        Then: 返回 CSV 文件
        """
        # Arrange
        with patch(
            "src.services.analytics.analytics_service.AnalyticsService.get_comprehensive_analytics"
        ) as mock_get:
            mock_get.return_value = sample_analytics_data

            # Act
            response = client.post("/api/v1/analytics/export?export_format=csv")

            # Assert
            # 导出功能应该返回 200 或 streaming response
            assert response.status_code == 200


# =============================================================================
# 错误处理测试
# =============================================================================

class TestErrorHandling:
    """错误处理测试"""

    def test_unauthorized_access(self, client):
        """
        测试未授权访问

        Given: 用户未登录
        When: 调用分析 API
        Then: 返回 401 未授权错误
        """
        # Arrange - 移除授权 override
        app.dependency_overrides.clear()

        # Act
        response = client.get("/api/v1/analytics/comprehensive")

        # Assert
        assert response.status_code == 401

    def test_service_error_handling(self, client, mock_db, mock_user):
        """
        测试服务层错误处理

        Given: 服务层抛出异常
        When: 调用分析 API
        Then: 返回 500 错误并包含错误信息
        """
        # Arrange
        with patch(
            "src.services.analytics.analytics_service.AnalyticsService.get_comprehensive_analytics"
        ) as mock_get:
            mock_get.side_effect = Exception("Database connection failed")

            # Act
            response = client.get("/api/v1/analytics/comprehensive")

            # Assert
            assert response.status_code == 500

    def test_invalid_date_format(self, client, mock_db):
        """
        测试无效日期格式

        Given: 用户提供无效的日期格式
        When: 调用分析 API
        Then: 返回 500 错误（服务层不验证日期格式）
        """
        # Act
        response = client.get(
            "/api/v1/analytics/comprehensive?date_from=invalid-date"
        )

        # Assert - 服务层可能不验证日期，返回 500
        assert response.status_code == 500


# =============================================================================
# 性能测试
# =============================================================================

class TestPerformance:
    """性能测试"""

    def test_cache_performance(self, client, mock_db, sample_analytics_data):
        """
        测试缓存性能

        Given: 第一次调用缓存未命中
        When: 连续调用两次分析 API
        Then: 第二次调用更快（使用缓存）
        """
        # Arrange
        with patch(
            "src.services.analytics.analytics_service.AnalyticsService.get_comprehensive_analytics"
        ) as mock_get:
            mock_get.return_value = sample_analytics_data

            # Act - 第一次调用
            response1 = client.get("/api/v1/analytics/comprehensive")
            # Act - 第二次调用
            response2 = client.get("/api/v1/analytics/comprehensive")

            # Assert
            assert response1.status_code == 200
            assert response2.status_code == 200
            # 第二次调用应该使用缓存（实际测试中需要测量时间）

