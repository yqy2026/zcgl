"""
用户和权限测试数据工厂
完整的RBAC测试数据生成体系
支持复杂权限场景和组织层级测试
"""

from datetime import datetime, timedelta

import factory

from src.models.auth import User
from src.models.organization import Organization
from src.models.rbac import Permission, Role, UserRoleAssignment


class OrganizationFactory(factory.Factory):
    """组织架构数据工厂"""

    class Meta:
        model = Organization
        sqlalchemy_session_persistence = True

    name = factory.Sequence(lambda n: f"测试组织_{n}")
    code = factory.Sequence(lambda n: f"ORG_{n:03d}")
    description = factory.Faker('paragraph', nb_sentences=2)
    parent_id = None  # 顶级组织
    level = 1
    sort_order = factory.Sequence(lambda n: n)
    is_active = True
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)
    created_by = 'test_user'
    updated_by = 'test_user'
    tenant_id = 'test_tenant_001'


class ChildOrganizationFactory(OrganizationFactory):
    """子级组织工厂"""

    parent_id = 1  # 模拟父级组织ID
    level = 2
    name = factory.Sequence(lambda n: f"测试子组织_{n}")
    code = factory.Sequence(lambda n: f"SUBORG_{n:03d}")


class PermissionFactory(factory.Factory):
    """权限数据工厂"""

    class Meta:
        model = Permission
        sqlalchemy_session_persistence = True

    name = factory.Sequence(lambda n: f"permission_{n}")
    display_name = factory.Faker('catch_phrase')
    description = factory.Faker('sentence', nb_sentences=1)
    resource = factory.Faker('random_element', elements=[
        'assets', 'users', 'roles', 'organizations', 'reports',
        'system_settings', 'audit_logs', 'backups'
    ])
    action = factory.Faker('random_element', elements=[
        'create', 'read', 'update', 'delete', 'admin', 'approve',
        'export', 'import', 'manage', 'monitor'
    ])
    max_level = factory.Faker('random_int', min=1, max=10)
    is_system_permission = False
    requires_approval = factory.Faker('boolean')
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)
    tenant_id = 'test_tenant_001'


class RoleFactory(factory.Factory):
    """角色数据工厂"""

    class Meta:
        model = Role
        sqlalchemy_session_persistence = True

    name = factory.Sequence(lambda n: f"role_{n}")
    display_name = factory.Faker('job')
    description = factory.Faker('paragraph', nb_sentences=2)
    level = factory.Faker('random_int', min=1, max=10)
    category = factory.Faker('random_element', elements=[
        '业务', '管理', '系统', '审计', '运营'
    ])
    is_system_role = False
    organization_id = 1
    scope = factory.Faker('random_element', elements=[
        'organization', 'department', 'team', 'project'
    ])
    scope_id = 'test_scope_001'
    is_active = True
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)
    created_by = 'test_user'
    updated_by = 'test_user'
    tenant_id = 'test_tenant_001'


class UserFactory(factory.Factory):
    """用户数据工厂"""

    class Meta:
        model = User
        sqlalchemy_session_persistence = True

    username = factory.Faker('user_name')
    email = factory.Faker('email')
    full_name = factory.Faker('name')
    phone = factory.Faker('phone_number')
    department = factory.Faker('company')
    position = factory.Faker('job')
    employee_id = factory.Sequence(lambda n: f"EMP_{n:06d}")
    is_active = True
    is_superuser = False
    last_login = None
    password_hash = "$2b$12$fake_hash_for_testing"
    organization_id = 1
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)
    created_by = 'test_user'
    updated_by = 'test_user'
    tenant_id = 'test_tenant_001'


class AdminUserFactory(UserFactory):
    """管理员用户工厂"""

    username = 'admin'
    email = 'admin@example.com'
    full_name = '系统管理员'
    is_active = True
    is_superuser = True
    employee_id = 'ADMIN_001'


class InactiveUserFactory(UserFactory):
    """非活跃用户工厂"""

    is_active = False
    username = factory.Sequence(lambda n: f"inactive_user_{n}")


class UserRoleAssignmentFactory(factory.Factory):
    """用户角色分配工厂"""

    class Meta:
        model = UserRoleAssignment
        sqlalchemy_session_persistence = True

    user_id = 1
    role_id = 1
    assigned_by = 'admin'
    assigned_at = factory.LazyFunction(datetime.now)
    expires_at = factory.LazyAttribute(
        lambda obj: obj.assigned_at + timedelta(days=365)
    )
    is_active = True
    notes = factory.Faker('sentence', nb_sentences=1)
    tenant_id = 'test_tenant_001'


