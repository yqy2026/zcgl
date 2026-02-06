#!/usr/bin/env python3
"""
RBAC系统初始化脚本
创建基础角色、权限和测试数据
"""

import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, text

from src.database import async_session_scope
from src.models.auth import User
from src.models.rbac import Permission, Role, UserRoleAssignment


async def create_basic_permissions(db):
    """创建基础权限"""
    permissions_data = [
        # 资产管理权限
        ("asset", "read", "查看资产", "查看资产基本信息"),
        ("asset", "create", "创建资产", "创建新资产"),
        ("asset", "update", "更新资产", "更新资产信息"),
        ("asset", "delete", "删除资产", "删除资产"),
        # 产权证管理权限
        ("property_certificate", "read", "查看产权证", "查看产权证信息"),
        ("property_certificate", "create", "创建产权证", "创建新产权证"),
        ("property_certificate", "update", "更新产权证", "更新产权证信息"),
        ("property_certificate", "delete", "删除产权证", "删除产权证"),
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

    created_permissions: list[Permission] = []
    all_permissions: list[Permission] = []
    for resource, action, display_name, description in permissions_data:
        # 检查权限是否已存在
        existing_result = await db.execute(
            select(Permission).where(
                Permission.resource == resource, Permission.action == action
            )
        )
        existing = existing_result.scalars().first()

        if existing:
            all_permissions.append(existing)
            continue

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
        all_permissions.append(permission)

    await db.commit()
    print(f"[OK] 创建了 {len(created_permissions)} 个基础权限")
    return all_permissions, len(created_permissions)


async def create_basic_roles(db):
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

    created_roles: list[Role] = []
    all_roles: list[Role] = []
    for name, display_name, description, level, category in roles_data:
        # 检查角色是否已存在
        existing_result = await db.execute(select(Role).where(Role.name == name))
        existing = existing_result.scalars().first()

        if existing:
            all_roles.append(existing)
            continue

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
        all_roles.append(role)

    await db.commit()
    print(f"[OK] 创建了 {len(created_roles)} 个基础角色")
    return all_roles, len(created_roles)


async def create_admin_user(db):
    """创建管理员用户"""
    # 检查管理员用户是否已存在
    existing_result = await db.execute(
        select(User).where(User.username == "admin")
    )
    existing_admin = existing_result.scalars().first()

    if not existing_admin:
        admin_user = User(
            id=str(uuid.uuid4()),
            username="admin",
            email="admin@example.com",
            full_name="系统管理员",
            is_active=True,
            password_hash="$2b$12$dummy_hash_for_admin",  # 实际使用中应该设置真实的密码哈希
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(admin_user)
        await db.commit()

        # Assign admin role via RBAC
        role_result = await db.execute(
            select(Role).where(Role.name.in_(["super_admin", "admin"]))
        )
        role = role_result.scalars().first()
        if role:
            assignment = UserRoleAssignment(
                user_id=admin_user.id,
                role_id=role.id,
                assigned_by="system",
                assigned_at=datetime.utcnow(),
                is_active=True,
            )
            db.add(assignment)
            await db.commit()

        print(f"[OK] 创建了管理员用户: {admin_user.username}")
        return admin_user
    else:
        # Ensure admin role assignment exists
        role_result = await db.execute(
            select(Role).where(Role.name.in_(["super_admin", "admin"]))
        )
        role = role_result.scalars().first()
        if role:
            assignment_result = await db.execute(
                select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == existing_admin.id,
                    UserRoleAssignment.role_id == role.id,
                    UserRoleAssignment.is_active,
                )
            )
            if assignment_result.scalars().first() is None:
                db.add(
                    UserRoleAssignment(
                        user_id=existing_admin.id,
                        role_id=role.id,
                        assigned_by="system",
                        assigned_at=datetime.utcnow(),
                        is_active=True,
                    )
                )
                await db.commit()

        print(f"[WARN] 管理员用户已存在: {existing_admin.username}")
        return existing_admin


async def assign_permissions_to_roles(db, roles, permissions):
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
                existing_result = await db.execute(
                    select(role_permissions).where(
                        role_permissions.c.role_id == role.id,
                        role_permissions.c.permission_id == permission.id,
                    )
                )
                existing = existing_result.first()

                if not existing:
                    await db.execute(
                        role_permissions.insert().values(
                            role_id=role.id,
                            permission_id=permission.id,
                            created_at=datetime.utcnow(),
                            created_by="system",
                        )
                    )

            print(f"[OK] 为角色 '{role.display_name}' 分配了 {len(role_perms)} 个权限")
    await db.commit()


async def create_test_users(db) -> tuple[int, int]:
    """创建测试用户"""
    # Legacy schema may still require users.role; skip seeding to avoid constraint errors.
    role_column = await db.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'users' AND column_name = 'role' LIMIT 1"
        )
    )
    if role_column.scalar() is not None:
        print("[WARN] users.role column exists; skip test user seeding.")
        return 0, 0

    test_users = [
        ("manager1", "manager1@example.com", "测试管理员", "USER"),
        ("user1", "user1@example.com", "测试用户1", "USER"),
        ("user2", "user2@example.com", "测试用户2", "USER"),
        ("viewer1", "viewer1@example.com", "测试查看者", "USER"),
    ]

    created_count = 0
    existing_count = 0
    for username, email, full_name, _role in test_users:
        existing_result = await db.execute(
            select(User).where(User.username == username)
        )
        existing = existing_result.scalars().first()
        if not existing:
            user = User(
                id=str(uuid.uuid4()),
                username=username,
                email=email,
                full_name=full_name,
                is_active=True,
                password_hash="$2b$12$dummy_hash_for_user",  # 实际使用中应该设置真实的密码哈希
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(user)
            created_count += 1
        else:
            existing_count += 1

    await db.commit()
    print(f"[OK] 创建了 {created_count} 个测试用户")
    return created_count, existing_count


async def assign_roles_to_users(db, roles, users):
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
        user_result = await db.execute(
            select(User).where(User.username == username)
        )
        user = user_result.scalars().first()
        if user and role_name in role_map:
            role = role_map[role_name]

            # 检查是否已存在分配
            existing_result = await db.execute(
                select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == user.id,
                    UserRoleAssignment.role_id == role.id,
                    UserRoleAssignment.is_active,
                )
            )
            existing = existing_result.scalars().first()

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

    await db.commit()
    print("[OK] 为测试用户分配了角色")


