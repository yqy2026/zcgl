"""
枚举字段CRUD操作单元测试
测试 EnumFieldTypeCRUD, EnumFieldValueCRUD, EnumFieldUsageCRUD
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from src.crud.enum_field import (
    EnumFieldTypeCRUD,
    EnumFieldUsageCRUD,
    EnumFieldValueCRUD,
    get_enum_field_type_crud,
    get_enum_field_usage_crud,
    get_enum_field_value_crud,
)
from src.models.enum_field import (
    EnumFieldType,
    EnumFieldUsage,
    EnumFieldValue,
)
from src.schemas.enum_field import (
    EnumFieldTypeCreate,
    EnumFieldTypeUpdate,
    EnumFieldUsageCreate,
    EnumFieldUsageUpdate,
    EnumFieldValueCreate,
    EnumFieldValueUpdate,
)


# ===================== Fixtures =====================
@pytest.fixture
def mock_db():
    """模拟数据库会话"""
    return MagicMock(spec=Session)


@pytest.fixture
def sample_enum_type():
    """示例枚举类型"""
    enum_type = EnumFieldType(
        id="enum_type_123",
        name="资产类型",
        code="asset_type",
        category="asset",
        description="资产分类",
        is_system=False,
        is_multiple=True,
        is_hierarchical=True,
        status="active",
        is_deleted=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    enum_type.enum_values = []
    return enum_type


@pytest.fixture
def sample_enum_value():
    """示例枚举值"""
    enum_value = EnumFieldValue(
        id="enum_value_123",
        enum_type_id="enum_type_123",
        label="办公用房",
        value="office",
        code="OFFICE",
        level=1,
        path="",
        sort_order=1,
        is_active=True,
        is_deleted=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    return enum_value


@pytest.fixture
def sample_enum_usage():
    """示例枚举使用记录"""
    usage = EnumFieldUsage(
        id="usage_123",
        enum_type_id="enum_type_123",
        table_name="assets",
        field_name="asset_type",
        field_label="资产类型",
        module_name="asset_management",
        is_required=True,
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    return usage


@pytest.fixture
def sample_enum_type_create():
    """示例枚举类型创建数据"""
    return EnumFieldTypeCreate(
        name="新资产类型",
        code="new_asset_type",
        category="asset",
        description="新增资产分类",
        is_system=False,
        is_multiple=False,
        is_hierarchical=False,
        status="active",
        created_by="admin",
    )


@pytest.fixture
def sample_enum_value_create():
    """示例枚举值创建数据"""
    return EnumFieldValueCreate(
        enum_type_id="enum_type_123",
        label="商业用房",
        value="commercial",
        code="COMMERCIAL",
        sort_order=2,
        is_active=True,
        created_by="admin",
    )


# ===================== EnumFieldTypeCRUD Tests =====================
class TestEnumFieldTypeCRUD:
    """测试枚举字段类型CRUD操作"""

    def test_get_enum_type_by_id_success(self, mock_db, sample_enum_type):
        """测试成功通过ID获取枚举类型"""
        # 模拟查询链 - 第一次查询返回枚举类型
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_enum_type

        # 模拟获取关联的枚举值
        mock_values_query = MagicMock()
        mock_values_query.filter.return_value = mock_values_query
        mock_values_query.order_by.return_value = mock_values_query
        mock_values_query.all.return_value = []

        # 配置查询顺序
        query_call_count = [0]

        def query_side_effect(*args, **kwargs):
            query_call_count[0] += 1
            if query_call_count[0] == 1:  # 第一次查询枚举类型
                return mock_query
            else:  # 后续查询枚举值
                return mock_values_query

        mock_db.query.side_effect = query_side_effect

        # 执行查询
        crud = EnumFieldTypeCRUD(mock_db)
        result = crud.get("enum_type_123")

        # 验证结果
        assert result is not None
        assert result.id == "enum_type_123"
        assert result.name == "资产类型"
        assert mock_query.filter.called

    def test_get_enum_type_by_id_not_found(self, mock_db):
        """测试获取不存在的枚举类型"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        crud = EnumFieldTypeCRUD(mock_db)
        result = crud.get("nonexistent_id")

        assert result is None

    def test_get_enum_type_by_code_success(self, mock_db, sample_enum_type):
        """测试成功通过编码获取枚举类型"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_enum_type

        crud = EnumFieldTypeCRUD(mock_db)
        result = crud.get_by_code("asset_type")

        assert result is not None
        assert result.code == "asset_type"
        assert mock_query.filter.called

    def test_get_enum_type_by_code_not_found(self, mock_db):
        """测试通过编码获取不存在的枚举类型"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        crud = EnumFieldTypeCRUD(mock_db)
        result = crud.get_by_code("nonexistent_code")

        assert result is None

    def test_get_multi_enum_types_no_filters(self, mock_db, sample_enum_type):
        """测试获取多个枚举类型（无筛选条件）"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_enum_type]

        # 模拟获取枚举值的查询
        mock_values_query = MagicMock()
        mock_values_query.filter.return_value = mock_values_query
        mock_values_query.order_by.return_value = mock_values_query
        mock_values_query.all.return_value = []

        # 配置查询顺序
        query_call_count = [0]

        def query_side_effect(*args, **kwargs):
            query_call_count[0] += 1
            if query_call_count[0] == 1:  # 第一次查询枚举类型
                return mock_query
            else:  # 后续查询枚举值
                return mock_values_query

        mock_db.query.side_effect = query_side_effect

        crud = EnumFieldTypeCRUD(mock_db)
        results = crud.get_multi(skip=0, limit=10)

        assert len(results) == 1
        assert results[0].id == "enum_type_123"

    def test_get_multi_enum_types_with_category_filter(self, mock_db, sample_enum_type):
        """测试按类别筛选枚举类型"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_enum_type]

        # 模拟获取枚举值
        mock_values_query = MagicMock()
        mock_values_query.filter.return_value = mock_values_query
        mock_values_query.order_by.return_value = mock_values_query
        mock_values_query.all.return_value = []

        query_call_count = [0]

        def query_side_effect(*args, **kwargs):
            query_call_count[0] += 1
            return mock_query if query_call_count[0] == 1 else mock_values_query

        mock_db.query.side_effect = query_side_effect

        crud = EnumFieldTypeCRUD(mock_db)
        results = crud.get_multi(category="asset")

        assert len(results) == 1
        assert mock_query.filter.call_count >= 2  # is_deleted 和 category 筛选

    def test_get_multi_enum_types_with_status_filter(self, mock_db, sample_enum_type):
        """测试按状态筛选枚举类型"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_enum_type]

        mock_values_query = MagicMock()
        mock_values_query.filter.return_value = mock_values_query
        mock_values_query.order_by.return_value = mock_values_query
        mock_values_query.all.return_value = []

        query_call_count = [0]

        def query_side_effect(*args, **kwargs):
            query_call_count[0] += 1
            return mock_query if query_call_count[0] == 1 else mock_values_query

        mock_db.query.side_effect = query_side_effect

        crud = EnumFieldTypeCRUD(mock_db)
        results = crud.get_multi(status="active")

        assert len(results) == 1

    def test_get_multi_enum_types_with_is_system_filter(
        self, mock_db, sample_enum_type
    ):
        """测试按是否系统内置筛选枚举类型"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_enum_type]

        mock_values_query = MagicMock()
        mock_values_query.filter.return_value = mock_values_query
        mock_values_query.order_by.return_value = mock_values_query
        mock_values_query.all.return_value = []

        query_call_count = [0]

        def query_side_effect(*args, **kwargs):
            query_call_count[0] += 1
            return mock_query if query_call_count[0] == 1 else mock_values_query

        mock_db.query.side_effect = query_side_effect

        crud = EnumFieldTypeCRUD(mock_db)
        results = crud.get_multi(is_system=False)

        assert len(results) == 1

    def test_get_multi_enum_types_with_keyword_filter(self, mock_db, sample_enum_type):
        """测试按关键词筛选枚举类型"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_enum_type]

        mock_values_query = MagicMock()
        mock_values_query.filter.return_value = mock_values_query
        mock_values_query.order_by.return_value = mock_values_query
        mock_values_query.all.return_value = []

        query_call_count = [0]

        def query_side_effect(*args, **kwargs):
            query_call_count[0] += 1
            return mock_query if query_call_count[0] == 1 else mock_values_query

        mock_db.query.side_effect = query_side_effect

        crud = EnumFieldTypeCRUD(mock_db)
        results = crud.get_multi(keyword="资产")

        assert len(results) == 1

    def test_create_enum_type_success(self, mock_db, sample_enum_type_create):
        """测试成功创建枚举类型"""
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        mock_db.flush = MagicMock()

        # 模拟refresh后对象获得ID
        EnumFieldType(id="new_enum_type_123", **sample_enum_type_create.model_dump())
        mock_db.refresh.side_effect = lambda obj: setattr(
            obj, "id", "new_enum_type_123"
        )

        crud = EnumFieldTypeCRUD(mock_db)
        result = crud.create(sample_enum_type_create)

        assert result is not None
        assert mock_db.add.called
        assert mock_db.commit.called
        assert mock_db.flush.called

    def test_create_enum_type_with_history(self, mock_db, sample_enum_type_create):
        """测试创建枚举类型时记录历史"""
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        mock_db.flush = MagicMock()

        EnumFieldType(id="new_enum_type_123", **sample_enum_type_create.model_dump())
        mock_db.refresh.side_effect = lambda obj: setattr(
            obj, "id", "new_enum_type_123"
        )

        crud = EnumFieldTypeCRUD(mock_db)
        crud.create(sample_enum_type_create)

        # 验证调用了两次add: 一次添加枚举类型，一次添加历史记录
        assert mock_db.add.call_count >= 2

    def test_update_enum_type_success(self, mock_db, sample_enum_type):
        """测试成功更新枚举类型"""
        update_data = EnumFieldTypeUpdate(
            name="更新后的资产类型", description="更新后的描述", updated_by="admin"
        )

        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        crud = EnumFieldTypeCRUD(mock_db)
        result = crud.update(sample_enum_type, update_data)

        assert result is not None
        assert mock_db.commit.called
        assert mock_db.refresh.called

    def test_update_enum_type_with_history(self, mock_db, sample_enum_type):
        """测试更新枚举类型时记录变更历史"""
        update_data = EnumFieldTypeUpdate(name="新名称", updated_by="admin")

        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        crud = EnumFieldTypeCRUD(mock_db)
        crud.update(sample_enum_type, update_data)

        # 验证添加了历史记录
        assert mock_db.add.called

    def test_delete_enum_type_success(self, mock_db, sample_enum_type):
        """测试成功删除枚举类型"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_enum_type

        # 模拟没有关联的枚举值
        mock_value_count_query = MagicMock()
        mock_db.query.return_value = mock_value_count_query
        mock_value_count_query.filter.return_value = mock_value_count_query
        mock_value_count_query.count.return_value = 0

        # 模拟没有使用记录
        mock_usage_count_query = MagicMock()
        mock_usage_count_query.filter.return_value = mock_usage_count_query
        mock_usage_count_query.count.return_value = 0

        mock_db.commit = MagicMock()

        # 配置查询顺序
        query_call_count = [0]

        def query_side_effect(*args, **kwargs):
            query_call_count[0] += 1
            if query_call_count[0] == 1:  # get enum_type
                return mock_query
            elif query_call_count[0] == 2:  # check value count
                return mock_value_count_query
            else:  # check usage count
                return mock_usage_count_query

        mock_db.query.side_effect = query_side_effect

        crud = EnumFieldTypeCRUD(mock_db)
        result = crud.delete("enum_type_123", deleted_by="admin")

        assert result is True
        assert sample_enum_type.is_deleted is True
        assert mock_db.commit.called

    def test_delete_enum_type_not_found(self, mock_db):
        """测试删除不存在的枚举类型"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        crud = EnumFieldTypeCRUD(mock_db)
        result = crud.delete("nonexistent_id")

        assert result is False

    def test_delete_enum_type_with_values_raises_error(self, mock_db, sample_enum_type):
        """测试删除包含枚举值的类型时抛出错误"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_enum_type

        # 模拟有关联的枚举值
        mock_value_count_query = MagicMock()
        mock_value_count_query.filter.return_value = mock_value_count_query
        mock_value_count_query.count.return_value = 5

        query_call_count = [0]

        def query_side_effect(*args, **kwargs):
            query_call_count[0] += 1
            return mock_query if query_call_count[0] == 1 else mock_value_count_query

        mock_db.query.side_effect = query_side_effect

        crud = EnumFieldTypeCRUD(mock_db)

        with pytest.raises(ValueError, match="无法删除包含枚举值的枚举类型"):
            crud.delete("enum_type_123")

    def test_delete_enum_type_with_usage_raises_error(self, mock_db, sample_enum_type):
        """测试删除正在使用的枚举类型时抛出错误"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_enum_type

        # 模拟没有枚举值
        mock_value_count_query = MagicMock()
        mock_value_count_query.filter.return_value = mock_value_count_query
        mock_value_count_query.count.return_value = 0

        # 模拟有使用记录
        mock_usage_count_query = MagicMock()
        mock_usage_count_query.filter.return_value = mock_usage_count_query
        mock_usage_count_query.count.return_value = 3

        query_call_count = [0]

        def query_side_effect(*args, **kwargs):
            query_call_count[0] += 1
            if query_call_count[0] == 1:
                return mock_query
            elif query_call_count[0] == 2:
                return mock_value_count_query
            else:
                return mock_usage_count_query

        mock_db.query.side_effect = query_side_effect

        crud = EnumFieldTypeCRUD(mock_db)

        with pytest.raises(ValueError, match="无法删除|包含"):
            crud.delete("enum_type_123")

    def test_get_categories(self, mock_db):
        """测试获取所有枚举类别"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.all.return_value = [("asset",), ("contract",), ("organization",)]

        crud = EnumFieldTypeCRUD(mock_db)
        result = crud.get_categories()

        assert len(result) == 3
        assert "asset" in result
        assert "contract" in result
        assert "organization" in result

    def test_get_statistics(self, mock_db):
        """测试获取统计信息"""
        # 模拟总类型数查询
        mock_total_query = MagicMock()
        mock_total_query.filter.return_value = mock_total_query
        mock_total_query.count.return_value = 10

        # 模拟活跃类型数查询
        mock_active_query = MagicMock()
        mock_active_query.filter.return_value = mock_active_query
        mock_active_query.count.return_value = 8

        # 模拟按类别统计查询
        mock_category_query = MagicMock()
        mock_category_query.filter.return_value = mock_category_query
        mock_category_query.group_by.return_value = mock_category_query
        mock_category_query.all.return_value = [
            ("asset", 5),
            ("contract", 3),
            (None, 2),
        ]

        query_call_count = [0]

        def query_side_effect(*args, **kwargs):
            query_call_count[0] += 1
            if query_call_count[0] == 1:
                return mock_total_query
            elif query_call_count[0] == 2:
                return mock_active_query
            else:
                return mock_category_query

        mock_db.query.side_effect = query_side_effect

        crud = EnumFieldTypeCRUD(mock_db)
        result = crud.get_statistics()

        assert result["total_types"] == 10
        assert result["active_types"] == 8
        assert len(result["categories"]) == 3
        assert any(
            cat["name"] == "asset" and cat["count"] == 5 for cat in result["categories"]
        )
        assert any(
            cat["name"] == "未分类" and cat["count"] == 2
            for cat in result["categories"]
        )