# 预定义权限场景
class AssetPermissionsFactory:
    """资产管理相关权限工厂"""

    @staticmethod
    def create_full_asset_permissions():
        """创建完整的资产管理权限"""
        permissions = []
        resources = ['assets', 'asset_history', 'asset_categories']
        actions = ['create', 'read', 'update', 'delete', 'export', 'import']

        for resource in resources:
            for action in actions:
                perm = PermissionFactory.create(
                    name=f"{resource}_{action}",
                    display_name=f"{resource}_{action}",
                    resource=resource,
                    action=action,
                    max_level=5 if action == 'admin' else 3
                )
                permissions.append(perm)

        return permissions

    @staticmethod
    def create_readonly_asset_permissions():
        """创建只读资产权限"""
        return [
            PermissionFactory.create(
                name='assets_read',
                display_name='资产查看',
                resource='assets',
                action='read',
                max_level=1
            ),
            PermissionFactory.create(
                name='asset_export',
                display_name='资产导出',
                resource='assets',
                action='export',
                max_level=2
            )
        ]


class SystemPermissionsFactory:
    """系统管理相关权限工厂"""

    @staticmethod
    def create_full_system_permissions():
        """创建完整的系统管理权限"""
        permissions = []
        resources = ['users', 'roles', 'organizations', 'system_settings']
        actions = ['create', 'read', 'update', 'delete', 'admin']

        for resource in resources:
            for action in actions:
                perm = PermissionFactory.create(
                    name=f"{resource}_{action}",
                    display_name=f"{resource}_{action}",
                    resource=resource,
                    action=action,
                    max_level=10,
                    is_system_permission=True,
                    requires_approval=True
                )
                permissions.append(perm)

        return permissions

    @staticmethod
    def create_audit_permissions():
        """创建审计权限"""
        return [
            PermissionFactory.create(
                name='audit_logs_read',
                display_name='审计日志查看',
                resource='audit_logs',
                action='read',
                max_level=8,
                is_system_permission=True
            ),
            PermissionFactory.create(
                name='audit_logs_export',
                display_name='审计日志导出',
                resource='audit_logs',
                action='export',
                max_level=9,
                is_system_permission=True
            )
        ]


# 预定义角色场景
class BusinessRolesFactory:
    """业务角色工厂"""

    @staticmethod
    def create_asset_manager_role():
        """创建资产管理员角色"""
        role = RoleFactory.create(
            name='asset_manager',
            display_name='资产管理员',
            description='负责资产的增删改查和日常管理',
            level=5,
            category='业务',
            scope='organization'
        )

        # 分配资产相关权限
        asset_perms = AssetPermissionsFactory.create_full_asset_permissions()
        for perm in asset_perms:
            role.permissions.append(perm)

        return role

    @staticmethod
    def create_asset_viewer_role():
        """创建资产查看员角色"""
        role = RoleFactory.create(
            name='asset_viewer',
            display_name='资产查看员',
            description='只能查看资产信息，不能修改',
            level=2,
            category='业务',
            scope='organization'
        )

        # 分配只读权限
        readonly_perms = AssetPermissionsFactory.create_readonly_asset_permissions()
        for perm in readonly_perms:
            role.permissions.append(perm)

        return role

    @staticmethod
    def create_financial_analyst_role():
        """创建财务分析师角色"""
        role = RoleFactory.create(
            name='financial_analyst',
            display_name='财务分析师',
            description='负责财务数据分析和报表生成',
            level=4,
            category='业务',
            scope='organization'
        )

        # 分配财务相关权限
        financial_perms = [
            PermissionFactory.create(
                name='financial_reports_read',
                display_name='财务报表查看',
                resource='reports',
                action='read',
                max_level=4
            ),
            PermissionFactory.create(
                name='financial_reports_export',
                display_name='财务报表导出',
                resource='reports',
                action='export',
                max_level=4
            )
        ]

        for perm in financial_perms:
            role.permissions.append(perm)

        return role


class SystemRolesFactory:
    """系统角色工厂"""

    @staticmethod
    def create_system_admin_role():
        """创建系统管理员角色"""
        role = RoleFactory.create(
            name='system_admin',
            display_name='系统管理员',
            description='系统最高权限管理员',
            level=10,
            category='系统',
            scope='organization',
            is_system_role=True
        )

        # 分配所有系统权限
        system_perms = SystemPermissionsFactory.create_full_system_permissions()
        for perm in system_perms:
            role.permissions.append(perm)

        return role

    @staticmethod
    def create_auditor_role():
        """创建审计员角色"""
        role = RoleFactory.create(
            name='auditor',
            display_name='审计员',
            description='负责系统审计和合规检查',
            level=8,
            category='审计',
            scope='organization',
            is_system_role=True
        )

        # 分配审计权限
        audit_perms = SystemPermissionsFactory.create_audit_permissions()
        for perm in audit_perms:
            role.permissions.append(perm)

        return role


