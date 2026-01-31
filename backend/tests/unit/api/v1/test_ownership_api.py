"""
Comprehensive Unit Tests for Ownership API Routes (src/api/v1/ownership.py)

This test module covers all endpoints in the ownership router to achieve 70%+ coverage:

Endpoints Tested:
1. GET /api/v1/ownership/dropdown-options - Get ownership dropdown options
2. POST /api/v1/ownership/ - Create ownership
3. PUT /api/v1/ownership/{ownership_id} - Update ownership
4. PUT /api/v1/ownership/{ownership_id}/projects - Update ownership projects
5. DELETE /api/v1/ownership/{ownership_id} - Delete ownership
6. GET /api/v1/ownership - Get ownership list
7. POST /api/v1/ownership/search - Search ownerships
8. GET /api/v1/ownership/statistics/summary - Get ownership statistics
9. POST /api/v1/ownership/{ownership_id}/toggle-status - Toggle ownership status
10. GET /api/v1/ownership/{ownership_id}/financial-summary - Get financial summary

Testing Approach:
- Mock all dependencies (OwnershipService, OwnershipCRUD, database, auth)
- Test successful responses
- Test error handling scenarios
- Test request validation
- Test response schemas
- Test edge cases
"""

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.core.exception_handler import (
    BaseBusinessError,
    DuplicateResourceError,
    InternalServerError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)

pytestmark = pytest.mark.api


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_current_user():
    """Create mock current user"""
    user = MagicMock()
    user.id = "user-id"
    user.username = "testuser"
    user.is_active = True
    return user


@pytest.fixture
def mock_ownership():
    """Create mock ownership object"""
    from types import SimpleNamespace

    ownership = SimpleNamespace(
        id="ownership-id-123",
        name="Test Ownership Company",
        code="OW2501001",
        short_name="Test Owner",
        is_active=True,
        data_status="正常",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        project_relations_data=[],
    )
    return ownership


@pytest.fixture
def mock_ownership_list():
    """Create mock ownership list"""
    ownerships = []
    for i in range(3):
        ownership = MagicMock()
        ownership.id = f"ownership-id-{i}"
        ownership.name = f"Ownership Company {i}"
        ownership.code = f"OW250100{i}"
        ownership.short_name = f"Owner {i}"
        ownership.is_active = True
        ownership.data_status = "正常"
        ownership.created_at = datetime.now(UTC)
        ownership.updated_at = datetime.now(UTC)
        ownership.project_relations_data = []
        ownerships.append(ownership)
    return ownerships


# ============================================================================
# Test: GET /dropdown-options - Get Ownership Dropdown Options
# ============================================================================


