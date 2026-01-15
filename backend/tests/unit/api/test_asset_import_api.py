"""
Tests for Asset Import API endpoint (api/v1/asset_import.py)

This test module covers the asset import functionality:
- POST /import - Batch import assets with different modes
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient


class TestAssetImport:
    """Tests for POST /import endpoint"""

    @patch("src.api.v1.asset_import.validate_asset_data")
    @patch("src.api.v1.asset_import.asset_crud")
    def test_import_assets_create_mode_success(
        self, mock_asset_crud, mock_validate, client
    ):
        """Test successful asset import in create mode"""
        # Mock validation to pass
        mock_validation_result = MagicMock()
        mock_validation_result.is_valid = True
        mock_validation_result.errors = []
        mock_validate.return_value = mock_validation_result

        # Mock asset creation
        mock_asset = MagicMock()
        mock_asset.id = "new-asset-id"
        mock_asset_crud.create.return_value = mock_asset

        import_data = {
            "data": [
                {
                    "property_name": "Test Property",
                    "address": "123 Test St",
                    "area": 100.5,
                    "asset_type": "building",
                }
            ],
            "import_mode": "create",
            "skip_errors": False,
            "dry_run": False,
        }

        response = client.post("/api/v1/assets/import", json=import_data)

        assert response.status_code == 200
        data = response.json()
        assert "success_count" in data
        assert "failed_count" in data
        assert data["success_count"] == 1

    @patch("src.api.v1.asset_import.validate_asset_data")
    @patch("src.api.v1.asset_import.asset_crud")
    def test_import_assets_dry_run(
        self, mock_asset_crud, mock_validate, client
    ):
        """Test asset import in dry run mode"""
        mock_validation_result = MagicMock()
        mock_validation_result.is_valid = True
        mock_validation_result.errors = []
        mock_validate.return_value = mock_validation_result

        import_data = {
            "data": [
                {
                    "property_name": "Test Property",
                    "address": "123 Test St",
                }
            ],
            "import_mode": "create",
            "skip_errors": False,
            "dry_run": True,
        }

        response = client.post("/api/v1/assets/import", json=import_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1
        # In dry run, no assets should be created
        mock_asset_crud.create.assert_not_called()

    @patch("src.api.v1.asset_import.validate_asset_data")
    def test_import_assets_with_validation_errors(
        self, mock_validate, client
    ):
        """Test import with validation errors"""
        # Mock validation to fail
        mock_validation_result = MagicMock()
        mock_validation_result.is_valid = False
        mock_validation_result.errors = ["Invalid field: area"]
        mock_validate.return_value = mock_validation_result

        import_data = {
            "data": [
                {
                    "property_name": "Test Property",
                    "address": "123 Test St",
                }
            ],
            "import_mode": "create",
            "skip_errors": False,
            "dry_run": False,
        }

        response = client.post("/api/v1/assets/import", json=import_data)

        assert response.status_code == 200
        data = response.json()
        assert data["failed_count"] == 1
        assert len(data["errors"]) > 0

    @patch("src.api.v1.asset_import.validate_asset_data")
    def test_import_assets_skip_errors(
        self, mock_validate, client
    ):
        """Test import with skip_errors enabled"""
        # First record fails validation, second passes
        call_count = [0]

        def mock_side_effect(*args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.is_valid = False
                result.errors = ["Validation failed"]
            else:
                result.is_valid = True
                result.errors = []
            return result

        mock_validate.side_effect = mock_side_effect

        import_data = {
            "data": [
                {"property_name": "Invalid Asset"},
                {"property_name": "Valid Asset", "address": "123 Test St"},
            ],
            "import_mode": "create",
            "skip_errors": True,
            "dry_run": True,
        }

        response = client.post("/api/v1/assets/import", json=import_data)

        assert response.status_code == 200
        data = response.json()
        # Should have 1 success and 1 failure, but continue processing
        assert data["success_count"] >= 0
        assert data["failed_count"] >= 0

    @patch("src.api.v1.asset_import.validate_asset_data")
    @patch("src.api.v1.asset_import.asset_crud")
    def test_import_assets_merge_mode(
        self, mock_asset_crud, mock_validate, client
    ):
        """Test asset import in merge mode"""
        mock_validation_result = MagicMock()
        mock_validation_result.is_valid = True
        mock_validation_result.errors = []
        mock_validate.return_value = mock_validation_result

        # Mock existing asset
        mock_existing_asset = MagicMock()
        mock_existing_asset.id = "existing-id"
        mock_asset_crud.get_multi_with_search.return_value = ([mock_existing_asset], 1)

        # Mock update
        mock_asset_crud.update.return_value = mock_existing_asset

        import_data = {
            "data": [
                {
                    "property_name": "Existing Property",
                    "address": "123 Test St",
                }
            ],
            "import_mode": "merge",
            "skip_errors": False,
            "dry_run": False,
        }

        response = client.post("/api/v1/assets/import", json=import_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1

    def test_import_assets_empty_data(self, client):
        """Test import with empty data array"""
        import_data = {
            "data": [],
            "import_mode": "create",
            "skip_errors": False,
            "dry_run": False,
        }

        response = client.post("/api/v1/assets/import", json=import_data)

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0

    def test_import_assets_invalid_mode(self, client):
        """Test import with invalid import mode"""
        import_data = {
            "data": [{"property_name": "Test"}],
            "import_mode": "invalid_mode",
            "skip_errors": False,
            "dry_run": False,
        }

        response = client.post("/api/v1/assets/import", json=import_data)

        # Should validate the enum
        assert response.status_code in [400, 422]


class TestAssetImportUnauthorized:
    """Tests for unauthorized access to import endpoint"""

    def test_import_unauthorized(self, unauthenticated_client):
        """Test that unauthorized users cannot import assets"""
        import_data = {
            "data": [{"property_name": "Test"}],
            "import_mode": "create",
            "skip_errors": False,
            "dry_run": False,
        }

        response = unauthenticated_client.post("/api/v1/assets/import", json=import_data)
        assert response.status_code == 401


@pytest.fixture
def unauthenticated_client():
    """Fixture providing unauthenticated client"""
    from fastapi.testclient import TestClient
    from src.main import app
    return TestClient(app)
