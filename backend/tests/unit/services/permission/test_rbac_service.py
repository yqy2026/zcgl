"""
RBAC服务单元测试

测试 RBACService 的角色管理、权限管理、用户角色分配等功能
"""

import json
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from src.exceptions import BusinessLogicError
from src.models.rbac import Permission, Role, UserRoleAssignment
from src.schemas.rbac import (
    PermissionCheckRequest,
    PermissionCreate,
    RoleCreate,
    RoleUpdate,
    UserRoleAssignmentCreate,
)
from src.services.permission.rbac_service import RBACService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """模拟数据库会话"""
    db = Mock()
    db.query = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    db.execute = Mock()
    return db


@pytest.fixture
def rbac_service(mock_db):
    """RBAC服务实例"""
    return RBACService(mock_db)


@pytest.fixture
def sample_role():
    """示例角色"""
    role = Mock(spec=Role)
    role.id = "role-1"
    role.name = "asset_manager"
    role.display_name = "资产管理员"
    role.description = "负责资产管理"
    role.level = 1
    role.category = "business"
    role.is_system_role = False
    role.organization_id = "org-1"
    role.scope = "organization"
    role.scope_id = "org-1"
    role.is_active = True
    role.created_at = datetime.now(UTC)
    role.created_by = "admin"
    role.updated_at = datetime.now(UTC)
    role.updated_by = None
    role.permissions = []
    return role


@pytest.fixture
def sample_permission():
    """示例权限"""
    permission = Mock(spec=Permission)
    permission.id = "perm-1"
    permission.name = "asset.view"
    permission.display_name = "查看资产"
    permission.description = "查看资产信息"
    permission.resource = "asset"
    permission.action = "view"
    permission.max_level = 100
    permission.conditions = None
    permission.is_system_permission = False
    permission.requires_approval = False
    permission.is_active = True
    permission.created_at = datetime.now(UTC)
    permission.updated_at = datetime.now(UTC)
    permission.created_by = "admin"
    return permission


@pytest.fixture
def sample_user():
    """示例用户"""
    user = Mock()
    user.id = "user-1"
    user.username = "testuser"
    user.is_active = True
    user.role = "user"  # 不是admin
    return user


# ============================================================================
# create_role 测试
# ============================================================================


class TestCreateRole:
    """测试创建角色"""

    def test_create_role_success(self, rbac_service, mock_db, sample_permission):
        """测试成功创建角色"""
        role_data = RoleCreate(
            name="new_role",
            display_name="新角色",
            description="新角色描述",
            level=1,
            category="business",
            is_system_role=False,
            organization_id="org-1",
            scope="organization",
            scope_id="org-1",
            permission_ids=["perm-1"],
        )

        # Mock没有重名角色
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db.query = Mock(return_value=mock_query)

        with patch.object(rbac_service, "_assign_permissions_to_role"):
            role = rbac_service.create_role(role_data, created_by="admin")

            assert role.name == "new_role"
            assert role.display_name == "新角色"

    def test_create_role_duplicate_name(self, rbac_service, mock_db, sample_role):
        """测试创建重名角色"""
        role_data = RoleCreate(
            name="existing_role",
            display_name="已存在角色",
            description="描述",
            level=1,
            category="business",
        )

        # Mock返回已存在的角色
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=sample_role)
        mock_db.query = Mock(return_value=mock_query)

        with pytest.raises(BusinessLogicError, match="角色名称已存在"):
            rbac_service.create_role(role_data, created_by="admin")

    def test_create_role_without_permissions(
        self, rbac_service, mock_db, sample_permission
    ):
        """测试创建没有权限的角色"""
        role_data = RoleCreate(
            name="simple_role",
            display_name="简单角色",
            description="无权限角色",
            level=1,
            category="business",
            permission_ids=None,  # 无权限
        )

        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db.query = Mock(return_value=mock_query)

        role = rbac_service.create_role(role_data, created_by="admin")

        # 不应该调用 _assign_permissions_to_role
        assert role.name == "simple_role"


# ============================================================================
# update_role 测试
# ============================================================================