class TestGetOwnershipDropdownOptions:
    """Tests for GET /api/v1/ownership/dropdown-options endpoint"""

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_get_dropdown_options_success(
        self, mock_service, mock_db, mock_current_user, mock_ownership_list
    ):
        """Test getting dropdown options successfully"""
        from src.api.v1.assets.ownership import get_ownership_dropdown_options

        mock_service.get_ownership_dropdown_options.return_value = [
            {
                "id": item.id,
                "name": item.name,
                "code": item.code,
                "short_name": item.short_name,
                "is_active": item.is_active,
                "data_status": item.data_status,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "asset_count": 5,
                "project_count": 2,
            }
            for item in mock_ownership_list
        ]

        result = get_ownership_dropdown_options(
            current_user=mock_current_user, db=mock_db, is_active=True
        )

        assert len(result) == 3
        assert result[0].name == "Ownership Company 0"
        assert result[0].asset_count == 5
        assert result[0].project_count == 2

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_get_dropdown_options_with_inactive_filter(
        self, mock_service, mock_db, mock_current_user, mock_ownership_list
    ):
        """Test getting dropdown options with is_active=False"""
        from src.api.v1.assets.ownership import get_ownership_dropdown_options

        mock_service.get_ownership_dropdown_options.return_value = [
            {
                "id": item.id,
                "name": item.name,
                "code": item.code,
                "short_name": item.short_name,
                "is_active": item.is_active,
                "data_status": item.data_status,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "asset_count": 0,
                "project_count": 0,
            }
            for item in mock_ownership_list
        ]

        result = get_ownership_dropdown_options(
            current_user=mock_current_user, db=mock_db, is_active=False
        )

        assert len(result) == 3

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_get_dropdown_options_no_active_filter(
        self, mock_service, mock_db, mock_current_user, mock_ownership_list
    ):
        """Test getting dropdown options with is_active=None"""
        from src.api.v1.assets.ownership import get_ownership_dropdown_options

        mock_service.get_ownership_dropdown_options.return_value = [
            {
                "id": item.id,
                "name": item.name,
                "code": item.code,
                "short_name": item.short_name,
                "is_active": item.is_active,
                "data_status": item.data_status,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "asset_count": 3,
                "project_count": 1,
            }
            for item in mock_ownership_list
        ]

        result = get_ownership_dropdown_options(
            current_user=mock_current_user, db=mock_db, is_active=None
        )

        assert len(result) == 3

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_get_dropdown_options_empty_list(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test getting dropdown options when no ownerships exist"""
        from src.api.v1.assets.ownership import get_ownership_dropdown_options

        mock_service.get_ownership_dropdown_options.return_value = []

        result = get_ownership_dropdown_options(
            current_user=mock_current_user, db=mock_db, is_active=True
        )

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_dropdown_options_exception(self, mock_db, mock_current_user):
        """Test getting dropdown options with database exception"""
        from src.api.v1.assets.ownership import get_ownership_dropdown_options
        from src.core.exception_handler import InternalServerError

        with patch("src.api.v1.assets.ownership.ownership_service") as mock_service:
            mock_service.get_ownership_dropdown_options.side_effect = Exception(
                "Database error"
            )

            with pytest.raises(InternalServerError) as exc_info:
                get_ownership_dropdown_options(
                    current_user=mock_current_user, db=mock_db, is_active=True
                )

            assert exc_info.value.status_code == 500
            assert "获取权属方选项失败" in exc_info.value.message


# ============================================================================
# Test: POST / - Create Ownership
# ============================================================================


class TestCreateOwnership:
    """Tests for POST /api/v1/ownership/ endpoint"""

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_create_ownership_success(
        self, mock_service, mock_db, mock_current_user, mock_ownership
    ):
        """Test creating ownership successfully"""
        from src.api.v1.assets.ownership import create_ownership
        from src.schemas.ownership import OwnershipCreate

        ownership_data = OwnershipCreate(
            name="New Ownership Company", short_name="New Owner"
        )

        mock_service.create_ownership.return_value = mock_ownership

        result = create_ownership(
            db=mock_db, ownership_in=ownership_data, current_user=mock_current_user
        )

        assert result.name == "Test Ownership Company"
        assert result.code == "OW2501001"
        mock_service.create_ownership.assert_called_once_with(
            mock_db, obj_in=ownership_data
        )

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_create_ownership_duplicate_name(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test creating ownership with duplicate name"""
        from src.api.v1.assets.ownership import create_ownership
        from src.schemas.ownership import OwnershipCreate

        ownership_data = OwnershipCreate(
            name="Existing Ownership", short_name="Existing"
        )

        mock_service.create_ownership.side_effect = DuplicateResourceError(
            "权属方",
            "name",
            "Existing Ownership",
        )

        with pytest.raises(BaseBusinessError) as exc_info:
            create_ownership(
                db=mock_db, ownership_in=ownership_data, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 409
        assert "权属方已存在" in exc_info.value.message

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_create_ownership_exception(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test creating ownership with unexpected exception"""
        from src.api.v1.assets.ownership import create_ownership
        from src.schemas.ownership import OwnershipCreate

        ownership_data = OwnershipCreate(name="New Company", short_name="New")

        mock_service.create_ownership.side_effect = Exception(
            "Database connection failed"
        )

        with pytest.raises(InternalServerError) as exc_info:
            create_ownership(
                db=mock_db, ownership_in=ownership_data, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500
        assert "创建权属方失败" in exc_info.value.message


# ============================================================================
# Test: PUT /{ownership_id} - Update Ownership
# ============================================================================


class TestUpdateOwnership:
    """Tests for PUT /api/v1/ownership/{ownership_id} endpoint"""

    @patch("src.api.v1.assets.ownership.ownership_service")
    @patch("src.api.v1.assets.ownership.ownership")
    @pytest.mark.asyncio
    async def test_update_ownership_success(
        self, mock_crud, mock_service, mock_db, mock_current_user, mock_ownership
    ):
        """Test updating ownership successfully"""
        from src.api.v1.assets.ownership import update_ownership
        from src.schemas.ownership import OwnershipUpdate

        update_data = OwnershipUpdate(name="Updated Ownership Name")

        mock_crud.get.return_value = mock_ownership
        mock_service.update_ownership.return_value = mock_ownership

        result = update_ownership(
            db=mock_db,
            ownership_id="ownership-id-123",
            ownership_in=update_data,
            current_user=mock_current_user,
        )

        assert result.name == "Test Ownership Company"
        mock_crud.get.assert_called_once_with(mock_db, id="ownership-id-123")
        mock_service.update_ownership.assert_called_once()

    @patch("src.api.v1.assets.ownership.ownership")
    @pytest.mark.asyncio
    async def test_update_ownership_not_found(
        self, mock_crud, mock_db, mock_current_user
    ):
        """Test updating non-existent ownership"""
        from src.api.v1.assets.ownership import update_ownership
        from src.schemas.ownership import OwnershipUpdate

        update_data = OwnershipUpdate(name="Updated Name")

        mock_crud.get.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            update_ownership(
                db=mock_db,
                ownership_id="nonexistent-id",
                ownership_in=update_data,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "不存在" in exc_info.value.message

    @patch("src.api.v1.assets.ownership.ownership_service")
    @patch("src.api.v1.assets.ownership.ownership")
    @pytest.mark.asyncio
    async def test_update_ownership_duplicate_name(
        self, mock_crud, mock_service, mock_db, mock_current_user, mock_ownership
    ):
        """Test updating ownership with duplicate name"""
        from src.api.v1.assets.ownership import update_ownership
        from src.schemas.ownership import OwnershipUpdate

        update_data = OwnershipUpdate(name="Existing Ownership Name")

        mock_crud.get.return_value = mock_ownership
        mock_service.update_ownership.side_effect = DuplicateResourceError(
            "权属方",
            "name",
            "Existing Ownership Name",
        )

        with pytest.raises(BaseBusinessError) as exc_info:
            update_ownership(
                db=mock_db,
                ownership_id="ownership-id-123",
                ownership_in=update_data,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 409
        assert "权属方已存在" in exc_info.value.message

    @patch("src.api.v1.assets.ownership.ownership_service")
    @patch("src.api.v1.assets.ownership.ownership")
    @pytest.mark.asyncio
    async def test_update_ownership_exception(
        self, mock_crud, mock_service, mock_db, mock_current_user, mock_ownership
    ):
        """Test updating ownership with unexpected exception"""
        from src.api.v1.assets.ownership import update_ownership
        from src.schemas.ownership import OwnershipUpdate

        update_data = OwnershipUpdate(name="Updated Name")

        mock_crud.get.return_value = mock_ownership
        mock_service.update_ownership.side_effect = Exception("Database error")

        with pytest.raises(InternalServerError) as exc_info:
            update_ownership(
                db=mock_db,
                ownership_id="ownership-id-123",
                ownership_in=update_data,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 500
        assert "更新权属方失败" in exc_info.value.message


# ============================================================================
# Test: PUT /{ownership_id}/projects - Update Ownership Projects
# ============================================================================


class TestUpdateOwnershipProjects:
    """Tests for PUT /api/v1/ownership/{ownership_id}/projects endpoint"""

    @patch("src.api.v1.assets.ownership.ownership_service")
    @patch("src.api.v1.assets.ownership.ownership")
    @pytest.mark.asyncio
    async def test_update_projects_success(
        self, mock_crud, mock_service, mock_db, mock_current_user, mock_ownership
    ):
        """Test updating ownership projects successfully"""
        from src.api.v1.assets.ownership import update_ownership_projects

        project_ids = ["project-1", "project-2", "project-3"]

        mock_crud.get.return_value = mock_ownership
        mock_service.update_related_projects.return_value = None
        mock_service.get_project_count.return_value = 3

        result = update_ownership_projects(
            db=mock_db,
            ownership_id="ownership-id-123",
            project_ids=project_ids,
            current_user=mock_current_user,
        )

        assert result.project_count == 3
        mock_service.update_related_projects.assert_called_once_with(
            mock_db, ownership_id="ownership-id-123", project_ids=project_ids
        )

    @patch("src.api.v1.assets.ownership.ownership")
    @pytest.mark.asyncio
    async def test_update_projects_not_found(
        self, mock_crud, mock_db, mock_current_user
    ):
        """Test updating projects for non-existent ownership"""
        from src.api.v1.assets.ownership import update_ownership_projects

        mock_crud.get.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            update_ownership_projects(
                db=mock_db,
                ownership_id="nonexistent-id",
                project_ids=["project-1"],
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "不存在" in exc_info.value.message

    @patch("src.api.v1.assets.ownership.ownership_service")
    @patch("src.api.v1.assets.ownership.ownership")
    @pytest.mark.asyncio
    async def test_update_projects_exception(
        self, mock_crud, mock_service, mock_db, mock_current_user, mock_ownership
    ):
        """Test updating projects with exception"""
        from src.api.v1.assets.ownership import update_ownership_projects

        mock_crud.get.return_value = mock_ownership
        mock_service.update_related_projects.side_effect = Exception("Database error")

        with pytest.raises(InternalServerError) as exc_info:
            update_ownership_projects(
                db=mock_db,
                ownership_id="ownership-id-123",
                project_ids=["project-1"],
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 500
        assert "更新关联项目失败" in exc_info.value.message


# ============================================================================
# Test: DELETE /{ownership_id} - Delete Ownership
# ============================================================================


class TestDeleteOwnership:
    """Tests for DELETE /api/v1/ownership/{ownership_id} endpoint"""

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_delete_ownership_success(
        self, mock_service, mock_db, mock_current_user, mock_ownership
    ):
        """Test deleting ownership successfully"""
        from src.api.v1.assets.ownership import delete_ownership

        mock_service.get_asset_count.return_value = 0
        mock_service.delete_ownership.return_value = mock_ownership

        result = delete_ownership(
            db=mock_db, ownership_id="ownership-id-123", current_user=mock_current_user
        )

        assert result.message == "权属方删除成功"
        assert result.id == "ownership-id-123"
        assert result.affected_assets == 0
        mock_service.get_asset_count.assert_called_once_with(
            mock_db, "ownership-id-123"
        )
        mock_service.delete_ownership.assert_called_once_with(
            mock_db, id="ownership-id-123"
        )

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_delete_ownership_with_assets(
        self, mock_service, mock_db, mock_current_user, mock_ownership
    ):
        """Test deleting ownership that has associated assets"""
        from src.api.v1.assets.ownership import delete_ownership

        mock_service.get_asset_count.return_value = 5
        mock_service.delete_ownership.return_value = mock_ownership

        result = delete_ownership(
            db=mock_db, ownership_id="ownership-id-123", current_user=mock_current_user
        )

        assert result.affected_assets == 5

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_delete_ownership_not_found(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test deleting non-existent ownership"""
        from src.api.v1.assets.ownership import delete_ownership

        mock_service.get_asset_count.return_value = 0
        mock_service.delete_ownership.side_effect = ResourceNotFoundError(
            "权属方",
            "nonexistent-id",
        )

        with pytest.raises(BaseBusinessError) as exc_info:
            delete_ownership(
                db=mock_db,
                ownership_id="nonexistent-id",
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "权属方不存在" in exc_info.value.message

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_delete_ownership_with_related_assets(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test deleting ownership that has related assets"""
        from src.api.v1.assets.ownership import delete_ownership

        mock_service.get_asset_count.return_value = 3
        mock_service.delete_ownership.side_effect = OperationNotAllowedError(
            "该权属方还有 3 个关联资产，无法删除",
            reason="ownership_has_assets",
        )

        with pytest.raises(BaseBusinessError) as exc_info:
            delete_ownership(
                db=mock_db,
                ownership_id="ownership-id-123",
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400
        assert "关联资产" in exc_info.value.message

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_delete_ownership_exception(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test deleting ownership with unexpected exception"""
        from src.api.v1.assets.ownership import delete_ownership

        mock_service.get_asset_count.return_value = 0
        mock_service.delete_ownership.side_effect = Exception("Database error")

        with pytest.raises(InternalServerError) as exc_info:
            delete_ownership(
                db=mock_db,
                ownership_id="ownership-id-123",
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 500
        assert "删除权属方失败" in exc_info.value.message


# ============================================================================
# Test: GET / - Get Ownership List
# ============================================================================


class TestGetOwnerships:
    """Tests for GET /api/v1/ownership/ endpoint"""

    @patch("src.api.v1.assets.ownership.ownership_service")
    @patch("src.api.v1.assets.ownership.ownership")
    @pytest.mark.asyncio
    async def test_get_ownerships_success(
        self, mock_crud, mock_service, mock_db, mock_current_user, mock_ownership_list
    ):
        """Test getting ownership list successfully"""
        from src.api.v1.assets.ownership import get_ownerships

        mock_crud.search.return_value = {
            "items": mock_ownership_list,
            "total": 3,
            "page": 1,
            "page_size": 10,
            "pages": 1,
        }
        mock_service.get_asset_count.return_value = 5
        mock_service.get_project_count.return_value = 2

        result = get_ownerships(
            current_user=mock_current_user,
            db=mock_db,
            page=1,
            page_size=10,
            keyword=None,
            is_active=None,
        )

        body = json.loads(result.body.decode())
        data = body["data"]
        pagination = data["pagination"]

        assert pagination["total"] == 3
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10
        assert pagination["total_pages"] == 1
        assert len(data["items"]) == 3
        assert data["items"][0]["asset_count"] == 5
        assert data["items"][0]["project_count"] == 2

    @patch("src.api.v1.assets.ownership.ownership_service")
    @patch("src.api.v1.assets.ownership.ownership")
    @pytest.mark.asyncio
    async def test_get_ownerships_with_keyword(
        self, mock_crud, mock_service, mock_db, mock_current_user, mock_ownership_list
    ):
        """Test getting ownership list with keyword search"""
        from src.api.v1.assets.ownership import get_ownerships

        mock_crud.search.return_value = {
            "items": mock_ownership_list[:1],
            "total": 1,
            "page": 1,
            "page_size": 10,
            "pages": 1,
        }
        mock_service.get_asset_count.return_value = 0
        mock_service.get_project_count.return_value = 0

        result = get_ownerships(
            current_user=mock_current_user,
            db=mock_db,
            page=1,
            page_size=10,
            keyword="Test",
            is_active=None,
        )

        body = json.loads(result.body.decode())
        assert body["data"]["pagination"]["total"] == 1
        mock_crud.search.assert_called_once()

    @patch("src.api.v1.assets.ownership.ownership_service")
    @patch("src.api.v1.assets.ownership.ownership")
    @pytest.mark.asyncio
    async def test_get_ownerships_with_filters(
        self, mock_crud, mock_service, mock_db, mock_current_user
    ):
        """Test getting ownership list with filters"""
        from src.api.v1.assets.ownership import get_ownerships

        mock_crud.search.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 10,
            "pages": 0,
        }

        result = get_ownerships(
            current_user=mock_current_user,
            db=mock_db,
            page=1,
            page_size=10,
            keyword=None,
            is_active=True,
        )

        body = json.loads(result.body.decode())
        assert body["data"]["pagination"]["total"] == 0

    @patch("src.api.v1.assets.ownership.ownership_service")
    @patch("src.api.v1.assets.ownership.ownership")
    @pytest.mark.asyncio
    async def test_get_ownerships_pagination(
        self, mock_crud, mock_service, mock_db, mock_current_user, mock_ownership_list
    ):
        """Test pagination of ownership list"""
        from src.api.v1.assets.ownership import get_ownerships

        mock_crud.search.return_value = {
            "items": mock_ownership_list,
            "total": 25,
            "page": 2,
            "page_size": 10,
            "pages": 3,
        }
        mock_service.get_asset_count.return_value = 0
        mock_service.get_project_count.return_value = 0

        result = get_ownerships(
            current_user=mock_current_user,
            db=mock_db,
            page=2,
            page_size=10,
            keyword=None,
            is_active=None,
        )

        body = json.loads(result.body.decode())
        pagination = body["data"]["pagination"]
        assert pagination["page"] == 2
        assert pagination["total_pages"] == 3


# ============================================================================
# Test: POST /search - Search Ownerships
# ============================================================================


class TestSearchOwnerships:
    """Tests for POST /api/v1/ownership/search endpoint"""

    @patch("src.api.v1.assets.ownership.ownership_service")
    @patch("src.api.v1.assets.ownership.ownership")
    @pytest.mark.asyncio
    async def test_search_ownerships_success(
        self, mock_crud, mock_service, mock_db, mock_current_user, mock_ownership_list
    ):
        """Test searching ownerships successfully"""
        from src.api.v1.assets.ownership import search_ownerships
        from src.schemas.ownership import OwnershipSearchRequest

        search_params = OwnershipSearchRequest(keyword="Test", page=1, page_size=10)

        mock_crud.search.return_value = {
            "items": mock_ownership_list,
            "total": 3,
            "page": 1,
            "page_size": 10,
            "pages": 1,
        }
        mock_service.get_asset_count.return_value = 3
        mock_service.get_project_count.return_value = 1

        result = search_ownerships(
            db=mock_db, search_params=search_params, current_user=mock_current_user
        )

        body = json.loads(result.body.decode())
        data = body["data"]
        assert data["pagination"]["total"] == 3
        assert len(data["items"]) == 3
        assert data["items"][0]["asset_count"] == 3
        assert data["items"][0]["project_count"] == 1
        mock_crud.search.assert_called_once_with(mock_db, search_params)

    @patch("src.api.v1.assets.ownership.ownership_service")
    @patch("src.api.v1.assets.ownership.ownership")
    @pytest.mark.asyncio
    async def test_search_ownerships_empty_results(
        self, mock_crud, mock_service, mock_db, mock_current_user
    ):
        """Test searching ownerships with no results"""
        from src.api.v1.assets.ownership import search_ownerships
        from src.schemas.ownership import OwnershipSearchRequest

        search_params = OwnershipSearchRequest(
            keyword="Nonexistent", page=1, page_size=10
        )

        mock_crud.search.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 10,
            "pages": 0,
        }

        result = search_ownerships(
            db=mock_db, search_params=search_params, current_user=mock_current_user
        )

        body = json.loads(result.body.decode())
        assert body["data"]["pagination"]["total"] == 0
        assert len(body["data"]["items"]) == 0


# ============================================================================
# Test: GET /statistics/summary - Get Ownership Statistics
# ============================================================================


class TestGetOwnershipStatistics:
    """Tests for GET /api/v1/ownership/statistics/summary endpoint"""

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_get_statistics_success(
        self, mock_service, mock_db, mock_current_user, mock_ownership_list
    ):
        """Test getting ownership statistics successfully"""
        from src.api.v1.assets.ownership import get_ownership_statistics

        mock_service.get_statistics.return_value = {
            "total_count": 10,
            "active_count": 8,
            "inactive_count": 2,
            "recent_created": mock_ownership_list[:3],
        }

        result = get_ownership_statistics(db=mock_db, current_user=mock_current_user)

        assert result.total_count == 10
        assert result.active_count == 8
        assert result.inactive_count == 2
        assert len(result.recent_created) == 3
        mock_service.get_statistics.assert_called_once_with(mock_db)

    @pytest.mark.asyncio
    async def test_get_statistics_empty(self, mock_db, mock_current_user):
        """Test getting ownership statistics with no ownerships"""
        from src.api.v1.assets.ownership import get_ownership_statistics

        with patch("src.api.v1.assets.ownership.ownership_service") as mock_service:
            mock_service.get_statistics.return_value = {
                "total_count": 0,
                "active_count": 0,
                "inactive_count": 0,
                "recent_created": [],
            }

            result = get_ownership_statistics(
                db=mock_db, current_user=mock_current_user
            )

            assert result.total_count == 0
            assert result.active_count == 0
            assert result.inactive_count == 0
            assert len(result.recent_created) == 0


# ============================================================================
# Test: POST /{ownership_id}/toggle-status - Toggle Ownership Status
# ============================================================================


class TestToggleOwnershipStatus:
    """Tests for POST /api/v1/ownership/{ownership_id}/toggle-status endpoint"""

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_toggle_status_success(
        self, mock_service, mock_db, mock_current_user, mock_ownership
    ):
        """Test toggling ownership status successfully"""
        from src.api.v1.assets.ownership import toggle_ownership_status

        mock_ownership.is_active = False
        mock_service.toggle_status.return_value = mock_ownership

        result = toggle_ownership_status(
            db=mock_db, ownership_id="ownership-id-123", current_user=mock_current_user
        )

        assert result.is_active is False
        mock_service.toggle_status.assert_called_once_with(
            mock_db, id="ownership-id-123"
        )

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_toggle_status_not_found(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test toggling status for non-existent ownership"""
        from src.api.v1.assets.ownership import toggle_ownership_status

        mock_service.toggle_status.side_effect = ResourceNotFoundError(
            "权属方",
            "nonexistent-id",
        )

        with pytest.raises(BaseBusinessError) as exc_info:
            toggle_ownership_status(
                db=mock_db,
                ownership_id="nonexistent-id",
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "权属方不存在" in exc_info.value.message

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_toggle_status_exception(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test toggling status with unexpected exception"""
        from src.api.v1.assets.ownership import toggle_ownership_status

        mock_service.toggle_status.side_effect = Exception("Database error")

        with pytest.raises(InternalServerError) as exc_info:
            toggle_ownership_status(
                db=mock_db,
                ownership_id="ownership-id-123",
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 500
        assert "切换状态失败" in exc_info.value.message


# ============================================================================
# Test: GET /{ownership_id}/financial-summary - Get Financial Summary
# ============================================================================


class TestGetOwnershipFinancialSummary:
    """Tests for GET /api/v1/ownership/{ownership_id}/financial-summary endpoint"""

    @patch("src.models.rent_contract.RentLedger")
    @pytest.mark.asyncio
    async def test_get_financial_summary_success(
        self, mock_rent_ledger, mock_db, mock_current_user
    ):
        """Test getting financial summary successfully"""
        from src.api.v1.assets.ownership import get_ownership_financial_summary
        from src.crud.ownership import ownership as real_ownership

        # Add arrears_amount attribute to the mock RentLedger model
        mock_rent_ledger.arrears_amount = MagicMock()

        # Create a mock ownership object with proper name attribute
        mock_ownership_obj = MagicMock()
        mock_ownership_obj.name = "Test Ownership Company"

        # Patch the get method to return our mock object
        real_ownership.get = MagicMock(return_value=mock_ownership_obj)

        # Mock database queries for financial data
        mock_query = MagicMock()

        # Setup scalar return values in order:
        # 1. due_amount, 2. paid_amount, 3. arrears_amount, 4. contract_count, 5. active_contract_count
        call_count = [0]

        def mock_scalar_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return 100000.0  # due_amount
            elif call_count[0] == 2:
                return 80000.0  # paid_amount
            elif call_count[0] == 3:
                return 20000.0  # arrears_amount
            elif call_count[0] == 4:
                return 5  # contract_count
            else:
                return 3  # active_contract_count

        mock_query.scalar.side_effect = mock_scalar_side_effect
        mock_query.filter.return_value = mock_query

        mock_db.query.return_value = mock_query

        result = get_ownership_financial_summary(
            ownership_id="ownership-id-123", db=mock_db, current_user=mock_current_user
        )

        assert result["ownership_id"] == "ownership-id-123"
        assert result["ownership_name"] == "Test Ownership Company"
        assert "financial_summary" in result
        assert "contract_summary" in result
        assert result["financial_summary"]["total_due_amount"] == 100000.0
        assert result["financial_summary"]["total_paid_amount"] == 80000.0
        assert result["financial_summary"]["total_arrears_amount"] == 20000.0

        # Restore original method
        real_ownership.get = (
            real_ownership.get.__wrapped__
            if hasattr(real_ownership.get, "__wrapped__")
            else lambda db, **kwargs: None
        )

    @pytest.mark.asyncio
    async def test_get_financial_summary_not_found(self, mock_db, mock_current_user):
        """Test getting financial summary for non-existent ownership"""
        from src.api.v1.assets.ownership import get_ownership_financial_summary
        from src.crud.ownership import ownership as real_ownership

        # Patch the get method to return None
        real_ownership.get = MagicMock(return_value=None)

        with pytest.raises(BaseBusinessError) as exc_info:
            get_ownership_financial_summary(
                ownership_id="nonexistent-id",
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "不存在" in exc_info.value.message

    @patch("src.models.rent_contract.RentLedger")
    @pytest.mark.asyncio
    async def test_get_financial_summary_no_contracts(
        self, mock_rent_ledger, mock_db, mock_current_user
    ):
        """Test getting financial summary when ownership has no contracts"""
        from src.api.v1.assets.ownership import get_ownership_financial_summary
        from src.crud.ownership import ownership as real_ownership

        # Add arrears_amount attribute to the mock RentLedger model
        mock_rent_ledger.arrears_amount = MagicMock()

        # Create a mock ownership object with proper name attribute
        mock_ownership_obj = MagicMock()
        mock_ownership_obj.name = "Test Ownership Company"

        # Patch the get method to return our mock object
        real_ownership.get = MagicMock(return_value=mock_ownership_obj)

        # Mock query to return zero values
        mock_query = MagicMock()
        call_count = [0]

        def mock_scalar_side_effect():
            call_count[0] += 1
            return 0

        mock_query.scalar.side_effect = mock_scalar_side_effect
        mock_query.filter.return_value = mock_query
        mock_db.query.return_value = mock_query

        result = get_ownership_financial_summary(
            ownership_id="ownership-id-123", db=mock_db, current_user=mock_current_user
        )

        assert result["ownership_id"] == "ownership-id-123"
        assert result["ownership_name"] == "Test Ownership Company"
        assert result["financial_summary"]["total_due_amount"] == 0.0
        assert result["financial_summary"]["total_paid_amount"] == 0.0
        assert result["contract_summary"]["total_contracts"] == 0


# ============================================================================
# Test: Edge Cases and Error Handling
# ============================================================================


class TestOwnershipEdgeCases:
    """Tests for edge cases and error handling"""

    @patch("src.api.v1.assets.ownership.ownership_service")
    @patch("src.api.v1.assets.ownership.ownership")
    @pytest.mark.asyncio
    async def test_get_ownerships_with_zero_count(
        self, mock_crud, mock_service, mock_db, mock_current_user
    ):
        """Test getting ownerships when no ownerships exist"""
        from src.api.v1.assets.ownership import get_ownerships

        mock_crud.search.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 10,
            "pages": 0,
        }

        result = get_ownerships(
            current_user=mock_current_user,
            db=mock_db,
            page=1,
            page_size=10,
            keyword=None,
            is_active=None,
        )

        body = json.loads(result.body.decode())
        data = body["data"]
        assert data["pagination"]["total"] == 0
        assert len(data["items"]) == 0
        assert data["pagination"]["total_pages"] == 0

    @pytest.mark.asyncio
    async def test_create_ownership_with_invalid_code(self, mock_db, mock_current_user):
        """Test creating ownership with invalid code format"""
        from src.schemas.ownership import OwnershipCreate

        # This should fail validation before reaching the endpoint
        with pytest.raises(ValueError):
            OwnershipCreate(name="Test Ownership", code="INVALID_CODE")

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_update_ownership_no_changes(
        self, mock_service, mock_db, mock_current_user, mock_ownership
    ):
        """Test updating ownership with no changes"""
        from src.api.v1.assets.ownership import update_ownership
        from src.schemas.ownership import OwnershipUpdate

        with patch("src.api.v1.assets.ownership.ownership") as mock_crud:
            mock_crud.get.return_value = mock_ownership
            mock_service.update_ownership.return_value = mock_ownership

            update_data = OwnershipUpdate()  # Empty update

            result = update_ownership(
                db=mock_db,
                ownership_id="ownership-id-123",
                ownership_in=update_data,
                current_user=mock_current_user,
            )

            # Should still return the ownership object
            assert result.id == "ownership-id-123"

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_update_projects_with_empty_list(
        self, mock_service, mock_db, mock_current_user, mock_ownership
    ):
        """Test updating ownership projects with empty list"""
        from src.api.v1.assets.ownership import update_ownership_projects

        with patch("src.api.v1.assets.ownership.ownership") as mock_crud:
            mock_crud.get.return_value = mock_ownership
            mock_service.update_related_projects.return_value = None
            mock_service.get_project_count.return_value = 0

            result = update_ownership_projects(
                db=mock_db,
                ownership_id="ownership-id-123",
                project_ids=[],
                current_user=mock_current_user,
            )

            assert result.project_count == 0
            mock_service.update_related_projects.assert_called_once()

    @patch("src.api.v1.assets.ownership.ownership")
    @pytest.mark.asyncio
    async def test_pagination_edge_cases(self, mock_crud, mock_db, mock_current_user):
        """Test pagination edge cases"""
        from src.api.v1.assets.ownership import get_ownerships

        with patch("src.api.v1.assets.ownership.ownership_service") as mock_service:
            # Test with page 1, size 1
            mock_crud.search.return_value = {
                "items": [],
                "total": 0,
                "page": 1,
                "page_size": 1,
                "pages": 0,
            }
            mock_service.get_asset_count.return_value = 0
            mock_service.get_project_count.return_value = 0

            result = get_ownerships(
                current_user=mock_current_user,
                db=mock_db,
                page=1,
                page_size=1,
                keyword=None,
                is_active=None,
            )

            body = json.loads(result.body.decode())
            pagination = body["data"]["pagination"]
            assert pagination["page_size"] == 1
            assert pagination["page"] == 1

    @patch("src.api.v1.assets.ownership.ownership_service")
    @pytest.mark.asyncio
    async def test_search_with_special_characters(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test searching with special characters in keyword"""
        from src.api.v1.assets.ownership import search_ownerships
        from src.schemas.ownership import OwnershipSearchRequest

        with patch("src.api.v1.assets.ownership.ownership") as mock_crud:
            search_params = OwnershipSearchRequest(
                keyword="测试公司 (2024)", page=1, page_size=10
            )

            mock_crud.search.return_value = {
                "items": [],
                "total": 0,
                "page": 1,
                "page_size": 10,
                "pages": 0,
            }

            result = search_ownerships(
                db=mock_db, search_params=search_params, current_user=mock_current_user
            )

            body = json.loads(result.body.decode())
            assert body["data"]["pagination"]["total"] == 0
            mock_crud.search.assert_called_once()

    @patch("src.models.rent_contract.RentLedger")
    @pytest.mark.asyncio
    async def test_financial_summary_payment_rate_calculation(
        self, mock_rent_ledger, mock_db, mock_current_user
    ):
        """Test payment rate calculation in financial summary"""
        from src.api.v1.assets.ownership import get_ownership_financial_summary
        from src.crud.ownership import ownership as real_ownership

        # Add arrears_amount attribute to the mock RentLedger model
        mock_rent_ledger.arrears_amount = MagicMock()

        # Create a mock ownership object with proper name attribute
        mock_ownership_obj = MagicMock()
        mock_ownership_obj.name = "Test Ownership Company"

        # Patch the get method to return our mock object
        real_ownership.get = MagicMock(return_value=mock_ownership_obj)

        mock_query = MagicMock()

        # Mock values: due=100000, paid=80000, arrears=20000, payment_rate should be 80%
        call_count = [0]

        def mock_scalar_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return 100000.0  # due_amount
            elif call_count[0] == 2:
                return 80000.0  # paid_amount
            elif call_count[0] == 3:
                return 20000.0  # arrears_amount
            elif call_count[0] == 4:
                return 5  # contract_count
            else:
                return 3  # active_contract_count

        mock_query.scalar.side_effect = mock_scalar_side_effect
        mock_query.filter.return_value = mock_query
        mock_db.query.return_value = mock_query

        result = get_ownership_financial_summary(
            ownership_id="ownership-id-123", db=mock_db, current_user=mock_current_user
        )

        # Payment rate should be (80000 / 100000) * 100 = 80.0
        assert result["financial_summary"]["payment_rate"] == 80.0

    @patch("src.models.rent_contract.RentLedger")
    @pytest.mark.asyncio
    async def test_financial_summary_zero_due_amount(
        self, mock_rent_ledger, mock_db, mock_current_user
    ):
        """Test payment rate when due amount is zero"""
        from src.api.v1.assets.ownership import get_ownership_financial_summary
        from src.crud.ownership import ownership as real_ownership

        # Add arrears_amount attribute to the mock RentLedger model
        mock_rent_ledger.arrears_amount = MagicMock()

        # Create a mock ownership object with proper name attribute
        mock_ownership_obj = MagicMock()
        mock_ownership_obj.name = "Test Ownership Company"

        # Patch the get method to return our mock object
        real_ownership.get = MagicMock(return_value=mock_ownership_obj)

        mock_query = MagicMock()
        call_count = [0]

        def mock_scalar_side_effect():
            call_count[0] += 1
            return 0

        mock_query.scalar.side_effect = mock_scalar_side_effect
        mock_query.filter.return_value = mock_query
        mock_db.query.return_value = mock_query

        result = get_ownership_financial_summary(
            ownership_id="ownership-id-123", db=mock_db, current_user=mock_current_user
        )

        # Payment rate should be 0 when due amount is 0
        assert result["financial_summary"]["payment_rate"] == 0.0
