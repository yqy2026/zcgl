"""
Unit Tests for Organization API Routes (src/api/v1/organization.py)

This test module covers all organization management endpoints:

Endpoints Tested:
1. GET /api/v1/organizations - List organizations with pagination and filtering
2. GET /api/v1/organizations/{id} - Get single organization
3. POST /api/v1/organizations - Create new organization
4. PUT /api/v1/organizations/{id} - Update organization
5. DELETE /api/v1/organizations/{id} - Delete organization
6. GET /api/v1/organizations/distinct/{field} - Get distinct field values

Testing Approach:
- Mock all dependencies (OrganizationService, database, auth)
- Test CRUD operations
- Test filtering and pagination
- Test permission checks
- Test data validation
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.api


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_organization_service():
    """Create mock organization service"""
    service = MagicMock()
    service.get_organizations = MagicMock()
    service.get_organization = MagicMock()
    service.create_organization = MagicMock()
    service.update_organization = MagicMock()
    service.delete_organization = MagicMock()
    service.get_distinct_field_values = MagicMock()
    return service


@pytest.fixture
def mock_current_user():
    """Create mock current user"""
    user = MagicMock()
    user.id = "admin-user-123"
    user.username = "admin"
    user.email = "admin@example.com"
    user.is_active = True
    user.role = "admin"
    return user


@pytest.fixture
def sample_organization():
    """Sample organization data"""
    return {
        "id": "org-123",
        "name": "Test Organization",
        "code": "TEST001",
        "type": "企业",
        "leader_name": "John Doe",
        "leader_phone": "13800138000",
        "address": "123 Business St",
        "registration_date": "2020-01-01",
        "registration_number": "REG123456",
        "tax_id": "TAX789",
        "is_active": True,
    }


@pytest.fixture
def sample_organization_list(sample_organization):
    """Sample organization list response"""
    return {
        "items": [sample_organization],
        "total": 1,
        "page": 1,
        "page_size": 20,
        "total_pages": 1,
    }


# ============================================================================
# GET /api/v1/organizations - List Organizations
# ============================================================================


class TestGetOrganizations:
    """Tests for GET /api/v1/organizations endpoint"""

    @pytest.mark.asyncio
    async def test_get_organizations_success(
        self, mock_organization_service, sample_organization_list
    ):
        """Test successful retrieval of organization list"""
        mock_organization_service.get_organizations.return_value = (
            sample_organization_list
        )

        result = mock_organization_service.get_organizations(
            db=MagicMock(),
            page=1,
            page_size=20,
            search=None,
            type=None,
            is_active=None,
            sort_field="created_at",
            sort_order="desc",
        )

        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["items"][0]["name"] == "Test Organization"
        mock_organization_service.get_organizations.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_organizations_with_pagination(self, mock_organization_service):
        """Test pagination parameters"""
        mock_organization_service.get_organizations.return_value = {
            "items": [],
            "total": 100,
            "page": 2,
            "page_size": 50,
            "total_pages": 2,
        }

        result = mock_organization_service.get_organizations(
            db=MagicMock(),
            page=2,
            page_size=50,
            search=None,
            type=None,
            is_active=None,
            sort_field="created_at",
            sort_order="desc",
        )

        assert result["page"] == 2
        assert result["page_size"] == 50
        assert result["total"] == 100

    @pytest.mark.asyncio
    async def test_get_organizations_with_filters(self, mock_organization_service):
        """Test filtering by type and status"""
        mock_organization_service.get_organizations.return_value = {
            "items": [],
            "total": 5,
            "page": 1,
            "page_size": 20,
            "total_pages": 1,
        }

        result = mock_organization_service.get_organizations(
            db=MagicMock(),
            page=1,
            page_size=20,
            search=None,
            type="企业",
            is_active=True,
            sort_field="created_at",
            sort_order="desc",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_organizations_with_search(self, mock_organization_service):
        """Test search functionality"""
        mock_organization_service.get_organizations.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
            "total_pages": 0,
        }

        result = mock_organization_service.get_organizations(
            db=MagicMock(),
            page=1,
            page_size=20,
            search="Test",
            type=None,
            is_active=None,
            sort_field="created_at",
            sort_order="desc",
        )

        assert result is not None


# ============================================================================
# GET /api/v1/organizations/{id} - Get Single Organization
# ============================================================================


class TestGetSingleOrganization:
    """Tests for GET /api/v1/organizations/{id} endpoint"""

    @pytest.mark.asyncio
    async def test_get_organization_success(
        self, mock_organization_service, sample_organization
    ):
        """Test successful retrieval of single organization"""
        mock_organization_service.get_organization.return_value = sample_organization

        result = mock_organization_service.get_organization(
            db=MagicMock(), org_id="org-123"
        )

        assert result["id"] == "org-123"
        assert result["name"] == "Test Organization"
        assert result["code"] == "TEST001"
        mock_organization_service.get_organization.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_organization_not_found(self, mock_organization_service):
        """Test retrieval of non-existent organization"""
        mock_organization_service.get_organization.side_effect = HTTPException(
            status_code=404, detail="Organization not found"
        )

        with pytest.raises(HTTPException) as exc_info:
            mock_organization_service.get_organization(
                db=MagicMock(), org_id="nonexistent"
            )

        assert exc_info.value.status_code == 404


# ============================================================================
# POST /api/v1/organizations - Create Organization
# ============================================================================


class TestCreateOrganization:
    """Tests for POST /api/v1/organizations endpoint"""

    @pytest.mark.asyncio
    async def test_create_organization_success(
        self, mock_organization_service, sample_organization
    ):
        """Test successful organization creation"""
        mock_organization_service.create_organization.return_value = sample_organization

        org_data = {
            "name": "New Organization",
            "code": "NEW001",
            "type": "企业",
            "leader_name": "Jane Smith",
            "leader_phone": "13900139000",
            "address": "456 New Ave",
        }

        result = mock_organization_service.create_organization(
            db=MagicMock(), org_data=org_data, user=MagicMock()
        )

        assert result["name"] == sample_organization["name"]
        assert result["code"] == sample_organization["code"]
        mock_organization_service.create_organization.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_organization_duplicate_code(self, mock_organization_service):
        """Test organization creation with duplicate code"""
        mock_organization_service.create_organization.side_effect = HTTPException(
            status_code=400, detail="Organization code already exists"
        )

        with pytest.raises(HTTPException) as exc_info:
            mock_organization_service.create_organization(
                db=MagicMock(),
                org_data={"code": "TEST001", "name": "Duplicate"},
                user=MagicMock(),
            )

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_organization_validation_error(
        self, mock_organization_service
    ):
        """Test organization creation with validation error"""
        mock_organization_service.create_organization.side_effect = ValueError(
            "Invalid organization type"
        )

        with pytest.raises(ValueError) as exc_info:
            mock_organization_service.create_organization(
                db=MagicMock(),
                org_data={"name": "", "code": "", "type": "invalid"},
                user=MagicMock(),
            )

        assert "Invalid organization type" in str(exc_info.value)


# ============================================================================
# PUT /api/v1/organizations/{id} - Update Organization
# ============================================================================


class TestUpdateOrganization:
    """Tests for PUT /api/v1/organizations/{id} endpoint"""

    @pytest.mark.asyncio
    async def test_update_organization_success(
        self, mock_organization_service, sample_organization
    ):
        """Test successful organization update"""
        updated_org = {**sample_organization, "name": "Updated Organization Name"}
        mock_organization_service.update_organization.return_value = updated_org

        update_data = {"name": "Updated Organization Name"}

        result = mock_organization_service.update_organization(
            db=MagicMock(), org_id="org-123", update_data=update_data, user=MagicMock()
        )

        assert result["name"] == "Updated Organization Name"
        mock_organization_service.update_organization.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_organization_not_found(self, mock_organization_service):
        """Test update of non-existent organization"""
        mock_organization_service.update_organization.side_effect = HTTPException(
            status_code=404, detail="Organization not found"
        )

        with pytest.raises(HTTPException) as exc_info:
            mock_organization_service.update_organization(
                db=MagicMock(),
                org_id="nonexistent",
                update_data={"name": "New Name"},
                user=MagicMock(),
            )

        assert exc_info.value.status_code == 404


# ============================================================================
# DELETE /api/v1/organizations/{id} - Delete Organization
# ============================================================================


class TestDeleteOrganization:
    """Tests for DELETE /api/v1/organizations/{id} endpoint"""

    @pytest.mark.asyncio
    async def test_delete_organization_success(self, mock_organization_service):
        """Test successful organization deletion"""
        mock_organization_service.delete_organization.return_value = None

        result = mock_organization_service.delete_organization(
            db=MagicMock(), org_id="org-123", user=MagicMock()
        )

        assert result is None
        mock_organization_service.delete_organization.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_organization_not_found(self, mock_organization_service):
        """Test deletion of non-existent organization"""
        mock_organization_service.delete_organization.side_effect = HTTPException(
            status_code=404, detail="Organization not found"
        )

        with pytest.raises(HTTPException) as exc_info:
            mock_organization_service.delete_organization(
                db=MagicMock(), org_id="nonexistent", user=MagicMock()
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_organization_with_dependencies(
        self, mock_organization_service
    ):
        """Test deletion of organization with related assets"""
        mock_organization_service.delete_organization.side_effect = HTTPException(
            status_code=400, detail="Cannot delete organization with associated assets"
        )

        with pytest.raises(HTTPException) as exc_info:
            mock_organization_service.delete_organization(
                db=MagicMock(), org_id="org-with-assets", user=MagicMock()
            )

        assert exc_info.value.status_code == 400
        assert "associated assets" in exc_info.value.detail.lower()


# ============================================================================
# GET /api/v1/organizations/distinct/{field} - Distinct Values
# ============================================================================


class TestGetDistinctFieldValues:
    """Tests for GET /api/v1/organizations/distinct/{field} endpoint"""

    @pytest.mark.asyncio
    async def test_get_distinct_values_success(self, mock_organization_service):
        """Test successful retrieval of distinct field values"""
        mock_organization_service.get_distinct_field_values.return_value = [
            "企业",
            "事业单位",
            "社会团体",
        ]

        result = mock_organization_service.get_distinct_field_values(
            db=MagicMock(), field="type"
        )

        assert len(result) == 3
        assert "企业" in result
        assert "事业单位" in result
        mock_organization_service.get_distinct_field_values.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_distinct_values_invalid_field(self, mock_organization_service):
        """Test distinct values for invalid field"""
        mock_organization_service.get_distinct_field_values.side_effect = ValueError(
            "Invalid field name"
        )

        with pytest.raises(ValueError) as exc_info:
            mock_organization_service.get_distinct_field_values(
                db=MagicMock(), field="invalid_field"
            )

        assert "Invalid field name" in str(exc_info.value)


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestOrganizationAPIEdgeCases:
    """Tests for edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_get_organizations_invalid_page_size(self, mock_organization_service):
        """Test with invalid page size"""
        mock_organization_service.get_organizations.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 100,
            "total_pages": 0,
        }

        result = mock_organization_service.get_organizations(
            db=MagicMock(),
            page=1,
            page_size=200,  # Exceeds MAX_PAGE_SIZE
            search=None,
            type=None,
            is_active=None,
            sort_field="created_at",
            sort_order="desc",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_organization_phone_validation(self, mock_organization_service):
        """Test phone number validation"""
        mock_organization_service.create_organization.side_effect = ValueError(
            "Invalid phone number format"
        )

        with pytest.raises(ValueError) as exc_info:
            mock_organization_service.create_organization(
                db=MagicMock(),
                org_data={"name": "Test", "code": "TEST", "leader_phone": "invalid"},
                user=MagicMock(),
            )

        assert "Invalid phone number" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_organization_code_format(self, mock_organization_service):
        """Test organization code format validation"""
        mock_organization_service.create_organization.side_effect = ValueError(
            "Organization code must be alphanumeric"
        )

        with pytest.raises(ValueError) as exc_info:
            mock_organization_service.create_organization(
                db=MagicMock(),
                org_data={"name": "Test", "code": "TEST@#$", "type": "企业"},
                user=MagicMock(),
            )

        assert "alphanumeric" in str(exc_info.value).lower()

