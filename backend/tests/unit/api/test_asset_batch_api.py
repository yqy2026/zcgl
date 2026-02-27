"""
Tests for Asset Batch API endpoints (api/v1/asset_batch.py)

This test module covers batch operations for assets:
- POST /batch-update - Batch update assets
- POST /validate - Validate asset data
- POST /batch-custom-fields - Batch update custom fields
- GET /all - Get all assets (no pagination)
- POST /by-ids - Get assets by ID list
- POST /batch-delete - Batch delete assets
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestBatchUpdateAssets:
    """Tests for POST /batch-update endpoint"""

    @patch("src.api.v1.assets.asset_batch.AsyncAssetBatchService")
    def test_batch_update_success(self, mock_batch_service, client):
        """Test successful batch update of assets"""
        # Mock service result
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "success_count": 5,
            "failed_count": 0,
            "errors": [],
            "updated_asset_ids": ["id1", "id2", "id3", "id4", "id5"],
        }
        mock_service_instance = MagicMock()
        mock_service_instance.batch_update = AsyncMock(return_value=mock_result)
        mock_batch_service.return_value = mock_service_instance

        update_request = {
            "asset_ids": ["id1", "id2", "id3"],
            "updates": {"status": "active"},
            "should_update_all": False,
        }

        response = client.post("/api/v1/assets/batch-update", json=update_request)

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 5
        assert data["failed_count"] == 0

    @patch("src.api.v1.assets.asset_batch.AsyncAssetBatchService")
    def test_batch_update_all_assets(self, mock_batch_service, client):
        """Test batch update with update_all flag"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "success_count": 100,
            "failed_count": 2,
            "errors": [
                {"asset_id": "id1", "error": "Update failed"},
                {"asset_id": "id2", "error": "Validation failed"},
            ],
            "updated_asset_ids": ["id3", "id4"],
        }
        mock_service_instance = MagicMock()
        mock_service_instance.batch_update = AsyncMock(return_value=mock_result)
        mock_batch_service.return_value = mock_service_instance

        update_request = {
            "asset_ids": ["id1"],
            "updates": {"status": "active"},
            "should_update_all": True,
        }

        response = client.post("/api/v1/assets/batch-update", json=update_request)

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 100
        assert data["failed_count"] == 2
        assert len(data["errors"]) == 2

    @patch("src.api.v1.assets.asset_batch.AsyncAssetBatchService")
    def test_batch_update_empty_ids(self, mock_batch_service, client):
        """Test batch update with empty asset IDs"""
        update_request = {
            "asset_ids": [],
            "updates": {"status": "active"},
            "should_update_all": False,
        }

        response = client.post("/api/v1/assets/batch-update", json=update_request)

        assert response.status_code == 500


class TestValidateAssetData:
    """Tests for POST /validate endpoint"""

    @patch("src.api.v1.assets.asset_batch.AsyncAssetBatchService")
    @patch("src.api.v1.assets.asset_batch.get_enum_validation_service_async")
    def test_validate_success(self, mock_enum_service, mock_batch_service, client):
        """Test successful asset data validation"""
        # Mock enum service
        mock_enum_service_instance = MagicMock()
        mock_enum_service.return_value = mock_enum_service_instance

        # Mock batch service
        mock_service_instance = MagicMock()
        mock_service_instance.validate_asset_data = AsyncMock(
            return_value=(
                True,
                [],
                [
                    {
                        "field": "address",
                        "message": "Warning: Optional field missing",
                        "code": "OPTIONAL_MISSING",
                    }
                ],
                ["property_name"],
            )
        )
        mock_batch_service.return_value = mock_service_instance

        validation_request = {
            "data": {
                "property_name": "Test Property",
                "address": "123 Test St",
                "area": 100.5,
            },
            "validate_rules": None,
        }

        response = client.post("/api/v1/assets/validate", json=validation_request)

        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data
        assert "errors" in data
        assert "warnings" in data

    @patch("src.api.v1.assets.asset_batch.AsyncAssetBatchService")
    @patch("src.api.v1.assets.asset_batch.get_enum_validation_service_async")
    def test_validate_with_errors(self, mock_enum_service, mock_batch_service, client):
        """Test validation with errors"""
        mock_enum_service_instance = MagicMock()
        mock_enum_service.return_value = mock_enum_service_instance

        mock_service_instance = MagicMock()
        mock_service_instance.validate_asset_data = AsyncMock(
            return_value=(
                False,
                [
                    {
                        "field": "area",
                        "error": "Invalid area value",
                        "code": "INVALID_VALUE",
                    },
                    {
                        "field": "property_name",
                        "error": "Missing required field",
                        "code": "REQUIRED",
                    },
                ],
                [],
                [],
            )
        )
        mock_batch_service.return_value = mock_service_instance

        validation_request = {
            "data": {"area": -100},  # Invalid
            "validate_rules": None,
        }

        response = client.post("/api/v1/assets/validate", json=validation_request)

        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert len(data["errors"]) > 0


