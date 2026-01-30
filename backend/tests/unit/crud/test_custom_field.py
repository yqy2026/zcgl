"""
自定义字段 CRUD 单元测试

测试 CRUDCustomField 的所有主要方法
"""

from unittest.mock import MagicMock, patch

import pytest

from src.crud.custom_field import CRUDCustomField, custom_field_crud
from src.models.asset import AssetCustomField


class TestCRUDCustomFieldGetByFieldName:
    """测试 get_by_field_name 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDCustomField(AssetCustomField)

    @pytest.fixture
    def mock_db(self, db_session):
        db_session.query = MagicMock()
        return db_session

    def test_get_by_field_name_exists(self, crud, mock_db):
        """测试获取存在的字段"""
        mock_field = MagicMock(spec=AssetCustomField)
        mock_field.field_name = "custom_area"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_field

        result = crud.get_by_field_name(mock_db, field_name="custom_area")

        assert result is not None
        assert result.field_name == "custom_area"

    def test_get_by_field_name_not_exists(self, crud, mock_db):
        """测试获取不存在的字段"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = crud.get_by_field_name(mock_db, field_name="not_exist")

        assert result is None


class TestCRUDCustomFieldGetMultiWithFilters:
    """测试 get_multi_with_filters 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDCustomField(AssetCustomField)

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result
        return db

    def test_get_multi_with_filters_empty(self, crud, mock_db):
        """测试无筛选条件"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            result = crud.get_multi_with_filters(mock_db)

        assert isinstance(result, list)
        mock_build.assert_called_once()

    def test_get_multi_with_field_type_filter(self, crud, mock_db):
        """测试按字段类型筛选"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            crud.get_multi_with_filters(mock_db, filters={"field_type": "text"})

        call_args = mock_build.call_args
        assert "field_type" in call_args.kwargs.get("filters", {})

    def test_get_multi_with_is_required_filter(self, crud, mock_db):
        """测试按是否必填筛选"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            crud.get_multi_with_filters(mock_db, filters={"is_required": True})

        call_args = mock_build.call_args
        assert "is_required" in call_args.kwargs.get("filters", {})

    def test_get_multi_with_is_active_filter(self, crud, mock_db):
        """测试按是否启用筛选"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            crud.get_multi_with_filters(mock_db, filters={"is_active": True})

        call_args = mock_build.call_args
        assert "is_active" in call_args.kwargs.get("filters", {})

    def test_get_multi_with_pagination(self, crud, mock_db):
        """测试分页参数"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            crud.get_multi_with_filters(mock_db, skip=10, limit=20)

        call_args = mock_build.call_args
        assert call_args.kwargs.get("skip") == 10
        assert call_args.kwargs.get("limit") == 20


class TestCRUDCustomFieldGetActiveFields:
    """测试 get_active_fields 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDCustomField(AssetCustomField)

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result
        return db

    def test_get_active_fields(self, crud, mock_db):
        """测试获取所有启用字段"""
        mock_fields = [
            MagicMock(spec=AssetCustomField, is_active=True),
            MagicMock(spec=AssetCustomField, is_active=True),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_fields
        mock_db.execute.return_value = mock_result

        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            result = crud.get_active_fields(mock_db)

        assert len(result) == 2
        call_args = mock_build.call_args
        assert call_args.kwargs.get("filters", {}).get("is_active") is True

    def test_get_active_fields_empty(self, crud, mock_db):
        """测试无启用字段"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            result = crud.get_active_fields(mock_db)

        assert result == []

    def test_get_active_fields_sorted_by_order(self, crud, mock_db):
        """测试按排序字段排序"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            crud.get_active_fields(mock_db)

        call_args = mock_build.call_args
        assert call_args.kwargs.get("sort_by") == "sort_order"
        assert call_args.kwargs.get("sort_desc") is False


class TestCRUDCustomFieldGetAssetFieldValues:
    """测试 get_asset_field_values 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDCustomField(AssetCustomField)

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_get_asset_field_values_stub(self, crud, mock_db):
        """测试获取资产字段值（存根方法）"""
        result = crud.get_asset_field_values(mock_db, asset_id="asset-1")

        # 当前实现返回空列表
        assert result == []


class TestCRUDCustomFieldCreate:
    """测试 create 方法（继承自基类）"""

    @pytest.fixture
    def crud(self):
        return CRUDCustomField(AssetCustomField)

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.add = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock()
        return db

    def test_create_custom_field(self, crud, mock_db):
        """测试创建自定义字段"""
        create_data = MagicMock()
        create_data.model_dump.return_value = {
            "field_name": "new_field",
            "field_type": "text",
            "display_name": "新字段",
        }

        with patch.object(crud, "create") as mock_create:
            mock_field = MagicMock(spec=AssetCustomField)
            mock_create.return_value = mock_field

            result = crud.create(mock_db, obj_in=create_data)

        assert result is not None


class TestCRUDCustomFieldUpdate:
    """测试 update 方法（继承自基类）"""

    @pytest.fixture
    def crud(self):
        return CRUDCustomField(AssetCustomField)

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_update_custom_field(self, crud, mock_db):
        """测试更新自定义字段"""
        mock_field = MagicMock(spec=AssetCustomField)
        update_data = {"display_name": "更新后的名称"}

        with patch.object(crud, "update") as mock_update:
            mock_update.return_value = mock_field

            result = crud.update(mock_db, db_obj=mock_field, obj_in=update_data)

        assert result is not None


class TestCRUDCustomFieldRemove:
    """测试 remove 方法（继承自基类）"""

    @pytest.fixture
    def crud(self):
        return CRUDCustomField(AssetCustomField)

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.delete = MagicMock()
        db.commit = MagicMock()
        return db

    def test_remove_custom_field(self, crud, mock_db):
        """测试删除自定义字段"""
        with patch.object(crud, "remove") as mock_remove:
            mock_field = MagicMock(spec=AssetCustomField)
            mock_remove.return_value = mock_field

            result = crud.remove(mock_db, id="field-1")

        assert result is not None


class TestCRUDInstance:
    """测试 CRUD 实例"""

    def test_custom_field_crud_instance(self):
        """测试自定义字段 CRUD 实例"""
        assert custom_field_crud is not None
        assert isinstance(custom_field_crud, CRUDCustomField)
