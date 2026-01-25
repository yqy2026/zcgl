"""
Analytics API 集成测试
测试重构后的 analytics.py API 端点
"""

import pytest

pytestmark = pytest.mark.skip(
    reason="Integration API tests require real JWT authentication setup"
)
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """创建测试客户端"""
    from src.main import app

    return TestClient(app)


@pytest.fixture
def auth_headers():
    """创建认证头（使用测试用户）"""
    # 注意：实际测试需要真实的 token 或使用测试用户
    # 这里返回一个基本的结构，实际使用时需要替换
    return {"Authorization": "Bearer test_token"}


class TestAnalyticsAPI:
    """测试 Analytics API 端点"""

    def test_analytics_comprehensive_endpoint_exists(self, client):
        """测试综合分析端点是否存在"""
        response = client.get("/api/v1/analytics/comprehensive")

        # 可能返回 401 (未认证) 或 422 (验证错误)，但不应该是 404
        assert response.status_code != 404
        assert response.status_code in [401, 422, 200]

    def test_analytics_comprehensive_with_params(self, client):
        """测试综合分析端点带参数"""
        response = client.get(
            "/api/v1/analytics/comprehensive?include_deleted=false&use_cache=true"
        )

        # 端点应该存在（不返回 404）
        assert response.status_code != 404

    def test_analytics_cache_stats_endpoint_exists(self, client):
        """测试缓存统计端点是否存在"""
        response = client.get("/api/v1/analytics/cache/stats")

        # 端点应该存在
        assert response.status_code != 404

    def test_analytics_cache_clear_endpoint_exists(self, client):
        """测试清除缓存端点是否存在"""
        response = client.post("/api/v1/analytics/cache/clear")

        # 端点应该存在
        assert response.status_code != 404

    def test_analytics_trend_endpoint_exists(self, client):
        """测试趋势数据端点是否存在"""
        response = client.get(
            "/api/v1/analytics/trend?trend_type=occupancy&time_dimension=monthly"
        )

        # 端点应该存在
        assert response.status_code != 404

    def test_analytics_distribution_endpoint_exists(self, client):
        """测试分布数据端点是否存在"""
        response = client.get(
            "/api/v1/analytics/distribution?distribution_type=property_nature"
        )

        # 端点应该存在
        assert response.status_code != 404

    def test_analytics_debug_cache_endpoint_exists(self, client):
        """测试调试缓存端点是否存在"""
        response = client.get("/api/v1/analytics/debug/cache")

        # 端点应该存在
        assert response.status_code != 404


class TestAnalyticsAPIResponseStructure:
    """测试 Analytics API 响应结构"""

    @pytest.fixture
    def mock_analytics_data(self, monkeypatch):
        """Mock AnalyticsService 返回数据"""
        from src.services.analytics.analytics_service import AnalyticsService

        def mock_get_comprehensive(self, filters, use_cache=True, current_user=None):
            return {
                "total_assets": 100,
                "timestamp": "2024-01-04T00:00:00",
                "area_summary": {"total_area": 5000},
                "occupancy_rate": {"rate": 0.85},
            }

        monkeypatch.setattr(
            AnalyticsService,
            "get_comprehensive_analytics",
            mock_get_comprehensive,
        )

    def test_comprehensive_response_structure(self, client, mock_analytics_data):
        """测试综合分析响应结构"""
        response = client.get("/api/v1/analytics/comprehensive")

        # 响应应该是 JSON
        assert response.headers["content-type"] == "application/json"

        # 响应应该有 data 字段（即使认证失败）
        json_response = response.json()
        assert "data" in json_response or "detail" in json_response


class TestAnalyticsAPIIntegration:
    """测试 Analytics API 与 Service 层集成"""

    def test_service_import(self):
        """测试 AnalyticsService 可以正确导入"""
        from src.services.analytics.analytics_service import AnalyticsService

        assert AnalyticsService is not None
        assert hasattr(AnalyticsService, "get_comprehensive_analytics")
        assert hasattr(AnalyticsService, "calculate_trend")
        assert hasattr(AnalyticsService, "calculate_distribution")
        assert hasattr(AnalyticsService, "clear_cache")
        assert hasattr(AnalyticsService, "get_cache_stats")

    def test_api_imports_service(self):
        """测试 API 层正确导入 Service"""
        import inspect

        from src.api.v1 import analytics

        # 检查 analytics.py 文件中导入了 AnalyticsService
        source = inspect.getsource(analytics)
        assert "AnalyticsService" in source

    def test_router_registration(self):
        """测试路由正确注册"""
        from src.api.v1.analytics.analytics import router

        # 检查路由定义
        routes = [route.path for route in router.routes]
        assert "/comprehensive" in routes
        assert "/cache/stats" in routes
        assert "/cache/clear" in routes
        assert "/trend" in routes
        assert "/distribution" in routes
        assert "/debug/cache" in routes