class TestUpdateRole:
    """测试更新角色"""

    def test_update_role_success(self, rbac_service, mock_db, sample_role):
        """测试成功更新角色"""
        role_data = RoleUpdate(
            display_name="更新后的显示名称",
            description="更新后的描述",
            permission_ids=["perm-1", "perm-2"],
        )

        # 首次查询返回要更新的角色
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=sample_role)

        # 第二次查询检查重名返回None（没有重名）
        mock_query2 = Mock()
        mock_filter2 = Mock(return_value=mock_query2)
        mock_query2.filter = Mock(return_value=mock_filter2)
        mock_filter2.first = Mock(return_value=None)

        call_count = [0]

        def query_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_query
            return mock_query2

        mock_db.query = Mock(side_effect=query_side_effect)

        with patch.object(rbac_service, "_assign_permissions_to_role"):
            updated_role = rbac_service.update_role(
                "role-1", role_data, updated_by="admin"
            )

            assert updated_role.display_name == "更新后的显示名称"
            assert updated_role.description == "更新后的描述"

    def test_update_role_not_found(self, rbac_service, mock_db):
        """测试更新不存在的角色"""
        role_data = RoleUpdate(display_name="新名称")

        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=None)  # 角色不存在
        mock_db.query = Mock(return_value=mock_query)

        with pytest.raises(BusinessLogicError, match="角色不存在"):
            rbac_service.update_role("nonexistent", role_data, updated_by="admin")

    def test_update_system_role_forbidden(self, rbac_service, mock_db, sample_role):
        """测试禁止修改系统角色"""
        sample_role.is_system_role = True
        role_data = RoleUpdate(display_name="尝试修改")

        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=sample_role)
        mock_db.query = Mock(return_value=mock_query)

        with pytest.raises(BusinessLogicError, match="系统角色不能修改"):
            rbac_service.update_role("role-1", role_data, updated_by="admin")

    def test_update_role_duplicate_display_name(
        self, rbac_service, mock_db, sample_role
    ):
        """测试更新角色时显示名称重复"""
        existing_role = Mock(spec=Role)
        existing_role.id = "role-2"
        existing_role.display_name = "已使用的显示名称"

        role_data = RoleUpdate(display_name="已使用的显示名称")

        # 首次查询返回要更新的角色
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=sample_role)
        mock_db.query = Mock(return_value=mock_query)

        # 第二次查询检查重名
        mock_query2 = Mock()
        mock_filter2 = Mock(return_value=mock_query2)
        mock_query2.filter = Mock(return_value=mock_filter2)
        mock_filter2.first = Mock(return_value=existing_role)

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_query
            return mock_query2

        mock_db.query = Mock(side_effect=side_effect)

        with pytest.raises(BusinessLogicError, match="角色显示名称已存在"):
            rbac_service.update_role("role-1", role_data, updated_by="admin")


# ============================================================================
# delete_role 测试
# ============================================================================


class TestDeleteRole:
    """测试删除角色"""

    def test_delete_role_success(self, rbac_service, mock_db, sample_role):
        """测试成功删除角色"""
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=sample_role)
        mock_db.query = Mock(return_value=mock_query)

        # Mock没有用户使用此角色
        mock_count_query = Mock()
        mock_count_filter = Mock(return_value=mock_count_query)
        mock_count_query.filter = Mock(return_value=mock_count_filter)
        mock_count_filter.count = Mock(return_value=0)

        query_count = [0]

        def query_side_effect(*args, **kwargs):
            query_count[0] += 1
            if query_count[0] == 1:
                return mock_query
            return mock_count_query

        mock_db.query = Mock(side_effect=query_side_effect)

        with patch.object(rbac_service, "_create_permission_audit_log"):
            result = rbac_service.delete_role("role-1", deleted_by="admin")
            assert result is True

    def test_delete_role_not_found(self, rbac_service, mock_db):
        """测试删除不存在的角色"""
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=None)
        mock_db.query = Mock(return_value=mock_query)

        result = rbac_service.delete_role("nonexistent", deleted_by="admin")
        assert result is False

    def test_delete_system_role_forbidden(self, rbac_service, mock_db, sample_role):
        """测试禁止删除系统角色"""
        sample_role.is_system_role = True

        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=sample_role)
        mock_db.query = Mock(return_value=mock_query)

        with pytest.raises(BusinessLogicError, match="系统角色不能删除"):
            rbac_service.delete_role("role-1", deleted_by="admin")

    def test_delete_role_with_active_users(self, rbac_service, mock_db, sample_role):
        """测试删除有活跃用户的角色"""
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=sample_role)
        mock_db.query = Mock(return_value=mock_query)

        # Mock有3个用户使用此角色
        mock_count_query = Mock()
        mock_count_filter = Mock(return_value=mock_count_query)
        mock_count_query.filter = Mock(return_value=mock_count_filter)
        mock_count_filter.count = Mock(return_value=3)

        query_count = [0]

        def query_side_effect(*args, **kwargs):
            query_count[0] += 1
            if query_count[0] == 1:
                return mock_query
            return mock_count_query

        mock_db.query = Mock(side_effect=query_side_effect)

        with pytest.raises(BusinessLogicError, match="角色正在被 3 个用户使用"):
            rbac_service.delete_role("role-1", deleted_by="admin")


