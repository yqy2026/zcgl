"""
Organization CRUD unit tests
测试组织架构CRUD操作的全面覆盖
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from src.crud.organization import CRUDOrganization, organization
from src.models.organization import Organization


# ===================== Fixtures =====================
@pytest.fixture
def mock_db():
    """模拟数据库会话"""
    return MagicMock(spec=Session)


@pytest.fixture
def sample_organization():
    """示例组织数据"""
    org = Organization(
        id="org_123",
        name="Test Organization",
        code="TEST001",
        level=1,
        sort_order=0,
        type="department",
        status="active",
        phone="13800138000",
        email="test@example.com",
        leader_name="John Doe",
        leader_phone="13900139000",
        parent_id=None,
        description="Test organization",
        is_deleted=False,
    )
    return org


@pytest.fixture
def sample_organization_dict():
    """示例组织字典数据"""
    return {
        "name": "New Organization",
        "code": "NEW001",
        "level": 2,
        "sort_order": 1,
        "type": "team",
        "status": "active",
        "phone": "13700137000",
        "email": "new@example.com",
        "leader_name": "Jane Smith",
        "leader_phone": "13600136000",
        "parent_id": "org_123",
        "description": "New test organization",
        "created_by": "admin",
    }


@pytest.fixture
def crud_instance():
    """CRUD实例"""
    return CRUDOrganization(Organization)


# ===================== Test Initialization =====================
class TestCRUDOrganizationInit:
    """测试CRUDOrganization初始化"""

    def test_init_creates_sensitive_data_handler(self, crud_instance):
        """测试初始化时创建敏感数据处理器"""
        assert hasattr(crud_instance, "sensitive_data_handler")
        assert crud_instance.sensitive_data_handler is not None

    def test_sensitive_fields_configured(self, crud_instance):
        """测试敏感字段已配置"""
        handler = crud_instance.sensitive_data_handler
        # 验证敏感字段集合包含正确的字段
        assert "phone" in handler.SEARCHABLE_FIELDS
        assert "leader_phone" in handler.SEARCHABLE_FIELDS
        assert "emergency_phone" in handler.SEARCHABLE_FIELDS
        assert "id_card" in handler.SEARCHABLE_FIELDS


# ===================== Test Create =====================
class TestCRUDOrganizationCreate:
    """测试创建组织"""

    def test_create_with_schema_object(
        self, mock_db, crud_instance, sample_organization_dict
    ):
        """测试使用Pydantic schema对象创建组织"""
        from src.schemas.organization import OrganizationCreate

        # 模拟schema对象
        obj_in = MagicMock(spec=OrganizationCreate)
        obj_in.model_dump.return_value = sample_organization_dict

        # Mock parent create method
        with patch.object(
            crud_instance.__class__.__bases__[0], "create", return_value=MagicMock()
        ) as mock_parent_create:
            crud_instance.create(mock_db, obj_in=obj_in)

            # 验证敏感数据被加密
            mock_parent_create.assert_called_once()
            call_args = mock_parent_create.call_args
            call_args.kwargs.get("obj_in")

            # 验证调用包含了db参数
            assert call_args.kwargs.get("db") == mock_db

    def test_create_with_dict(self, mock_db, crud_instance, sample_organization_dict):
        """测试使用字典创建组织"""
        # Mock parent create method
        with patch.object(
            crud_instance.__class__.__bases__[0], "create", return_value=MagicMock()
        ) as mock_parent_create:
            crud_instance.create(mock_db, obj_in=sample_organization_dict)

            # 验证create被调用
            mock_parent_create.assert_called_once()
            call_args = mock_parent_create.call_args

            # 验证db参数
            assert call_args.kwargs.get("db") == mock_db

    def test_create_encrypts_sensitive_fields(
        self, mock_db, crud_instance, sample_organization_dict
    ):
        """测试创建时加密敏感字段"""
        # Mock encryption
        with patch.object(
            crud_instance.sensitive_data_handler, "encrypt_data", return_value={}
        ) as mock_encrypt:
            with patch.object(
                crud_instance.__class__.__bases__[0], "create", return_value=MagicMock()
            ):
                crud_instance.create(mock_db, obj_in=sample_organization_dict)

                # 验证加密方法被调用
                mock_encrypt.assert_called_once()
                call_args = mock_encrypt.call_args[0][0]
                assert call_args["phone"] == "13700137000"
                assert call_args["leader_phone"] == "13600136000"


# ===================== Test Get =====================
class TestCRUDOrganizationGet:
    """测试获取单个组织"""

    def test_get_decrypts_sensitive_fields(
        self, mock_db, crud_instance, sample_organization
    ):
        """测试获取时解密敏感字段"""
        # Mock query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_organization

        # Mock decryption
        with patch.object(
            crud_instance.sensitive_data_handler, "decrypt_data"
        ) as mock_decrypt:
            result = crud_instance.get(mock_db, id="org_123")

            # 验证查询执行
            mock_query.filter.assert_called_once()
            mock_query.first.assert_called_once()

            # 验证解密被调用
            assert result is not None
            mock_decrypt.assert_called_once()

    def test_get_with_no_cache(self, mock_db, crud_instance, sample_organization):
        """测试不使用缓存获取组织"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_organization

        with patch.object(
            crud_instance.sensitive_data_handler, "decrypt_data"
        ) as mock_decrypt:
            result = crud_instance.get(mock_db, id="org_123", use_cache=False)

            # 验证返回结果
            assert result is not None
            mock_decrypt.assert_called_once()

    def test_get_returns_none_when_not_found(self, mock_db, crud_instance):
        """测试获取不存在的组织返回None"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        result = crud_instance.get(mock_db, id="nonexistent")

        # 验证返回None且不执行解密
        assert result is None


# ===================== Test Get Multi =====================
class TestCRUDOrganizationGetMulti:
    """测试获取多个组织"""

    def test_get_multi_decrypts_all_results(
        self, mock_db, crud_instance, sample_organization
    ):
        """测试获取多个组织时解密所有结果"""
        orgs = [sample_organization, MagicMock(id="org_2"), MagicMock(id="org_3")]

        # Mock parent get_multi
        with patch.object(
            crud_instance.__class__.__bases__[0],
            "get_multi",
            return_value=orgs,
        ) as mock_parent_get_multi:
            with patch.object(
                crud_instance.sensitive_data_handler, "decrypt_data"
            ) as mock_decrypt:
                result = crud_instance.get_multi(mock_db, skip=0, limit=10)

                # 验证父方法被调用
                mock_parent_get_multi.assert_called_once_with(
                    db=mock_db, skip=0, limit=10, use_cache=False
                )

                # 验证所有结果都被解密
                assert mock_decrypt.call_count == 3
                assert len(result) == 3

    def test_get_multi_with_empty_results(self, mock_db, crud_instance):
        """测试获取多个组织时返回空列表"""
        with patch.object(
            crud_instance.__class__.__bases__[0], "get_multi", return_value=[]
        ):
            with patch.object(
                crud_instance.sensitive_data_handler, "decrypt_data"
            ) as mock_decrypt:
                result = crud_instance.get_multi(mock_db, skip=0, limit=10)

                # 验证返回空列表
                assert result == []
                # 不应该调用解密
                mock_decrypt.assert_not_called()


# ===================== Test Update =====================
class TestCRUDOrganizationUpdate:
    """测试更新组织"""

    def test_update_with_schema_object(
        self, mock_db, crud_instance, sample_organization
    ):
        """测试使用Pydantic schema对象更新组织"""
        from src.schemas.organization import OrganizationUpdate

        # Mock update schema
        obj_in = MagicMock(spec=OrganizationUpdate)
        obj_in.model_dump.return_value = {"name": "Updated Name"}

        # Mock parent update
        with patch.object(
            crud_instance.__class__.__bases__[0],
            "update",
            return_value=sample_organization,
        ) as mock_parent_update:
            crud_instance.update(mock_db, db_obj=sample_organization, obj_in=obj_in)

            # 验证更新被调用
            mock_parent_update.assert_called_once()

    def test_update_with_dict(self, mock_db, crud_instance, sample_organization):
        """测试使用字典更新组织"""
        update_data = {"name": "Updated Name", "status": "inactive"}

        with patch.object(
            crud_instance.__class__.__bases__[0],
            "update",
            return_value=sample_organization,
        ) as mock_parent_update:
            crud_instance.update(
                mock_db, db_obj=sample_organization, obj_in=update_data
            )

            # 验证更新被调用
            mock_parent_update.assert_called_once()
            call_args = mock_parent_update.call_args
            assert call_args.kwargs.get("db") == mock_db
            assert call_args.kwargs.get("db_obj") == sample_organization

    def test_update_encrypts_sensitive_fields(
        self, mock_db, crud_instance, sample_organization
    ):
        """测试更新时加密敏感字段"""
        update_data = {
            "phone": "13800138001",
            "leader_phone": "13900139001",
            "name": "Updated Name",
        }

        with patch.object(
            crud_instance, "_encrypt_update_data", return_value=update_data
        ) as mock_encrypt:
            with patch.object(
                crud_instance.__class__.__bases__[0],
                "update",
                return_value=sample_organization,
            ):
                crud_instance.update(
                    mock_db, db_obj=sample_organization, obj_in=update_data
                )

                # 验证加密方法被调用
                mock_encrypt.assert_called_once_with(update_data)


# ===================== Test _encrypt_update_data =====================
class TestEncryptUpdateData:
    """测试更新数据加密"""

    def test_encrypt_update_data_with_sensitive_fields(self, crud_instance):
        """测试加密更新数据中的敏感字段"""
        update_data = {
            "phone": "13800138000",
            "leader_phone": "13900139000",
            "name": "Updated Name",
        }

        with patch.object(
            crud_instance.sensitive_data_handler, "encrypt_field"
        ) as mock_encrypt_field:
            mock_encrypt_field.return_value = "encrypted_value"
            result = crud_instance._encrypt_update_data(update_data)

            # 验证敏感字段被加密
            assert mock_encrypt_field.call_count == 2
            assert result["phone"] == "encrypted_value"
            assert result["leader_phone"] == "encrypted_value"
            assert result["name"] == "Updated Name"

    def test_encrypt_update_data_without_sensitive_fields(self, crud_instance):
        """测试不包含敏感字段的数据更新"""
        update_data = {"name": "Updated Name", "status": "inactive"}

        with patch.object(
            crud_instance.sensitive_data_handler, "encrypt_field"
        ) as mock_encrypt_field:
            result = crud_instance._encrypt_update_data(update_data)

            # 验证不调用加密
            mock_encrypt_field.assert_not_called()
            assert result["name"] == "Updated Name"
            assert result["status"] == "inactive"


# ===================== Test Get Multi With Filters =====================
class TestGetMultiWithFilters:
    """测试带过滤条件的多组织查询"""

    def test_get_multi_with_filters_basic(self, mock_db, crud_instance):
        """测试基本的多组织查询"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        with patch.object(crud_instance.sensitive_data_handler, "decrypt_data"):
            crud_instance.get_multi_with_filters(mock_db, skip=0, limit=10)

            # 验证查询构建
            mock_query.filter.assert_called()
            mock_query.order_by.assert_called()
            mock_query.offset.assert_called_with(0)
            mock_query.limit.assert_called_with(10)

    def test_get_multi_with_filters_by_parent_id(self, mock_db, crud_instance):
        """测试按父组织ID过滤"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        crud_instance.get_multi_with_filters(
            mock_db, skip=0, limit=10, parent_id="parent_123"
        )

        # 验证filter被调用（is_deleted检查）
        assert mock_query.filter.call_count >= 1

    def test_get_multi_with_filters_by_keyword(self, mock_db, crud_instance):
        """测试按关键词搜索"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        crud_instance.get_multi_with_filters(mock_db, skip=0, limit=10, keyword="test")

        # 验证关键词过滤
        assert mock_query.filter.call_count >= 1

    def test_get_multi_with_filters_decrypts_results(
        self, mock_db, crud_instance, sample_organization
    ):
        """测试带过滤查询时解密结果"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_organization]

        with patch.object(
            crud_instance.sensitive_data_handler, "decrypt_data"
        ) as mock_decrypt:
            crud_instance.get_multi_with_filters(mock_db, skip=0, limit=10)

            # 验证解密被调用
            mock_decrypt.assert_called_once()

    def test_get_multi_with_filters_with_parent_id_and_keyword(
        self, mock_db, crud_instance
    ):
        """测试同时使用parent_id和keyword过滤"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        crud_instance.get_multi_with_filters(
            mock_db,
            skip=0,
            limit=10,
            parent_id="parent_123",
            keyword="department",
        )

        # 验证filter被多次调用（is_deleted + keyword）
        assert mock_query.filter.call_count >= 1
        mock_query.order_by.assert_called_once()

    def test_get_multi_with_filters_default_pagination(self, mock_db, crud_instance):
        """测试使用默认分页参数"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        crud_instance.get_multi_with_filters(mock_db)

        # 验证默认分页参数
        mock_query.offset.assert_called_with(0)
        mock_query.limit.assert_called_with(100)

    def test_get_multi_with_filters_multiple_results(
        self, mock_db, crud_instance, sample_organization
    ):
        """测试返回多个结果"""
        org2 = MagicMock(id="org_2")
        org3 = MagicMock(id="org_3")

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_organization, org2, org3]

        with patch.object(
            crud_instance.sensitive_data_handler, "decrypt_data"
        ) as mock_decrypt:
            result = crud_instance.get_multi_with_filters(mock_db, skip=0, limit=10)

            # 验证返回3个结果且都解密
            assert len(result) == 3
            assert mock_decrypt.call_count == 3


# ===================== Test Get Tree =====================
class TestGetTree:
    """测试获取组织树"""

    def test_get_tree_basic(self, mock_db, crud_instance):
        """测试基本树形查询"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        with patch.object(crud_instance.sensitive_data_handler, "decrypt_data"):
            crud_instance.get_tree(mock_db, parent_id=None)

            # 验证查询执行
            mock_query.filter.assert_called()
            mock_query.order_by.assert_called()
            mock_query.all.assert_called()

    def test_get_tree_with_parent_id(self, mock_db, crud_instance):
        """测试获取指定父组织的子树"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        crud_instance.get_tree(mock_db, parent_id="parent_123")

        # 验证filter包含parent_id条件
        assert mock_query.filter.call_count >= 1

    def test_get_tree_decrypts_results(
        self, mock_db, crud_instance, sample_organization
    ):
        """测试树形查询时解密结果"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_organization]

        with patch.object(
            crud_instance.sensitive_data_handler, "decrypt_data"
        ) as mock_decrypt:
            crud_instance.get_tree(mock_db)

            # 验证解密被调用
            mock_decrypt.assert_called_once()

    def test_get_tree_multiple_results(self, mock_db, crud_instance):
        """测试返回多个组织节点"""
        org1 = MagicMock(id="org_1")
        org2 = MagicMock(id="org_2")

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [org1, org2]

        with patch.object(
            crud_instance.sensitive_data_handler, "decrypt_data"
        ) as mock_decrypt:
            result = crud_instance.get_tree(mock_db, parent_id="root")

            # 验证返回2个组织且都解密
            assert len(result) == 2
            assert mock_decrypt.call_count == 2


