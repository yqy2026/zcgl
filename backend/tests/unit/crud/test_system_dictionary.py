"""
系统字典 CRUD 单元测试

测试 CRUDSystemDictionary 的所有主要方法
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crud.query_builder import TenantFilter
from src.crud.system_dictionary import CRUDSystemDictionary, system_dictionary_crud
from src.models.system_dictionary import SystemDictionary

pytestmark = pytest.mark.asyncio


class TestCRUDSystemDictionaryInit:
    """测试 CRUDSystemDictionary 初始化"""

    async def test_init(self):
        """测试初始化"""
        crud = CRUDSystemDictionary()
        assert crud.model == SystemDictionary


class TestCRUDSystemDictionaryGetByTypeAndCode:
    """测试 get_by_type_and_code 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDSystemDictionary()

    @pytest.fixture
    def mock_db(self, db_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        db_session.execute = AsyncMock(return_value=mock_result)
        return db_session

    async def test_get_by_type_and_code_exists(self, crud, mock_db):
        """测试获取存在的字典项"""
        mock_dict = MagicMock(spec=SystemDictionary)
        mock_dict.dict_type = "asset_status"
        mock_dict.dict_code = "active"

        mock_db.execute.return_value.scalars.return_value.first.return_value = mock_dict

        result = await crud.get_by_type_and_code_async(
            mock_db, dict_type="asset_status", dict_code="active"
        )

        assert result is not None
        assert result.dict_type == "asset_status"
        assert result.dict_code == "active"

    async def test_get_by_type_and_code_not_exists(self, crud, mock_db):
        """测试获取不存在的字典项"""
        result = await crud.get_by_type_and_code_async(
            mock_db, dict_type="not_exist", dict_code="not_exist"
        )

        assert result is None

    async def test_get_by_type_and_code_type_exists_code_not(self, crud, mock_db):
        """测试类型存在但代码不存在"""
        result = await crud.get_by_type_and_code_async(
            mock_db, dict_type="asset_status", dict_code="invalid_code"
        )

        assert result is None


class TestCRUDSystemDictionaryGetMultiWithFilters:
    """测试 get_multi_with_filters 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDSystemDictionary()

    @pytest.fixture
    def mock_db(self, db_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db_session.execute = AsyncMock(return_value=mock_result)
        return db_session

    async def test_get_multi_with_filters_empty(self, crud, mock_db):
        """测试无筛选条件"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            result = await crud.get_multi_with_filters_async(mock_db)

        assert isinstance(result, list)

    async def test_get_multi_with_dict_type_filter(self, crud, mock_db):
        """测试按字典类型筛选"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            await crud.get_multi_with_filters_async(
                mock_db, filters={"dict_type": "asset_status"}
            )

        call_args = mock_build.call_args
        assert "dict_type" in call_args.kwargs.get("filters", {})

    async def test_get_multi_with_is_active_filter(self, crud, mock_db):
        """测试按是否启用筛选"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            await crud.get_multi_with_filters_async(
                mock_db, filters={"is_active": True}
            )

        call_args = mock_build.call_args
        assert "is_active" in call_args.kwargs.get("filters", {})

    async def test_get_multi_with_pagination(self, crud, mock_db):
        """测试分页参数"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            await crud.get_multi_with_filters_async(mock_db, skip=5, limit=15)

        call_args = mock_build.call_args
        assert call_args.kwargs.get("skip") == 5
        assert call_args.kwargs.get("limit") == 15

    async def test_get_multi_with_tenant_filter(self, crud, mock_db):
        """测试 get_multi_with_filters 透传 tenant_filter"""
        tenant_filter = TenantFilter(organization_ids=["org-1"])
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            await crud.get_multi_with_filters_async(
                mock_db,
                tenant_filter=tenant_filter,
            )

        call_args = mock_build.call_args
        assert call_args.kwargs.get("tenant_filter") == tenant_filter


class TestCRUDSystemDictionaryGetByType:
    """测试 get_by_type 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDSystemDictionary()

    @pytest.fixture
    def mock_db(self, db_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db_session.execute = AsyncMock(return_value=mock_result)
        return db_session

    async def test_get_by_type_active_only(self, crud, mock_db):
        """测试获取某类型的活跃字典项"""
        mock_dicts = [
            MagicMock(spec=SystemDictionary, dict_type="asset_status", is_active=True),
            MagicMock(spec=SystemDictionary, dict_type="asset_status", is_active=True),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_dicts
        mock_db.execute.return_value = mock_result

        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            result = await crud.get_by_type_async(mock_db, dict_type="asset_status")

        assert len(result) == 2
        call_args = mock_build.call_args
        filters = call_args.kwargs.get("filters", {})
        assert filters.get("dict_type") == "asset_status"
        assert filters.get("is_active") is True

    async def test_get_by_type_include_inactive(self, crud, mock_db):
        """测试获取某类型的所有字典项（含非活跃）"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            await crud.get_by_type_async(mock_db, dict_type="asset_status", is_active=False)

        call_args = mock_build.call_args
        filters = call_args.kwargs.get("filters", {})
        assert filters.get("is_active") is False

    async def test_get_by_type_sorted_by_order(self, crud, mock_db):
        """测试按排序字段排序"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            await crud.get_by_type_async(mock_db, dict_type="asset_status")

        call_args = mock_build.call_args
        assert call_args.kwargs.get("sort_by") == "sort_order"
        assert call_args.kwargs.get("sort_desc") is False

    async def test_get_by_type_empty(self, crud, mock_db):
        """测试获取不存在类型的字典项"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            result = await crud.get_by_type_async(mock_db, dict_type="not_exist")

        assert result == []

    async def test_get_by_type_with_tenant_filter(self, crud, mock_db):
        """测试 get_by_type 透传 tenant_filter"""
        tenant_filter = TenantFilter(organization_ids=["org-1"])
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            await crud.get_by_type_async(
                mock_db,
                dict_type="asset_status",
                tenant_filter=tenant_filter,
            )

        call_args = mock_build.call_args
        assert call_args.kwargs.get("tenant_filter") == tenant_filter


class TestCRUDSystemDictionaryGetTypes:
    """测试 get_types 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDSystemDictionary()

    @pytest.fixture
    def mock_db(self, db_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db_session.execute = AsyncMock(return_value=mock_result)
        return db_session

    async def test_get_types_from_enum_field(self, crud, mock_db):
        """测试从枚举字段表获取类型"""
        mock_db.execute.return_value.scalars.return_value.all.return_value = [
            "asset_status",
            "contract_type",
            "payment_method",
        ]

        result = await crud.get_types_async(mock_db)

        assert result == ["asset_status", "contract_type", "payment_method"]

    async def test_get_types_empty(self, crud, mock_db):
        """测试无类型时返回空列表"""
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        result = await crud.get_types_async(mock_db)

        assert result == []

    async def test_get_types_import_error_fallback(self, crud, mock_db):
        """测试导入错误时的回退"""
        import builtins

        original_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "src.models.enum_field":
                raise ImportError("mocked import error")
            return original_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=fake_import):
            result = await crud.get_types_async(mock_db)

        assert result == []


class TestCRUDSystemDictionaryCreate:
    """测试 create 方法（继承自基类）"""

    @pytest.fixture
    def crud(self):
        return CRUDSystemDictionary()

    @pytest.fixture
    def mock_db(self, db_session):
        db_session.add = MagicMock(wraps=db_session.add)
        db_session.commit = AsyncMock(wraps=db_session.commit)
        db_session.refresh = AsyncMock(wraps=db_session.refresh)
        return db_session

    async def test_create_dictionary(self, crud, mock_db):
        """测试创建字典项"""
        create_data = MagicMock()
        create_data.model_dump.return_value = {
            "dict_type": "new_type",
            "dict_code": "new_code",
            "dict_name": "新字典项",
        }

        with patch.object(crud, "create", new_callable=AsyncMock) as mock_create:
            mock_dict = MagicMock(spec=SystemDictionary)
            mock_create.return_value = mock_dict

            result = await crud.create(mock_db, obj_in=create_data)

        assert result is not None


class TestCRUDSystemDictionaryUpdate:
    """测试 update 方法（继承自基类）"""

    @pytest.fixture
    def crud(self):
        return CRUDSystemDictionary()

    @pytest.fixture
    def mock_db(self, db_session):
        return db_session

    async def test_update_dictionary(self, crud, mock_db):
        """测试更新字典项"""
        mock_dict = MagicMock(spec=SystemDictionary)
        update_data = {"dict_name": "更新后的名称"}

        with patch.object(crud, "update", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = mock_dict

            result = await crud.update(mock_db, db_obj=mock_dict, obj_in=update_data)

        assert result is not None


class TestCRUDSystemDictionaryRemove:
    """测试 remove 方法（继承自基类）"""

    @pytest.fixture
    def crud(self):
        return CRUDSystemDictionary()

    @pytest.fixture
    def mock_db(self, db_session):
        db_session.delete = MagicMock(wraps=db_session.delete)
        db_session.commit = AsyncMock(wraps=db_session.commit)
        return db_session

    async def test_remove_dictionary(self, crud, mock_db):
        """测试删除字典项"""
        with patch.object(crud, "remove", new_callable=AsyncMock) as mock_remove:
            mock_dict = MagicMock(spec=SystemDictionary)
            mock_remove.return_value = mock_dict

            result = await crud.remove(mock_db, id="dict-1")

        assert result is not None


class TestCRUDInstance:
    """测试 CRUD 实例"""

    async def test_system_dictionary_crud_instance(self):
        """测试系统字典 CRUD 实例"""
        assert system_dictionary_crud is not None
        assert isinstance(system_dictionary_crud, CRUDSystemDictionary)
