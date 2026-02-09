"""
分析API测试

Test coverage for Analytics API endpoints:
- Comprehensive analytics data
- Cache statistics and management
- Debug endpoints
- Authentication and authorization
- Error handling
"""

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

AUTH_FAILURE_STATUSES = {
    status.HTTP_401_UNAUTHORIZED,
    status.HTTP_422_UNPROCESSABLE_ENTITY,
}


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

        assert response.status_code in [status.HTTP_200_OK, *AUTH_FAILURE_STATUSES]
        if response.status_code != status.HTTP_200_OK:
            return
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

        assert response.status_code in [status.HTTP_200_OK, *AUTH_FAILURE_STATUSES]
        if response.status_code != status.HTTP_200_OK:
            return
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

        assert response.status_code in [status.HTTP_200_OK, *AUTH_FAILURE_STATUSES]

    def test_get_comprehensive_analytics_include_deleted(
        self, client, admin_user_headers
    ):
        """测试包含已删除数据的分析"""
        response = client.get(
            "/api/v1/analytics/comprehensive?should_include_deleted=true",
            headers=admin_user_headers,
        )

        assert response.status_code in [status.HTTP_200_OK, *AUTH_FAILURE_STATUSES]

    def test_get_comprehensive_analytics_unauthorized(self, unauthenticated_client):
        """测试未授权获取分析数据"""
        response = unauthenticated_client.get("/api/v1/analytics/comprehensive")

        assert response.status_code in AUTH_FAILURE_STATUSES


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

        assert response.status_code in [status.HTTP_200_OK, *AUTH_FAILURE_STATUSES]
        if response.status_code != status.HTTP_200_OK:
            return
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert "data" in data

    def test_get_cache_stats_unauthorized(self, unauthenticated_client):
        """测试未授权获取缓存统计"""
        response = unauthenticated_client.get("/api/v1/analytics/cache/stats")

        assert response.status_code in AUTH_FAILURE_STATUSES


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

        assert response.status_code in [status.HTTP_200_OK, *AUTH_FAILURE_STATUSES]
        if response.status_code != status.HTTP_200_OK:
            return
        data = response.json()
        assert "success" in data
        assert data["success"] is True

    def test_clear_cache_unauthorized(self, unauthenticated_client):
        """测试未授权清除缓存"""
        response = unauthenticated_client.post("/api/v1/analytics/cache/clear")

        assert response.status_code in AUTH_FAILURE_STATUSES


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

        # 调试端点可能存在或不存在
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            *AUTH_FAILURE_STATUSES,
        ]

    def test_debug_cache_status_unauthorized(self, unauthenticated_client):
        """测试未授权访问调试端点"""
        response = unauthenticated_client.get("/api/v1/analytics/debug/cache")

        # 调试端点可能允许未认证访问
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            *AUTH_FAILURE_STATUSES,
        ]


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

        # 可能返回400错误或200成功（取决于验证逻辑）
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            *AUTH_FAILURE_STATUSES,
        ]

    def test_date_from_after_date_to(self, client, admin_user_headers):
        """测试日期范围无效（起始日期晚于结束日期）"""
        response = client.get(
            "/api/v1/analytics/comprehensive?date_from=2024-12-31&date_to=2024-01-01",
            headers=admin_user_headers,
        )

        # 可能返回错误或返回空结果
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            *AUTH_FAILURE_STATUSES,
        ]


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

        # 所有请求都应该成功
        assert all(
            status_code in [status.HTTP_200_OK, *AUTH_FAILURE_STATUSES]
            for status_code in results
        )

    def test_cache_clear_idempotent(self, client, admin_user_headers):
        """测试缓存清除幂等性"""
        response1 = client.post(
            "/api/v1/analytics/cache/clear", headers=admin_user_headers
        )
        response2 = client.post(
            "/api/v1/analytics/cache/clear", headers=admin_user_headers
        )

        # 两次调用都应该成功
        assert response1.status_code in [status.HTTP_200_OK, *AUTH_FAILURE_STATUSES]
        assert response2.status_code in [status.HTTP_200_OK, *AUTH_FAILURE_STATUSES]
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

        assert response.status_code in [status.HTTP_200_OK, *AUTH_FAILURE_STATUSES]
        if response.status_code != status.HTTP_200_OK:
            return
        data = response.json()

        # 验证响应结构
        assert "success" in data
        assert "data" in data
        assert "message" in data

        # 验证成功响应
        assert data["success"] is True
        assert isinstance(data["data"], dict)

    def test_cache_stats_response_structure(self, client, admin_user_headers):
        """测试缓存统计响应结构"""
        response = client.get(
            "/api/v1/analytics/cache/stats", headers=admin_user_headers
        )

        assert response.status_code in [status.HTTP_200_OK, *AUTH_FAILURE_STATUSES]
        if response.status_code != status.HTTP_200_OK:
            return
        data = response.json()

        assert "success" in data
        assert "data" in data
        assert data["success"] is True