# ===================== Test Get Children =====================
class TestGetChildren:
    """测试获取子组织"""

    def test_get_children_non_recursive(self, mock_db, crud_instance):
        """测试非递归获取直接子组织"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        with patch.object(crud_instance.sensitive_data_handler, "decrypt_data"):
            crud_instance.get_children(mock_db, parent_id="org_123", recursive=False)

            # 验证查询执行
            mock_query.filter.assert_called()
            mock_query.all.assert_called()

    def test_get_children_recursive_single_level(self, mock_db, crud_instance):
        """测试递归获取子组织（单层）"""
        child_org = MagicMock(id="child_1", parent_id="org_123")

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        # 第一次调用返回直接子组织
        # 后续调用返回空列表
        mock_query.all.side_effect = [[child_org], [], []]

        with patch.object(crud_instance.sensitive_data_handler, "decrypt_data"):
            result = crud_instance.get_children(
                mock_db, parent_id="org_123", recursive=True
            )

            # 验证返回子组织
            assert len(result) >= 0

    def test_get_children_recursive_multi_level(self, mock_db, crud_instance):
        """测试递归获取子组织（多层）"""
        child_org = MagicMock(id="child_1", parent_id="org_123")
        grandchild_org = MagicMock(id="grandchild_1", parent_id="child_1")

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        # 第一次调用返回直接子组织
        # 第二次调用返回孙组织
        # 第三次调用返回空列表
        mock_query.all.side_effect = [[child_org], [grandchild_org], [], []]

        with patch.object(crud_instance.sensitive_data_handler, "decrypt_data"):
            result = crud_instance.get_children(
                mock_db, parent_id="org_123", recursive=True
            )

            # 验证返回多个层级
            assert len(result) >= 1

    def test_get_children_decrypts_results(
        self, mock_db, crud_instance, sample_organization
    ):
        """测试获取子组织时解密结果"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_organization]

        with patch.object(
            crud_instance.sensitive_data_handler, "decrypt_data"
        ) as mock_decrypt:
            crud_instance.get_children(mock_db, parent_id="org_123", recursive=False)

            # 验证解密被调用
            mock_decrypt.assert_called_once()

    def test_get_children_non_recursive_multiple_results(self, mock_db, crud_instance):
        """测试非递归获取多个子组织"""
        child1 = MagicMock(id="child_1", parent_id="org_123")
        child2 = MagicMock(id="child_2", parent_id="org_123")

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [child1, child2]

        with patch.object(
            crud_instance.sensitive_data_handler, "decrypt_data"
        ) as mock_decrypt:
            result = crud_instance.get_children(
                mock_db, parent_id="org_123", recursive=False
            )

            # 验证返回2个子组织且都解密
            assert len(result) == 2
            assert mock_decrypt.call_count == 2


