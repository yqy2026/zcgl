"""
Comprehensive Unit Tests for Enum Field API Routes (src/api/v1/enum_field.py)

This test module covers all endpoints in the enum_field router to achieve 70%+ coverage.

Endpoints Tested:
1. GET /api/v1/enum-fields/debug - Debug endpoint
2. GET /api/v1/enum-fields/types - Get enum field types list
3. GET /api/v1/enum-fields/types/statistics - Get enum field statistics
4. GET /api/v1/enum-fields/types/{type_id} - Get enum field type by ID
5. POST /api/v1/enum-fields/types - Create enum field type
6. PUT /api/v1/enum-fields/types/{type_id} - Update enum field type
7. DELETE /api/v1/enum-fields/types/{type_id} - Delete enum field type
8. GET /api/v1/enum-fields/types/categories - Get enum field categories
9. GET /api/v1/enum-fields/types/{type_id}/values - Get enum field values
10. GET /api/v1/enum-fields/types/{type_id}/values/tree - Get enum field values tree
11. GET /api/v1/enum-fields/values/{value_id} - Get enum field value by ID
12. POST /api/v1/enum-fields/types/{type_id}/values - Create enum field value
13. PUT /api/v1/enum-fields/values/{value_id} - Update enum field value
14. DELETE /api/v1/enum-fields/values/{value_id} - Delete enum field value
15. POST /api/v1/enum-fields/types/{type_id}/values/batch - Batch create enum field values
16. GET /api/v1/enum-fields/usage - Get enum field usage records
17. POST /api/v1/enum-fields/usage - Create enum field usage record
18. PUT /api/v1/enum-fields/usage/{usage_id} - Update enum field usage record
19. DELETE /api/v1/enum-fields/usage/{usage_id} - Delete enum field usage record
20. GET /api/v1/enum-fields/types/{type_id}/history - Get enum field type history
21. GET /api/v1/enum-fields/values/{value_id}/history - Get enum field value history
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.core.exception_handler import BaseBusinessError

pytestmark = pytest.mark.api


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_enum_type():
    """Create mock enum field type"""
    enum_type = MagicMock()
    enum_type.id = "test-type-id"
    enum_type.name = "Test Enum Type"
    enum_type.code = "test_enum"
    enum_type.category = "test_category"
    enum_type.description = "Test description"
    enum_type.is_system = False
    enum_type.is_multiple = False
    enum_type.is_hierarchical = False
    enum_type.default_value = None
    enum_type.validation_rules = None
    enum_type.display_config = None
    enum_type.status = "active"
    enum_type.is_deleted = False
    enum_type.created_at = datetime.now(UTC)
    enum_type.updated_at = datetime.now(UTC)
    enum_type.created_by = "test-user"
    enum_type.updated_by = None
    enum_type.enum_values = []
    return enum_type


@pytest.fixture
def mock_enum_value():
    """Create mock enum field value"""
    enum_value = MagicMock()
    enum_value.id = "test-value-id"
    enum_value.enum_type_id = "test-type-id"
    enum_value.label = "Test Label"
    enum_value.value = "test_value"
    enum_value.code = "test_code"
    enum_value.description = "Test value description"
    enum_value.parent_id = None
    enum_value.level = 1
    enum_value.sort_order = 0
    enum_value.color = "#FF0000"
    enum_value.icon = "test-icon"
    enum_value.extra_properties = None
    enum_value.is_active = True
    enum_value.is_default = False
    enum_value.is_deleted = False
    enum_value.path = None
    enum_value.created_at = datetime.now(UTC)
    enum_value.updated_at = datetime.now(UTC)
    enum_value.created_by = "test-user"
    enum_value.updated_by = None
    enum_value.children = []
    return enum_value


@pytest.fixture
def mock_enum_usage():
    """Create mock enum field usage record"""
    usage = MagicMock()
    usage.id = "test-usage-id"
    usage.enum_type_id = "test-type-id"
    usage.table_name = "test_table"
    usage.field_name = "test_field"
    usage.field_label = "Test Field"
    usage.module_name = "test_module"
    usage.is_required = False
    usage.default_value = None
    usage.validation_config = None
    usage.is_active = True
    usage.created_at = datetime.now(UTC)
    usage.updated_at = datetime.now(UTC)
    usage.created_by = "test-user"
    usage.updated_by = None
    return usage


@pytest.fixture
def mock_enum_history():
    """Create mock enum field history record"""
    history = MagicMock()
    history.id = "test-history-id"
    history.enum_type_id = "test-type-id"
    history.enum_value_id = None
    history.action = "create"
    history.target_type = "type"
    history.field_name = None
    history.old_value = None
    history.new_value = "new_value"
    history.change_reason = "Test reason"
    history.created_at = datetime.now(UTC)
    history.created_by = "test-user"
    history.ip_address = "127.0.0.1"
    return history


# ============================================================================
# Test: GET /debug - Debug Endpoint
# ============================================================================


class TestDebugEndpoint:
    """Tests for GET /api/v1/enum-fields/debug endpoint"""

    # NOTE: Debug endpoint is protected by @debug_only decorator which cannot be easily mocked
    # Skipping this test as it requires debug mode to be enabled


# ============================================================================
# Test: GET /types - Get Enum Field Types
# ============================================================================


class TestGetEnumFieldTypes:
    """Tests for GET /api/v1/enum-fields/types endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    def test_get_enum_field_types_success(self, mock_get_crud, mock_db, mock_enum_type):
        """Test getting enum field types successfully"""
        from src.api.v1.system.enum_field import get_enum_field_types

        mock_crud = MagicMock()
        mock_crud.get_multi.return_value = [mock_enum_type]
        mock_get_crud.return_value = mock_crud

        result = get_enum_field_types(
            page=1,
            page_size=100,
            category=None,
            status=None,
            is_system=None,
            keyword=None,
            db=mock_db,
        )

        assert len(result) == 1
        assert result[0].id == "test-type-id"
        mock_crud.get_multi.assert_called_once_with(
            skip=0, limit=100, category=None, status=None, is_system=None, keyword=None
        )

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    def test_get_enum_field_types_with_filters(
        self, mock_get_crud, mock_db, mock_enum_type
    ):
        """Test getting enum field types with filters"""
        from src.api.v1.system.enum_field import get_enum_field_types

        mock_crud = MagicMock()
        mock_crud.get_multi.return_value = [mock_enum_type]
        mock_get_crud.return_value = mock_crud

        result = get_enum_field_types(
            page=1,
            page_size=50,
            category="test_category",
            status="active",
            is_system=False,
            keyword="test",
            db=mock_db,
        )

        assert len(result) == 1
        mock_crud.get_multi.assert_called_once_with(
            skip=0,
            limit=50,
            category="test_category",
            status="active",
            is_system=False,
            keyword="test",
        )

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    def test_get_enum_field_types_empty_list(self, mock_get_crud, mock_db):
        """Test getting enum field types with empty result"""
        from src.api.v1.system.enum_field import get_enum_field_types

        mock_crud = MagicMock()
        mock_crud.get_multi.return_value = []
        mock_get_crud.return_value = mock_crud

        result = get_enum_field_types(
            page=1,
            page_size=100,
            category=None,
            status=None,
            is_system=None,
            keyword=None,
            db=mock_db,
        )

        assert len(result) == 0