class TestBatchCustomFieldUpdate:
    """Tests for POST /batch-custom-fields endpoint"""

    @patch("src.api.v1.assets.asset_batch.AsyncAssetService")
    def test_batch_custom_field_update_success(self, mock_asset_service, client):
        """Test successful batch custom field update"""
        mock_service_instance = MagicMock()
        mock_service_instance.get_assets_by_ids = AsyncMock(
            return_value=[MagicMock(id="id1"), MagicMock(id="id2"), MagicMock(id="id3")]
        )
        mock_asset_service.return_value = mock_service_instance

        update_request = {
            "asset_ids": ["id1", "id2", "id3"],
            "field_values": {"custom_field_1": "value1"},
        }

        response = client.post(
            "/api/v1/assets/batch-custom-fields", json=update_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 3
        assert data["failed_count"] == 0

    @patch("src.api.v1.assets.asset_batch.AsyncAssetService")
    def test_batch_custom_field_update_partial_failure(
        self, mock_asset_service, client
    ):
        """Test batch custom field update with some failures"""
        mock_service_instance = MagicMock()
        mock_service_instance.get_assets_by_ids = AsyncMock(
            return_value=[MagicMock(id="id1")]
        )
        mock_asset_service.return_value = mock_service_instance

        update_request = {
            "asset_ids": ["id1", "id2", "id3"],
            "field_values": {"custom_field_1": "value1"},
        }

        response = client.post(
            "/api/v1/assets/batch-custom-fields", json=update_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1
        assert data["failed_count"] == 2


class TestGetAllAssets:
    """Tests for GET /all endpoint"""

    @patch("src.api.v1.assets.asset_batch.AssetListItemResponse.model_validate")
    @patch("src.api.v1.assets.asset_batch.AsyncAssetService")
    def test_get_all_assets_success(
        self, mock_asset_service, mock_model_validate, client
    ):
        """Test successful retrieval of all assets"""
        # Mock assets
        mock_assets = [
            MagicMock(id="id1", property_name="Property 1"),
            MagicMock(id="id2", property_name="Property 2"),
        ]
        mock_model_validate.side_effect = (
            lambda asset: {"id": asset.id, "property_name": asset.property_name}
        )
        mock_service_instance = MagicMock()
        mock_service_instance.get_assets = AsyncMock(return_value=(mock_assets, 2))
        mock_asset_service.return_value = mock_service_instance

        response = client.get("/api/v1/assets/all")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    @patch("src.api.v1.assets.asset_batch.AsyncAssetService")
    def test_get_all_assets_empty(self, mock_asset_service, client):
        """Test getting all assets when none exist"""
        mock_service_instance = MagicMock()
        mock_service_instance.get_assets = AsyncMock(return_value=([], 0))
        mock_asset_service.return_value = mock_service_instance

        response = client.get("/api/v1/assets/all")

        assert response.status_code == 200
        data = response.json()
        # Should return empty list or appropriate structure
        assert "data" in data
        assert isinstance(data["data"], list)


class TestGetAssetsByIds:
    """Tests for POST /by-ids endpoint"""

    @patch("src.api.v1.assets.asset_batch.AssetListItemResponse.model_validate")
    @patch("src.api.v1.assets.asset_batch.AsyncAssetService")
    def test_get_assets_by_ids_success(
        self, mock_asset_service, mock_model_validate, client
    ):
        """Test successful retrieval of assets by IDs"""
        mock_assets = [
            MagicMock(id="id1", property_name="Property 1"),
            MagicMock(id="id2", property_name="Property 2"),
            MagicMock(id="id3", property_name="Property 3"),
        ]
        mock_model_validate.side_effect = (
            lambda asset: {"id": asset.id, "property_name": asset.property_name}
        )

        mock_service_instance = MagicMock()
        mock_service_instance.get_assets_by_ids = AsyncMock(return_value=mock_assets)
        mock_asset_service.return_value = mock_service_instance

        request_data = {"ids": ["id1", "id2", "id3"]}

        response = client.post("/api/v1/assets/by-ids", json=request_data)

        assert response.status_code == 200
        data = response.json()
        # Should return list of assets
        assert "data" in data
        assert isinstance(data["data"], list)

    @patch("src.api.v1.assets.asset_batch.AssetListItemResponse.model_validate")
    @patch("src.api.v1.assets.asset_batch.AsyncAssetService")
    def test_get_assets_by_ids_some_not_found(
        self, mock_asset_service, mock_model_validate, client
    ):
        """Test getting assets by IDs when some don't exist"""
        mock_assets = [
            MagicMock(id="id1", property_name="Property 1"),
        ]
        mock_model_validate.side_effect = (
            lambda asset: {"id": asset.id, "property_name": asset.property_name}
        )

        mock_service_instance = MagicMock()
        mock_service_instance.get_assets_by_ids = AsyncMock(return_value=mock_assets)
        mock_asset_service.return_value = mock_service_instance

        request_data = {
            "ids": ["id1", "id2", "id3"]  # id2 and id3 don't exist
        }

        response = client.post("/api/v1/assets/by-ids", json=request_data)

        assert response.status_code == 200
        # Should return only found assets or appropriate response

    def test_get_assets_by_ids_empty_list(self, client):
        """Test getting assets with empty ID list"""
        request_data = {"ids": []}

        response = client.post("/api/v1/assets/by-ids", json=request_data)

        assert response.status_code == 200


class TestBatchDeleteAssets:
    """Tests for POST /batch-delete endpoint"""

    @patch("src.api.v1.assets.asset_batch.AsyncAssetBatchService")
    def test_batch_delete_success(self, mock_batch_service, client):
        """Test successful batch deletion of assets"""
        mock_service_instance = MagicMock()
        mock_service_instance.batch_delete = AsyncMock(
            return_value=MagicMock(success_count=3)
        )
        mock_batch_service.return_value = mock_service_instance

        delete_request = {"asset_ids": ["id1", "id2", "id3"]}

        response = client.post("/api/v1/assets/batch-delete", json=delete_request)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["deleted_count"] == 3

    @patch("src.api.v1.assets.asset_batch.AsyncAssetBatchService")
    def test_batch_delete_empty_ids(self, mock_batch_service, client):
        """Test batch delete with empty ID list"""
        delete_request = {"asset_ids": []}

        response = client.post("/api/v1/assets/batch-delete", json=delete_request)

        assert response.status_code == 500

    @patch("src.api.v1.assets.asset_batch.AsyncAssetBatchService")
    def test_batch_delete_exception(self, mock_batch_service, client):
        """Test batch delete when service raises error"""
        mock_service_instance = MagicMock()
        mock_service_instance.batch_delete = AsyncMock(side_effect=Exception("boom"))
        mock_batch_service.return_value = mock_service_instance

        delete_request = {"asset_ids": ["id1", "id2", "id3"]}

        response = client.post("/api/v1/assets/batch-delete", json=delete_request)

        assert response.status_code == 500


class TestBatchOperationsUnauthorized:
    """Tests for unauthorized access to batch operations"""

    def test_batch_update_unauthorized(self, unauthenticated_client):
        """Test that unauthorized users cannot batch update"""
        update_request = {
            "asset_ids": ["id1"],
            "updates": {"status": "active"},
        }
        response = unauthenticated_client.post(
            "/api/v1/assets/batch-update", json=update_request
        )
        assert response.status_code == 401

    def test_batch_delete_unauthorized(self, unauthenticated_client):
        """Test that unauthorized users cannot batch delete"""
        delete_request = {"asset_ids": ["id1"]}
        response = unauthenticated_client.post(
            "/api/v1/assets/batch-delete", json=delete_request
        )
        assert response.status_code == 401

    def test_validate_authorized(self, unauthenticated_client):
        """Test that validate requires authentication"""
        validation_request = {
            "data": {"property_name": "Test"},
        }
        response = unauthenticated_client.post(
            "/api/v1/assets/validate", json=validation_request
        )
        assert response.status_code == 401


@pytest.fixture
def unauthenticated_client():
    """Fixture providing unauthenticated client"""
    from src.main import app

    with TestClient(app) as test_client:
        yield test_client
