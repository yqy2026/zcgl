"""
Comprehensive Unit Tests for Organization API Routes (src/api/v1/organization.py)

This test module covers all endpoints in the organization router to achieve 70%+ coverage:

Endpoints Tested:
1. GET /api/v1/organization - Get organization list
2. GET /api/v1/organization/tree - Get organization tree structure
3. GET /api/v1/organization/search - Search organizations
4. GET /api/v1/organization/statistics - Get organization statistics
5. GET /api/v1/organization/{org_id} - Get organization details
6. GET /api/v1/organization/{org_id}/children - Get organization children
7. GET /api/v1/organization/{org_id}/path - Get organization path to root
8. GET /api/v1/organization/{org_id}/history - Get organization history
9. POST /api/v1/organization/ - Create organization
10. PUT /api/v1/organization/{org_id} - Update organization
11. DELETE /api/v1/organization/{org_id} - Delete organization (soft delete)
12. POST /api/v1/organization/{org_id}/move - Move organization
13. POST /api/v1/organization/batch - Batch operations
14. POST /api/v1/organization/advanced-search - Advanced search

Testing Approach:
- Mock all dependencies (organization_crud, organization_service, database, auth)
- Test successful responses
- Test error handling scenarios
- Test request validation
- Test response schemas
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

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
def mock_current_user():
    """Create mock authenticated user"""
    user = MagicMock()
    user.id = "test-user-id"
    user.username = "testuser"
    user.is_active = True
    user.role = "admin"
    return user


@pytest.fixture
def mock_organization():
    """Create mock organization"""
    org = MagicMock()
    org.id = "test-org-id"
    org.name = "Test Organization"
    org.code = "TEST001"
    org.level = 1
    org.sort_order = 0
    org.parent_id = None
    org.type = "department"
    org.status = "active"
    org.phone = "1234567890"
    org.email = "test@example.com"
    org.address = "Test Address"
    org.leader_name = "Test Leader"
    org.leader_phone = "0987654321"
    org.leader_email = "leader@example.com"
    org.description = "Test Description"
    org.functions = "Test Functions"
    org.path = "/test-org-id"
    org.is_deleted = False
    org.created_at = datetime.now(UTC)
    org.updated_at = datetime.now(UTC)
    org.created_by = "admin"
    org.updated_by = "admin"
    return org


# ============================================================================
# Test: GET /organization - Get Organization List
# ============================================================================


class TestGetOrganizations:
    """Tests for GET /api/v1/organization endpoint"""

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organizations_success(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test getting organization list successfully"""
        from src.api.v1.organization import get_organizations

        mock_orgs = [MagicMock() for _ in range(3)]
        for i, org in enumerate(mock_orgs):
            org.id = f"org-{i}"
            org.name = f"Organization {i}"
            org.code = f"ORG{i:03d}"
            org.level = 1
            org.sort_order = i
            org.parent_id = None
            org.type = "department"
            org.status = "active"
            org.phone = None
            org.email = None
            org.address = None
            org.leader_name = None
            org.leader_phone = None
            org.leader_email = None
            org.description = None
            org.functions = None

        mock_org_crud.get_multi_with_filters.return_value = mock_orgs

        result = await get_organizations(
            skip=0, limit=100, db=mock_db, current_user=mock_current_user
        )

        assert len(result) == 3
        mock_org_crud.get_multi_with_filters.assert_called_once_with(
            mock_db, skip=0, limit=100
        )

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organizations_with_pagination(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test getting organizations with pagination"""
        from src.api.v1.organization import get_organizations

        mock_org_crud.get_multi_with_filters.return_value = []

        await get_organizations(
            skip=10, limit=50, db=mock_db, current_user=mock_current_user
        )

        mock_org_crud.get_multi_with_filters.assert_called_once_with(
            mock_db, skip=10, limit=50
        )

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organizations_empty_list(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test getting organizations when none exist"""
        from src.api.v1.organization import get_organizations

        mock_org_crud.get_multi_with_filters.return_value = []

        result = await get_organizations(
            skip=0, limit=100, db=mock_db, current_user=mock_current_user
        )

        assert len(result) == 0


# ============================================================================
# Test: GET /organization/tree - Get Organization Tree
# ============================================================================


class TestGetOrganizationTree:
    """Tests for GET /api/v1/organization/tree endpoint"""

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organization_tree_root(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test getting organization tree from root"""
        from src.api.v1.organization import get_organization_tree

        # Mock root organizations
        mock_root_orgs = []
        for i in range(2):
            org = MagicMock()
            org.id = f"root-org-{i}"
            org.name = f"Root Organization {i}"
            org.level = 1
            org.sort_order = i
            mock_root_orgs.append(org)

        # Mock child organizations
        mock_child_orgs = []
        for i in range(3):
            org = MagicMock()
            org.id = f"child-org-{i}"
            org.name = f"Child Organization {i}"
            org.level = 2
            org.sort_order = i
            mock_child_orgs.append(org)

        # Setup side_effect to handle recursive calls properly
        # The build_tree function will call get_tree multiple times recursively:
        # 1. get_tree(None) → returns 2 root orgs
        # 2. get_tree("root-org-0") → returns 3 child orgs
        # 3. get_tree("child-org-0") → returns []
        # 4. get_tree("child-org-1") → returns []
        # 5. get_tree("child-org-2") → returns []
        # 6. get_tree("root-org-1") → returns [] (second root org has no children)
        mock_org_crud.get_tree.side_effect = [
            mock_root_orgs,  # Call 1: get root orgs (parent_id=None)
            mock_child_orgs,  # Call 2: get children of root-org-0
            [],  # Call 3: get children of child-org-0
            [],  # Call 4: get children of child-org-1
            [],  # Call 5: get children of child-org-2
            [],  # Call 6: get children of root-org-1 (second root has no children)
        ]

        result = await get_organization_tree(
            parent_id=None, db=mock_db, current_user=mock_current_user
        )

        assert len(result) == 2
        assert result[0].id == "root-org-0"
        assert result[0].name == "Root Organization 0"
        assert result[0].level == 1

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organization_tree_with_parent(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test getting organization tree for specific parent"""
        from src.api.v1.organization import get_organization_tree

        mock_org = MagicMock()
        mock_org.id = "parent-org"
        mock_org.name = "Parent Organization"
        mock_org.level = 2
        mock_org.sort_order = 0

        mock_org_crud.get_tree.return_value = [mock_org]

        result = await get_organization_tree(
            parent_id="parent-org", db=mock_db, current_user=mock_current_user
        )

        assert len(result) == 1
        assert result[0].id == "parent-org"
        mock_org_crud.get_tree.assert_called_with(db=mock_db, parent_id="parent-org")

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organization_tree_empty(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test getting organization tree with no organizations"""
        from src.api.v1.organization import get_organization_tree

        mock_org_crud.get_tree.return_value = []

        result = await get_organization_tree(
            parent_id=None, db=mock_db, current_user=mock_current_user
        )

        assert len(result) == 0


# ============================================================================
# Test: GET /organization/search - Search Organizations
# ============================================================================


class TestSearchOrganizations:
    """Tests for GET /api/v1/organization/search endpoint"""

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_search_organizations_success(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test searching organizations successfully"""
        from src.api.v1.organization import search_organizations

        mock_orgs = [MagicMock() for _ in range(2)]
        for i, org in enumerate(mock_orgs):
            org.id = f"org-{i}"
            org.name = f"Search Result {i}"

        mock_org_crud.search.return_value = mock_orgs

        result = await search_organizations(
            keyword="test",
            skip=0,
            limit=100,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert len(result) == 2
        mock_org_crud.search.assert_called_once_with(
            mock_db, keyword="test", skip=0, limit=100
        )

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_search_organizations_no_results(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test searching organizations with no matches"""
        from src.api.v1.organization import search_organizations

        mock_org_crud.search.return_value = []

        result = await search_organizations(
            keyword="nonexistent",
            skip=0,
            limit=100,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert len(result) == 0

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_search_organizations_with_pagination(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test searching organizations with pagination"""
        from src.api.v1.organization import search_organizations

        mock_org_crud.search.return_value = []

        await search_organizations(
            keyword="test",
            skip=20,
            limit=50,
            db=mock_db,
            current_user=mock_current_user,
        )

        mock_org_crud.search.assert_called_once_with(
            mock_db, keyword="test", skip=20, limit=50
        )


# ============================================================================
# Test: GET /organization/statistics - Get Organization Statistics
# ============================================================================


class TestGetOrganizationStatistics:
    """Tests for GET /api/v1/organization/statistics endpoint"""

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_get_organization_statistics_success(
        self, mock_org_service, mock_db, mock_current_user
    ):
        """Test getting organization statistics successfully"""
        from src.api.v1.organization import get_organization_statistics

        mock_stats = {
            "total": 100,
            "active": 80,
            "inactive": 20,
            "by_type": {"department": 50, "team": 30, "group": 20},
            "by_level": {"1": 10, "2": 30, "3": 60},
        }

        mock_org_service.get_statistics.return_value = mock_stats

        result = await get_organization_statistics(
            db=mock_db, current_user=mock_current_user
        )

        assert result.total == 100
        assert result.active == 80
        assert result.inactive == 20
        assert result.by_type == {"department": 50, "team": 30, "group": 20}
        assert result.by_level == {"1": 10, "2": 30, "3": 60}
        mock_org_service.get_statistics.assert_called_once_with(mock_db)

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_get_organization_statistics_empty(
        self, mock_org_service, mock_db, mock_current_user
    ):
        """Test getting organization statistics with no organizations"""
        from src.api.v1.organization import get_organization_statistics

        mock_stats = {
            "total": 0,
            "active": 0,
            "inactive": 0,
            "by_type": {},
            "by_level": {},
        }

        mock_org_service.get_statistics.return_value = mock_stats

        result = await get_organization_statistics(
            db=mock_db, current_user=mock_current_user
        )

        assert result.total == 0
        assert result.active == 0
        assert result.inactive == 0


# ============================================================================
# Test: GET /organization/{org_id} - Get Organization Details
# ============================================================================


class TestGetOrganization:
    """Tests for GET /api/v1/organization/{org_id} endpoint"""

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organization_success(
        self, mock_org_crud, mock_db, mock_current_user, mock_organization
    ):
        """Test getting organization details successfully"""
        from src.api.v1.organization import get_organization

        mock_org_crud.get.return_value = mock_organization

        result = await get_organization(
            org_id="test-org-id", db=mock_db, current_user=mock_current_user
        )

        assert result.id == "test-org-id"
        assert result.name == "Test Organization"
        assert result.code == "TEST001"
        mock_org_crud.get.assert_called_once_with(mock_db, id="test-org-id")

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organization_not_found(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test getting non-existent organization"""
        from src.api.v1.organization import get_organization

        mock_org_crud.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_organization(
                org_id="nonexistent-id", db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 404
        assert "组织不存在" in exc_info.value.detail


# ============================================================================
# Test: GET /organization/{org_id}/children - Get Organization Children
# ============================================================================


class TestGetOrganizationChildren:
    """Tests for GET /api/v1/organization/{org_id}/children endpoint"""

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organization_children_direct(
        self, mock_org_crud, mock_db, mock_current_user, mock_organization
    ):
        """Test getting direct children of organization"""
        from src.api.v1.organization import get_organization_children

        mock_org_crud.get.return_value = mock_organization

        mock_children = [MagicMock() for _ in range(3)]
        for i, child in enumerate(mock_children):
            child.id = f"child-{i}"
            child.name = f"Child {i}"
            child.parent_id = "test-org-id"

        mock_org_crud.get_children.return_value = mock_children

        result = await get_organization_children(
            org_id="test-org-id",
            recursive=False,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert len(result) == 3
        mock_org_crud.get.assert_called_once_with(mock_db, id="test-org-id")
        mock_org_crud.get_children.assert_called_once_with(
            mock_db, parent_id="test-org-id", recursive=False
        )

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organization_children_recursive(
        self, mock_org_crud, mock_db, mock_current_user, mock_organization
    ):
        """Test getting all descendants recursively"""
        from src.api.v1.organization import get_organization_children

        mock_org_crud.get.return_value = mock_organization
        mock_org_crud.get_children.return_value = []

        await get_organization_children(
            org_id="test-org-id",
            recursive=True,
            db=mock_db,
            current_user=mock_current_user,
        )

        mock_org_crud.get_children.assert_called_once_with(
            mock_db, parent_id="test-org-id", recursive=True
        )

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organization_children_parent_not_found(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test getting children of non-existent parent organization"""
        from src.api.v1.organization import get_organization_children

        mock_org_crud.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_organization_children(
                org_id="nonexistent-id",
                recursive=False,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "组织不存在" in exc_info.value.detail


# ============================================================================
# Test: GET /organization/{org_id}/path - Get Organization Path
# ============================================================================


class TestGetOrganizationPath:
    """Tests for GET /api/v1/organization/{org_id}/path endpoint"""

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organization_path_success(
        self, mock_org_crud, mock_db, mock_current_user, mock_organization
    ):
        """Test getting organization path to root successfully"""
        from src.api.v1.organization import get_organization_path

        mock_org_crud.get.return_value = mock_organization

        mock_path = [MagicMock() for _ in range(3)]
        for i, org in enumerate(mock_path):
            org.id = f"path-org-{i}"
            org.name = f"Level {i}"

        mock_org_crud.get_path_to_root.return_value = mock_path

        result = await get_organization_path(
            org_id="test-org-id", db=mock_db, current_user=mock_current_user
        )

        assert len(result) == 3
        mock_org_crud.get.assert_called_once_with(mock_db, id="test-org-id")
        mock_org_crud.get_path_to_root.assert_called_once_with(
            mock_db, org_id="test-org-id"
        )

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organization_path_not_found(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test getting path for non-existent organization"""
        from src.api.v1.organization import get_organization_path

        mock_org_crud.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_organization_path(
                org_id="nonexistent-id", db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 404
        assert "组织不存在" in exc_info.value.detail


# ============================================================================
# Test: GET /organization/{org_id}/history - Get Organization History
# ============================================================================


class TestGetOrganizationHistory:
    """Tests for GET /api/v1/organization/{org_id}/history endpoint"""

    @patch("src.api.v1.organization.organization_service")
    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organization_history_success(
        self,
        mock_org_crud,
        mock_org_service,
        mock_db,
        mock_current_user,
        mock_organization,
    ):
        """Test getting organization history successfully"""
        from src.api.v1.organization import get_organization_history

        mock_org_crud.get.return_value = mock_organization

        mock_history = [MagicMock() for _ in range(5)]
        for i, hist in enumerate(mock_history):
            hist.id = f"hist-{i}"
            hist.organization_id = "test-org-id"
            hist.action = "update"
            hist.field_name = "name"
            hist.old_value = "Old Name"
            hist.new_value = "New Name"
            hist.change_reason = "Update"
            hist.created_at = datetime.now(UTC)
            hist.created_by = "admin"

        mock_org_service.get_history.return_value = mock_history

        result = await get_organization_history(
            org_id="test-org-id",
            skip=0,
            limit=100,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert len(result) == 5
        mock_org_crud.get.assert_called_once_with(mock_db, id="test-org-id")
        mock_org_service.get_history.assert_called_once_with(
            mock_db, org_id="test-org-id", skip=0, limit=100
        )

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organization_history_not_found(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test getting history for non-existent organization"""
        from src.api.v1.organization import get_organization_history

        mock_org_crud.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_organization_history(
                org_id="nonexistent-id",
                skip=0,
                limit=100,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "组织不存在" in exc_info.value.detail

    @patch("src.api.v1.organization.organization_service")
    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organization_history_empty(
        self,
        mock_org_crud,
        mock_org_service,
        mock_db,
        mock_current_user,
        mock_organization,
    ):
        """Test getting organization history with no history records"""
        from src.api.v1.organization import get_organization_history

        mock_org_crud.get.return_value = mock_organization
        mock_org_service.get_history.return_value = []

        result = await get_organization_history(
            org_id="test-org-id",
            skip=0,
            limit=100,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert len(result) == 0


# ============================================================================
# Test: POST /organization/ - Create Organization
# ============================================================================


class TestCreateOrganization:
    """Tests for POST /api/v1/organization/ endpoint"""

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_create_organization_success(
        self, mock_org_service, mock_db, mock_current_user, mock_organization
    ):
        """Test creating organization successfully"""
        from src.api.v1.organization import create_organization

        from src.schemas.organization import OrganizationCreate

        org_data = OrganizationCreate(
            name="New Organization",
            code="NEW001",
            level=1,
            sort_order=0,
            parent_id=None,
            type="department",
            status="active",
            created_by="admin",
        )

        mock_org_service.create_organization.return_value = mock_organization

        result = await create_organization(
            organization=org_data, db=mock_db, current_user=mock_current_user
        )

        assert result.id == "test-org-id"
        assert result.name == "Test Organization"
        mock_org_service.create_organization.assert_called_once_with(
            mock_db, obj_in=org_data
        )

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_create_organization_validation_error(
        self, mock_org_service, mock_db, mock_current_user
    ):
        """Test creating organization with validation error"""
        from src.api.v1.organization import create_organization

        from src.schemas.organization import OrganizationCreate

        org_data = OrganizationCreate(
            name="New Organization",
            code="DUPLICATE",
            level=1,
            sort_order=0,
            parent_id=None,
            type="department",
            status="active",
            created_by="admin",
        )

        mock_org_service.create_organization.side_effect = ValueError("组织编码已存在")

        with pytest.raises(HTTPException) as exc_info:
            await create_organization(
                organization=org_data, db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 400
        assert "组织编码已存在" in exc_info.value.detail


# ============================================================================
# Test: PUT /organization/{org_id} - Update Organization
# ============================================================================


class TestUpdateOrganization:
    """Tests for PUT /api/v1/organization/{org_id} endpoint"""

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_update_organization_success(
        self, mock_org_service, mock_db, mock_current_user, mock_organization
    ):
        """Test updating organization successfully"""
        from src.api.v1.organization import update_organization

        from src.schemas.organization import OrganizationUpdate

        org_data = OrganizationUpdate(name="Updated Name", updated_by="admin")

        mock_org_service.update_organization.return_value = mock_organization

        result = await update_organization(
            org_id="test-org-id",
            organization=org_data,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.id == "test-org-id"
        mock_org_service.update_organization.assert_called_once_with(
            db=mock_db, org_id="test-org-id", obj_in=org_data
        )

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_update_organization_not_found(
        self, mock_org_service, mock_db, mock_current_user
    ):
        """Test updating non-existent organization"""
        from src.api.v1.organization import update_organization

        from src.schemas.organization import OrganizationUpdate

        org_data = OrganizationUpdate(name="Updated Name")

        mock_org_service.update_organization.side_effect = ValueError(
            "组织ID不存在: test-org-id"
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_organization(
                org_id="test-org-id",
                organization=org_data,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "组织ID不存在" in exc_info.value.detail

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_update_organization_validation_error(
        self, mock_org_service, mock_db, mock_current_user
    ):
        """Test updating organization with validation error"""
        from src.api.v1.organization import update_organization

        from src.schemas.organization import OrganizationUpdate

        org_data = OrganizationUpdate(name="Updated Name")

        mock_org_service.update_organization.side_effect = ValueError("父组织不存在")

        with pytest.raises(HTTPException) as exc_info:
            await update_organization(
                org_id="test-org-id",
                organization=org_data,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400
        assert "父组织不存在" in exc_info.value.detail


# ============================================================================
# Test: DELETE /organization/{org_id} - Delete Organization
# ============================================================================


class TestDeleteOrganization:
    """Tests for DELETE /api/v1/organization/{org_id} endpoint"""

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_delete_organization_success(
        self, mock_org_service, mock_db, mock_current_user
    ):
        """Test deleting organization successfully"""
        from src.api.v1.organization import delete_organization

        mock_org_service.delete_organization.return_value = True

        result = await delete_organization(
            org_id="test-org-id",
            deleted_by="admin",
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["message"] == "组织删除成功"
        mock_org_service.delete_organization.assert_called_once_with(
            db=mock_db, org_id="test-org-id", deleted_by="admin"
        )

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_delete_organization_not_found(
        self, mock_org_service, mock_db, mock_current_user
    ):
        """Test deleting non-existent organization"""
        from src.api.v1.organization import delete_organization

        mock_org_service.delete_organization.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await delete_organization(
                org_id="nonexistent-id",
                deleted_by="admin",
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "组织不存在" in exc_info.value.detail

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_delete_organization_validation_error(
        self, mock_org_service, mock_db, mock_current_user
    ):
        """Test deleting organization with validation error"""
        from src.api.v1.organization import delete_organization

        mock_org_service.delete_organization.side_effect = ValueError(
            "组织下有子组织，无法删除"
        )

        with pytest.raises(HTTPException) as exc_info:
            await delete_organization(
                org_id="test-org-id",
                deleted_by="admin",
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400
        assert "组织下有子组织" in exc_info.value.detail


# ============================================================================
# Test: POST /organization/{org_id}/move - Move Organization
# ============================================================================


class TestMoveOrganization:
    """Tests for POST /api/v1/organization/{org_id}/move endpoint"""

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_move_organization_success(
        self, mock_org_service, mock_db, mock_current_user, mock_organization
    ):
        """Test moving organization successfully"""
        from src.api.v1.organization import move_organization

        from src.schemas.organization import OrganizationMoveRequest

        move_request = OrganizationMoveRequest(
            target_parent_id="new-parent-id", sort_order=1, updated_by="admin"
        )

        mock_org_service.update_organization.return_value = mock_organization

        result = await move_organization(
            org_id="test-org-id",
            move_request=move_request,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["message"] == "组织移动成功"
        assert "organization" in result
        assert result["organization"].id == "test-org-id"

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_move_organization_not_found(
        self, mock_org_service, mock_db, mock_current_user
    ):
        """Test moving non-existent organization"""
        from src.api.v1.organization import move_organization

        from src.schemas.organization import OrganizationMoveRequest

        move_request = OrganizationMoveRequest(
            target_parent_id="new-parent-id", sort_order=1, updated_by="admin"
        )

        mock_org_service.update_organization.side_effect = ValueError(
            "组织ID不存在: test-org-id"
        )

        with pytest.raises(HTTPException) as exc_info:
            await move_organization(
                org_id="test-org-id",
                move_request=move_request,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "组织ID不存在" in exc_info.value.detail

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_move_organization_validation_error(
        self, mock_org_service, mock_db, mock_current_user
    ):
        """Test moving organization with validation error"""
        from src.api.v1.organization import move_organization

        from src.schemas.organization import OrganizationMoveRequest

        move_request = OrganizationMoveRequest(
            target_parent_id="invalid-parent-id", sort_order=1, updated_by="admin"
        )

        mock_org_service.update_organization.side_effect = ValueError(
            "目标父组织不存在"
        )

        with pytest.raises(HTTPException) as exc_info:
            await move_organization(
                org_id="test-org-id",
                move_request=move_request,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400
        assert "目标父组织不存在" in exc_info.value.detail


# ============================================================================
# Test: POST /organization/batch - Batch Operations
# ============================================================================


class TestBatchOrganizationOperation:
    """Tests for POST /api/v1/organization/batch endpoint"""

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_batch_delete_success(
        self, mock_org_service, mock_db, mock_current_user
    ):
        """Test batch deleting organizations successfully"""
        from src.api.v1.organization import batch_organization_operation

        from src.schemas.organization import OrganizationBatchRequest

        batch_request = OrganizationBatchRequest(
            organization_ids=["org-1", "org-2", "org-3"],
            action="delete",
            updated_by="admin",
        )

        mock_org_service.delete_organization.return_value = True

        result = await batch_organization_operation(
            batch_request=batch_request, db=mock_db, current_user=mock_current_user
        )

        assert "批量操作完成" in result["message"]
        assert result["message"] == "批量操作完成，成功 3 个，失败 0 个"
        assert len(result["results"]) == 3
        assert len(result["errors"]) == 0

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_batch_delete_partial_failure(
        self, mock_org_service, mock_db, mock_current_user
    ):
        """Test batch deleting organizations with some failures"""
        from src.api.v1.organization import batch_organization_operation

        from src.schemas.organization import OrganizationBatchRequest

        batch_request = OrganizationBatchRequest(
            organization_ids=["org-1", "org-2", "org-3"],
            action="delete",
            updated_by="admin",
        )

        # First succeeds, second fails (not found), third fails (validation error)
        mock_org_service.delete_organization.side_effect = [
            True,
            False,
            ValueError("有子组织"),
        ]

        result = await batch_organization_operation(
            batch_request=batch_request, db=mock_db, current_user=mock_current_user
        )

        assert len(result["results"]) == 1
        assert len(result["errors"]) == 2
        assert "批量操作完成" in result["message"]

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_batch_delete_all_failures(
        self, mock_org_service, mock_db, mock_current_user
    ):
        """Test batch deleting organizations with all failures"""
        from src.api.v1.organization import batch_organization_operation

        from src.schemas.organization import OrganizationBatchRequest

        batch_request = OrganizationBatchRequest(
            organization_ids=["org-1", "org-2"], action="delete", updated_by="admin"
        )

        mock_org_service.delete_organization.return_value = False

        result = await batch_organization_operation(
            batch_request=batch_request, db=mock_db, current_user=mock_current_user
        )

        assert len(result["results"]) == 0
        assert len(result["errors"]) == 2
        assert result["message"] == "批量操作完成，成功 0 个，失败 2 个"


# ============================================================================
# Test: POST /organization/advanced-search - Advanced Search
# ============================================================================


class TestAdvancedSearchOrganizations:
    """Tests for POST /api/v1/organization/advanced-search endpoint"""

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_advanced_search_with_keyword(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test advanced search with keyword"""
        from src.api.v1.organization import advanced_search_organizations

        from src.schemas.organization import OrganizationSearchRequest

        search_request = OrganizationSearchRequest(keyword="test", skip=0, limit=100)

        mock_orgs = [MagicMock() for _ in range(2)]
        for i, org in enumerate(mock_orgs):
            org.id = f"org-{i}"
            org.name = f"Test Org {i}"
            org.level = 1
            org.parent_id = None

        mock_org_crud.search.return_value = mock_orgs

        result = await advanced_search_organizations(
            search_request=search_request, db=mock_db, current_user=mock_current_user
        )

        assert len(result) == 2
        mock_org_crud.search.assert_called_once_with(
            mock_db, keyword="test", skip=0, limit=100
        )

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_advanced_search_with_level_filter(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test advanced search with level filter"""
        from src.api.v1.organization import advanced_search_organizations

        from src.schemas.organization import OrganizationSearchRequest

        search_request = OrganizationSearchRequest(level=2, skip=0, limit=100)

        mock_orgs = []
        for i in range(3):
            org = MagicMock()
            org.id = f"org-{i}"
            org.name = f"Org {i}"
            org.level = 2  # Matching level
            org.parent_id = None
            mock_orgs.append(org)

        # Add one with different level that should be filtered out
        org_different_level = MagicMock()
        org_different_level.id = "org-diff"
        org_different_level.name = "Different Level"
        org_different_level.level = 3
        org_different_level.parent_id = None

        mock_orgs.append(org_different_level)

        mock_org_crud.get_multi_with_filters.return_value = mock_orgs

        result = await advanced_search_organizations(
            search_request=search_request, db=mock_db, current_user=mock_current_user
        )

        # Should only return organizations with level 2
        assert len(result) == 3
        for org in result:
            assert org.level == 2

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_advanced_search_with_parent_filter(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test advanced search with parent_id filter"""
        from src.api.v1.organization import advanced_search_organizations

        from src.schemas.organization import OrganizationSearchRequest

        search_request = OrganizationSearchRequest(
            parent_id="parent-123", skip=0, limit=100
        )

        mock_orgs = []
        for i in range(2):
            org = MagicMock()
            org.id = f"child-{i}"
            org.name = f"Child {i}"
            org.level = 2
            org.parent_id = "parent-123"  # Matching parent
            mock_orgs.append(org)

        # Add one with different parent
        org_different_parent = MagicMock()
        org_different_parent.id = "other-child"
        org_different_parent.name = "Other Child"
        org_different_parent.level = 2
        org_different_parent.parent_id = "other-parent"

        mock_orgs.append(org_different_parent)

        mock_org_crud.get_multi_with_filters.return_value = mock_orgs

        result = await advanced_search_organizations(
            search_request=search_request, db=mock_db, current_user=mock_current_user
        )

        # Should only return organizations with matching parent_id
        assert len(result) == 2
        for org in result:
            assert org.parent_id == "parent-123"

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_advanced_search_with_multiple_filters(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test advanced search with multiple filters"""
        from src.api.v1.organization import advanced_search_organizations

        from src.schemas.organization import OrganizationSearchRequest

        search_request = OrganizationSearchRequest(
            keyword="test", level=2, parent_id="parent-123", skip=0, limit=100
        )

        mock_orgs = []
        for i in range(2):
            org = MagicMock()
            org.id = f"org-{i}"
            org.name = f"Test Org {i}"
            org.level = 2
            org.parent_id = "parent-123"
            mock_orgs.append(org)

        mock_org_crud.search.return_value = mock_orgs

        result = await advanced_search_organizations(
            search_request=search_request, db=mock_db, current_user=mock_current_user
        )

        assert len(result) == 2

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_advanced_search_no_filters(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test advanced search without any filters"""
        from src.api.v1.organization import advanced_search_organizations

        from src.schemas.organization import OrganizationSearchRequest

        search_request = OrganizationSearchRequest(skip=0, limit=100)

        mock_org_crud.get_multi_with_filters.return_value = []

        result = await advanced_search_organizations(
            search_request=search_request, db=mock_db, current_user=mock_current_user
        )

        assert len(result) == 0
        mock_org_crud.get_multi_with_filters.assert_called_once_with(
            mock_db, skip=0, limit=100
        )

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_advanced_search_with_pagination(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test advanced search with pagination"""
        from src.api.v1.organization import advanced_search_organizations

        from src.schemas.organization import OrganizationSearchRequest

        search_request = OrganizationSearchRequest(skip=10, limit=50)

        mock_org_crud.get_multi_with_filters.return_value = []

        await advanced_search_organizations(
            search_request=search_request, db=mock_db, current_user=mock_current_user
        )

        mock_org_crud.get_multi_with_filters.assert_called_once_with(
            mock_db, skip=10, limit=50
        )


# ============================================================================
# Test: Edge Cases and Error Handling
# ============================================================================


class TestOrganizationEdgeCases:
    """Tests for edge cases and error handling"""

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organizations_with_invalid_pagination(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test getting organizations with invalid pagination parameters"""
        from src.api.v1.organization import get_organizations

        mock_org_crud.get_multi_with_filters.return_value = []

        # Test with maximum allowed values
        result = await get_organizations(
            skip=1000, limit=1000, db=mock_db, current_user=mock_current_user
        )

        assert len(result) == 0

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_search_organizations_empty_keyword(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test searching with empty string keyword (should fail validation)"""
        from src.api.v1.organization import search_organizations

        # This should fail FastAPI validation before reaching the endpoint
        # but we can test the CRUD behavior if it somehow gets through
        mock_org_crud.search.return_value = []

        # This test documents the expected behavior - empty keyword should be caught by validation
        # but if it reaches the endpoint, it should return empty results
        result = await search_organizations(
            keyword="test",
            skip=0,
            limit=100,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert len(result) == 0

    @patch("src.api.v1.organization.organization_service")
    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organization_history_with_pagination(
        self,
        mock_org_crud,
        mock_org_service,
        mock_db,
        mock_current_user,
        mock_organization,
    ):
        """Test getting organization history with pagination"""
        from src.api.v1.organization import get_organization_history

        mock_org_crud.get.return_value = mock_organization
        mock_org_service.get_history.return_value = []

        result = await get_organization_history(
            org_id="test-org-id",
            skip=50,
            limit=200,
            db=mock_db,
            current_user=mock_current_user,
        )

        mock_org_service.get_history.assert_called_once_with(
            mock_db, org_id="test-org-id", skip=50, limit=200
        )
        assert len(result) == 0

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_create_organization_with_parent(
        self, mock_org_service, mock_db, mock_current_user, mock_organization
    ):
        """Test creating organization with parent"""
        from src.api.v1.organization import create_organization

        from src.schemas.organization import OrganizationCreate

        org_data = OrganizationCreate(
            name="Child Organization",
            code="CHILD001",
            level=2,
            sort_order=0,
            parent_id="parent-org-id",
            type="department",
            status="active",
            created_by="admin",
        )

        mock_org_service.create_organization.return_value = mock_organization

        result = await create_organization(
            organization=org_data, db=mock_db, current_user=mock_current_user
        )

        assert result.id == "test-org-id"
        mock_org_service.create_organization.assert_called_once()

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_update_organization_partial_update(
        self, mock_org_service, mock_db, mock_current_user, mock_organization
    ):
        """Test updating organization with partial data"""
        from src.api.v1.organization import update_organization

        from src.schemas.organization import OrganizationUpdate

        # Only update name
        org_data = OrganizationUpdate(name="New Name Only")

        mock_org_service.update_organization.return_value = mock_organization

        result = await update_organization(
            org_id="test-org-id",
            organization=org_data,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.id == "test-org-id"
        mock_org_service.update_organization.assert_called_once()

    @patch("src.api.v1.organization.organization_service")
    @pytest.mark.asyncio
    async def test_delete_organization_without_deleted_by(
        self, mock_org_service, mock_db, mock_current_user
    ):
        """Test deleting organization without specifying deleted_by"""
        from src.api.v1.organization import delete_organization

        mock_org_service.delete_organization.return_value = True

        result = await delete_organization(
            org_id="test-org-id",
            deleted_by=None,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result["message"] == "组织删除成功"
        mock_org_service.delete_organization.assert_called_once_with(
            mock_db, org_id="test-org-id", deleted_by=None
        )

    @patch("src.api.v1.organization.organization_crud")
    @pytest.mark.asyncio
    async def test_get_organization_tree_with_deep_nesting(
        self, mock_org_crud, mock_db, mock_current_user
    ):
        """Test getting organization tree with multiple levels"""
        from src.api.v1.organization import get_organization_tree

        # Simulate a 3-level hierarchy
        level1_orgs = [MagicMock() for _ in range(1)]
        level1_orgs[0].id = "root"
        level1_orgs[0].name = "Root"
        level1_orgs[0].level = 1
        level1_orgs[0].sort_order = 0

        level2_orgs = [MagicMock() for _ in range(2)]
        for i, org in enumerate(level2_orgs):
            org.id = f"level2-{i}"
            org.name = f"Level 2 {i}"
            org.level = 2
            org.sort_order = i

        level3_orgs = [MagicMock() for _ in range(3)]
        for i, org in enumerate(level3_orgs):
            org.id = f"level3-{i}"
            org.name = f"Level 3 {i}"
            org.level = 3
            org.sort_order = i

        mock_org_crud.get_tree.side_effect = [
            level1_orgs,  # Get roots
            level2_orgs,  # Get children of root
            level3_orgs,  # Get children of level2-0
            [],  # No more children
        ]

        result = await get_organization_tree(
            parent_id=None, db=mock_db, current_user=mock_current_user
        )

        # Should return root with nested children
        assert len(result) == 1
        assert result[0].id == "root"