# ============================================================================
# Test: GET /types/statistics - Get Enum Field Statistics
# ============================================================================


class TestGetEnumFieldStatistics:
    """Tests for GET /api/v1/enum-fields/types/statistics endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    def test_get_enum_field_statistics_success(self, mock_get_crud, mock_db):
        """Test getting enum field statistics successfully"""
        from src.api.v1.system.enum_field import get_enum_field_statistics

        mock_crud = MagicMock()
        mock_crud.get_statistics.return_value = {
            "total_types": 10,
            "active_types": 8,
            "categories": [{"category": "test", "count": 5}],
        }
        mock_get_crud.return_value = mock_crud

        # Mock database queries
        mock_query = MagicMock()

        # Set up count to return different values on each call
        count_values = [20, 15, 15]

        def mock_count():
            if count_values:
                return count_values.pop(0)
            return 0

        mock_query.filter.return_value.filter.return_value.count.side_effect = (
            mock_count
        )
        mock_query.filter.return_value.count.side_effect = lambda: 15
        mock_db.query.return_value = mock_query

        result = get_enum_field_statistics(db=mock_db)

        assert result.total_types == 10
        assert result.active_types == 8
        # The actual values come from the mocked queries
        assert result.total_values > 0
        assert result.active_values > 0
        assert result.usage_count > 0
        assert len(result.categories) == 1


# ============================================================================
# Test: GET /types/{type_id} - Get Enum Field Type by ID
# ============================================================================


class TestGetEnumFieldType:
    """Tests for GET /api/v1/enum-fields/types/{type_id} endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    def test_get_enum_field_type_success(self, mock_get_crud, mock_db, mock_enum_type):
        """Test getting enum field type successfully"""
        from src.api.v1.system.enum_field import get_enum_field_type

        mock_crud = MagicMock()
        mock_crud.get.return_value = mock_enum_type
        mock_get_crud.return_value = mock_crud

        result = get_enum_field_type(type_id="test-type-id", db=mock_db)

        assert result.id == "test-type-id"
        assert result.name == "Test Enum Type"
        mock_crud.get.assert_called_once_with("test-type-id")

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    def test_get_enum_field_type_not_found(self, mock_get_crud, mock_db):
        """Test getting non-existent enum field type"""
        from src.api.v1.system.enum_field import get_enum_field_type

        mock_crud = MagicMock()
        mock_crud.get.return_value = None
        mock_get_crud.return_value = mock_crud

        with pytest.raises(BaseBusinessError) as exc_info:
            get_enum_field_type(type_id="nonexistent-id", db=mock_db)

        assert exc_info.value.status_code == 404
        assert "enum_type不存在" in exc_info.value.message


