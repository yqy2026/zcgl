"""Tests for asset filter/dropdown endpoints"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.crud.asset import asset_crud
from src.models.asset import Asset
from src.models.ownership import Ownership
from src.services.organization_permission_service import (
    invalidate_user_accessible_organizations_cache,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def authenticated_client(client: TestClient, test_data) -> TestClient:
    """Authenticate client with real login cookie before each test."""
    admin_user = test_data["admin"]
    invalidate_user_accessible_organizations_cache(str(admin_user.id))
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": admin_user.username, "password": "Admin123!@#"},
    )
    assert response.status_code == 200

    auth_token = response.cookies.get("auth_token")
    csrf_token = response.cookies.get("csrf_token")
    assert auth_token is not None
    client.cookies.set("auth_token", auth_token)
    if csrf_token is not None:
        client.cookies.set("csrf_token", csrf_token)
    return client


class TestAssetFilterEndpoints:
    """Test suite for asset filter/dropdown endpoints"""

    @staticmethod
    def _seed_assets_for_filters(db_session, organization_id: str, suffix: str) -> None:
        """Seed deterministic asset rows for filter endpoint assertions."""
        db_session.add_all(
            [
                Asset(
                    property_name=f"筛选资产-A-{suffix}",
                    address="集成测试地址-A",
                    ownership_status=f"已确权-{suffix}",
                    property_nature=f"经营类-{suffix}",
                    usage_status=f"出租-{suffix}",
                    business_category=f"业态B-{suffix}",
                    organization_id=organization_id,
                    data_status="正常",
                ),
                Asset(
                    property_name=f"筛选资产-B-{suffix}",
                    address="集成测试地址-B",
                    ownership_status=f"待确权-{suffix}",
                    property_nature=f"非经营类-{suffix}",
                    usage_status=f"空置-{suffix}",
                    business_category=f"业态A-{suffix}",
                    organization_id=organization_id,
                    data_status="正常",
                ),
                Asset(
                    property_name=f"筛选资产-C-{suffix}",
                    address="集成测试地址-C",
                    ownership_status=f"已确权-{suffix}",
                    property_nature=f"经营类-{suffix}",
                    usage_status=f"出租-{suffix}",
                    business_category=f"业态A-{suffix}",
                    organization_id=organization_id,
                    data_status="正常",
                ),
                Asset(
                    property_name=f"筛选资产-D-{suffix}",
                    address="集成测试地址-D",
                    ownership_status=f"已确权-{suffix}",
                    property_nature=f"经营类-{suffix}",
                    usage_status=f"出租-{suffix}",
                    business_category="",
                    organization_id=organization_id,
                    data_status="正常",
                ),
            ]
        )
        db_session.commit()

    @staticmethod
    def _seed_ownership_entities(db_session, suffix: str) -> tuple[str, str]:
        """Seed ownership rows to validate status filter + dedup behavior."""
        expected_name = f"去重权属-{suffix}"
        deleted_name = f"已删除权属-{suffix}"
        db_session.add_all(
            [
                Ownership(
                    name=expected_name,
                    code=f"OW{suffix[:4]}001",
                    short_name="去重1",
                    data_status="正常",
                ),
                Ownership(
                    name=expected_name,
                    code=f"OW{suffix[:4]}002",
                    short_name="去重2",
                    data_status="正常",
                ),
                Ownership(
                    name="",
                    code=f"OW{suffix[:4]}003",
                    short_name="空名",
                    data_status="正常",
                ),
                Ownership(
                    name=deleted_name,
                    code=f"OW{suffix[:4]}004",
                    short_name="删除",
                    data_status="已删除",
                ),
            ]
        )
        db_session.commit()
        return expected_name, deleted_name

    def test_ownership_entities_endpoint(self, authenticated_client: TestClient):
        """Test GET /ownership-entities"""
        response = authenticated_client.get("/api/v1/assets/ownership-entities")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(isinstance(item, str) for item in data)

    def test_ownership_entities_filters_deleted_and_deduplicates(
        self, authenticated_client: TestClient, db_session
    ):
        """Ownership entities should deduplicate names and filter invalid statuses."""
        suffix = uuid4().hex[:8]
        expected_name, deleted_name = self._seed_ownership_entities(db_session, suffix)

        response = authenticated_client.get("/api/v1/assets/ownership-entities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data == sorted(data)
        assert len(data) == len(set(data))
        assert expected_name in data
        assert data.count(expected_name) == 1
        assert deleted_name not in data
        assert "" not in data

    def test_business_categories_endpoint(self, authenticated_client: TestClient):
        """Test GET /business-categories"""
        response = authenticated_client.get("/api/v1/assets/business-categories")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_usage_statuses_endpoint(self, authenticated_client: TestClient):
        """Test GET /usage-statuses"""
        response = authenticated_client.get("/api/v1/assets/usage-statuses")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_property_natures_endpoint(self, authenticated_client: TestClient):
        """Test GET /property-natures"""
        response = authenticated_client.get("/api/v1/assets/property-natures")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_ownership_statuses_endpoint(self, authenticated_client: TestClient):
        """Test GET /ownership-statuses"""
        response = authenticated_client.get("/api/v1/assets/ownership-statuses")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_endpoint_returns_sorted_unique_values(
        self, authenticated_client: TestClient
    ):
        """Test that endpoints return sorted, unique values"""
        response = authenticated_client.get("/api/v1/assets/ownership-entities")
        data = response.json()

        # Check uniqueness
        assert len(data) == len(set(data))

        # Check sorted (ascending)
        assert data == sorted(data)

    def test_backward_compatibility(self, authenticated_client: TestClient):
        """Ensure response format matches original implementation"""
        response = authenticated_client.get("/api/v1/assets/ownership-entities")
        data = response.json()

        # Verify response structure
        assert isinstance(data, list)
        assert all(isinstance(item, str) for item in data)

    def test_unauthorized_access(self, client: TestClient):
        """Test that unauthorized requests are rejected"""
        response = client.get("/api/v1/assets/ownership-entities")

        assert response.status_code == 401

    def test_all_filters_consistent_structure(
        self, authenticated_client: TestClient
    ):
        """Test that all filter endpoints have consistent response structure"""
        endpoints = [
            "/api/v1/assets/ownership-entities",
            "/api/v1/assets/business-categories",
            "/api/v1/assets/usage-statuses",
            "/api/v1/assets/property-natures",
            "/api/v1/assets/ownership-statuses",
        ]

        for endpoint in endpoints:
            response = authenticated_client.get(endpoint)

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            # All endpoints should return lists of strings
            assert all(isinstance(item, str) for item in data)
            # All values should be sorted
            assert data == sorted(data)
            # All values should be unique
            assert len(data) == len(set(data))

    def test_filter_endpoints_include_seeded_values(
        self, authenticated_client: TestClient, db_session, test_data
    ):
        """Filter endpoints should reflect deterministic seeded asset values."""
        suffix = uuid4().hex[:8]
        organization_id = str(test_data["organization"].id)
        self._seed_assets_for_filters(db_session, organization_id, suffix)
        asset_crud.clear_cache()

        business_categories = authenticated_client.get(
            "/api/v1/assets/business-categories"
        ).json()
        usage_statuses = authenticated_client.get("/api/v1/assets/usage-statuses").json()
        property_natures = authenticated_client.get(
            "/api/v1/assets/property-natures"
        ).json()
        ownership_statuses = authenticated_client.get(
            "/api/v1/assets/ownership-statuses"
        ).json()

        assert f"业态A-{suffix}" in business_categories
        assert f"业态B-{suffix}" in business_categories
        assert "" not in business_categories
        assert business_categories == sorted(business_categories)
        assert len(business_categories) == len(set(business_categories))

        assert f"出租-{suffix}" in usage_statuses
        assert f"空置-{suffix}" in usage_statuses
        assert usage_statuses == sorted(usage_statuses)
        assert len(usage_statuses) == len(set(usage_statuses))

        assert f"经营类-{suffix}" in property_natures
        assert f"非经营类-{suffix}" in property_natures
        assert property_natures == sorted(property_natures)
        assert len(property_natures) == len(set(property_natures))

        assert f"已确权-{suffix}" in ownership_statuses
        assert f"待确权-{suffix}" in ownership_statuses
        assert ownership_statuses == sorted(ownership_statuses)
        assert len(ownership_statuses) == len(set(ownership_statuses))