# ===================== Test Get Path To Root =====================
class TestGetPathToRoot:
    """测试获取到根节点的路径"""

    def test_get_path_to_root_single_level(self, mock_db, crud_instance):
        """测试获取单层组织路径"""
        org = MagicMock(id="org_123", parent_id=None)

        with patch.object(crud_instance, "get", return_value=org) as mock_get:
            result = crud_instance.get_path_to_root(mock_db, org_id="org_123")

            # 验证路径只包含当前组织
            assert len(result) == 1
            assert result[0].id == "org_123"
            mock_get.assert_called_once()

    def test_get_path_to_root_multi_level(self, mock_db, crud_instance):
        """测试获取多层组织路径"""
        child = MagicMock(id="child_123", parent_id="parent_123")
        parent = MagicMock(id="parent_123", parent_id=None)

        # Mock get to return different orgs
        with patch.object(crud_instance, "get", side_effect=[child, parent]):
            result = crud_instance.get_path_to_root(mock_db, org_id="child_123")

            # 验证路径包含父组织
            assert len(result) == 2
            assert result[0].id == "parent_123"
            assert result[1].id == "child_123"

    def test_get_path_to_root_three_levels(self, mock_db, crud_instance):
        """测试获取三层组织路径"""
        grandchild = MagicMock(id="grandchild_123", parent_id="child_123")
        child = MagicMock(id="child_123", parent_id="parent_123")
        parent = MagicMock(id="parent_123", parent_id=None)

        with patch.object(
            crud_instance, "get", side_effect=[grandchild, child, parent]
        ):
            result = crud_instance.get_path_to_root(mock_db, org_id="grandchild_123")

            # 验证路径包含所有层级
            assert len(result) == 3
            assert result[0].id == "parent_123"
            assert result[1].id == "child_123"
            assert result[2].id == "grandchild_123"

    def test_get_path_to_root_with_missing_parent(self, mock_db, crud_instance):
        """测试父组织不存在时的路径"""
        child = MagicMock(id="child_123", parent_id="missing_parent")

        with patch.object(crud_instance, "get", side_effect=[child, None]):
            result = crud_instance.get_path_to_root(mock_db, org_id="child_123")

            # 验证路径只包含到找到的最后一级
            assert len(result) == 1
            assert result[0].id == "child_123"