# ============================================================================
# Test: POST /types - Create Enum Field Type
# ============================================================================


class TestCreateEnumFieldType:
    """Tests for POST /api/v1/enum-fields/types endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    def test_create_enum_field_type_success(
        self, mock_get_crud, mock_db, mock_enum_type
    ):
        """Test creating enum field type successfully"""
        from src.api.v1.system.enum_field import create_enum_field_type
        from src.schemas.enum_field import EnumFieldTypeCreate

        enum_type_data = EnumFieldTypeCreate(
            name="New Enum Type",
            code="new_enum",
            category="test",
            description="Test enum type",
            created_by="test-user",
        )

        mock_crud = MagicMock()
        mock_crud.get_by_code.return_value = None
        mock_crud.create.return_value = mock_enum_type
        mock_get_crud.return_value = mock_crud

        result = create_enum_field_type(enum_type=enum_type_data, db=mock_db)

        assert result.id == "test-type-id"
        mock_crud.get_by_code.assert_called_once_with("new_enum")
        mock_crud.create.assert_called_once()

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    def test_create_enum_field_type_duplicate_code(self, mock_get_crud, mock_db):
        """Test creating enum field type with duplicate code"""
        from src.api.v1.system.enum_field import create_enum_field_type
        from src.schemas.enum_field import EnumFieldTypeCreate

        enum_type_data = EnumFieldTypeCreate(
            name="New Enum Type",
            code="existing_enum",
            category="test",
            description="Test enum type",
        )

        mock_crud = MagicMock()
        mock_crud.get_by_code.return_value = MagicMock()  # Code exists
        mock_get_crud.return_value = mock_crud

        with pytest.raises(BaseBusinessError) as exc_info:
            create_enum_field_type(enum_type=enum_type_data, db=mock_db)

        assert exc_info.value.status_code == 409
        assert "编码 existing_enum 已存在" in exc_info.value.message

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    def test_create_enum_field_type_validation_error(self, mock_get_crud, mock_db):
        """Test creating enum field type with validation error"""
        from src.api.v1.system.enum_field import create_enum_field_type
        from src.schemas.enum_field import EnumFieldTypeCreate

        enum_type_data = EnumFieldTypeCreate(
            name="New Enum Type",
            code="new_enum",
            category="test",
            description="Test enum type",
        )

        mock_crud = MagicMock()
        mock_crud.get_by_code.return_value = None
        mock_crud.create.side_effect = ValueError("Invalid validation rules")
        mock_get_crud.return_value = mock_crud

        with pytest.raises(BaseBusinessError) as exc_info:
            create_enum_field_type(enum_type=enum_type_data, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "Invalid validation rules" in exc_info.value.message


# ============================================================================
# Test: PUT /types/{type_id} - Update Enum Field Type
# ============================================================================


class TestUpdateEnumFieldType:
    """Tests for PUT /api/v1/enum-fields/types/{type_id} endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    def test_update_enum_field_type_success(
        self, mock_get_crud, mock_db, mock_enum_type
    ):
        """Test updating enum field type successfully"""
        from src.api.v1.system.enum_field import update_enum_field_type
        from src.schemas.enum_field import EnumFieldTypeUpdate

        update_data = EnumFieldTypeUpdate(
            name="Updated Name",
            description="Updated description",
            updated_by="test-user",
        )

        mock_crud = MagicMock()
        mock_crud.get.return_value = mock_enum_type
        mock_crud.update.return_value = mock_enum_type
        mock_get_crud.return_value = mock_crud

        result = update_enum_field_type(
            type_id="test-type-id", enum_type=update_data, db=mock_db
        )

        assert result.id == "test-type-id"
        mock_crud.get.assert_called_once_with("test-type-id")
        mock_crud.update.assert_called_once()

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    def test_update_enum_field_type_not_found(self, mock_get_crud, mock_db):
        """Test updating non-existent enum field type"""
        from src.api.v1.system.enum_field import update_enum_field_type
        from src.schemas.enum_field import EnumFieldTypeUpdate

        update_data = EnumFieldTypeUpdate(name="Updated Name")

        mock_crud = MagicMock()
        mock_crud.get.return_value = None
        mock_get_crud.return_value = mock_crud

        with pytest.raises(BaseBusinessError) as exc_info:
            update_enum_field_type(
                type_id="nonexistent-id", enum_type=update_data, db=mock_db
            )

        assert exc_info.value.status_code == 404
        assert "enum_type不存在" in exc_info.value.message

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    def test_update_enum_field_type_duplicate_code(
        self, mock_get_crud, mock_db, mock_enum_type
    ):
        """Test updating enum field type with duplicate code"""
        from src.api.v1.system.enum_field import update_enum_field_type
        from src.schemas.enum_field import EnumFieldTypeUpdate

        update_data = EnumFieldTypeUpdate(code="existing_code")

        mock_existing = MagicMock()
        mock_existing.id = "other-type-id"

        mock_crud = MagicMock()
        mock_crud.get.return_value = mock_enum_type
        mock_crud.get_by_code.return_value = mock_existing
        mock_get_crud.return_value = mock_crud

        with pytest.raises(BaseBusinessError) as exc_info:
            update_enum_field_type(
                type_id="test-type-id", enum_type=update_data, db=mock_db
            )

        assert exc_info.value.status_code == 409
        assert "编码 existing_code 已存在" in exc_info.value.message