# 用户场景工厂
class UserScenariosFactory:
    """用户场景工厂"""

    @staticmethod
    def create_complete_user_hierarchy():
        """创建完整的用户层级结构"""
        # 创建组织架构
        parent_org = OrganizationFactory.create(name="总公司")
        child_org1 = ChildOrganizationFactory.create(
            name="技术部",
            parent_id=parent_org.id
        )
        child_org2 = ChildOrganizationFactory.create(
            name="财务部",
            parent_id=parent_org.id
        )

        # 创建系统管理员
        system_admin_role = SystemRolesFactory.create_system_admin_role()
        system_admin = AdminUserFactory.create(
            organization_id=parent_org.id
        )
        UserRoleAssignmentFactory.create(
            user_id=system_admin.id,
            role_id=system_admin_role.id
        )

        # 创建资产管理员
        asset_manager_role = BusinessRolesFactory.create_asset_manager_role()
        asset_manager = UserFactory.create(
            username="asset_manager",
            full_name="资产管理员",
            organization_id=child_org1.id
        )
        UserRoleAssignmentFactory.create(
            user_id=asset_manager.id,
            role_id=asset_manager_role.id
        )

        # 创建资产查看员
        asset_viewer_role = BusinessRolesFactory.create_asset_viewer_role()
        asset_viewer = UserFactory.create(
            username="asset_viewer",
            full_name="资产查看员",
            organization_id=child_org1.id
        )
        UserRoleAssignmentFactory.create(
            user_id=asset_viewer.id,
            role_id=asset_viewer_role.id
        )

        # 创建财务分析师
        financial_role = BusinessRolesFactory.create_financial_analyst_role()
        financial_analyst = UserFactory.create(
            username="financial_analyst",
            full_name="财务分析师",
            organization_id=child_org2.id
        )
        UserRoleAssignmentFactory.create(
            user_id=financial_analyst.id,
            role_id=financial_role.id
        )

        # 创建审计员
        auditor_role = SystemRolesFactory.create_auditor_role()
        auditor = UserFactory.create(
            username="auditor",
            full_name="审计员",
            organization_id=parent_org.id
        )
        UserRoleAssignmentFactory.create(
            user_id=auditor.id,
            role_id=auditor_role.id
        )

        # 创建非活跃用户
        inactive_user = InactiveUserFactory.create(
            username="inactive_user",
            organization_id=child_org1.id
        )

        return {
            'organizations': [parent_org, child_org1, child_org2],
            'users': {
                'system_admin': system_admin,
                'asset_manager': asset_manager,
                'asset_viewer': asset_viewer,
                'financial_analyst': financial_analyst,
                'auditor': auditor,
                'inactive_user': inactive_user
            },
            'roles': {
                'system_admin': system_admin_role,
                'asset_manager': asset_manager_role,
                'asset_viewer': asset_viewer_role,
                'financial_analyst': financial_role,
                'auditor': auditor_role
            }
        }

    @staticmethod
    def create_cross_organization_users():
        """创建跨组织用户"""
        # 创建多个组织
        org1 = OrganizationFactory.create(name="北京分公司")
        org2 = OrganizationFactory.create(name="上海分公司")
        org3 = OrganizationFactory.create(name="深圳分公司")

        # 创建跨组织用户
        cross_org_user = UserFactory.create(
            username="cross_org_manager",
            full_name="跨区域经理",
            organization_id=org1.id
        )

        # 为用户分配多个组织的角色
        role1 = BusinessRolesFactory.create_asset_manager_role()
        role1.organization_id = org1.id

        role2 = BusinessRolesFactory.create_asset_manager_role()
        role2.name = 'asset_manager_sh'
        role2.organization_id = org2.id

        # 分配角色
        UserRoleAssignmentFactory.create(
            user_id=cross_org_user.id,
            role_id=role1.id
        )
        UserRoleAssignmentFactory.create(
            user_id=cross_org_user.id,
            role_id=role2.id
        )

        return {
            'organizations': [org1, org2, org3],
            'cross_org_user': cross_org_user,
            'roles': [role1, role2]
        }

    @staticmethod
    def create_users_with_expiring_roles():
        """创建角色即将过期的用户"""
        user = UserFactory.create(username="expiring_role_user")

        # 即将过期的角色（7天后）
        expiring_role = RoleFactory.create(name="temp_role")
        UserRoleAssignmentFactory.create(
            user_id=user.id,
            role_id=expiring_role.id,
            expires_at=datetime.now() + timedelta(days=7)
        )

        # 已经过期的角色
        expired_role = RoleFactory.create(name="expired_role")
        UserRoleAssignmentFactory.create(
            user_id=user.id,
            role_id=expired_role.id,
            expires_at=datetime.now() - timedelta(days=1),
            is_active=False
        )

        return {
            'user': user,
            'expiring_role': expiring_role,
            'expired_role': expired_role
        }


