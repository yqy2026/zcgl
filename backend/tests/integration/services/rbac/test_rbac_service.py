"""
RBACService 集成测试
测试角色、权限、用户角色分配等功能
"""

import pytest
from sqlalchemy.orm import Session

from src.models.rbac import Role, UserRoleAssignment
from src.schemas.rbac import RoleCreate, RoleUpdate, UserRoleAssignmentCreate
from src.services.rbac.service import RBACService

# ============================================================================
# Test Data Factory
# ============================================================================


class RBACTestDataFactory:
    """RBAC 测试数据工厂"""

    @staticmethod
    def create_role_dict(**kwargs):
        """生成角色创建数据"""
        default_data = {
            "name": "test_role",
            "display_name": "测试角色",
            "description": "这是一个测试角色",
            "level": 1,
            "category": "custom",
            "scope": "global",
            "is_system_role": False,
        }
        default_data.update(kwargs)
        return default_data

    @staticmethod
    def create_permission_dict(db: Session, **kwargs):
        """生成权限创建数据并返回Permission对象"""
        from src.crud.rbac import permission_crud

        default_data = {
            "name": "test:permission",
            "display_name": "测试权限",
            "description": "测试权限描述",
            "resource": "test",
            "action": "read",
        }
        default_data.update(kwargs)

        return permission_crud.create(db, obj_in=default_data, commit=False)


# ============================================================================
# Test Class 1: Role Creation
# ============================================================================


class TestRoleCreation:
    """角色创建测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.service = RBACService()
        self.factory = RBACTestDataFactory()

    def test_create_role_success(self):
        """测试成功创建角色"""
        role_data = RoleCreate(**self.factory.create_role_dict())

        role = self.service.create_role(
            self.db, obj_in=role_data, created_by="test_user"
        )

        assert role.id is not None
        assert role.name == "test_role"
        assert role.display_name == "测试角色"
        assert role.created_by == "test_user"

    def test_create_role_with_permissions(self):
        """测试创建带权限的角色"""
        # 创建权限
        perm1 = self.factory.create_permission_dict(self.db, name="asset:read")
        perm2 = self.factory.create_permission_dict(self.db, name="asset:write")
        self.db.commit()

        role_data = RoleCreate(
            **self.factory.create_role_dict(permission_ids=[perm1.id, perm2.id])
        )

        role = self.service.create_role(
            self.db, obj_in=role_data, created_by="test_user"
        )

        assert role.id is not None
        # 验证权限已关联（通过查询验证）

    def test_create_duplicate_name_raises_error(self):
        """测试创建重复名称角色抛出异常"""
        role_data = RoleCreate(**self.factory.create_role_dict())

        # 创建第一个角色
        self.service.create_role(self.db, obj_in=role_data, created_by="test_user")

        # 尝试创建相同名称的角色
        with pytest.raises(ValueError, match="角色名称.*已存在"):
            self.service.create_role(self.db, obj_in=role_data, created_by="test_user")


# ============================================================================
# Test Class 2: Role Update
# ============================================================================


class TestRoleUpdate:
    """角色更新测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.service = RBACService()
        self.factory = RBACTestDataFactory()

        # 创建测试角色
        self.role = self.service.create_role(
            self.db,
            obj_in=RoleCreate(**self.factory.create_role_dict()),
            created_by="test_user",
        )

    def test_update_role_basic_fields(self):
        """测试更新角色基本信息"""
        update_data = RoleUpdate(
            display_name="更新后的角色", description="更新后的描述"
        )

        updated = self.service.update_role(
            self.db, role_id=self.role.id, obj_in=update_data, updated_by="test_user"
        )

        assert updated.display_name == "更新后的角色"
        assert updated.description == "更新后的描述"
        assert updated.updated_by == "test_user"

    def test_update_nonexistent_role_raises_error(self):
        """测试更新不存在的角色抛出异常"""
        with pytest.raises(ValueError, match="角色不存在"):
            self.service.update_role(
                self.db,
                role_id="nonexistent-id",
                obj_in=RoleUpdate(display_name="新名称"),
                updated_by="test_user",
            )


# ============================================================================
# Test Class 3: Role Deletion
# ============================================================================