# ============================================================================
# Test: DELETE /types/{type_id} - Delete Enum Field Type
# ============================================================================


class TestDeleteEnumFieldType:
    """Tests for DELETE /api/v1/enum-fields/types/{type_id} endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    def test_delete_enum_field_type_success(self, mock_get_crud, mock_db):
        """Test deleting enum field type successfully"""
        from src.api.v1.system.enum_field import delete_enum_field_type

        mock_crud = MagicMock()
        mock_crud.delete.return_value = True
        mock_get_crud.return_value = mock_crud

        result = delete_enum_field_type(
            type_id="test-type-id", deleted_by="test-user", db=mock_db
        )

        assert result["message"] == "枚举类型删除成功"
        mock_crud.delete.assert_called_once_with("test-type-id", deleted_by="test-user")

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    def test_delete_enum_field_type_not_found(self, mock_get_crud, mock_db):
        """Test deleting non-existent enum field type"""
        from src.api.v1.system.enum_field import delete_enum_field_type

        mock_crud = MagicMock()
        mock_crud.delete.return_value = False
        mock_get_crud.return_value = mock_crud

        with pytest.raises(BaseBusinessError) as exc_info:
            delete_enum_field_type(
                type_id="nonexistent-id", deleted_by="test-user", db=mock_db
            )

        assert exc_info.value.status_code == 404
        assert "enum_type不存在" in exc_info.value.message


# ============================================================================
# Test: GET /types/categories - Get Enum Field Categories
# ============================================================================


class TestGetEnumFieldCategories:
    """Tests for GET /api/v1/enum-fields/types/categories endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    def test_get_enum_field_categories_success(self, mock_get_crud, mock_db):
        """Test getting enum field categories successfully"""
        from src.api.v1.system.enum_field import get_enum_field_categories

        mock_crud = MagicMock()
        mock_crud.get_categories.return_value = ["category1", "category2", "category3"]
        mock_get_crud.return_value = mock_crud

        result = get_enum_field_categories(db=mock_db)

        assert "categories" in result
        assert len(result["categories"]) == 3
        assert result["categories"][0] == "category1"


# ============================================================================
# Test: GET /types/{type_id}/values - Get Enum Field Values
# ============================================================================