# 测试数据清理工具
class UserTestDataCleanup:
    """用户相关测试数据清理工具"""

    @staticmethod
    def cleanup_test_data(session):
        """清理用户相关测试数据"""
        # 按依赖关系倒序删除
        session.query(UserRoleAssignment).delete()
        session.query(User).delete()
        session.query(Role).delete()
        session.query(Permission).delete()
        session.query(Organization).delete()
        session.commit()

    @staticmethod
    def create_rbac_test_data(session):
        """创建RBAC测试所需的基础数据"""
        # 创建完整的用户层级
        hierarchy = UserScenariosFactory.create_complete_user_hierarchy()

        # 保存到数据库
        session.add_all(hierarchy['organizations'])
        session.add_all(hierarchy['users'].values())
        session.add_all(hierarchy['roles'].values())

        # 添加角色关联
        for user_role in session.query(UserRoleAssignment).all():
            session.add(user_role)

        session.commit()

        return hierarchy

    @staticmethod
    def create_permission_test_matrix(session):
        """创建权限测试矩阵数据"""
        # 创建各种权限组合
        permissions = []

        # 资产权限
        asset_perms = AssetPermissionsFactory.create_full_asset_permissions()
        permissions.extend(asset_perms)

        # 系统权限
        system_perms = SystemPermissionsFactory.create_full_system_permissions()
        permissions.extend(system_perms)

        # 审计权限
        audit_perms = SystemPermissionsFactory.create_audit_permissions()
        permissions.extend(audit_perms)

        session.add_all(permissions)

        # 创建不同级别的角色
        roles = []
        for level in [1, 3, 5, 8, 10]:
            role = RoleFactory.create(
                name=f"level_{level}_role",
                display_name=f"Level {level} Role",
                level=level,
                category='测试'
            )

            # 分配对应级别的权限
            for perm in permissions:
                if perm.max_level <= level:
                    role.permissions.append(perm)

            roles.append(role)

        session.add_all(roles)
        session.commit()

        return {
            'permissions': permissions,
            'roles': roles
        }


# 权限验证工具
class PermissionTestUtils:
    """权限测试工具类"""

    @staticmethod
    def get_user_permissions(user_id: int, session) -> list[str]:
        """获取用户的所有权限"""
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        permissions = []
        for role_assignment in user.role_assignments:
            if role_assignment.is_active and not role_assignment.is_expired():
                for permission in role_assignment.role.permissions:
                    permissions.append(f"{permission.resource}_{permission.action}")

        return permissions

    @staticmethod
    def check_user_has_permission(user_id: int, resource: str, action: str, session) -> bool:
        """检查用户是否具有指定权限"""
        permission_name = f"{resource}_{action}"
        user_permissions = PermissionTestUtils.get_user_permissions(user_id, session)
        return permission_name in user_permissions

    @staticmethod
    def create_permission_hierarchy():
        """创建权限层级结构用于测试"""
        return {
            'admin': ['*'],  # 所有权限
            'manager': ['assets_*', 'reports_read', 'reports_export'],
            'analyst': ['assets_read', 'reports_read'],
            'viewer': ['assets_read'],
            'guest': []
        }


# 导出主要工厂函数
def create_test_user_hierarchy():
    """创建测试用户层级结构的便捷函数"""
    return UserScenariosFactory.create_complete_user_hierarchy()

def create_cross_organization_test_data():
    """创建跨组织测试数据的便捷函数"""
    return UserScenariosFactory.create_cross_organization_users()

def create_rbac_test_matrix():
    """创建RBAC测试矩阵的便捷函数"""
    from src.database import SessionLocal
    session = SessionLocal()
    try:
        return UserTestDataCleanup.create_permission_test_matrix(session)
    finally:
        session.close()
