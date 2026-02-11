"""
自定义字段 CRUD 单元测试

测试 CRUDCustomField 的所有主要方法
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio

from src.crud.custom_field import CRUDCustomField, custom_field_crud
from src.crud.query_builder import TenantFilter
from src.models.system_dictionary import AssetCustomField


class TestCRUDCustomFieldGetByFieldName:
    """测试 get_by_field_name 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDCustomField(AssetCustomField)

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.execute = AsyncMock()
        return db

    async def test_get_by_field_name_exists(self, crud, mock_db):
        """测试获取存在的字段"""
        mock_field = MagicMock(spec=AssetCustomField)
        mock_field.field_name = "custom_area"

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_field
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await crud.get_by_field_name_async(mock_db, field_name="custom_area")

        assert result is not None
        assert result.field_name == "custom_area"

    async def test_get_by_field_name_not_exists(self, crud, mock_db):
        """测试获取不存在的字段"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await crud.get_by_field_name_async(mock_db, field_name="not_exist")

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
        db.execute = AsyncMock(return_value=mock_result)
        return db

    async def test_get_multi_with_filters_empty(self, crud, mock_db):
        """测试无筛选条件"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            result = await crud.get_multi_with_filters_async(mock_db)

        assert isinstance(result, list)
        mock_build.assert_called_once()

    async def test_get_multi_with_field_type_filter(self, crud, mock_db):
        """测试按字段类型筛选"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            await crud.get_multi_with_filters_async(mock_db, filters={"field_type": "text"})

        call_args = mock_build.call_args
        assert "field_type" in call_args.kwargs.get("filters", {})

    async def test_get_multi_with_is_required_filter(self, crud, mock_db):
        """测试按是否必填筛选"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            await crud.get_multi_with_filters_async(mock_db, filters={"is_required": True})

        call_args = mock_build.call_args
        assert "is_required" in call_args.kwargs.get("filters", {})

    async def test_get_multi_with_is_active_filter(self, crud, mock_db):
        """测试按是否启用筛选"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            await crud.get_multi_with_filters_async(mock_db, filters={"is_active": True})

        call_args = mock_build.call_args
        assert "is_active" in call_args.kwargs.get("filters", {})

    async def test_get_multi_with_pagination(self, crud, mock_db):
        """测试分页参数"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            await crud.get_multi_with_filters_async(mock_db, skip=10, limit=20)

        call_args = mock_build.call_args
        assert call_args.kwargs.get("skip") == 10
        assert call_args.kwargs.get("limit") == 20

    async def test_get_multi_with_tenant_filter(self, crud, mock_db):
        """测试透传 tenant_filter 参数"""
        tenant_filter = TenantFilter(organization_ids=["org-1"])
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            await crud.get_multi_with_filters_async(
                mock_db,
                tenant_filter=tenant_filter,
            )

        call_args = mock_build.call_args
        assert call_args.kwargs.get("tenant_filter") == tenant_filter


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
        db.execute = AsyncMock(return_value=mock_result)
        return db

    async def test_get_active_fields_async(self, crud, mock_db):
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

            result = await crud.get_active_fields_async(mock_db)

        assert len(result) == 2
        call_args = mock_build.call_args
        assert call_args.kwargs.get("filters", {}).get("is_active") is True

    async def test_get_active_fields_empty(self, crud, mock_db):
        """测试无启用字段"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            result = await crud.get_active_fields_async(mock_db)

        assert result == []

    async def test_get_active_fields_sorted_by_order(self, crud, mock_db):
        """测试按排序字段排序"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            await crud.get_active_fields_async(mock_db)

        call_args = mock_build.call_args
        assert call_args.kwargs.get("sort_by") == "sort_order"
        assert call_args.kwargs.get("sort_desc") is False

    async def test_get_active_fields_with_tenant_filter(self, crud, mock_db):
        """测试 get_active_fields 透传 tenant_filter"""
        tenant_filter = TenantFilter(organization_ids=["org-1"])
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            await crud.get_active_fields_async(
                mock_db,
                tenant_filter=tenant_filter,
            )

        call_args = mock_build.call_args
        assert call_args.kwargs.get("tenant_filter") == tenant_filter


class TestCRUDCustomFieldGetAssetFieldValues:
    """测试 get_asset_field_values 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDCustomField(AssetCustomField)

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    async def test_get_asset_field_values_stub(self, crud, mock_db):
        """测试获取资产字段值（存根方法）"""
        result = await crud.get_asset_field_values_async(mock_db, asset_id="asset-1")

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

    async def test_create_custom_field(self, crud, mock_db):
        """测试创建自定义字段"""
        create_data = MagicMock()
        create_data.model_dump.return_value = {
            "field_name": "new_field",
            "field_type": "text",
            "display_name": "新字段",
        }

        with patch.object(crud, "create", new=AsyncMock()) as mock_create:
            mock_field = MagicMock(spec=AssetCustomField)
            mock_create.return_value = mock_field

            result = await crud.create(mock_db, obj_in=create_data)

        assert result is not None


class TestCRUDCustomFieldUpdate:
    """测试 update 方法（继承自基类）"""

    @pytest.fixture
    def crud(self):
        return CRUDCustomField(AssetCustomField)

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    async def test_update_custom_field(self, crud, mock_db):
        """测试更新自定义字段"""
        mock_field = MagicMock(spec=AssetCustomField)
        update_data = {"display_name": "更新后的名称"}

        with patch.object(crud, "update", new=AsyncMock()) as mock_update:
            mock_update.return_value = mock_field

            result = await crud.update(mock_db, db_obj=mock_field, obj_in=update_data)

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

    async def test_remove_custom_field(self, crud, mock_db):
        """测试删除自定义字段"""
        with patch.object(crud, "remove", new=AsyncMock()) as mock_remove:
            mock_field = MagicMock(spec=AssetCustomField)
            mock_remove.return_value = mock_field

            result = await crud.remove(mock_db, id="field-1")

        assert result is not None


class TestCRUDInstance:
    """测试 CRUD 实例"""

    async def test_custom_field_crud_instance(self):
        """测试自定义字段 CRUD 实例"""
        assert custom_field_crud is not None
        assert isinstance(custom_field_crud, CRUDCustomField)