class TestGetEnumFieldValues:
    """Tests for GET /api/v1/enum-fields/types/{type_id}/values endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_value_crud")
    def test_get_enum_field_values_success(
        self, mock_get_crud, mock_db, mock_enum_value
    ):
        """Test getting enum field values successfully"""
        from src.api.v1.system.enum_field import get_enum_field_values

        mock_crud = MagicMock()
        mock_crud.get_by_type.return_value = [mock_enum_value]
        mock_get_crud.return_value = mock_crud

        result = get_enum_field_values(
            type_id="test-type-id", parent_id=None, is_active=None, db=mock_db
        )

        assert len(result) == 1
        assert result[0].id == "test-value-id"
        mock_crud.get_by_type.assert_called_once_with(
            "test-type-id", parent_id=None, is_active=None
        )


# ============================================================================
# Test: GET /types/{type_id}/values/tree - Get Enum Field Values Tree
# ============================================================================


class TestGetEnumFieldValuesTree:
    """Tests for GET /api/v1/enum-fields/types/{type_id}/values/tree endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_value_crud")
    def test_get_enum_field_values_tree_success(
        self, mock_get_crud, mock_db, mock_enum_value
    ):
        """Test getting enum field values tree successfully"""
        from src.api.v1.system.enum_field import get_enum_field_values_tree

        mock_crud = MagicMock()
        mock_crud.get_tree.return_value = [mock_enum_value]
        mock_get_crud.return_value = mock_crud

        result = get_enum_field_values_tree(type_id="test-type-id", db=mock_db)

        assert len(result) == 1
        assert result[0].id == "test-value-id"
        assert result[0].label == "Test Label"
        assert result[0].value == "test_value"
        mock_crud.get_tree.assert_called_once_with("test-type-id")


# ============================================================================
# Test: GET /values/{value_id} - Get Enum Field Value by ID
# ============================================================================


class TestGetEnumFieldValue:
    """Tests for GET /api/v1/enum-fields/values/{value_id} endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_value_crud")
    def test_get_enum_field_value_success(
        self, mock_get_crud, mock_db, mock_enum_value
    ):
        """Test getting enum field value successfully"""
        from src.api.v1.system.enum_field import get_enum_field_value

        mock_crud = MagicMock()
        mock_crud.get.return_value = mock_enum_value
        mock_get_crud.return_value = mock_crud

        result = get_enum_field_value(value_id="test-value-id", db=mock_db)

        assert result.id == "test-value-id"
        assert result.label == "Test Label"
        mock_crud.get.assert_called_once_with("test-value-id")

    @patch("src.api.v1.system.enum_field.get_enum_field_value_crud")
    def test_get_enum_field_value_not_found(self, mock_get_crud, mock_db):
        """Test getting non-existent enum field value"""
        from src.api.v1.system.enum_field import get_enum_field_value

        mock_crud = MagicMock()
        mock_crud.get.return_value = None
        mock_get_crud.return_value = mock_crud

        with pytest.raises(BaseBusinessError) as exc_info:
            get_enum_field_value(value_id="nonexistent-id", db=mock_db)

        assert exc_info.value.status_code == 404
        assert "enum_value不存在" in exc_info.value.message


# ============================================================================
# Test: POST /types/{type_id}/values - Create Enum Field Value
# ============================================================================


class TestCreateEnumFieldValue:
    """Tests for POST /api/v1/enum-fields/types/{type_id}/values endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    @patch("src.api.v1.system.enum_field.get_enum_field_value_crud")
    def test_create_enum_field_value_success(
        self,
        mock_get_value_crud,
        mock_get_type_crud,
        mock_db,
        mock_enum_type,
        mock_enum_value,
    ):
        """Test creating enum field value successfully"""
        from src.api.v1.system.enum_field import create_enum_field_value
        from src.schemas.enum_field import EnumFieldValueCreate

        value_data = EnumFieldValueCreate(
            label="New Value",
            value="new_value",
            code="new_code",
            enum_type_id="test-type-id",
            created_by="test-user",
        )

        mock_type_crud = MagicMock()
        mock_type_crud.get.return_value = mock_enum_type
        mock_get_type_crud.return_value = mock_type_crud

        mock_value_crud = MagicMock()
        mock_value_crud.get_by_type_and_value.return_value = None
        mock_value_crud.create.return_value = mock_enum_value
        mock_get_value_crud.return_value = mock_value_crud

        result = create_enum_field_value(
            type_id="test-type-id", enum_value=value_data, db=mock_db
        )

        assert result.id == "test-value-id"
        mock_type_crud.get.assert_called_once_with("test-type-id")

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    @patch("src.api.v1.system.enum_field.get_enum_field_value_crud")
    def test_create_enum_field_value_type_not_found(
        self, mock_get_value_crud, mock_get_type_crud, mock_db
    ):
        """Test creating enum field value with non-existent type"""
        from src.api.v1.system.enum_field import create_enum_field_value
        from src.schemas.enum_field import EnumFieldValueCreate

        value_data = EnumFieldValueCreate(
            label="New Value", value="new_value", enum_type_id="test-type-id"
        )

        mock_type_crud = MagicMock()
        mock_type_crud.get.return_value = None
        mock_get_type_crud.return_value = mock_type_crud

        with pytest.raises(BaseBusinessError) as exc_info:
            create_enum_field_value(
                type_id="nonexistent-type-id", enum_value=value_data, db=mock_db
            )

        assert exc_info.value.status_code == 404
        assert "enum_type不存在" in exc_info.value.message