async def create_dynamic_permission_samples(db) -> bool:
    """创建动态权限示例"""
    from src.models.dynamic_permission import DynamicPermission, TemporaryPermission
    from src.models.rbac import Permission

    # 获取测试用户和权限
    test_user_result = await db.execute(
        select(User).where(User.username == "user1")
    )
    test_user = test_user_result.scalars().first()
    if not test_user:
        print("[WARN] 测试用户不存在，跳过动态权限创建")
        return False

    assigned_by_result = await db.execute(
        select(User).where(User.username == "admin")
    )
    assigned_by_user = assigned_by_result.scalars().first()
    assigned_by = assigned_by_user.id if assigned_by_user else test_user.id

    # 获取一个权限
    asset_perm_result = await db.execute(
        select(Permission).where(
            Permission.resource == "asset", Permission.action == "create"
        )
    )
    asset_create_perm = asset_perm_result.scalars().first()

    if asset_create_perm:
        created_any = False

        existing_temp = (
            await db.execute(
                select(TemporaryPermission).where(
                    TemporaryPermission.user_id == test_user.id,
                    TemporaryPermission.permission_id == asset_create_perm.id,
                    TemporaryPermission.is_active.is_(True),
                )
            )
        ).scalars().first()
        if not existing_temp:
            # 创建一个临时权限（有效期为7天）
            temp_permission = TemporaryPermission(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                permission_id=asset_create_perm.id,
                scope="global",
                expires_at=datetime.utcnow() + timedelta(days=7),
                assigned_by=assigned_by,
                assigned_at=datetime.utcnow(),
                is_active=True,
            )
            db.add(temp_permission)
            created_any = True

        existing_dynamic = (
            await db.execute(
                select(DynamicPermission).where(
                    DynamicPermission.user_id == test_user.id,
                    DynamicPermission.permission_id == asset_create_perm.id,
                    DynamicPermission.is_active.is_(True),
                )
            )
        ).scalars().first()
        if not existing_dynamic:
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
                assigned_by=assigned_by,
                assigned_at=datetime.utcnow(),
                is_active=True,
            )
            db.add(dynamic_permission)
            created_any = True

        if created_any:
            await db.commit()
            print("[OK] 创建了动态权限示例")
            return True

        print("[WARN] 动态权限示例已存在，跳过创建")
        return False

    return False


async def main():
    """主函数"""
    print("开始初始化RBAC系统数据...")

    try:
        async with async_session_scope() as db:
            # 1. 创建基础权限
            permissions, permissions_created = await create_basic_permissions(db)

            # 2. 创建基础角色
            roles, roles_created = await create_basic_roles(db)

            # 3. 创建管理员用户
            await create_admin_user(db)

            # 4. 为角色分配权限
            await assign_permissions_to_roles(db, roles, permissions)

            # 5. 创建测试用户
            test_users_created, test_users_existing = await create_test_users(db)

            # 6. 为测试用户分配角色
            if (test_users_created + test_users_existing) > 0:
                await assign_roles_to_users(db, roles, None)
            else:
                print("[WARN] 未创建测试用户，跳过角色分配")

            # 7. 创建动态权限示例
            dynamic_permissions_created = await create_dynamic_permission_samples(db)

        print("\nRBAC系统初始化完成！")
        print("创建内容:")
        print(f"   - 基础权限新增: {permissions_created} (总数: {len(permissions)})")
        print(f"   - 基础角色新增: {roles_created} (总数: {len(roles)})")
        print("   - 管理员用户: 已确保存在")
        print(
            f"   - 测试用户新增: {test_users_created} (已存在: {test_users_existing})"
        )
        print(
            "   - 动态权限示例: 已创建"
            if dynamic_permissions_created
            else "   - 动态权限示例: 跳过"
        )

        print("\n默认登录信息:")
        print("   管理员用户名: admin")
        if (test_users_created + test_users_existing) > 0:
            print("   测试用户名: manager1, user1, user2, viewer1")
        else:
            print("   测试用户名: 未创建")
        print("   (默认密码需要在实际部署时设置)")

    except Exception as e:
        print(f"初始化失败: {str(e)}")
        import traceback

        traceback.print_exc()
if __name__ == "__main__":
    asyncio.run(main())