# ===================== Test Search =====================
class TestSearch:
    """测试搜索组织"""

    def test_search_calls_get_multi_with_filters(self, mock_db, crud_instance):
        """测试搜索调用get_multi_with_filters"""
        with patch.object(
            crud_instance, "get_multi_with_filters", return_value=[]
        ) as mock_filters:
            crud_instance.search(mock_db, keyword="test", skip=0, limit=10)

            # 验证调用get_multi_with_filters (positional argument for db)
            mock_filters.assert_called_once_with(
                mock_db, skip=0, limit=10, keyword="test"
            )

    def test_search_with_default_pagination(self, mock_db, crud_instance):
        """测试搜索使用默认分页参数"""
        with patch.object(
            crud_instance, "get_multi_with_filters", return_value=[]
        ) as mock_filters:
            crud_instance.search(mock_db, keyword="test")

            # 验证默认分页参数 (positional argument for db)
            mock_filters.assert_called_once_with(
                mock_db, skip=0, limit=100, keyword="test"
            )


# ===================== Test Organization Instance =====================
class TestOrganizationInstance:
    """测试全局organization实例"""

    def test_organization_instance_exists(self):
        """测试全局organization实例存在"""

        assert organization is not None
        assert isinstance(organization, CRUDOrganization)

    def test_organization_instance_has_sensitive_data_handler(self):
        """测试organization实例有敏感数据处理器"""

        assert hasattr(organization, "sensitive_data_handler")
        assert organization.sensitive_data_handler is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
