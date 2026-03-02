"""
Tests for Asset Import API endpoint (api/v1/assets/asset_import.py)

This test module covers the asset import functionality:
- POST /import - Batch import assets with different modes
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.schemas.asset import AssetImportResponse


@pytest.fixture(autouse=True)
def allow_asset_import_authz(monkeypatch):
    """Bypass row-level authz in unit tests and focus on endpoint behavior."""

    async def _allow(*args, **kwargs):
        return SimpleNamespace(allowed=True)

    monkeypatch.setattr(
        "src.api.v1.assets.asset_import.authz_service.check_access",
        _allow,
    )


class TestAssetImport:
    """Tests for POST /import endpoint"""

    @patch("src.api.v1.assets.asset_import.AsyncAssetImportService")
    def test_import_assets_create_mode_success(self, mock_import_service, client):
        """Test successful asset import in create mode"""
        mock_service = mock_import_service.return_value
        mock_service.import_assets = AsyncMock(
            return_value=AssetImportResponse(
                success_count=1,
                failed_count=0,
                total_count=1,
                errors=[],
                imported_assets=["new-asset-id"],
                import_id="import_20260213_100001",
            )
        )

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
            "should_skip_errors": False,
            "is_dry_run": False,
        }

        response = client.post("/api/v1/assets/import", json=import_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1
        assert data["import_id"] == "import_20260213_100001"

        called_request = mock_service.import_assets.call_args.kwargs["request"]
        assert called_request.should_skip_errors is False
        assert called_request.is_dry_run is False

    @patch("src.api.v1.assets.asset_import.AsyncAssetImportService")
    def test_import_assets_dry_run(self, mock_import_service, client):
        """Test asset import in dry run mode"""
        mock_service = mock_import_service.return_value
        mock_service.import_assets = AsyncMock(
            return_value=AssetImportResponse(
                success_count=1,
                failed_count=0,
                total_count=1,
                errors=[],
                imported_assets=["dry-run-only"],
                import_id=None,
            )
        )

        import_data = {
            "data": [
                {
                    "property_name": "Test Property",
                    "address": "123 Test St",
                }
            ],
            "import_mode": "create",
            "should_skip_errors": False,
            "is_dry_run": True,
        }

        response = client.post("/api/v1/assets/import", json=import_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1
        assert data["import_id"] is None

        called_request = mock_service.import_assets.call_args.kwargs["request"]
        assert called_request.is_dry_run is True

    @patch("src.api.v1.assets.asset_import.AsyncAssetImportService")
    def test_import_assets_with_validation_errors(self, mock_import_service, client):
        """Test import with validation errors"""
        mock_service = mock_import_service.return_value
        mock_service.import_assets = AsyncMock(
            return_value=AssetImportResponse(
                success_count=0,
                failed_count=1,
                total_count=1,
                errors=[
                    {
                        "row_index": 1,
                        "field": "area",
                        "message": "Invalid field: area",
                        "code": "VALIDATION_ERROR",
                    }
                ],
                imported_assets=[],
                import_id="import_20260213_100002",
            )
        )

        import_data = {
            "data": [
                {
                    "property_name": "Test Property",
                    "address": "123 Test St",
                }
            ],
            "import_mode": "create",
            "should_skip_errors": False,
            "is_dry_run": False,
        }

        response = client.post("/api/v1/assets/import", json=import_data)

        assert response.status_code == 200
        data = response.json()
        assert data["failed_count"] == 1
        assert data["errors"][0]["field"] == "area"
        assert data["errors"][0]["message"] == "Invalid field: area"

    @patch("src.api.v1.assets.asset_import.AsyncAssetImportService")
    def test_import_assets_skip_errors(self, mock_import_service, client):
        """Test import with skip_errors enabled"""
        mock_service = mock_import_service.return_value
        mock_service.import_assets = AsyncMock(
            return_value=AssetImportResponse(
                success_count=1,
                failed_count=1,
                total_count=2,
                errors=[
                    {
                        "row_index": 1,
                        "field": "property_name",
                        "message": "Validation failed",
                        "code": "VALIDATION_ERROR",
                    }
                ],
                imported_assets=["valid-asset-id"],
                import_id="import_20260213_100003",
            )
        )

        import_data = {
            "data": [
                {"property_name": "Invalid Asset"},
                {"property_name": "Valid Asset", "address": "123 Test St"},
            ],
            "import_mode": "create",
            "should_skip_errors": True,
            "is_dry_run": False,
        }

        response = client.post("/api/v1/assets/import", json=import_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1
        assert data["failed_count"] == 1

        called_request = mock_service.import_assets.call_args.kwargs["request"]
        assert called_request.should_skip_errors is True

    @patch("src.api.v1.assets.asset_import.AsyncAssetImportService")
    def test_import_assets_merge_mode(self, mock_import_service, client):
        """Test asset import in merge mode"""
        mock_service = mock_import_service.return_value
        mock_service.import_assets = AsyncMock(
            return_value=AssetImportResponse(
                success_count=1,
                failed_count=0,
                total_count=1,
                errors=[],
                imported_assets=["existing-id"],
                import_id="import_20260213_100004",
            )
        )

        import_data = {
            "data": [
                {
                    "property_name": "Existing Property",
                    "address": "123 Test St",
                }
            ],
            "import_mode": "merge",
            "should_skip_errors": False,
            "is_dry_run": False,
        }

        response = client.post("/api/v1/assets/import", json=import_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1

        called_request = mock_service.import_assets.call_args.kwargs["request"]
        assert called_request.import_mode == "merge"

    @patch("src.api.v1.assets.asset_import.AsyncAssetImportService")
    def test_import_assets_empty_data(self, mock_import_service, client):
        """Test import with empty data array"""
        mock_service = mock_import_service.return_value
        mock_service.import_assets = AsyncMock(
            return_value=AssetImportResponse(
                success_count=0,
                failed_count=0,
                total_count=0,
                errors=[],
                imported_assets=[],
                import_id="import_20260213_100005",
            )
        )

        import_data = {
            "data": [],
            "import_mode": "create",
            "should_skip_errors": False,
            "is_dry_run": False,
        }

        response = client.post("/api/v1/assets/import", json=import_data)

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0

    def test_import_assets_missing_required_data_returns_422(self, client):
        """Test import request validation when required fields are missing"""
        response = client.post(
            "/api/v1/assets/import",
            json={
                "import_mode": "create",
                "should_skip_errors": False,
                "is_dry_run": False,
            },
        )

        assert response.status_code == 422

    @patch("src.api.v1.assets.asset_import.AsyncAssetImportService")
    def test_import_assets_service_failure_returns_500(
        self, mock_import_service, client
    ):
        """Test service exception is translated to internal error response"""
        mock_service = mock_import_service.return_value
        mock_service.import_assets = AsyncMock(side_effect=RuntimeError("db outage"))

        response = client.post(
            "/api/v1/assets/import",
            json={
                "data": [{"property_name": "Test"}],
                "import_mode": "create",
                "should_skip_errors": False,
                "is_dry_run": False,
            },
        )

        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"


class TestAssetImportUnauthorized:
    """Tests for unauthorized access to import endpoint"""

    def test_import_unauthorized(self, unauthenticated_client):
        """Test that unauthorized users cannot import assets"""
        import_data = {
            "data": [{"property_name": "Test"}],
            "import_mode": "create",
            "should_skip_errors": False,
            "is_dry_run": False,
        }

        response = unauthenticated_client.post(
            "/api/v1/assets/import", json=import_data
        )
        assert response.status_code == 401