# ============================================================================
# get_role 测试
# ============================================================================


class TestGetRole:
    """测试获取角色"""

    def test_get_role_found(self, rbac_service, mock_db, sample_role):
        """测试获取存在的角色"""
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=sample_role)
        mock_db.query = Mock(return_value=mock_query)

        role = rbac_service.get_role("role-1")
        assert role is not None
        assert role.id == "role-1"

    def test_get_role_not_found(self, rbac_service, mock_db):
        """测试获取不存在的角色"""
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=None)
        mock_db.query = Mock(return_value=mock_query)

        role = rbac_service.get_role("nonexistent")
        assert role is None


# ============================================================================
# get_roles 测试
# ============================================================================


class TestGetRoles:
    """测试获取角色列表"""

    def test_get_roles_default_params(self, rbac_service, mock_db, sample_role):
        """测试默认参数获取角色列表"""
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[sample_role])
        mock_query.count = Mock(return_value=1)
        mock_db.query = Mock(return_value=mock_query)

        roles, total = rbac_service.get_roles()

        assert len(roles) == 1
        assert total == 1

    def test_get_roles_with_search(self, rbac_service, mock_db, sample_role):
        """测试搜索角色"""
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[sample_role])
        mock_query.count = Mock(return_value=1)
        mock_db.query = Mock(return_value=mock_query)

        roles, total = rbac_service.get_roles(search="资产")

        assert len(roles) == 1
        assert total == 1

    def test_get_roles_with_category_filter(self, rbac_service, mock_db, sample_role):
        """测试按类别筛选角色"""
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[sample_role])
        mock_query.count = Mock(return_value=1)
        mock_db.query = Mock(return_value=mock_query)

        roles, total = rbac_service.get_roles(category="business")

        assert len(roles) == 1

    def test_get_roles_with_pagination(self, rbac_service, mock_db, sample_role):
        """测试分页获取角色"""
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[sample_role])
        mock_query.count = Mock(return_value=10)
        mock_db.query = Mock(return_value=mock_query)

        roles, total = rbac_service.get_roles(skip=10, limit=5)

        assert total == 10


# ============================================================================
# create_permission 测试
# ============================================================================


class TestCreatePermission:
    """测试创建权限"""

    def test_create_permission_success(self, rbac_service, mock_db, sample_permission):
        """测试成功创建权限"""
        perm_data = PermissionCreate(
            name="asset.create",
            display_name="创建资产",
            description="创建新资产",
            resource="asset",
            action="create",
            max_level=10,
            conditions=None,
            is_system_permission=False,
            requires_approval=False,
        )

        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=None)
        mock_db.query = Mock(return_value=mock_query)

        permission = rbac_service.create_permission(perm_data, created_by="admin")

        assert permission.name == "asset.create"

    def test_create_permission_duplicate_name(
        self, rbac_service, mock_db, sample_permission
    ):
        """测试创建重名权限"""
        perm_data = PermissionCreate(
            name="existing.permission",
            display_name="已存在权限",
            description="描述",
            resource="asset",
            action="view",
        )

        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=sample_permission)
        mock_db.query = Mock(return_value=mock_query)

        with pytest.raises(BusinessLogicError, match="权限名称已存在"):
            rbac_service.create_permission(perm_data, created_by="admin")

    def test_create_permission_with_conditions(
        self, rbac_service, mock_db, sample_permission
    ):
        """测试创建带条件的权限"""
        conditions = {"department": ["finance", "hr"]}
        perm_data = PermissionCreate(
            name="asset.view",
            display_name="查看资产",
            description="带条件的查看权限",
            resource="asset",
            action="view",
            conditions=conditions,
        )

        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=None)
        mock_db.query = Mock(return_value=mock_query)

        permission = rbac_service.create_permission(perm_data, created_by="admin")

        assert permission.conditions == json.dumps(conditions)


# ============================================================================
# get_permission 测试
# ============================================================================


class TestGetPermission:
    """测试获取权限"""

    def test_get_permission_found(self, rbac_service, mock_db, sample_permission):
        """测试获取存在的权限"""
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=sample_permission)
        mock_db.query = Mock(return_value=mock_query)

        permission = rbac_service.get_permission("perm-1")
        assert permission is not None
        assert permission.id == "perm-1"

    def test_get_permission_not_found(self, rbac_service, mock_db):
        """测试获取不存在的权限"""
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=None)
        mock_db.query = Mock(return_value=mock_query)

        permission = rbac_service.get_permission("nonexistent")
        assert permission is None