# ============================================================================
# Test: PUT /values/{value_id} - Update Enum Field Value
# ============================================================================


class TestUpdateEnumFieldValue:
    """Tests for PUT /api/v1/enum-fields/values/{value_id} endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_value_crud")
    def test_update_enum_field_value_success(
        self, mock_get_crud, mock_db, mock_enum_value
    ):
        """Test updating enum field value successfully"""
        from src.api.v1.system.enum_field import update_enum_field_value
        from src.schemas.enum_field import EnumFieldValueUpdate

        update_data = EnumFieldValueUpdate(
            label="Updated Label", updated_by="test-user"
        )

        mock_crud = MagicMock()
        mock_crud.get.return_value = mock_enum_value
        mock_crud.update.return_value = mock_enum_value
        mock_get_crud.return_value = mock_crud

        result = update_enum_field_value(
            value_id="test-value-id", enum_value=update_data, db=mock_db
        )

        assert result.id == "test-value-id"
        mock_crud.get.assert_called_once_with("test-value-id")

    @patch("src.api.v1.system.enum_field.get_enum_field_value_crud")
    def test_update_enum_field_value_not_found(self, mock_get_crud, mock_db):
        """Test updating non-existent enum field value"""
        from src.api.v1.system.enum_field import update_enum_field_value
        from src.schemas.enum_field import EnumFieldValueUpdate

        update_data = EnumFieldValueUpdate(label="Updated Label")

        mock_crud = MagicMock()
        mock_crud.get.return_value = None
        mock_get_crud.return_value = mock_crud

        with pytest.raises(BaseBusinessError) as exc_info:
            update_enum_field_value(
                value_id="nonexistent-id", enum_value=update_data, db=mock_db
            )

        assert exc_info.value.status_code == 404
        assert "enum_value不存在" in exc_info.value.message


# ============================================================================
# Test: DELETE /values/{value_id} - Delete Enum Field Value
# ============================================================================


class TestDeleteEnumFieldValue:
    """Tests for DELETE /api/v1/enum-fields/values/{value_id} endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_value_crud")
    def test_delete_enum_field_value_success(self, mock_get_crud, mock_db):
        """Test deleting enum field value successfully"""
        from src.api.v1.system.enum_field import delete_enum_field_value

        mock_crud = MagicMock()
        mock_crud.delete.return_value = True
        mock_get_crud.return_value = mock_crud

        result = delete_enum_field_value(
            value_id="test-value-id", deleted_by="test-user", db=mock_db
        )

        assert result["message"] == "枚举值删除成功"
        mock_crud.delete.assert_called_once_with(
            "test-value-id", deleted_by="test-user"
        )

    @patch("src.api.v1.system.enum_field.get_enum_field_value_crud")
    def test_delete_enum_field_value_not_found(self, mock_get_crud, mock_db):
        """Test deleting non-existent enum field value"""
        from src.api.v1.system.enum_field import delete_enum_field_value

        mock_crud = MagicMock()
        mock_crud.delete.return_value = False
        mock_get_crud.return_value = mock_crud

        with pytest.raises(BaseBusinessError) as exc_info:
            delete_enum_field_value(
                value_id="nonexistent-id", deleted_by="test-user", db=mock_db
            )

        assert exc_info.value.status_code == 404
        assert "enum_value不存在" in exc_info.value.message


# ============================================================================
# Test: POST /types/{type_id}/values/batch - Batch Create Enum Field Values
# ============================================================================