# ===================== EnumFieldValueCRUD Tests =====================
class TestEnumFieldValueCRUD:
    """测试枚举字段值CRUD操作"""

    def test_get_enum_value_by_id_success(self, mock_db, sample_enum_value):
        """测试成功通过ID获取枚举值"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_enum_value

        crud = EnumFieldValueCRUD(mock_db)
        result = crud.get("enum_value_123")

        assert result is not None
        assert result.id == "enum_value_123"
        assert result.label == "办公用房"

    def test_get_enum_value_by_id_not_found(self, mock_db):
        """测试获取不存在的枚举值"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        crud = EnumFieldValueCRUD(mock_db)
        result = crud.get("nonexistent_id")

        assert result is None

    def test_get_by_type_and_value_success(self, mock_db, sample_enum_value):
        """测试成功通过类型ID和值获取枚举值"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_enum_value

        crud = EnumFieldValueCRUD(mock_db)
        result = crud.get_by_type_and_value("enum_type_123", "office")

        assert result is not None
        assert result.value == "office"

    def test_get_by_type_and_value_not_found(self, mock_db):
        """测试通过类型ID和值获取不存在的枚举值"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        crud = EnumFieldValueCRUD(mock_db)
        result = crud.get_by_type_and_value("enum_type_123", "nonexistent")

        assert result is None

    def test_get_by_type_top_level(self, mock_db, sample_enum_value):
        """测试获取顶级枚举值"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_enum_value]

        crud = EnumFieldValueCRUD(mock_db)
        results = crud.get_by_type("enum_type_123", parent_id=None)

        assert len(results) == 1
        assert results[0].label == "办公用房"

    def test_get_by_type_with_parent(self, mock_db, sample_enum_value):
        """测试获取指定父级的枚举值"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_enum_value]

        crud = EnumFieldValueCRUD(mock_db)
        results = crud.get_by_type("enum_type_123", parent_id="parent_123")

        assert len(results) == 1

    def test_get_by_type_with_active_filter(self, mock_db, sample_enum_value):
        """测试按启用状态筛选枚举值"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_enum_value]

        crud = EnumFieldValueCRUD(mock_db)
        results = crud.get_by_type("enum_type_123", is_active=True)

        assert len(results) == 1

    def test_get_tree_structure(self, mock_db):
        """测试获取树形结构"""
        # 模拟顶级节点（无子节点）
        top_level_value = EnumFieldValue(
            id="top_1",
            enum_type_id="enum_type_123",
            label="顶级",
            value="top",
            level=1,
            is_active=True,
            is_deleted=False,
        )

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        # 第一次调用返回顶级节点，后续调用返回空列表（表示没有子节点）
        call_count = [0]

        def all_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return [top_level_value]
            else:
                return []  # 没有子节点

        mock_query.all.side_effect = all_side_effect

        crud = EnumFieldValueCRUD(mock_db)
        results = crud.get_tree("enum_type_123")

        assert len(results) == 1
        assert results[0].label == "顶级"
        # 验证确实调用了多次查询（递归查询子节点）
        assert call_count[0] >= 2

    def test_create_enum_value_success(self, mock_db, sample_enum_value_create):
        """测试成功创建枚举值"""
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        mock_db.flush = MagicMock()

        EnumFieldValue(id="new_enum_value_123", **sample_enum_value_create.model_dump())
        mock_db.refresh.side_effect = lambda obj: setattr(
            obj, "id", "new_enum_value_123"
        )

        crud = EnumFieldValueCRUD(mock_db)
        result = crud.create(sample_enum_value_create)

        assert result is not None
        assert mock_db.add.called
        assert mock_db.commit.called

    def test_create_enum_value_with_parent(self, mock_db):
        """测试创建带父级的枚举值（计算层级和路径）"""
        # 模拟父节点
        parent_value = EnumFieldValue(
            id="parent_123",
            enum_type_id="enum_type_123",
            label="父级",
            value="parent",
            level=1,
            path="parent_123",
            is_deleted=False,
        )

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = parent_value

        value_create = EnumFieldValueCreate(
            enum_type_id="enum_type_123",
            label="子级",
            value="child",
            parent_id="parent_123",
            created_by="admin",
        )

        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        mock_db.flush = MagicMock()

        EnumFieldValue(id="child_123", **value_create.model_dump())
        mock_db.refresh.side_effect = lambda obj: (
            setattr(obj, "id", "child_123")
            or setattr(obj, "level", 2)
            or setattr(obj, "path", "parent_123/parent_123")
        )

        crud = EnumFieldValueCRUD(mock_db)
        result = crud.create(value_create)

        assert result is not None

    def test_update_enum_value_success(self, mock_db, sample_enum_value):
        """测试成功更新枚举值"""
        update_data = EnumFieldValueUpdate(label="更新后的标签", updated_by="admin")

        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        crud = EnumFieldValueCRUD(mock_db)
        result = crud.update(sample_enum_value, update_data)

        assert result is not None
        assert mock_db.commit.called

    def test_update_enum_value_with_parent_change(self, mock_db, sample_enum_value):
        """测试更新枚举值的父级（重新计算层级和路径）"""
        # 模拟新父节点
        new_parent = EnumFieldValue(
            id="new_parent_123",
            enum_type_id="enum_type_123",
            label="新父级",
            value="new_parent",
            level=1,
            path="new_parent_123",
            is_deleted=False,
        )

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = new_parent

        update_data = EnumFieldValueUpdate(
            parent_id="new_parent_123", updated_by="admin"
        )

        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        crud = EnumFieldValueCRUD(mock_db)
        result = crud.update(sample_enum_value, update_data)

        assert result is not None

    def test_delete_enum_value_success(self, mock_db, sample_enum_value):
        """测试成功删除枚举值"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_enum_value

        # 模拟没有子枚举值
        mock_children_query = MagicMock()
        mock_children_query.filter.return_value = mock_children_query
        mock_children_query.count.return_value = 0

        query_call_count = [0]

        def query_side_effect(*args, **kwargs):
            query_call_count[0] += 1
            return mock_query if query_call_count[0] == 1 else mock_children_query

        mock_db.query.side_effect = query_side_effect

        mock_db.commit = MagicMock()

        crud = EnumFieldValueCRUD(mock_db)
        result = crud.delete("enum_value_123", deleted_by="admin")

        assert result is True
        assert sample_enum_value.is_deleted is True
        assert mock_db.commit.called

    def test_delete_enum_value_not_found(self, mock_db):
        """测试删除不存在的枚举值"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        crud = EnumFieldValueCRUD(mock_db)
        result = crud.delete("nonexistent_id")

        assert result is False

    def test_delete_enum_value_with_children_raises_error(
        self, mock_db, sample_enum_value
    ):
        """测试删除包含子枚举值的值时抛出错误"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_enum_value

        # 模拟有子枚举值
        mock_children_query = MagicMock()
        mock_children_query.filter.return_value = mock_children_query
        mock_children_query.count.return_value = 3

        query_call_count = [0]

        def query_side_effect(*args, **kwargs):
            query_call_count[0] += 1
            return mock_query if query_call_count[0] == 1 else mock_children_query

        mock_db.query.side_effect = query_side_effect

        crud = EnumFieldValueCRUD(mock_db)

        with pytest.raises(ValueError, match="无法删除包含子枚举值的枚举值"):
            crud.delete("enum_value_123")

    def test_batch_create_enum_values(self, mock_db, sample_enum_value_create):
        """测试批量创建枚举值"""
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        mock_db.flush = MagicMock()

        EnumFieldValue(id="new_value_123", **sample_enum_value_create.model_dump())
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", "new_value_123")

        values_data = [
            {
                "label": "值1",
                "value": "value1",
                "code": "VALUE1",
            },
            {
                "label": "值2",
                "value": "value2",
                "code": "VALUE2",
            },
        ]

        crud = EnumFieldValueCRUD(mock_db)
        results = crud.batch_create("enum_type_123", values_data, created_by="admin")

        assert len(results) == 2
        assert mock_db.commit.call_count == 2