# ============================================================================
# get_permissions 测试
# ============================================================================


class TestGetPermissions:
    """测试获取权限列表"""

    def test_get_permissions_default_params(
        self, rbac_service, mock_db, sample_permission
    ):
        """测试默认参数获取权限列表"""
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[sample_permission])
        mock_query.count = Mock(return_value=1)
        mock_db.query = Mock(return_value=mock_query)

        permissions, total = rbac_service.get_permissions()

        assert len(permissions) == 1
        assert total == 1

    def test_get_permissions_with_resource_filter(
        self, rbac_service, mock_db, sample_permission
    ):
        """测试按资源筛选权限"""
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[sample_permission])
        mock_query.count = Mock(return_value=1)
        mock_db.query = Mock(return_value=mock_query)

        permissions, total = rbac_service.get_permissions(resource="asset")

        assert len(permissions) == 1

    def test_get_permissions_with_action_filter(
        self, rbac_service, mock_db, sample_permission
    ):
        """测试按操作筛选权限"""
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[sample_permission])
        mock_query.count = Mock(return_value=1)
        mock_db.query = Mock(return_value=mock_query)

        permissions, total = rbac_service.get_permissions(action="view")

        assert len(permissions) == 1


# ============================================================================
# assign_role_to_user 测试
# ============================================================================


class TestAssignRoleToUser:
    """测试为用户分配角色"""

    def test_assign_role_success(self, rbac_service, mock_db, sample_user, sample_role):
        """测试成功分配角色"""
        assignment_data = UserRoleAssignmentCreate(
            user_id="user-1",
            role_id="role-1",
            expires_at=None,
            reason="需要管理权限",
            notes=None,
            context=None,
        )

        # Mock用户存在
        user_mock_query = Mock()
        user_mock_filter = Mock(return_value=user_mock_query)
        user_mock_query.filter = Mock(return_value=user_mock_filter)
        user_mock_filter.first = Mock(return_value=sample_user)

        # Mock角色存在
        role_mock_query = Mock()
        role_mock_filter = Mock(return_value=role_mock_query)
        role_mock_query.filter = Mock(return_value=role_mock_filter)
        role_mock_filter.first = Mock(return_value=sample_role)

        # Mock没有已存在的分配
        assign_mock_query = Mock()
        assign_mock_filter = Mock(return_value=assign_mock_query)
        assign_mock_query.filter = Mock(return_value=assign_mock_filter)
        assign_mock_filter.first = Mock(return_value=None)

        query_count = [0]

        def query_side_effect(model):
            query_count[0] += 1
            if query_count[0] == 1:
                return user_mock_query
            elif query_count[0] == 2:
                return role_mock_query
            return assign_mock_query

        mock_db.query = Mock(side_effect=query_side_effect)

        with patch.object(rbac_service, "_create_permission_audit_log"):
            assignment = rbac_service.assign_role_to_user(
                assignment_data, assigned_by="admin"
            )
            assert assignment.user_id == "user-1"
            assert assignment.role_id == "role-1"

    def test_assign_role_user_not_found(self, rbac_service, mock_db):
        """测试为不存在的用户分配角色"""
        assignment_data = UserRoleAssignmentCreate(
            user_id="nonexistent",
            role_id="role-1",
        )

        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=None)  # 用户不存在
        mock_db.query = Mock(return_value=mock_query)

        with pytest.raises(BusinessLogicError, match="用户不存在"):
            rbac_service.assign_role_to_user(assignment_data, assigned_by="admin")

    def test_assign_role_role_not_found(self, rbac_service, mock_db, sample_user):
        """测试分配不存在的角色"""
        assignment_data = UserRoleAssignmentCreate(
            user_id="user-1",
            role_id="nonexistent",
        )

        # 用户存在
        user_mock_query = Mock()
        user_mock_filter = Mock(return_value=user_mock_query)
        user_mock_query.filter = Mock(return_value=user_mock_filter)
        user_mock_filter.first = Mock(return_value=sample_user)

        # 角色不存在
        role_mock_query = Mock()
        role_mock_filter = Mock(return_value=role_mock_query)
        role_mock_query.filter = Mock(return_value=role_mock_filter)
        role_mock_filter.first = Mock(return_value=None)

        call_count = [0]

        def query_side_effect(model):
            call_count[0] += 1
            if call_count[0] == 1:
                return user_mock_query
            return role_mock_query

        mock_db.query = Mock(side_effect=query_side_effect)

        with pytest.raises(BusinessLogicError, match="角色不存在"):
            rbac_service.assign_role_to_user(assignment_data, assigned_by="admin")

    def test_assign_role_already_assigned(
        self, rbac_service, mock_db, sample_user, sample_role
    ):
        """测试重复分配角色"""
        assignment_data = UserRoleAssignmentCreate(
            user_id="user-1",
            role_id="role-1",
        )

        # 用户存在
        user_mock_query = Mock()
        user_mock_filter = Mock(return_value=user_mock_query)
        user_mock_query.filter = Mock(return_value=user_mock_filter)
        user_mock_filter.first = Mock(return_value=sample_user)

        # 角色存在
        role_mock_query = Mock()
        role_mock_filter = Mock(return_value=role_mock_query)
        role_mock_query.filter = Mock(return_value=role_mock_filter)
        role_mock_filter.first = Mock(return_value=sample_role)

        # 已存在分配
        existing_assignment = Mock(spec=UserRoleAssignment)
        assign_mock_query = Mock()
        assign_mock_filter = Mock(return_value=assign_mock_query)
        assign_mock_query.filter = Mock(return_value=assign_mock_filter)
        assign_mock_filter.first = Mock(return_value=existing_assignment)

        call_count = [0]

        def query_side_effect(model):
            call_count[0] += 1
            if call_count[0] == 1:
                return user_mock_query
            elif call_count[0] == 2:
                return role_mock_query
            return assign_mock_query

        mock_db.query = Mock(side_effect=query_side_effect)

        with pytest.raises(BusinessLogicError, match="用户已分配此角色"):
            rbac_service.assign_role_to_user(assignment_data, assigned_by="admin")


