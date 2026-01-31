"""
RBAC CRUD 操作单元测试
"""

from unittest.mock import MagicMock, patch

import pytest

from src.crud.rbac import (
    CRUDPermission,
    CRUDRole,
    CRUDUserRoleAssignment,
    permission_crud,
    role_crud,
    user_role_assignment_crud,
)
from src.models.rbac import Permission, Role, UserRoleAssignment


# ============================================================================
# CRUDRole 测试
# ============================================================================
class TestCRUDRole:
    """测试角色 CRUD"""

    @pytest.fixture
    def crud(self):
        """创建角色 CRUD 实例"""
        return CRUDRole(Role)

    @pytest.fixture
    def mock_role(self):
        """模拟角色对象"""
        role = MagicMock(spec=Role)
        role.id = "role_123"
        role.name = "admin"
        role.display_name = "管理员"
        role.category = "system"
        role.is_active = True
        role.level = 1
        return role

    def test_create_filters_permission_ids(self, crud, mock_db):
        """测试创建时过滤 permission_ids 字段"""
        role_data = {
            "name": "test_role",
            "display_name": "测试角色",
            "permission_ids": ["perm_1", "perm_2"],  # 应该被过滤
        }

        with patch.object(crud, "query_builder"):
            with patch("src.crud.base.CRUDBase.create") as mock_create:
                mock_create.return_value = MagicMock(spec=Role)
                crud.create(mock_db, obj_in=role_data)

                # 验证 permission_ids 被移除
                call_args = mock_create.call_args
                assert "permission_ids" not in call_args.kwargs.get("obj_in", {})

    def test_get_by_name_success(self, crud, mock_db, mock_role):
        """测试根据名称获取角色"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_role

        result = crud.get_by_name(mock_db, "admin")

        assert result == mock_role
        mock_db.query.assert_called_once_with(Role)

    def test_get_by_name_not_found(self, crud, mock_db):
        """测试角色名称不存在"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = crud.get_by_name(mock_db, "nonexistent")

        assert result is None

    def test_get_multi_with_filters(self, crud, mock_db, mock_role):
        """测试带筛选条件的角色列表"""
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = [mock_role]
        mock_db.execute.return_value = mock_execute

        # Mock count query
        mock_count = MagicMock()
        mock_count.scalar.return_value = 1
        mock_db.execute.side_effect = [mock_execute, mock_count]

        with patch.object(crud.query_builder, "build_query") as mock_build:
            with patch.object(
                crud.query_builder, "build_count_query"
            ) as mock_count_build:
                mock_build.return_value = MagicMock()
                mock_count_build.return_value = MagicMock()

                roles, total = crud.get_multi_with_filters(
                    mock_db,
                    category="system",
                    is_active=True,
                    search="admin",
                )

        assert len(roles) == 1
        assert total == 1

    def test_count_by_category(self, crud, mock_db):
        """测试按类别统计角色数"""
        mock_db.query.return_value.group_by.return_value.all.return_value = [
            ("system", 5),
            ("custom", 10),
        ]

        result = crud.count_by_category(mock_db)

        assert result["system"] == 5
        assert result["custom"] == 10


# ============================================================================
# CRUDPermission 测试
# ============================================================================
class TestCRUDPermission:
    """测试权限 CRUD"""

    @pytest.fixture
    def crud(self):
        """创建权限 CRUD 实例"""
        return CRUDPermission(Permission)

    @pytest.fixture
    def mock_permission(self):
        """模拟权限对象"""
        perm = MagicMock(spec=Permission)
        perm.id = "perm_123"
        perm.name = "asset:read"
        perm.display_name = "读取资产"
        perm.resource = "asset"
        perm.action = "read"
        perm.is_system_permission = True
        return perm

    def test_get_multi_with_filters(self, crud, mock_db, mock_permission):
        """测试带筛选条件的权限列表"""
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = [mock_permission]
        mock_db.execute.return_value = mock_execute

        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()

            permissions = crud.get_multi_with_filters(
                mock_db,
                resource="asset",
                action="read",
                is_system_permission=True,
            )

        assert len(permissions) == 1

    def test_count_by_resource(self, crud, mock_db):
        """测试按资源统计权限数"""
        mock_db.query.return_value.group_by.return_value.all.return_value = [
            ("asset", 10),
            ("user", 5),
            ("role", 3),
        ]

        result = crud.count_by_resource(mock_db)

        assert result["asset"] == 10
        assert result["user"] == 5
        assert result["role"] == 3


# ============================================================================
# CRUDUserRoleAssignment 测试
# ============================================================================
class TestCRUDUserRoleAssignment:
    """测试用户角色分配 CRUD"""

    @pytest.fixture
    def crud(self):
        """创建用户角色分配 CRUD 实例"""
        return CRUDUserRoleAssignment(UserRoleAssignment)

    @pytest.fixture
    def mock_assignment(self):
        """模拟用户角色分配对象"""
        assignment = MagicMock(spec=UserRoleAssignment)
        assignment.id = "assignment_123"
        assignment.user_id = "user_123"
        assignment.role_id = "role_123"
        assignment.is_active = True
        assignment.expires_at = None
        return assignment

    def test_get_by_user_and_role_success(self, crud, mock_db, mock_assignment):
        """测试根据用户和角色获取分配"""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_assignment
        )

        result = crud.get_by_user_and_role(mock_db, "user_123", "role_123")

        assert result == mock_assignment

    def test_get_by_user_and_role_not_found(self, crud, mock_db):
        """测试分配不存在"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = crud.get_by_user_and_role(mock_db, "user_123", "role_456")

        assert result is None

    def test_get_user_active_assignments(self, crud, mock_db, mock_assignment):
        """测试获取用户活跃角色"""
        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_assignment
        ]

        result = crud.get_user_active_assignments(mock_db, "user_123")

        assert len(result) == 1
        assert result[0] == mock_assignment

    def test_get_user_active_assignments_empty(self, crud, mock_db):
        """测试用户没有活跃角色"""
        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = crud.get_user_active_assignments(mock_db, "user_without_roles")

        assert result == []

    def test_count_by_role(self, crud, mock_db):
        """测试统计角色的用户数"""
        mock_db.query.return_value.filter.return_value.count.return_value = 10

        result = crud.count_by_role(mock_db, "role_123")

        assert result == 10


# ============================================================================
# 全局实例测试
# ============================================================================
class TestGlobalInstances:
    """测试全局实例"""

    def test_role_crud_instance_exists(self):
        """测试角色 CRUD 全局实例存在"""
        assert role_crud is not None
        assert isinstance(role_crud, CRUDRole)

    def test_permission_crud_instance_exists(self):
        """测试权限 CRUD 全局实例存在"""
        assert permission_crud is not None
        assert isinstance(permission_crud, CRUDPermission)

    def test_user_role_assignment_crud_instance_exists(self):
        """测试用户角色分配 CRUD 全局实例存在"""
        assert user_role_assignment_crud is not None
        assert isinstance(user_role_assignment_crud, CRUDUserRoleAssignment)