# ===================== EnumFieldUsageCRUD Tests =====================
class TestEnumFieldUsageCRUD:
    """测试枚举字段使用记录CRUD操作"""

    def test_get_usage_by_id_success(self, mock_db, sample_enum_usage):
        """测试成功通过ID获取使用记录"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_enum_usage

        crud = EnumFieldUsageCRUD(mock_db)
        result = crud.get("usage_123")

        assert result is not None
        assert result.id == "usage_123"

    def test_get_usage_by_id_not_found(self, mock_db):
        """测试获取不存在的使用记录"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        crud = EnumFieldUsageCRUD(mock_db)
        result = crud.get("nonexistent_id")

        assert result is None

    def test_get_by_field_success(self, mock_db, sample_enum_usage):
        """测试成功通过表名和字段名获取使用记录"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_enum_usage

        crud = EnumFieldUsageCRUD(mock_db)
        result = crud.get_by_field("assets", "asset_type")

        assert result is not None
        assert result.table_name == "assets"
        assert result.field_name == "asset_type"

    def test_get_by_field_not_found(self, mock_db):
        """测试通过表名和字段名获取不存在的使用记录"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        crud = EnumFieldUsageCRUD(mock_db)
        result = crud.get_by_field("nonexistent_table", "nonexistent_field")

        assert result is None

    def test_get_by_enum_type(self, mock_db, sample_enum_usage):
        """测试通过枚举类型ID获取使用记录"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_enum_usage]

        crud = EnumFieldUsageCRUD(mock_db)
        results = crud.get_by_enum_type("enum_type_123")

        assert len(results) == 1
        assert results[0].enum_type_id == "enum_type_123"

    def test_create_usage_success(self, mock_db):
        """测试成功创建使用记录"""
        usage_create = EnumFieldUsageCreate(
            enum_type_id="enum_type_123",
            table_name="assets",
            field_name="asset_category",
            field_label="资产类别",
            module_name="asset_management",
            is_required=True,
            is_active=True,
            created_by="admin",
        )

        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        EnumFieldUsage(id="new_usage_123", **usage_create.model_dump())
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", "new_usage_123")

        crud = EnumFieldUsageCRUD(mock_db)
        result = crud.create(usage_create)

        assert result is not None
        assert mock_db.add.called
        assert mock_db.commit.called

    def test_update_usage_success(self, mock_db, sample_enum_usage):
        """测试成功更新使用记录"""
        update_data = EnumFieldUsageUpdate(
            field_label="更新后的字段标签", is_required=False, updated_by="admin"
        )

        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        crud = EnumFieldUsageCRUD(mock_db)
        result = crud.update(sample_enum_usage, update_data)

        assert result is not None
        assert mock_db.commit.called

    def test_delete_usage_success(self, mock_db, sample_enum_usage):
        """测试成功删除使用记录"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_enum_usage

        mock_db.delete = MagicMock()
        mock_db.commit = MagicMock()

        crud = EnumFieldUsageCRUD(mock_db)
        result = crud.delete("usage_123")

        assert result is True
        assert mock_db.delete.called
        assert mock_db.commit.called

    def test_delete_usage_not_found(self, mock_db):
        """测试删除不存在的使用记录"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        crud = EnumFieldUsageCRUD(mock_db)
        result = crud.delete("nonexistent_id")

        assert result is False


# ===================== Factory Function Tests =====================
class TestFactoryFunctions:
    """测试工厂函数"""

    def test_get_enum_field_type_crud(self, mock_db):
        """测试获取EnumFieldTypeCRUD实例"""
        crud = get_enum_field_type_crud(mock_db)
        assert isinstance(crud, EnumFieldTypeCRUD)
        assert crud.db == mock_db

    def test_get_enum_field_value_crud(self, mock_db):
        """测试获取EnumFieldValueCRUD实例"""
        crud = get_enum_field_value_crud(mock_db)
        assert isinstance(crud, EnumFieldValueCRUD)
        assert crud.db == mock_db

    def test_get_enum_field_usage_crud(self, mock_db):
        """测试获取EnumFieldUsageCRUD实例"""
        crud = get_enum_field_usage_crud(mock_db)
        assert isinstance(crud, EnumFieldUsageCRUD)
        assert crud.db == mock_db


# ===================== Edge Cases and Error Handling =====================
class TestEdgeCases:
    """测试边界情况和错误处理"""

    def test_update_enum_type_no_changes(self, mock_db, sample_enum_type):
        """测试更新枚举类型但没有实际变更"""
        update_data = EnumFieldTypeUpdate(updated_by="admin")

        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        crud = EnumFieldTypeCRUD(mock_db)
        result = crud.update(sample_enum_type, update_data)

        assert result is not None
        # 即使没有字段变更，也应该提交
        assert mock_db.commit.called

    def test_update_enum_value_no_changes(self, mock_db, sample_enum_value):
        """测试更新枚举值但没有实际变更"""
        update_data = EnumFieldValueUpdate(updated_by="admin")

        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        crud = EnumFieldValueCRUD(mock_db)
        result = crud.update(sample_enum_value, update_data)

        assert result is not None
        assert mock_db.commit.called

    def test_create_enum_value_without_parent(self, mock_db):
        """测试创建不带父级的枚举值"""
        value_create = EnumFieldValueCreate(
            enum_type_id="enum_type_123",
            label="独立值",
            value="standalone",
            parent_id=None,
            created_by="admin",
        )

        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        mock_db.flush = MagicMock()

        EnumFieldValue(id="standalone_123", **value_create.model_dump())
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", "standalone_123")

        crud = EnumFieldValueCRUD(mock_db)
        result = crud.create(value_create)

        assert result is not None

    def test_get_empty_categories(self, mock_db):
        """测试获取空类别列表"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.all.return_value = []

        crud = EnumFieldTypeCRUD(mock_db)
        result = crud.get_categories()

        assert len(result) == 0

    def test_get_statistics_no_categories(self, mock_db):
        """测试获取统计信息（无类别）"""
        mock_total_query = MagicMock()
        mock_total_query.filter.return_value = mock_total_query
        mock_total_query.count.return_value = 5

        mock_active_query = MagicMock()
        mock_active_query.filter.return_value = mock_active_query
        mock_active_query.count.return_value = 3

        mock_category_query = MagicMock()
        mock_category_query.filter.return_value = mock_category_query
        mock_category_query.group_by.return_value = mock_category_query
        mock_category_query.all.return_value = []

        query_call_count = [0]

        def query_side_effect(*args, **kwargs):
            query_call_count[0] += 1
            if query_call_count[0] == 1:
                return mock_total_query
            elif query_call_count[0] == 2:
                return mock_active_query
            else:
                return mock_category_query

        mock_db.query.side_effect = query_side_effect

        crud = EnumFieldTypeCRUD(mock_db)
        result = crud.get_statistics()

        assert result["total_types"] == 5
        assert result["active_types"] == 3
        assert len(result["categories"]) == 0

    def test_get_tree_empty_tree(self, mock_db):
        """测试获取空树结构"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        crud = EnumFieldValueCRUD(mock_db)
        results = crud.get_tree("enum_type_123")

        assert len(results) == 0

    def test_batch_create_empty_list(self, mock_db):
        """测试批量创建空列表"""
        crud = EnumFieldValueCRUD(mock_db)
        results = crud.batch_create("enum_type_123", [], created_by="admin")

        assert len(results) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