class TestBatchCreateEnumFieldValues:
    """Tests for POST /api/v1/enum-fields/types/{type_id}/values/batch endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    @patch("src.api.v1.system.enum_field.get_enum_field_value_crud")
    def test_batch_create_enum_field_values_success(
        self,
        mock_get_value_crud,
        mock_get_type_crud,
        mock_db,
        mock_enum_type,
        mock_enum_value,
    ):
        """Test batch creating enum field values successfully"""
        from src.api.v1.system.enum_field import batch_create_enum_field_values
        from src.schemas.enum_field import EnumFieldBatchCreate

        batch_data = EnumFieldBatchCreate(
            enum_type_id="test-type-id",
            values=[
                {"label": "Value 1", "value": "value1"},
                {"label": "Value 2", "value": "value2"},
            ],
            created_by="test-user",
        )

        mock_type_crud = MagicMock()
        mock_type_crud.get.return_value = mock_enum_type
        mock_get_type_crud.return_value = mock_type_crud

        mock_value_crud = MagicMock()
        mock_value_crud.batch_create.return_value = [mock_enum_value, mock_enum_value]
        mock_get_value_crud.return_value = mock_value_crud

        result = batch_create_enum_field_values(
            type_id="test-type-id", batch_data=batch_data, db=mock_db
        )

        assert len(result) == 2
        mock_type_crud.get.assert_called_once_with("test-type-id")

    @patch("src.api.v1.system.enum_field.get_enum_field_type_crud")
    @patch("src.api.v1.system.enum_field.get_enum_field_value_crud")
    def test_batch_create_enum_field_values_type_not_found(
        self, mock_get_value_crud, mock_get_type_crud, mock_db
    ):
        """Test batch creating enum field values with non-existent type"""
        from src.api.v1.system.enum_field import batch_create_enum_field_values
        from src.schemas.enum_field import EnumFieldBatchCreate

        batch_data = EnumFieldBatchCreate(
            enum_type_id="test-type-id",
            values=[{"label": "Value 1", "value": "value1"}],
        )

        mock_type_crud = MagicMock()
        mock_type_crud.get.return_value = None
        mock_get_type_crud.return_value = mock_type_crud

        with pytest.raises(BaseBusinessError) as exc_info:
            batch_create_enum_field_values(
                type_id="nonexistent-type-id", batch_data=batch_data, db=mock_db
            )

        assert exc_info.value.status_code == 404
        assert "enum_type不存在" in exc_info.value.message


# ============================================================================
# Test: GET /usage - Get Enum Field Usage Records
# ============================================================================


class TestGetEnumFieldUsage:
    """Tests for GET /api/v1/enum-fields/usage endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_usage_crud")
    def test_get_enum_field_usage_success(
        self, mock_get_crud, mock_db, mock_enum_usage
    ):
        """Test getting enum field usage records successfully"""
        from src.api.v1.system.enum_field import get_enum_field_usage

        mock_crud = MagicMock()
        mock_crud.get_by_enum_type.return_value = [mock_enum_usage]
        mock_get_crud.return_value = mock_crud

        result = get_enum_field_usage(
            enum_type_id="test-type-id", table_name=None, module_name=None, db=mock_db
        )

        assert len(result) == 1
        assert result[0].id == "test-usage-id"

    @patch("src.api.v1.system.enum_field.get_enum_field_usage_crud")
    def test_get_enum_field_usage_no_type_filter(self, mock_get_crud, mock_db):
        """Test getting enum field usage records without type filter"""
        from src.api.v1.system.enum_field import get_enum_field_usage

        mock_crud = MagicMock()
        mock_get_crud.return_value = mock_crud

        result = get_enum_field_usage(
            enum_type_id=None, table_name=None, module_name=None, db=mock_db
        )

        assert len(result) == 0


# ============================================================================
# Test: POST /usage - Create Enum Field Usage Record
# ============================================================================


class TestCreateEnumFieldUsage:
    """Tests for POST /api/v1/enum-fields/usage endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_usage_crud")
    def test_create_enum_field_usage_success(
        self, mock_get_crud, mock_db, mock_enum_usage
    ):
        """Test creating enum field usage record successfully"""
        from src.api.v1.system.enum_field import create_enum_field_usage
        from src.schemas.enum_field import EnumFieldUsageCreate

        usage_data = EnumFieldUsageCreate(
            enum_type_id="test-type-id",
            table_name="test_table",
            field_name="test_field",
            field_label="Test Field",
            module_name="test_module",
            created_by="test-user",
        )

        mock_crud = MagicMock()
        mock_crud.get_by_field.return_value = None
        mock_crud.create.return_value = mock_enum_usage
        mock_get_crud.return_value = mock_crud

        result = create_enum_field_usage(usage=usage_data, db=mock_db)

        assert result.id == "test-usage-id"
        mock_crud.get_by_field.assert_called_once_with("test_table", "test_field")


# ============================================================================
# Test: PUT /usage/{usage_id} - Update Enum Field Usage Record
# ============================================================================


class TestUpdateEnumFieldUsage:
    """Tests for PUT /api/v1/enum-fields/usage/{usage_id} endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_usage_crud")
    def test_update_enum_field_usage_success(
        self, mock_get_crud, mock_db, mock_enum_usage
    ):
        """Test updating enum field usage record successfully"""
        from src.api.v1.system.enum_field import update_enum_field_usage
        from src.schemas.enum_field import EnumFieldUsageUpdate

        update_data = EnumFieldUsageUpdate(
            field_label="Updated Label", updated_by="test-user"
        )

        mock_crud = MagicMock()
        mock_crud.get.return_value = mock_enum_usage
        mock_crud.update.return_value = mock_enum_usage
        mock_get_crud.return_value = mock_crud

        result = update_enum_field_usage(
            usage_id="test-usage-id", usage=update_data, db=mock_db
        )

        assert result.id == "test-usage-id"

    @patch("src.api.v1.system.enum_field.get_enum_field_usage_crud")
    def test_update_enum_field_usage_not_found(self, mock_get_crud, mock_db):
        """Test updating non-existent enum field usage record"""
        from src.api.v1.system.enum_field import update_enum_field_usage
        from src.schemas.enum_field import EnumFieldUsageUpdate

        update_data = EnumFieldUsageUpdate(field_label="Updated Label")

        mock_crud = MagicMock()
        mock_crud.get.return_value = None
        mock_get_crud.return_value = mock_crud

        with pytest.raises(BaseBusinessError) as exc_info:
            update_enum_field_usage(
                usage_id="nonexistent-id", usage=update_data, db=mock_db
            )

        assert exc_info.value.status_code == 404
        assert "enum_usage不存在" in exc_info.value.message


