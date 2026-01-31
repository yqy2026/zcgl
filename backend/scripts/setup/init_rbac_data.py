#!/usr/bin/env python3
"""
RBAC系统初始化脚本
创建基础角色、权限和测试数据
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uuid
from datetime import datetime, timedelta

from src.database import get_db
from src.models.auth import User
from src.models.rbac import Permission, Role, UserRoleAssignment


def create_basic_permissions(db):
    """创建基础权限"""
    permissions_data = [
        # 资产管理权限
        ("asset", "read", "查看资产", "查看资产基本信息"),
        ("asset", "create", "创建资产", "创建新资产"),
        ("asset", "update", "更新资产", "更新资产信息"),
        ("asset", "delete", "删除资产", "删除资产"),
        # 项目管理权限
        ("project", "read", "查看项目", "查看项目信息"),
        ("project", "create", "创建项目", "创建新项目"),
        ("project", "update", "更新项目", "更新项目信息"),
        ("project", "delete", "删除项目", "删除项目"),
        # 权属管理权限
        ("ownership", "read", "查看权属", "查看权属信息"),
        ("ownership", "create", "创建权属", "创建新权属"),
        ("ownership", "update", "更新权属", "更新权属信息"),
        ("ownership", "delete", "删除权属", "删除权属"),
        # 租金合同权限
        ("rent_contract", "read", "查看租金合同", "查看租金合同信息"),
        ("rent_contract", "create", "创建租金合同", "创建新租金合同"),
        ("rent_contract", "update", "更新租金合同", "更新租金合同信息"),
        ("rent_contract", "delete", "删除租金合同", "删除租金合同"),
        # 统计分析权限
        ("statistics", "read", "查看统计", "查看统计信息"),
        ("statistics", "export", "导出统计", "导出统计数据"),
        # Excel配置权限
        ("excel_config", "read", "查看Excel配置", "查看Excel导入导出配置"),
        ("excel_config", "write", "管理Excel配置", "创建/更新/删除Excel配置"),
        # 系统管理权限
        ("system", "manage", "系统管理", "系统管理权限"),
        ("system", "audit", "审计查看", "查看审计日志"),
        ("system", "backup", "数据备份", "数据备份权限"),
        # 用户管理权限
        ("user", "read", "查看用户", "查看用户信息"),
        ("user", "create", "创建用户", "创建新用户"),
        ("user", "update", "更新用户", "更新用户信息"),
        ("user", "delete", "删除用户", "删除用户"),
        # 角色权限管理
        ("role", "read", "查看角色", "查看角色信息"),
        ("role", "create", "创建角色", "创建新角色"),
        ("role", "update", "更新角色", "更新角色信息"),
        ("role", "delete", "删除角色", "删除角色"),
        ("role", "assign", "分配角色", "分配用户角色"),
        # 组织管理权限
        ("organization", "read", "查看组织", "查看组织信息"),
        ("organization", "create", "创建组织", "创建新组织"),
        ("organization", "update", "更新组织", "更新组织信息"),
        ("organization", "delete", "删除组织", "删除组织"),
        # 动态权限管理
        ("dynamic_permission", "read", "查看动态权限", "查看动态权限"),
        ("dynamic_permission", "assign", "分配动态权限", "分配动态权限"),
        ("dynamic_permission", "revoke", "撤销动态权限", "撤销动态权限"),
        ("dynamic_permission", "check", "检查权限", "检查用户权限"),
        # 审计权限
        ("audit", "read", "查看审计", "查看审计日志"),
        ("audit", "export", "导出审计", "导出审计数据"),
    ]

    created_permissions = []
    for resource, action, display_name, description in permissions_data:
        # 检查权限是否已存在
        existing = (
            db.query(Permission)
            .filter(Permission.resource == resource, Permission.action == action)
            .first()
        )

        if not existing:
            permission = Permission(
                name=f"{resource}:{action}",
                display_name=display_name,
                description=description,
                resource=resource,
                action=action,
                is_system_permission=True,
                created_by="system",
            )
            db.add(permission)
            created_permissions.append(permission)

    db.commit()
    print(f"✅ 创建了 {len(created_permissions)} 个基础权限")
    return created_permissions


def create_basic_roles(db):
    """创建基础角色"""
    roles_data = [
        ("admin", "系统管理员", "系统超级管理员，拥有所有权限", 1, "system"),
        ("manager", "管理员", "部门管理员，拥有大部分管理权限", 2, "management"),
        ("user", "普通用户", "普通用户，基础操作权限", 3, "business"),
        ("viewer", "只读用户", "只能查看数据，不能修改", 4, "read_only"),
        ("asset_manager", "资产管理员", "负责资产管理的专业人员", 2, "asset"),
        ("project_manager", "项目经理", "负责项目管理的专业人员", 2, "project"),
        ("auditor", "审计员", "负责审计工作的专业人员", 2, "audit"),
    ]

    created_roles = []
    for name, display_name, description, level, category in roles_data:
        # 检查角色是否已存在
        existing = db.query(Role).filter(Role.name == name).first()

        if not existing:
            role = Role(
                name=name,
                display_name=display_name,
                description=description,
                level=level,
                category=category,
                is_system_role=True,
                created_by="system",
            )
            db.add(role)
            created_roles.append(role)

    db.commit()
    print(f"✅ 创建了 {len(created_roles)} 个基础角色")
    return created_roles


def create_admin_user(db):
    """创建管理员用户"""
    # 检查管理员用户是否已存在
    existing_admin = db.query(User).filter(User.username == "admin").first()

    if not existing_admin:
        admin_user = User(
            id=str(uuid.uuid4()),
            username="admin",
            email="admin@example.com",
            full_name="系统管理员",
            role="ADMIN",
            is_active=True,
            is_verified=True,
            password_hash="$2b$12$dummy_hash_for_admin",  # 实际使用中应该设置真实的密码哈希
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(admin_user)
        db.commit()
        print(f"✅ 创建了管理员用户: {admin_user.username}")
        return admin_user
    else:
        print(f"⚠️ 管理员用户已存在: {existing_admin.username}")
        return existing_admin


def assign_permissions_to_roles(db, roles, permissions):
    """为角色分配权限"""
    role_permission_map = {
        "admin": [p for p in permissions],  # 管理员拥有所有权限
        "manager": [
            p for p in permissions if not p.resource.startswith("system")
        ],  # 管理员拥有除系统管理外的所有权限
        "user": [
            p for p in permissions if p.action in ["read"]
        ],  # 普通用户只有读取权限
        "viewer": [
            p for p in permissions if p.action in ["read"]
        ],  # 只读用户只有读取权限
        "asset_manager": [
            p for p in permissions if p.resource in ["asset", "statistics"]
        ],  # 资产管理员可以管理资产和查看统计
        "project_manager": [
            p for p in permissions if p.resource in ["project", "statistics"]
        ],  # 项目经理可以管理项目和查看统计
        "auditor": [
            p for p in permissions if p.resource in ["audit", "statistics"]
        ],  # 审计员可以查看审计和统计
    }

    from src.models.rbac import role_permissions

    for role in roles:
        if role.name in role_permission_map:
            role_perms = role_permission_map[role.name]
            for permission in role_perms:
                # 检查是否已存在关联
                existing = (
                    db.query(role_permissions)
                    .filter(
                        role_permissions.c.role_id == role.id,
                        role_permissions.c.permission_id == permission.id,
                    )
                    .first()
                )

                if not existing:
                    db.execute(
                        role_permissions.insert().values(
                            role_id=role.id,
                            permission_id=permission.id,
                            created_at=datetime.utcnow(),
                            created_by="system",
                        )
                    )

            print(f"✅ 为角色 '{role.display_name}' 分配了 {len(role_perms)} 个权限")


def create_test_users(db):
    """创建测试用户"""
    test_users = [
        ("manager1", "manager1@example.com", "测试管理员", "USER"),
        ("user1", "user1@example.com", "测试用户1", "USER"),
        ("user2", "user2@example.com", "测试用户2", "USER"),
        ("viewer1", "viewer1@example.com", "测试查看者", "USER"),
    ]

    for username, email, full_name, role in test_users:
        existing = db.query(User).filter(User.username == username).first()
        if not existing:
            user = User(
                id=str(uuid.uuid4()),
                username=username,
                email=email,
                full_name=full_name,
                role=role,
                is_active=True,
                is_verified=True,
                password_hash="$2b$12$dummy_hash_for_user",  # 实际使用中应该设置真实的密码哈希
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(user)

    db.commit()
    print(f"✅ 创建了 {len(test_users)} 个测试用户")


def assign_roles_to_users(db, roles, users):
    """为用户分配角色"""
    role_map = {role.name: role for role in roles}

    # 为测试用户分配角色
    user_role_assignments = [
        ("manager1", "manager"),
        ("user1", "user"),
        ("user2", "user"),
        ("viewer1", "viewer"),
    ]

    for username, role_name in user_role_assignments:
        user = db.query(User).filter(User.username == username).first()
        if user and role_name in role_map:
            role = role_map[role_name]

            # 检查是否已存在分配
            existing = (
                db.query(UserRoleAssignment)
                .filter(
                    UserRoleAssignment.user_id == user.id,
                    UserRoleAssignment.role_id == role.id,
                    UserRoleAssignment.is_active,
                )
                .first()
            )

            if not existing:
                assignment = UserRoleAssignment(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    role_id=role.id,
                    assigned_by="system",
                    assigned_at=datetime.utcnow(),
                    expires_at=None,  # 永久分配
                    is_active=True,
                    reason="系统初始化分配",
                )
                db.add(assignment)

    db.commit()
    print("✅ 为测试用户分配了角色")


def create_dynamic_permission_samples(db):
    """创建动态权限示例"""
    from src.models.dynamic_permission import DynamicPermission, TemporaryPermission
    from src.models.rbac import Permission

    # 获取测试用户和权限
    test_user = db.query(User).filter(User.username == "user1").first()
    if not test_user:
        print("⚠️ 测试用户不存在，跳过动态权限创建")
        return

    # 获取一个权限
    asset_create_perm = (
        db.query(Permission)
        .filter(Permission.resource == "asset", Permission.action == "create")
        .first()
    )

    if asset_create_perm:
        # 创建一个临时权限（有效期为7天）
        temp_permission = TemporaryPermission(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            permission_id=asset_create_perm.id,
            scope="global",
            expires_at=datetime.utcnow() + timedelta(days=7),
            assigned_by="system",
            assigned_at=datetime.utcnow(),
            is_active=True,
        )
        db.add(temp_permission)

        # 创建一个动态权限
        dynamic_permission = DynamicPermission(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            permission_id=asset_create_perm.id,
            permission_type="user_specific",
            scope="organization",
            scope_id=None,  # 可以设置为具体的组织ID
            conditions={"max_daily_operations": 10},  # 每天最多10次操作
            expires_at=datetime.utcnow() + timedelta(days=30),
            assigned_by="system",
            assigned_at=datetime.utcnow(),
            is_active=True,
        )
        db.add(dynamic_permission)

        db.commit()
        print("✅ 创建了动态权限示例")


def main():
    """主函数"""
    print("开始初始化RBAC系统数据...")

    try:
        # 创建数据库会话
        db = next(get_db())

        # 1. 创建基础权限
        permissions = create_basic_permissions(db)

        # 2. 创建基础角色
        roles = create_basic_roles(db)

        # 3. 创建管理员用户
        create_admin_user(db)

        # 4. 为角色分配权限
        assign_permissions_to_roles(db, roles, permissions)

        # 5. 创建测试用户
        create_test_users(db)

        # 6. 为测试用户分配角色
        assign_roles_to_users(db, roles, None)

        # 7. 创建动态权限示例
        create_dynamic_permission_samples(db)

        print("\nRBAC系统初始化完成！")
        print("创建内容:")
        print(f"   - {len(permissions)} 个基础权限")
        print(f"   - {len(roles)} 个基础角色")
        print("   - 1 个管理员用户")
        print("   - 4 个测试用户")
        print("   - 动态权限示例")

        print("\n默认登录信息:")
        print("   管理员用户名: admin")
        print("   测试用户名: manager1, user1, user2, viewer1")
        print("   (默认密码需要在实际部署时设置)")

    except Exception as e:
        print(f"初始化失败: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