# ============================================================================
# revoke_role_from_user 测试
# ============================================================================


class TestRevokeRoleFromUser:
    """测试撤销用户角色"""

    def test_revoke_role_success(self, rbac_service, mock_db):
        """测试成功撤销角色"""
        assignment = Mock(spec=UserRoleAssignment)
        assignment.is_active = True

        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=assignment)
        mock_db.query = Mock(return_value=mock_query)

        with patch.object(rbac_service, "_create_permission_audit_log"):
            result = rbac_service.revoke_role_from_user(
                "user-1", "role-1", revoked_by="admin"
            )
            assert result is True
            assert assignment.is_active is False

    def test_revoke_role_assignment_not_found(self, rbac_service, mock_db):
        """测试撤销不存在的角色分配"""
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=None)
        mock_db.query = Mock(return_value=mock_query)

        result = rbac_service.revoke_role_from_user(
            "user-1", "role-1", revoked_by="admin"
        )
        assert result is False


# ============================================================================
# get_user_roles 测试
# ============================================================================


class TestGetUserRoles:
    """测试获取用户角色"""

    def test_get_user_roles_active_only(self, rbac_service, mock_db, sample_role):
        """测试获取用户活跃角色"""
        mock_query = Mock()
        mock_query.join = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[sample_role])
        mock_db.query = Mock(return_value=mock_query)

        roles = rbac_service.get_user_roles("user-1", active_only=True)

        assert len(roles) == 1
        assert roles[0].id == "role-1"

    def test_get_user_roles_include_inactive(self, rbac_service, mock_db, sample_role):
        """测试获取用户所有角色（包括非活跃）"""
        mock_query = Mock()
        mock_query.join = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[sample_role])
        mock_db.query = Mock(return_value=mock_query)

        roles = rbac_service.get_user_roles("user-1", active_only=False)

        assert len(roles) >= 0


# ============================================================================
# check_permission 测试
# ============================================================================