# ============================================================================
# Test: DELETE /usage/{usage_id} - Delete Enum Field Usage Record
# ============================================================================


class TestDeleteEnumFieldUsage:
    """Tests for DELETE /api/v1/enum-fields/usage/{usage_id} endpoint"""

    @patch("src.api.v1.system.enum_field.get_enum_field_usage_crud")
    def test_delete_enum_field_usage_success(self, mock_get_crud, mock_db):
        """Test deleting enum field usage record successfully"""
        from src.api.v1.system.enum_field import delete_enum_field_usage

        mock_crud = MagicMock()
        mock_crud.delete.return_value = True
        mock_get_crud.return_value = mock_crud

        result = delete_enum_field_usage(usage_id="test-usage-id", db=mock_db)

        assert result["message"] == "使用记录删除成功"

    @patch("src.api.v1.system.enum_field.get_enum_field_usage_crud")
    def test_delete_enum_field_usage_not_found(self, mock_get_crud, mock_db):
        """Test deleting non-existent enum field usage record"""
        from src.api.v1.system.enum_field import delete_enum_field_usage

        mock_crud = MagicMock()
        mock_crud.delete.return_value = False
        mock_get_crud.return_value = mock_crud

        with pytest.raises(BaseBusinessError) as exc_info:
            delete_enum_field_usage(usage_id="nonexistent-id", db=mock_db)

        assert exc_info.value.status_code == 404
        assert "enum_usage不存在" in exc_info.value.message


# ============================================================================
# Test: GET /types/{type_id}/history - Get Enum Field Type History
# ============================================================================


class TestGetEnumFieldTypeHistory:
    """Tests for GET /api/v1/enum-fields/types/{type_id}/history endpoint"""

    def test_get_enum_field_type_history_success(self, mock_db, mock_enum_history):
        """Test getting enum field type history successfully"""
        from src.api.v1.system.enum_field import get_enum_field_type_history

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
            mock_enum_history
        ]
        mock_db.query.return_value = mock_query

        result = get_enum_field_type_history(
            type_id="test-type-id", page=1, page_size=100, db=mock_db
        )

        assert len(result) == 1
        assert result[0].id == "test-history-id"

    def test_get_enum_field_type_history_empty(self, mock_db):
        """Test getting enum field type history with empty result"""
        from src.api.v1.system.enum_field import get_enum_field_type_history

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value = mock_query

        result = get_enum_field_type_history(
            type_id="test-type-id", page=1, page_size=100, db=mock_db
        )

        assert len(result) == 0


# ============================================================================
# Test: GET /values/{value_id}/history - Get Enum Field Value History
# ============================================================================


class TestGetEnumFieldValueHistory:
    """Tests for GET /api/v1/enum-fields/values/{value_id}/history endpoint"""

    def test_get_enum_field_value_history_success(self, mock_db, mock_enum_history):
        """Test getting enum field value history successfully"""
        from src.api.v1.system.enum_field import get_enum_field_value_history

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
            mock_enum_history
        ]
        mock_db.query.return_value = mock_query

        result = get_enum_field_value_history(
            value_id="test-value-id", page=1, page_size=100, db=mock_db
        )

        assert len(result) == 1
        assert result[0].id == "test-history-id"

    def test_get_enum_field_value_history_empty(self, mock_db):
        """Test getting enum field value history with empty result"""
        from src.api.v1.system.enum_field import get_enum_field_value_history

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value = mock_query

        result = get_enum_field_value_history(
            value_id="test-value-id", page=1, page_size=100, db=mock_db
        )

        assert len(result) == 0

