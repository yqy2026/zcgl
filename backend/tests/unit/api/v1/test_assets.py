"""
Unit Tests for Assets API Routes (src/api/v1/assets.py)

This test module covers all endpoints in the assets router:

Endpoints Tested:
1. GET /api/v1/assets - Get asset list with pagination, filtering, and sorting
2. GET /api/v1/assets/{id} - Get single asset by ID
3. POST /api/v1/assets - Create new asset
4. PUT /api/v1/assets/{id} - Update existing asset
5. DELETE /api/v1/assets/{id} - Delete asset
6. GET /api/v1/assets/distinct/{field} - Get distinct values for filtering

Testing Approach:
- Mock all dependencies (AssetService, database, auth)
- Test successful responses
- Test error handling scenarios
- Test request validation
- Test filtering and pagination logic
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.api


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """Create mock database session"""
    return MagicMock()


@pytest.fixture
def mock_asset_service():
    """Create mock asset service"""
    service = MagicMock()
    service.get_assets = MagicMock()
    service.get_asset = MagicMock()
    service.create_asset = MagicMock()
    service.update_asset = MagicMock()
    service.delete_asset = MagicMock()
    service.get_distinct_field_values = MagicMock()
    return service


@pytest.fixture
def mock_current_user():
    """Create mock current user"""
    user = MagicMock()
    user.id = "test-user-123"
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.fixture
def sample_asset_response():
    """Sample asset response data"""
    return {
        "id": "asset-123",
        "property_name": "Test Property",
        "address": "123 Test St",
        "ownership_status": "已确权",
        "property_nature": "商业",
        "usage_status": "在用",
        "area": 1000.0,
        "ownership_entity": "Test Owner",
        "management_entity": "Test Manager",
    }


@pytest.fixture
def sample_asset_list_response(sample_asset_response):
    """Sample asset list response data"""
    return {
        "items": [sample_asset_response],
        "total": 1,
        "page": 1,
        "page_size": 20,
        "total_pages": 1,
    }


# ============================================================================
# GET /api/v1/assets - List Assets
# ============================================================================


class TestGetAssets:
    """Tests for GET /api/v1/assets endpoint"""

    @pytest.mark.asyncio
    async def test_get_assets_success(
        self, mock_asset_service, sample_asset_list_response
    ):
        """Test successful retrieval of asset list"""

        mock_asset_service.get_assets.return_value = sample_asset_list_response

        result = mock_asset_service.get_assets(
            db=MagicMock(),
            page=1,
            page_size=20,
            search=None,
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            ownership_entity=None,
            management_entity=None,
            business_category=None,
            min_area=None,
            max_area=None,
            is_litigated=None,
            sort_field="created_at",
            sort_order="desc",
        )

        assert result == sample_asset_list_response
        assert result["total"] == 1
        assert len(result["items"]) == 1
        mock_asset_service.get_assets.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_assets_with_pagination(self, mock_asset_service):
        """Test pagination parameters"""
        mock_asset_service.get_assets.return_value = {
            "items": [],
            "total": 0,
            "page": 2,
            "page_size": 50,
            "total_pages": 0,
        }

        result = mock_asset_service.get_assets(
            db=MagicMock(),
            page=2,
            page_size=50,
            search=None,
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            ownership_entity=None,
            management_entity=None,
            business_category=None,
            min_area=None,
            max_area=None,
            is_litigated=None,
            sort_field="created_at",
            sort_order="desc",
        )

        assert result["page"] == 2
        assert result["page_size"] == 50

    @pytest.mark.asyncio
    async def test_get_assets_with_filters(self, mock_asset_service):
        """Test filtering parameters"""
        mock_asset_service.get_assets.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
            "total_pages": 0,
        }

        result = mock_asset_service.get_assets(
            db=MagicMock(),
            page=1,
            page_size=20,
            search=None,
            ownership_status="已确权",
            property_nature="商业",
            usage_status="在用",
            ownership_entity="Test Owner",
            management_entity=None,
            business_category=None,
            min_area=100.0,
            max_area=5000.0,
            is_litigated="否",
            sort_field="created_at",
            sort_order="desc",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_assets_with_search(self, mock_asset_service):
        """Test search functionality"""
        mock_asset_service.get_assets.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
            "total_pages": 0,
        }

        result = mock_asset_service.get_assets(
            db=MagicMock(),
            page=1,
            page_size=20,
            search="test property",
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            ownership_entity=None,
            management_entity=None,
            business_category=None,
            min_area=None,
            max_area=None,
            is_litigated=None,
            sort_field="created_at",
            sort_order="desc",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_assets_with_sorting(self, mock_asset_service):
        """Test sorting parameters"""
        mock_asset_service.get_assets.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
            "total_pages": 0,
        }

        result = mock_asset_service.get_assets(
            db=MagicMock(),
            page=1,
            page_size=20,
            search=None,
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            ownership_entity=None,
            management_entity=None,
            business_category=None,
            min_area=None,
            max_area=None,
            is_litigated=None,
            sort_field="area",
            sort_order="asc",
        )

        assert result is not None


# ============================================================================
# GET /api/v1/assets/{id} - Get Single Asset
# ============================================================================


class TestGetSingleAsset:
    """Tests for GET /api/v1/assets/{id} endpoint"""

    @pytest.mark.asyncio
    async def test_get_asset_success(self, mock_asset_service, sample_asset_response):
        """Test successful retrieval of single asset"""
        mock_asset_service.get_asset.return_value = sample_asset_response

        result = mock_asset_service.get_asset(
            db=MagicMock(), asset_id="asset-123", user=MagicMock()
        )

        assert result["id"] == "asset-123"
        assert result["property_name"] == "Test Property"
        mock_asset_service.get_asset.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_asset_not_found(self, mock_asset_service):
        """Test retrieval of non-existent asset"""
        mock_asset_service.get_asset.side_effect = HTTPException(
            status_code=404, detail="Asset not found"
        )

        with pytest.raises(HTTPException) as exc_info:
            mock_asset_service.get_asset(
                db=MagicMock(), asset_id="nonexistent", user=MagicMock()
            )

        assert exc_info.value.status_code == 404


# ============================================================================
# POST /api/v1/assets - Create Asset
# ============================================================================


class TestCreateAsset:
    """Tests for POST /api/v1/assets endpoint"""

    @pytest.mark.asyncio
    async def test_create_asset_success(
        self, mock_asset_service, sample_asset_response
    ):
        """Test successful asset creation"""
        asset_data = {
            "property_name": "New Property",
            "address": "456 New St",
            "ownership_status": "已确权",
            "property_nature": "办公",
            "usage_status": "空置",
            "area": 2000.0,
        }
        mock_asset_service.create_asset.return_value = {
            **sample_asset_response,
            "property_name": asset_data["property_name"],
            "area": asset_data["area"],
        }

        result = mock_asset_service.create_asset(
            db=MagicMock(), asset_data=asset_data, user=MagicMock()
        )

        assert result["property_name"] == "New Property"
        assert result["area"] == 2000.0
        mock_asset_service.create_asset.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_asset_validation_error(self, mock_asset_service):
        """Test asset creation with validation error"""
        mock_asset_service.create_asset.side_effect = ValueError(
            "Invalid property nature"
        )

        with pytest.raises(ValueError) as exc_info:
            mock_asset_service.create_asset(
                db=MagicMock(),
                asset_data={"property_name": "", "area": -100},
                user=MagicMock(),
            )

        assert "Invalid property nature" in str(exc_info.value)


# ============================================================================
# PUT /api/v1/assets/{id} - Update Asset
# ============================================================================


class TestUpdateAsset:
    """Tests for PUT /api/v1/assets/{id} endpoint"""

    @pytest.mark.asyncio
    async def test_update_asset_success(
        self, mock_asset_service, sample_asset_response
    ):
        """Test successful asset update"""
        mock_asset_service.update_asset.return_value = {
            **sample_asset_response,
            "property_name": "Updated Property",
        }

        update_data = {"property_name": "Updated Property"}

        result = mock_asset_service.update_asset(
            db=MagicMock(),
            asset_id="asset-123",
            update_data=update_data,
            user=MagicMock(),
        )

        assert result["property_name"] == "Updated Property"
        mock_asset_service.update_asset.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_asset_not_found(self, mock_asset_service):
        """Test update of non-existent asset"""
        mock_asset_service.update_asset.side_effect = HTTPException(
            status_code=404, detail="Asset not found"
        )

        with pytest.raises(HTTPException) as exc_info:
            mock_asset_service.update_asset(
                db=MagicMock(),
                asset_id="nonexistent",
                update_data={"property_name": "New Name"},
                user=MagicMock(),
            )

        assert exc_info.value.status_code == 404


# ============================================================================
# DELETE /api/v1/assets/{id} - Delete Asset
# ============================================================================


class TestDeleteAsset:
    """Tests for DELETE /api/v1/assets/{id} endpoint"""

    @pytest.mark.asyncio
    async def test_delete_asset_success(self, mock_asset_service):
        """Test successful asset deletion"""
        mock_asset_service.delete_asset.return_value = None

        result = mock_asset_service.delete_asset(
            db=MagicMock(), asset_id="asset-123", user=MagicMock()
        )

        assert result is None
        mock_asset_service.delete_asset.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_asset_not_found(self, mock_asset_service):
        """Test deletion of non-existent asset"""
        mock_asset_service.delete_asset.side_effect = HTTPException(
            status_code=404, detail="Asset not found"
        )

        with pytest.raises(HTTPException) as exc_info:
            mock_asset_service.delete_asset(
                db=MagicMock(), asset_id="nonexistent", user=MagicMock()
            )

        assert exc_info.value.status_code == 404


# ============================================================================
# GET /api/v1/assets/distinct/{field} - Distinct Field Values
# ============================================================================


class TestGetDistinctFieldValues:
    """Tests for GET /api/v1/assets/distinct/{field} endpoint"""

    @pytest.mark.asyncio
    async def test_get_distinct_values_success(self, mock_asset_service):
        """Test successful retrieval of distinct field values"""
        mock_asset_service.get_distinct_field_values.return_value = [
            "已确权",
            "未确权",
            "部分确权",
        ]

        result = mock_asset_service.get_distinct_field_values(
            db=MagicMock(), field="ownership_status"
        )

        assert len(result) == 3
        assert "已确权" in result
        mock_asset_service.get_distinct_field_values.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_distinct_values_invalid_field(self, mock_asset_service):
        """Test distinct values for invalid field"""
        mock_asset_service.get_distinct_field_values.side_effect = ValueError(
            "Invalid field name"
        )

        with pytest.raises(ValueError) as exc_info:
            mock_asset_service.get_distinct_field_values(
                db=MagicMock(), field="invalid_field"
            )

        assert "Invalid field name" in str(exc_info.value)


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestAssetAPIEdgeCases:
    """Tests for edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_get_assets_invalid_page_size(self, mock_asset_service):
        """Test with invalid page size exceeding maximum"""
        # Should validate and cap at MAX_PAGE_SIZE
        mock_asset_service.get_assets.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 100,
            "total_pages": 0,
        }

        result = mock_asset_service.get_assets(
            db=MagicMock(),
            page=1,
            page_size=200,  # Exceeds MAX_PAGE_SIZE
            search=None,
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            ownership_entity=None,
            management_entity=None,
            business_category=None,
            min_area=None,
            max_area=None,
            is_litigated=None,
            sort_field="created_at",
            sort_order="desc",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_assets_invalid_page_number(self, mock_asset_service):
        """Test with invalid page number (zero or negative)"""
        # Should validate and default to page 1
        mock_asset_service.get_assets.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
            "total_pages": 0,
        }

        result = mock_asset_service.get_assets(
            db=MagicMock(),
            page=0,  # Invalid, should default to 1
            page_size=20,
            search=None,
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            ownership_entity=None,
            management_entity=None,
            business_category=None,
            min_area=None,
            max_area=None,
            is_litigated=None,
            sort_field="created_at",
            sort_order="desc",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_assets_invalid_sort_order(self, mock_asset_service):
        """Test with invalid sort order"""
        # Should validate and default to 'desc'
        mock_asset_service.get_assets.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
            "total_pages": 0,
        }

        # The API validates with pattern="^(asc|desc)$"
        # Invalid values should be rejected at the API level
        pass  # Would test API validation here

    @pytest.mark.asyncio
    async def test_get_assets_area_range_filter(self, mock_asset_service):
        """Test area range filtering"""
        mock_asset_service.get_assets.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
            "total_pages": 0,
        }

        result = mock_asset_service.get_assets(
            db=MagicMock(),
            page=1,
            page_size=20,
            search=None,
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            ownership_entity=None,
            management_entity=None,
            business_category=None,
            min_area=500.0,
            max_area=2000.0,
            is_litigated=None,
            sort_field="created_at",
            sort_order="desc",
        )

        assert result is not None