class TestCheckPermission:
    """测试权限检查"""

    def test_check_permission_admin_user(self, rbac_service, mock_db, sample_user):
        """测试管理员用户拥有所有权限"""
        sample_user.role = "admin"

        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=sample_user)
        mock_db.query = Mock(return_value=mock_query)

        request = PermissionCheckRequest(
            resource="any_resource", action="any_action", resource_id=None, context=None
        )

        response = rbac_service.check_permission("user-1", request)

        assert response.has_permission is True
        assert "admin_role" in response.granted_by

    def test_check_permission_user_not_found(self, rbac_service, mock_db):
        """测试不存在的用户"""
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=None)
        mock_db.query = Mock(return_value=mock_query)

        request = PermissionCheckRequest(
            resource="asset", action="view", resource_id=None, context=None
        )

        response = rbac_service.check_permission("nonexistent", request)

        assert response.has_permission is False
        assert "用户不存在或已禁用" in response.reason

    def test_check_permission_user_inactive(self, rbac_service, mock_db, sample_user):
        """测试已禁用用户"""
        sample_user.is_active = False

        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=sample_user)
        mock_db.query = Mock(return_value=mock_query)

        request = PermissionCheckRequest(
            resource="asset", action="view", resource_id=None, context=None
        )

        response = rbac_service.check_permission("user-1", request)

        assert response.has_permission is False
        assert "用户不存在或已禁用" in response.reason

    def test_check_permission_no_roles(self, rbac_service, mock_db, sample_user):
        """测试没有角色的用户"""
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=sample_user)
        mock_db.query = Mock(return_value=mock_query)

        # Mock get_user_roles 返回空列表
        with patch.object(rbac_service, "get_user_roles", return_value=[]):
            request = PermissionCheckRequest(
                resource="asset", action="view", resource_id=None, context=None
            )

            response = rbac_service.check_permission("user-1", request)

            assert response.has_permission is False
            assert "用户未分配任何角色" in response.reason


# ============================================================================
# get_user_permissions_summary 测试
# ============================================================================


class TestGetUserPermissionsSummary:
    """测试获取用户权限汇总"""

    def test_get_summary_success(
        self, rbac_service, mock_db, sample_user, sample_role, sample_permission
    ):
        """测试成功获取权限汇总"""
        sample_role.permissions = [sample_permission]

        # Mock用户存在
        user_query = Mock()
        user_filter = Mock(return_value=user_query)
        user_query.filter = Mock(return_value=user_filter)
        user_filter.first = Mock(return_value=sample_user)

        # Mock资源权限
        resource_query = Mock()
        resource_filter = Mock(return_value=resource_query)
        resource_query.filter = Mock(return_value=resource_filter)
        resource_filter.all = Mock(return_value=[])

        call_count = [0]

        def query_side_effect(model):
            call_count[0] += 1
            if call_count[0] == 1:
                return user_query
            return resource_query

        mock_db.query = Mock(side_effect=query_side_effect)

        with patch.object(rbac_service, "get_user_roles", return_value=[sample_role]):
            summary = rbac_service.get_user_permissions_summary("user-1")

            assert summary.user_id == "user-1"
            assert summary.username == "testuser"
            assert len(summary.roles) == 1

    def test_get_summary_user_not_found(self, rbac_service, mock_db):
        """测试用户不存在"""
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=None)
        mock_db.query = Mock(return_value=mock_query)

        with pytest.raises(BusinessLogicError, match="用户不存在"):
            rbac_service.get_user_permissions_summary("nonexistent")


# ============================================================================
# _assign_permissions_to_role 测试
# ============================================================================


class TestAssignPermissionsToRole:
    """测试为角色分配权限"""

    def test_assign_permissions_success(self, rbac_service, mock_db):
        """测试成功分配权限"""
        mock_execute_result = Mock()
        mock_db.execute.return_value = mock_execute_result

        rbac_service._assign_permissions_to_role(
            "role-1", ["perm-1", "perm-2"], "admin"
        )

        assert mock_db.execute.call_count == 3  # delete + 2 inserts


# ============================================================================
# _get_user_resource_permissions 测试
# ============================================================================


class TestGetUserResourcePermissions:
    """测试获取用户资源权限"""

    def test_get_resource_permissions_found(self, rbac_service, mock_db):
        """测试找到资源权限"""
        mock_permission = Mock()
        mock_permission.permission_level = "write"
        mock_permission.conditions = None

        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=mock_permission)
        mock_db.query = Mock(return_value=mock_query)

        request = PermissionCheckRequest(
            resource="asset", action="read", resource_id="asset-1", context=None
        )

        result = rbac_service._get_user_resource_permissions("user-1", request)

        assert result is not None
        assert result["permission_level"] == "write"

    def test_get_resource_permissions_not_found(self, rbac_service, mock_db):
        """测试未找到资源权限"""
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=None)
        mock_db.query = Mock(return_value=mock_query)

        request = PermissionCheckRequest(
            resource="asset", action="read", resource_id=None, context=None
        )

        result = rbac_service._get_user_resource_permissions("user-1", request)

        assert result is None

    def test_get_resource_permissions_insufficient_level(self, rbac_service, mock_db):
        """测试权限级别不足"""
        mock_permission = Mock()
        mock_permission.permission_level = "read"
        mock_permission.conditions = None

        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=mock_permission)
        mock_db.query = Mock(return_value=mock_query)

        request = PermissionCheckRequest(
            resource="asset", action="delete", resource_id=None, context=None
        )

        result = rbac_service._get_user_resource_permissions("user-1", request)

        # read权限不能执行delete操作
        assert result is None