class TestRoleDeletion:
    """角色删除测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.service = RBACService()
        self.factory = RBACTestDataFactory()

    def test_delete_role_success(self):
        """测试成功删除角色"""
        role = self.service.create_role(
            self.db,
            obj_in=RoleCreate(**self.factory.create_role_dict()),
            created_by="test_user",
        )
        role_id = role.id

        result = self.service.delete_role(
            self.db, role_id=role_id, deleted_by="test_user"
        )

        assert result is True

        # 验证角色已删除
        deleted = self.db.query(Role).filter(Role.id == role_id).first()
        assert deleted is None

    def test_delete_nonexistent_role_returns_false(self):
        """测试删除不存在的角色返回False"""
        result = self.service.delete_role(
            self.db, role_id="nonexistent-id", deleted_by="test_user"
        )
        assert result is False


# ============================================================================
# Test Class 4: Permission Assignment
# ============================================================================


class TestPermissionAssignment:
    """权限分配测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.service = RBACService()
        self.factory = RBACTestDataFactory()

        # 创建测试角色和权限
        self.role = self.service.create_role(
            self.db,
            obj_in=RoleCreate(**self.factory.create_role_dict()),
            created_by="test_user",
        )
        self.perm1 = self.factory.create_permission_dict(self.db, name="asset:read")
        self.perm2 = self.factory.create_permission_dict(self.db, name="asset:write")
        self.db.commit()

    def test_update_role_permissions(self):
        """测试更新角色权限"""
        # 添加权限到角色
        self.service.update_role_permissions(
            self.db,
            role_id=self.role.id,
            permission_ids=[self.perm1.id, self.perm2.id],
            updated_by="test_user",
        )

        # 验证权限已分配
        # (需要通过查询role_permissions表验证)

    def test_clear_role_permissions(self):
        """测试清除角色权限"""
        # 先添加权限
        self.service.update_role_permissions(
            self.db,
            role_id=self.role.id,
            permission_ids=[self.perm1.id],
            updated_by="test_user",
        )

        # 清除权限
        self.service.update_role_permissions(
            self.db, role_id=self.role.id, permission_ids=[], updated_by="test_user"
        )

        # 验证权限已清除


# ============================================================================
# Test Class 5: User Role Assignment
# ============================================================================


class TestUserRoleAssignment:
    """用户角色分配测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.service = RBACService()
        self.factory = RBACTestDataFactory()

        # 创建测试角色
        self.role = self.service.create_role(
            self.db,
            obj_in=RoleCreate(**self.factory.create_role_dict()),
            created_by="test_user",
        )

    def test_assign_role_to_user(self):
        """测试为用户分配角色"""
        assignment_data = UserRoleAssignmentCreate(
            user_id="test_user_id", role_id=self.role.id
        )

        assignment = self.service.assign_role_to_user(
            self.db, obj_in=assignment_data, assigned_by="admin"
        )

        assert assignment.id is not None
        assert assignment.user_id == "test_user_id"
        assert assignment.role_id == self.role.id

    def test_assign_duplicate_role_raises_error(self):
        """测试重复分配角色抛出异常"""
        assignment_data = UserRoleAssignmentCreate(
            user_id="test_user_id", role_id=self.role.id
        )

        # 第一次分配
        self.service.assign_role_to_user(
            self.db, obj_in=assignment_data, assigned_by="admin"
        )

        # 尝试重复分配
        with pytest.raises(ValueError, match="用户已分配此角色"):
            self.service.assign_role_to_user(
                self.db, obj_in=assignment_data, assigned_by="admin"
            )

    def test_revoke_user_role(self):
        """测试撤销用户角色"""
        assignment_data = UserRoleAssignmentCreate(
            user_id="test_user_id", role_id=self.role.id
        )

        # 先分配角色
        assignment = self.service.assign_role_to_user(
            self.db, obj_in=assignment_data, assigned_by="admin"
        )

        # 撤销角色
        result = self.service.revoke_user_role(
            self.db, user_id="test_user_id", role_id=self.role.id
        )

        assert result is True

        # 验证已撤销（记录仍存在但is_active=False）
        revoked = (
            self.db.query(UserRoleAssignment)
            .filter(UserRoleAssignment.id == assignment.id)
            .first()
        )
        assert revoked is not None
        assert revoked.is_active is False
