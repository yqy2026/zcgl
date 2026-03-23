"""
分析API测试

Test coverage for Analytics API endpoints:
- Comprehensive analytics data
- Cache statistics and management
- Debug endpoints
- Authentication and authorization
- Error handling
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.database import get_async_db
from src.main import app
from src.middleware.auth import get_current_active_user

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def admin_user_headers():
    """管理员用户认证头"""
    # Since client fixture mocks authentication, we don't need real token
    return {}


@pytest.fixture
def client(monkeypatch):
    """轻量客户端：绕过真实数据库连接，仅测试路由行为。"""
    mock_user = Mock()
    mock_user.id = "admin_001"
    mock_user.username = "admin"
    mock_user.is_active = True

    async def override_get_db():
        yield AsyncMock()

    async def mock_get_comprehensive_analytics(
        _self,
        *,
        filters=None,
        should_use_cache=True,
        current_user=None,
    ):
        return {
            "total_assets": 1,
            "total_income": 1200.0,
            "self_operated_rent_income": 1000.0,
            "agency_service_income": 200.0,
            "customer_entity_count": 2,
            "customer_contract_count": 2,
            "metrics_version": "req-ana-001-v1",
            "filters_applied": filters or {},
            "should_use_cache": should_use_cache,
            "requested_by": getattr(current_user, "username", None),
        }

    monkeypatch.setattr(
        "src.services.analytics.analytics_service.AnalyticsService.get_comprehensive_analytics",
        mock_get_comprehensive_analytics,
    )

    app.dependency_overrides[get_async_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    monkeypatch.setattr(
        "src.middleware.auth.authz_service.check_access",
        AsyncMock(return_value=SimpleNamespace(allowed=True, reason_code="ALLOW")),
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client():
    """未认证客户端：同样避免触发真实数据库连接。"""

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_async_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ============================================================================
# Comprehensive Analytics Tests
# ============================================================================


class TestComprehensiveAnalytics:
    """测试综合分析API"""

    def test_get_comprehensive_analytics_success(self, client, admin_user_headers):
        """测试成功获取综合分析数据"""
        response = client.get(
            "/api/v1/analytics/comprehensive", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert "data" in data

    def test_get_comprehensive_analytics_with_date_filters(
        self, client, admin_user_headers
    ):
        """测试带日期筛选的综合分析"""
        response = client.get(
            "/api/v1/analytics/comprehensive?date_from=2024-01-01&date_to=2024-12-31",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    def test_get_comprehensive_analytics_without_cache(
        self, client, admin_user_headers
    ):
        """测试不使用缓存获取分析数据"""
        response = client.get(
            "/api/v1/analytics/comprehensive?should_use_cache=false",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK

    def test_get_comprehensive_analytics_include_deleted(
        self, client, admin_user_headers
    ):
        """测试包含已删除数据的分析"""
        response = client.get(
            "/api/v1/analytics/comprehensive?should_include_deleted=true",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK

    def test_get_comprehensive_analytics_unauthorized(self, unauthenticated_client):
        """测试未授权获取分析数据"""
        response = unauthenticated_client.get("/api/v1/analytics/comprehensive")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Cache Statistics Tests
# ============================================================================


class TestCacheStatistics:
    """测试缓存统计API"""

    def test_get_cache_stats_success(self, client, admin_user_headers):
        """测试成功获取缓存统计"""
        response = client.get(
            "/api/v1/analytics/cache/stats", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert "data" in data

    def test_get_cache_stats_unauthorized(self, unauthenticated_client):
        """测试未授权获取缓存统计"""
        response = unauthenticated_client.get("/api/v1/analytics/cache/stats")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Cache Management Tests
# ============================================================================


class TestCacheManagement:
    """测试缓存管理API"""

    def test_clear_cache_success(self, client, admin_user_headers):
        """测试成功清除缓存"""
        response = client.post(
            "/api/v1/analytics/cache/clear", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "success" in data
        assert data["success"] is True

    def test_clear_cache_unauthorized(self, unauthenticated_client):
        """测试未授权清除缓存"""
        response = unauthenticated_client.post("/api/v1/analytics/cache/clear")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Debug Endpoints Tests
# ============================================================================


class TestDebugEndpoints:
    """测试调试端点"""

    def test_debug_cache_status(self, client, admin_user_headers):
        """测试调试缓存状态"""
        response = client.get(
            "/api/v1/analytics/debug/cache", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_debug_cache_status_unauthorized(self, unauthenticated_client):
        """测试未授权访问调试端点"""
        response = unauthenticated_client.get("/api/v1/analytics/debug/cache")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Data Validation Tests
# ============================================================================


class TestAnalyticsDataValidation:
    """测试分析数据验证"""

    def test_invalid_date_format(self, client, admin_user_headers):
        """测试无效的日期格式"""
        response = client.get(
            "/api/v1/analytics/comprehensive?date_from=invalid-date",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK

    def test_date_from_after_date_to(self, client, admin_user_headers):
        """测试日期范围无效（起始日期晚于结束日期）"""
        response = client.get(
            "/api/v1/analytics/comprehensive?date_from=2024-12-31&date_to=2024-01-01",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK


# ============================================================================
# Performance Tests
# ============================================================================


class TestAnalyticsPerformance:
    """测试分析API性能"""

    def test_concurrent_analytics_requests(self, client, admin_user_headers):
        """测试并发分析请求"""
        import threading

        results = []

        def make_request():
            response = client.get(
                "/api/v1/analytics/cache/stats", headers=admin_user_headers
            )
            results.append(response.status_code)

        threads = [threading.Thread(target=make_request) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(status_code == status.HTTP_200_OK for status_code in results)

    def test_cache_clear_idempotent(self, client, admin_user_headers):
        """测试缓存清除幂等性"""
        response1 = client.post(
            "/api/v1/analytics/cache/clear", headers=admin_user_headers
        )
        response2 = client.post(
            "/api/v1/analytics/cache/clear", headers=admin_user_headers
        )

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK
        assert response1.status_code == response2.status_code


# ============================================================================
# Response Structure Tests
# ============================================================================


class TestAnalyticsResponseStructure:
    """测试响应结构"""

    def test_comprehensive_analytics_response_structure(
        self, client, admin_user_headers
    ):
        """测试综合分析响应结构"""
        response = client.get(
            "/api/v1/analytics/comprehensive", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # 验证响应结构
        assert "success" in data
        assert "data" in data
        assert "message" in data

        # 验证成功响应
        assert data["success"] is True
        assert isinstance(data["data"], dict)
        assert data["data"]["total_income"] == 1200.0
        assert data["data"]["self_operated_rent_income"] == 1000.0
        assert data["data"]["agency_service_income"] == 200.0
        assert data["data"]["customer_entity_count"] == 2
        assert data["data"]["customer_contract_count"] == 2
        assert data["data"]["metrics_version"] == "req-ana-001-v1"

    def test_export_should_include_metrics_version_in_payload(
        self, client, admin_user_headers
    ):
        response = client.post(
            "/api/v1/analytics/export?export_format=csv",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert "req-ana-001-v1" in response.text

    def test_cache_stats_response_structure(self, client, admin_user_headers):
        """测试缓存统计响应结构"""
        response = client.get(
            "/api/v1/analytics/cache/stats", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "success" in data
        assert "data" in data
        assert data["success"] is True