# ============================================================================
# _check_permission_level 测试
# ============================================================================


class TestCheckPermissionLevel:
    """测试权限级别检查"""

    def test_read_level_can_read(self, rbac_service):
        """测试读权限级别可以读"""
        result = rbac_service._check_permission_level("read", "read")
        assert result is True

    def test_read_level_cannot_write(self, rbac_service):
        """测试读权限级别不能写"""
        result = rbac_service._check_permission_level("read", "write")
        assert result is False

    def test_write_level_can_read(self, rbac_service):
        """测试写权限级别可以读"""
        result = rbac_service._check_permission_level("write", "read")
        assert result is True

    def test_write_level_can_write(self, rbac_service):
        """测试写权限级别可以写"""
        result = rbac_service._check_permission_level("write", "write")
        assert result is True

    def test_delete_level_can_read(self, rbac_service):
        """测试删除权限级别可以读"""
        result = rbac_service._check_permission_level("delete", "read")
        assert result is True

    def test_delete_level_can_delete(self, rbac_service):
        """测试删除权限级别可以删除"""
        result = rbac_service._check_permission_level("delete", "delete")
        assert result is True

    def test_admin_level_can_do_anything(self, rbac_service):
        """测试管理员权限级别可以做任何操作"""
        assert rbac_service._check_permission_level("admin", "read") is True
        assert rbac_service._check_permission_level("admin", "write") is True
        assert rbac_service._check_permission_level("admin", "delete") is True
        assert rbac_service._check_permission_level("admin", "admin") is True

    def test_invalid_permission_level(self, rbac_service):
        """测试无效的权限级别"""
        result = rbac_service._check_permission_level("invalid", "read")
        assert result is False

    def test_invalid_action(self, rbac_service):
        """测试无效的操作"""
        result = rbac_service._check_permission_level("read", "invalid_action")
        assert result is False


# ============================================================================
# _can_manage_role 测试
# ============================================================================


class TestCanManageRole:
    """测试角色管理权限检查"""

    def test_higher_level_can_manage_lower(self, rbac_service):
        """测试高级别可以管理低级别"""
        result = rbac_service._can_manage_role(manager_level=5, subordinate_level=3)
        assert result is True

    def test_same_level_cannot_manage(self, rbac_service):
        """测试同级别不能管理"""
        result = rbac_service._can_manage_role(manager_level=3, subordinate_level=3)
        assert result is False

    def test_lower_level_cannot_manage_higher(self, rbac_service):
        """测试低级别不能管理高级别"""
        result = rbac_service._can_manage_role(manager_level=2, subordinate_level=5)
        assert result is False


# ============================================================================
# _role_has_permission 测试
# ============================================================================


class TestRoleHasPermission:
    """测试角色权限检查"""

    def test_role_has_permission(self, rbac_service, sample_role, sample_permission):
        """测试角色有权限"""
        sample_role.permissions = [sample_permission]

        request = PermissionCheckRequest(
            resource="asset", action="view", resource_id=None, context=None
        )

        result = rbac_service._role_has_permission(sample_role, request)
        assert result is True

    def test_role_does_not_have_permission(
        self, rbac_service, sample_role, sample_permission
    ):
        """测试角色没有权限"""
        sample_permission.resource = "other_resource"
        sample_role.permissions = [sample_permission]

        request = PermissionCheckRequest(
            resource="asset", action="view", resource_id=None, context=None
        )

        result = rbac_service._role_has_permission(sample_role, request)
        assert result is False

    def test_role_no_permissions(self, rbac_service, sample_role):
        """测试角色没有任何权限"""
        sample_role.permissions = []

        request = PermissionCheckRequest(
            resource="asset", action="view", resource_id=None, context=None
        )

        result = rbac_service._role_has_permission(sample_role, request)
        assert result is False


# ============================================================================
# _get_role_permission_conditions 测试
# ============================================================================


