"""Tests for asset filter/dropdown endpoints"""

import pytest
from fastapi.testclient import TestClient


class TestAssetFilterEndpoints:
    """Test suite for asset filter/dropdown endpoints"""

    def test_ownership_entities_endpoint(
        self, client: TestClient, test_token: str
    ):
        """Test GET /ownership-entities"""
        response = client.get(
            "/api/v1/assets/ownership-entities",
            headers={"Authorization": f"Bearer {test_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(isinstance(item, str) for item in data)

    def test_business_categories_endpoint(
        self, client: TestClient, test_token: str
    ):
        """Test GET /business-categories"""
        response = client.get(
            "/api/v1/assets/business-categories",
            headers={"Authorization": f"Bearer {test_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_usage_statuses_endpoint(self, client: TestClient, test_token: str):
        """Test GET /usage-statuses"""
        response = client.get(
            "/api/v1/assets/usage-statuses",
            headers={"Authorization": f"Bearer {test_token}"},
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_property_natures_endpoint(self, client: TestClient, test_token: str):
        """Test GET /property-natures"""
        response = client.get(
            "/api/v1/assets/property-natures",
            headers={"Authorization": f"Bearer {test_token}"},
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_ownership_statuses_endpoint(
        self, client: TestClient, test_token: str
    ):
        """Test GET /ownership-statuses"""
        response = client.get(
            "/api/v1/assets/ownership-statuses",
            headers={"Authorization": f"Bearer {test_token}"},
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_endpoint_returns_sorted_unique_values(
        self, client: TestClient, test_token: str
    ):
        """Test that endpoints return sorted, unique values"""
        response = client.get(
            "/api/v1/assets/ownership-entities",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        data = response.json()

        # Check uniqueness
        assert len(data) == len(set(data))

        # Check sorted (ascending)
        assert data == sorted(data)

    def test_backward_compatibility(self, client: TestClient, test_token: str):
        """Ensure response format matches original implementation"""
        response = client.get(
            "/api/v1/assets/ownership-entities",
            headers={"Authorization": f"Bearer {test_token}"},
        )
        data = response.json()

        # Verify response structure
        assert isinstance(data, list)
        assert all(isinstance(item, str) for item in data)

    def test_unauthorized_access(self, client: TestClient):
        """Test that unauthorized requests are rejected"""
        response = client.get("/api/v1/assets/ownership-entities")

        assert response.status_code == 401

    def test_all_filters_consistent_structure(
        self, client: TestClient, test_token: str
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
            response = client.get(
                endpoint,
                headers={"Authorization": f"Bearer {test_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            # All endpoints should return lists of strings
            assert all(isinstance(item, str) for item in data)
            # All values should be sorted
            assert data == sorted(data)
            # All values should be unique
            assert len(data) == len(set(data))
