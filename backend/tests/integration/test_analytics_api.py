"""
Analytics API 集成测试
测试 analytics.py 的真实认证与真实数据链路
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.models.asset import Asset

pytestmark = pytest.mark.integration


@pytest.fixture
def authenticated_client(client: TestClient, test_data) -> TestClient:
    """使用真实登录流程为客户端注入认证 cookie。"""
    admin_user = test_data["admin"]
    response = client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "Admin123!@#"},
    )
    assert response.status_code == 200

    auth_token = response.cookies.get("auth_token")
    csrf_token = response.cookies.get("csrf_token")
    assert auth_token is not None
    client.cookies.set("auth_token", auth_token)
    if csrf_token is not None:
        client.cookies.set("csrf_token", csrf_token)
    setattr(client, "_csrf_token", csrf_token)
    return client


@pytest.fixture
def csrf_headers(authenticated_client: TestClient) -> dict[str, str]:
    """返回 cookie-only 认证下写操作所需 CSRF 头。"""
    csrf_token = getattr(authenticated_client, "_csrf_token", None)
    if csrf_token is None:
        return {}
    return {"X-CSRF-Token": csrf_token}


def _seed_assets_for_analytics(
    db_session,
    *,
    organization_id: str,
    suffix: str,
) -> tuple[str, str]:
    """写入可预测资产数据用于分析断言。"""
    unique_nature_normal = f"分析性质-正常-{suffix}"
    unique_nature_deleted = f"分析性质-删除-{suffix}"

    db_session.add_all(
        [
            Asset(
                property_name=f"分析资产-正常-{suffix}",
                address=f"分析地址-正常-{suffix}",
                ownership_status="已确权",
                property_nature=unique_nature_normal,
                usage_status="出租",
                business_category=f"分析业态-正常-{suffix}",
                organization_id=organization_id,
                rentable_area=1000,
                rented_area=800,
                data_status="正常",
            ),
            Asset(
                property_name=f"分析资产-删除-{suffix}",
                address=f"分析地址-删除-{suffix}",
                ownership_status="待确权",
                property_nature=unique_nature_deleted,
                usage_status="空置",
                business_category=f"分析业态-删除-{suffix}",
                organization_id=organization_id,
                rentable_area=500,
                rented_area=0,
                data_status="已删除",
            ),
        ]
    )
    db_session.commit()
    return unique_nature_normal, unique_nature_deleted


class TestAnalyticsAPIContracts:
    """Analytics API 真实契约测试。"""

    def test_analytics_requires_authentication(self, client: TestClient) -> None:
        response = client.get("/api/v1/analytics/comprehensive")
        assert response.status_code == 401
        payload = response.json()
        assert payload.get("success") is False

    def test_analytics_comprehensive_endpoint_exists(self, authenticated_client):
        """综合分析端点返回统一结构。"""
        response = authenticated_client.get("/api/v1/analytics/comprehensive")

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True
        data = payload.get("data")
        assert isinstance(data, dict)
        assert isinstance(data.get("total_assets"), int)
        assert isinstance(data.get("timestamp"), str)
        assert isinstance(data.get("area_summary"), dict)
        assert isinstance(data.get("occupancy_rate"), dict)

    def test_analytics_comprehensive_with_params(self, authenticated_client):
        """综合分析端点参数化请求。"""
        response = authenticated_client.get(
            "/api/v1/analytics/comprehensive?should_include_deleted=false&should_use_cache=false"
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True

    def test_comprehensive_include_deleted_expands_scope(
        self,
        authenticated_client: TestClient,
        db_session,
        test_data,
    ) -> None:
        """include_deleted=true 应至少包含多出的已删除资产。"""
        suffix = uuid4().hex[:8]
        _seed_assets_for_analytics(
            db_session,
            organization_id=test_data["organization"].id,
            suffix=suffix,
        )

        without_deleted = authenticated_client.get(
            "/api/v1/analytics/comprehensive"
            "?should_include_deleted=false&should_use_cache=false"
        )
        with_deleted = authenticated_client.get(
            "/api/v1/analytics/comprehensive"
            "?should_include_deleted=true&should_use_cache=false"
        )

        assert without_deleted.status_code == 200
        assert with_deleted.status_code == 200

        without_total = without_deleted.json()["data"]["total_assets"]
        with_total = with_deleted.json()["data"]["total_assets"]
        assert isinstance(without_total, int)
        assert isinstance(with_total, int)
        assert with_total >= without_total + 1

    def test_analytics_cache_stats_endpoint_exists(self, authenticated_client):
        """缓存统计端点返回统一结构。"""
        response = authenticated_client.get("/api/v1/analytics/cache/stats")

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True
        data = payload.get("data")
        assert isinstance(data, dict)
        assert isinstance(data.get("cache_type"), str)
        assert isinstance(data.get("stats"), dict)
        assert isinstance(data.get("timestamp"), str)

    def test_analytics_cache_clear_endpoint_exists(
        self, authenticated_client, csrf_headers
    ):
        """清除缓存端点返回稳定数据。"""
        response = authenticated_client.post(
            "/api/v1/analytics/cache/clear", headers=csrf_headers
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True
        data = payload.get("data")
        assert isinstance(data, dict)
        assert data.get("status") in {"success", "failed"}
        assert isinstance(data.get("cleared_keys"), int)
        assert isinstance(data.get("timestamp"), str)

    def test_analytics_trend_endpoint_exists(self, authenticated_client):
        """趋势端点返回统一结构。"""
        response = authenticated_client.get(
            "/api/v1/analytics/trend?trend_type=occupancy&time_dimension=monthly"
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True
        data = payload.get("data")
        assert isinstance(data, dict)
        assert data.get("trend_type") == "occupancy"
        assert data.get("time_dimension") == "monthly"
        assert isinstance(data.get("data"), list)

    def test_analytics_distribution_endpoint_contains_seeded_data(
        self, authenticated_client, db_session, test_data
    ):
        """分布端点应包含测试写入的唯一分类值。"""
        suffix = uuid4().hex[:8]
        unique_nature_normal, _ = _seed_assets_for_analytics(
            db_session,
            organization_id=test_data["organization"].id,
            suffix=suffix,
        )

        response = authenticated_client.get(
            "/api/v1/analytics/distribution?distribution_type=property_nature"
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("success") is True
        data = payload.get("data")
        assert isinstance(data, dict)
        assert data.get("distribution_type") == "property_nature"
        distribution = data.get("data")
        assert isinstance(distribution, dict)
        assert unique_nature_normal in distribution
        seeded_entry = distribution[unique_nature_normal]
        assert isinstance(seeded_entry, dict)
        assert int(seeded_entry.get("count", 0)) >= 1

    def test_analytics_distribution_invalid_type(self, authenticated_client):
        """非法分布类型应返回 400 业务错误。"""
        response = authenticated_client.get(
            "/api/v1/analytics/distribution?distribution_type=invalid_type"
        )
        assert response.status_code == 400
        payload = response.json()
        assert payload.get("success") is False
        error = payload.get("error")
        assert isinstance(error, dict)
        assert error.get("code") == "INVALID_REQUEST"

    def test_analytics_debug_cache_endpoint_exists(self, authenticated_client):
        """调试缓存端点在测试环境保持不可见（404）。"""
        debug_client = TestClient(
            authenticated_client.app,
            raise_server_exceptions=False,
        )
        debug_client.cookies.update(authenticated_client.cookies)
        response = debug_client.get("/api/v1/analytics/debug/cache")

        # debug-only + localhost 限制：测试环境应返回 404（不暴露端点）
        assert response.status_code == 404
        payload = response.json()
        assert payload.get("success") is False

    def test_router_registration_via_openapi(self, authenticated_client):
        """路由应在 OpenAPI 中可见（真实注册验证）。"""
        response = authenticated_client.get("/openapi.json")
        assert response.status_code == 200
        paths = response.json().get("paths", {})
        assert "/api/v1/analytics/comprehensive" in paths
        assert "/api/v1/analytics/cache/stats" in paths
        assert "/api/v1/analytics/cache/clear" in paths
        assert "/api/v1/analytics/trend" in paths
        assert "/api/v1/analytics/distribution" in paths
        assert "/api/v1/analytics/debug/cache" in paths