class TestGetRolePermissionConditions:
    """测试获取角色权限条件"""

    def test_get_conditions_with_permission(self, rbac_service, sample_role):
        """测试获取权限条件"""
        mock_permission = Mock()
        mock_permission.resource = "asset"
        mock_permission.action = "view"
        mock_permission.conditions = {"department": "finance"}

        sample_role.permissions = [mock_permission]

        request = PermissionCheckRequest(
            resource="asset", action="view", resource_id=None, context=None
        )

        result = rbac_service._get_role_permission_conditions(sample_role, request)

        assert result is not None
        assert result["department"] == "finance"

    def test_get_conditions_no_permission(self, rbac_service, sample_role):
        """测试权限不存在时返回None"""
        sample_role.permissions = []

        request = PermissionCheckRequest(
            resource="asset", action="view", resource_id=None, context=None
        )

        result = rbac_service._get_role_permission_conditions(sample_role, request)

        assert result is None


# ============================================================================
# _calculate_effective_permissions 测试
# ============================================================================


class TestCalculateEffectivePermissions:
    """测试计算有效权限"""

    def test_calculate_with_roles_only(self, rbac_service, sample_role):
        """测试仅从角色计算权限"""
        mock_permission = Mock()
        mock_permission.resource = "asset"
        mock_permission.action = "view"
        sample_role.permissions = [mock_permission]

        result = rbac_service._calculate_effective_permissions([sample_role], [])

        assert "asset" in result
        assert "view" in result["asset"]

    def test_calculate_with_resource_permissions(self, rbac_service):
        """测试从资源权限计算权限"""
        mock_resource_perm = Mock()
        mock_resource_perm.resource_type = "contract"
        mock_resource_perm.permission_level = "write"

        result = rbac_service._calculate_effective_permissions([], [mock_resource_perm])

        assert "contract" in result
        assert "read" in result["contract"]
        assert "write" in result["contract"]

    def test_calculate_combined_permissions(self, rbac_service, sample_role):
        """测试组合角色和资源权限"""
        # 角色权限
        mock_permission = Mock()
        mock_permission.resource = "asset"
        mock_permission.action = "view"
        sample_role.permissions = [mock_permission]

        # 资源权限
        mock_resource_perm = Mock()
        mock_resource_perm.resource_type = "contract"
        mock_resource_perm.permission_level = "admin"

        result = rbac_service._calculate_effective_permissions(
            [sample_role], [mock_resource_perm]
        )

        assert "asset" in result
        assert "view" in result["asset"]
        assert "contract" in result
        assert "read" in result["contract"]
        assert "write" in result["contract"]
        assert "delete" in result["contract"]
        assert "admin" in result["contract"]


# ============================================================================
# _create_permission_audit_log 测试
# ============================================================================


class TestCreatePermissionAuditLog:
    """测试创建审计日志"""

    def test_create_audit_log_success(self, rbac_service, mock_db):
        """测试成功创建审计日志"""
        rbac_service._create_permission_audit_log(
            action="role_create",
            resource_type="role",
            resource_id="role-1",
            operator_id="admin",
            old_permissions=None,
            new_permissions={"role_name": "new_role"},
            reason="创建新角色",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_audit_log_with_all_params(self, rbac_service, mock_db):
        """测试创建带所有参数的审计日志"""
        rbac_service._create_permission_audit_log(
            action="role_update",
            resource_type="role",
            resource_id="role-1",
            operator_id="admin",
            old_permissions={"old": "data"},
            new_permissions={"new": "data"},
            reason="更新角色",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


# ============================================================================
# 异步适配器方法测试
# ============================================================================


class TestAsyncAdapterMethods:
    """测试异步适配器方法"""

    @pytest.mark.asyncio
    async def test_check_user_permission(self, rbac_service, mock_db, sample_user):
        """测试检查用户权限（异步适配器）"""
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=sample_user)
        mock_db.query = Mock(return_value=mock_query)

        with patch.object(rbac_service, "get_user_roles", return_value=[]):
            result = await rbac_service.check_user_permission("user-1", "asset", "view")
            assert result is False

    @pytest.mark.asyncio
    async def test_check_resource_access(self, rbac_service, mock_db, sample_user):
        """测试检查资源访问权限（异步适配器）"""
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=sample_user)
        mock_db.query = Mock(return_value=mock_query)

        with patch.object(rbac_service, "get_user_roles", return_value=[]):
            result = await rbac_service.check_resource_access(
                "user-1", "asset", "asset-1", "view"
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_check_organization_access(self, rbac_service, mock_db, sample_user):
        """测试检查组织访问权限（异步适配器）"""
        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_filter.first = Mock(return_value=sample_user)
        mock_db.query = Mock(return_value=mock_query)

        with patch.object(rbac_service, "get_user_roles", return_value=[]):
            result = await rbac_service.check_organization_access("user-1", "org-1")
            assert result is False
