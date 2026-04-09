#!/usr/bin/env python3
"""
RBAC系统初始化脚本
创建基础角色、权限和测试数据
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text

from src.database import async_session_scope
from src.models.auth import User
from src.models.rbac import Permission, PermissionGrant, Role, UserRoleAssignment

TARGET_SYSTEM_ROLE_DEFINITIONS = [
    ("system_admin", "系统管理员", "系统超级管理员，拥有全局权限", 1, "system"),
    ("ops_admin", "运营管理员", "运营管理员，负责业务域全量管理", 2, "operations"),
    ("perm_admin", "权限管理员", "权限管理员，仅管理用户/角色/权限/策略", 2, "security"),
    ("reviewer", "审核员", "负责审批与审核处理", 3, "review"),
    ("executive", "业务经办", "负责日常业务录入与维护", 4, "business"),
    ("viewer", "只读用户", "只读查看业务数据", 5, "read_only"),
]

LEGACY_SYSTEM_ROLE_NAMES = {
    "admin",
    "manager",
    "user",
    "asset_manager",
    "project_manager",
    "auditor",
}

SYSTEM_MANAGEMENT_RESOURCES = {
    "system",
    "user",
    "role",
    "permission_grant",
    "organization",
    "backup",
    "dictionary",
    "enum_field",
    "error_recovery",
    "history",
    "llm_prompt",
    "operation_log",
    "system_monitoring",
    "system_settings",
    "task",
}
BUSINESS_RESOURCES = {
    "asset",
    "property_certificate",
    "project",
    "ownership",
    "contract",
    "contract_group",
    "approval",
    "analytics",
    "excel_config",
    "audit",
    "collection",
    "contact",
    "custom_field",
    "notification",
    "occupancy",
    "party",
}

ROLE_PERMISSION_MATRIX: dict[str, callable] = {
    "system_admin": lambda permissions: [p for p in permissions],
    "ops_admin": lambda permissions: [
        p for p in permissions if p.resource not in SYSTEM_MANAGEMENT_RESOURCES
    ],
    "perm_admin": lambda permissions: [
        p
        for p in permissions
        if p.resource in SYSTEM_MANAGEMENT_RESOURCES
        or (p.resource == "system" and p.action in {"admin", "manage"})
    ],
    "reviewer": lambda permissions: [
        p
        for p in permissions
        if (p.resource in BUSINESS_RESOURCES and p.action == "read")
        or (p.resource == "approval" and p.action in {"read", "approve", "reject", "withdraw"})
    ],
    "executive": lambda permissions: [
        p
        for p in permissions
        if (
            p.resource
            in {
                "asset",
                "property_certificate",
                "project",
                "ownership",
                "contract",
                "contract_group",
            }
            and p.action in {"create", "read", "update", "delete"}
        )
        or (p.resource == "analytics" and p.action in {"read", "export"})
        or (p.resource == "approval" and p.action in {"read", "start"})
        or (p.resource == "excel_config" and p.action in {"read", "create", "update", "delete"})
    ],
    "viewer": lambda permissions: [
        p
        for p in permissions
        if (p.resource in BUSINESS_RESOURCES and p.action == "read")
        or (p.resource == "analytics" and p.action == "export")
    ],
}

TEST_USER_ROLE_ASSIGNMENTS = [
    ("manager1", "ops_admin"),
    ("user1", "executive"),
    ("user2", "executive"),
    ("viewer1", "viewer"),
]

BASIC_PERMISSIONS_DATA = [
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
    # 合同/合同组权限
    ("contract", "read", "查看合同", "查看合同信息"),
    ("contract", "create", "创建合同", "创建新合同"),
    ("contract", "update", "更新合同", "更新合同信息"),
    ("contract", "delete", "删除合同", "删除合同"),
    ("contract_group", "read", "查看合同组", "查看合同组信息"),
    ("contract_group", "create", "创建合同组", "创建新合同组"),
    ("contract_group", "update", "更新合同组", "更新合同组信息"),
    ("contract_group", "delete", "删除合同组", "删除合同组"),
    # 分析权限
    ("analytics", "read", "查看分析", "查看分析信息"),
    ("analytics", "export", "导出分析", "导出分析数据"),
    ("analytics", "update", "更新分析配置", "更新分析缓存与口径相关配置"),
    # Excel配置权限
    ("excel_config", "read", "查看Excel配置", "查看Excel导入导出配置"),
    ("excel_config", "create", "创建Excel配置", "创建Excel导入导出配置"),
    ("excel_config", "update", "更新Excel配置", "更新Excel导入导出配置"),
    ("excel_config", "delete", "删除Excel配置", "删除Excel导入导出配置"),
    # 审批流权限
    ("approval", "read", "查看审批", "查看审批任务与流程"),
    ("approval", "start", "发起审批", "发起业务审批流程"),
    ("approval", "approve", "审批通过", "处理审批通过动作"),
    ("approval", "reject", "审批驳回", "处理审批驳回动作"),
    ("approval", "withdraw", "审批撤回", "撤回本人发起的审批"),
    # 系统管理权限
    ("system", "admin", "系统管理员", "全局管理员权限"),
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
    ("organization", "update", "更新组织", "更新组织信息"),
    ("organization", "delete", "删除组织", "删除组织"),
    # 统一授权管理
    ("permission_grant", "read", "查看统一授权", "查看统一授权记录"),
    ("permission_grant", "assign", "分配统一授权", "分配统一授权记录"),
    ("permission_grant", "revoke", "撤销统一授权", "撤销统一授权记录"),
    ("permission_grant", "check", "检查权限", "检查用户权限"),
    # 审计权限
    ("audit", "read", "查看审计", "查看审计日志"),
    ("audit", "export", "导出审计", "导出审计数据"),
    # 其余系统/业务资源权限（与当前 API 契约保持一致）
    ("backup", "create", "创建备份", "创建数据备份"),
    ("backup", "read", "查看备份", "查看备份列表与详情"),
    ("backup", "update", "恢复备份", "执行备份恢复"),
    ("backup", "delete", "删除备份", "删除备份文件"),
    ("collection", "create", "创建收藏", "创建收藏记录"),
    ("collection", "read", "查看收藏", "查看收藏记录"),
    ("collection", "update", "更新收藏", "更新收藏记录"),
    ("collection", "delete", "删除收藏", "删除收藏记录"),
    ("contact", "create", "创建联系人", "创建联系人记录"),
    ("contact", "read", "查看联系人", "查看联系人记录"),
    ("contact", "update", "更新联系人", "更新联系人记录"),
    ("contact", "delete", "删除联系人", "删除联系人记录"),
    ("party", "create", "创建主体", "创建主体主档"),
    ("party", "read", "查看主体", "查看主体主档与绑定信息"),
    ("party", "update", "更新主体", "更新主体主档与绑定信息"),
    ("party", "delete", "删除主体", "删除主体主档"),
    ("custom_field", "read", "查看自定义字段", "查看自定义字段定义"),
    ("dictionary", "create", "创建字典", "创建字典类型和值"),
    ("dictionary", "read", "查看字典", "查看字典类型和值"),
    ("dictionary", "delete", "删除字典", "删除字典类型和值"),
    ("enum_field", "create", "创建枚举字段", "创建枚举字段"),
    ("enum_field", "read", "查看枚举字段", "查看枚举字段"),
    ("enum_field", "update", "更新枚举字段", "更新枚举字段"),
    ("enum_field", "delete", "删除枚举字段", "删除枚举字段"),
    ("error_recovery", "read", "查看错误恢复", "查看错误恢复任务"),
    ("error_recovery", "update", "更新错误恢复", "执行错误恢复操作"),
    ("error_recovery", "delete", "删除错误恢复", "删除错误恢复记录"),
    ("history", "read", "查看历史", "查看历史记录"),
    ("history", "delete", "删除历史", "删除历史记录"),
    ("llm_prompt", "create", "创建提示词", "创建提示词模板"),
    ("llm_prompt", "read", "查看提示词", "查看提示词模板"),
    ("llm_prompt", "update", "更新提示词", "更新提示词模板"),
    ("notification", "read", "查看通知", "查看通知"),
    ("notification", "update", "更新通知", "更新通知状态"),
    ("notification", "delete", "删除通知", "删除通知"),
    ("occupancy", "read", "查看出租率", "查看出租率与占用率信息"),
    ("operation_log", "read", "查看操作日志", "查看操作日志"),
    ("operation_log", "delete", "删除操作日志", "清理操作日志"),
    ("system_monitoring", "create", "创建系统监控配置", "创建系统监控配置"),
    ("system_monitoring", "read", "查看系统监控", "查看系统监控数据"),
    ("system_monitoring", "update", "更新系统监控", "更新系统监控配置"),
    ("system_monitoring", "delete", "删除系统监控", "删除系统监控配置"),
    ("system_settings", "create", "创建系统设置", "创建系统设置"),
    ("system_settings", "read", "查看系统设置", "查看系统设置"),
    ("system_settings", "update", "更新系统设置", "更新系统设置"),
    ("task", "create", "创建任务", "创建异步任务"),
    ("task", "read", "查看任务", "查看异步任务"),
    ("task", "update", "更新任务", "更新异步任务"),
    ("task", "delete", "删除任务", "删除异步任务"),
]


async def create_basic_permissions(db):
    """创建基础权限"""
    created_permissions: list[Permission] = []
    all_permissions: list[Permission] = []
    for resource, action, display_name, description in BASIC_PERMISSIONS_DATA:
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
    created_roles: list[Role] = []
    all_roles: list[Role] = []
    for name, display_name, description, level, category in TARGET_SYSTEM_ROLE_DEFINITIONS:
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

    legacy_roles_result = await db.execute(
        select(Role).where(Role.name.in_(sorted(LEGACY_SYSTEM_ROLE_NAMES)))
    )
    legacy_roles = list(legacy_roles_result.scalars().all())
    for legacy_role in legacy_roles:
        legacy_role.is_active = False
        legacy_role.updated_by = "system"
        legacy_role.updated_at = datetime.now(UTC).replace(tzinfo=None)
        db.add(legacy_role)

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
            phone="13800000000",
            full_name="系统管理员",
            is_active=True,
            password_hash="$2b$12$dummy_hash_for_admin",  # 实际使用中应该设置真实的密码哈希
            created_at=datetime.now(UTC).replace(tzinfo=None),
            updated_at=datetime.now(UTC).replace(tzinfo=None),
            created_by="system",
            updated_by="system",
        )
        db.add(admin_user)
        await db.commit()

        # Assign admin role via RBAC
        role_result = await db.execute(
            select(Role).where(Role.name.in_(["system_admin", "super_admin", "admin"]))
        )
        role = role_result.scalars().first()
        if role:
            assignment = UserRoleAssignment(
                user_id=admin_user.id,
                role_id=role.id,
                assigned_by="system",
                assigned_at=datetime.now(UTC).replace(tzinfo=None),
                is_active=True,
            )
            db.add(assignment)
            await db.commit()

        print(f"[OK] 创建了管理员用户: {admin_user.username}")
        return admin_user
    else:
        # Ensure admin role assignment exists
        role_result = await db.execute(
            select(Role).where(Role.name.in_(["system_admin", "super_admin", "admin"]))
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
                        assigned_at=datetime.now(UTC).replace(tzinfo=None),
                        is_active=True,
                    )
                )
                await db.commit()

        print(f"[WARN] 管理员用户已存在: {existing_admin.username}")
        return existing_admin


async def assign_permissions_to_roles(db, roles, permissions):
    """为角色分配权限"""
    from src.models.rbac import role_permissions

    for role in roles:
        resolver = ROLE_PERMISSION_MATRIX.get(role.name)
        if resolver is not None:
            role_perms = resolver(permissions)
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
                            created_at=datetime.now(UTC).replace(tzinfo=None),
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
        ("manager1", "manager1@example.com", "13800000001", "测试管理员", "USER"),
        ("user1", "user1@example.com", "13800000002", "测试用户1", "USER"),
        ("user2", "user2@example.com", "13800000003", "测试用户2", "USER"),
        ("viewer1", "viewer1@example.com", "13800000004", "测试查看者", "USER"),
    ]

    created_count = 0
    existing_count = 0
    for username, email, phone, full_name, _role in test_users:
        existing_result = await db.execute(
            select(User).where(User.username == username)
        )
        existing = existing_result.scalars().first()
        if not existing:
            user = User(
                id=str(uuid.uuid4()),
                username=username,
                email=email,
                phone=phone,
                full_name=full_name,
                is_active=True,
                password_hash="$2b$12$dummy_hash_for_user",  # 实际使用中应该设置真实的密码哈希
                created_at=datetime.now(UTC).replace(tzinfo=None),
                updated_at=datetime.now(UTC).replace(tzinfo=None),
                created_by="system",
                updated_by="system",
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
    for username, role_name in TEST_USER_ROLE_ASSIGNMENTS:
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
                    assigned_at=datetime.now(UTC).replace(tzinfo=None),
                    expires_at=None,  # 永久分配
                    is_active=True,
                    reason="系统初始化分配",
                )
                db.add(assignment)

    await db.commit()
    print("[OK] 为测试用户分配了角色")


async def create_permission_grant_samples(db) -> bool:
    """创建统一权限授权示例"""

    # 获取测试用户和权限
    test_user_result = await db.execute(
        select(User).where(User.username == "user1")
    )
    test_user = test_user_result.scalars().first()
    if not test_user:
        print("[WARN] 测试用户不存在，跳过统一授权创建")
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
                select(PermissionGrant).where(
                    PermissionGrant.user_id == test_user.id,
                    PermissionGrant.permission_id == asset_create_perm.id,
                    PermissionGrant.grant_type == "temporary",
                    PermissionGrant.is_active.is_(True),
                )
            )
        ).scalars().first()
        if not existing_temp:
            # 创建一个临时授权（有效期7天）
            temp_permission = PermissionGrant(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                permission_id=asset_create_perm.id,
                grant_type="temporary",
                effect="allow",
                scope="global",
                starts_at=datetime.now(UTC).replace(tzinfo=None),
                expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7),
                priority=110,
                source_type="init_seed",
                source_id="sample_temporary_asset_create",
                granted_by=assigned_by,
                is_active=True,
            )
            db.add(temp_permission)
            created_any = True

        existing_dynamic = (
            await db.execute(
                select(PermissionGrant).where(
                    PermissionGrant.user_id == test_user.id,
                    PermissionGrant.permission_id == asset_create_perm.id,
                    PermissionGrant.grant_type == "dynamic",
                    PermissionGrant.is_active.is_(True),
                )
            )
        ).scalars().first()
        if not existing_dynamic:
            # 创建一个动态授权
            permission_grant_sample = PermissionGrant(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                permission_id=asset_create_perm.id,
                grant_type="dynamic",
                effect="allow",
                scope="organization",
                scope_id=None,  # 可以设置为具体的组织ID
                conditions={"max_daily_operations": 10},  # 每天最多10次操作
                starts_at=datetime.now(UTC).replace(tzinfo=None),
                expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=30),
                priority=100,
                source_type="init_seed",
                source_id="sample_dynamic_asset_create",
                granted_by=assigned_by,
                is_active=True,
            )
            db.add(permission_grant_sample)
            created_any = True

        if created_any:
            await db.commit()
            print("[OK] 创建了统一授权示例")
            return True

        print("[WARN] 统一授权示例已存在，跳过创建")
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

            # 7. 创建统一授权示例
            permission_grants_created = await create_permission_grant_samples(db)

        print("\nRBAC系统初始化完成！")
        print("创建内容:")
        print(f"   - 基础权限新增: {permissions_created} (总数: {len(permissions)})")
        print(f"   - 基础角色新增: {roles_created} (总数: {len(roles)})")
        print("   - 管理员用户: 已确保存在")
        print(
            f"   - 测试用户新增: {test_users_created} (已存在: {test_users_existing})"
        )
        print(
            "   - 统一授权示例: 已创建"
            if permission_grants_created
            else "   - 统一授权示例: 跳过"
        )

        print("\n默认登录信息:")
        print("   管理员用户名: admin")
        if (test_users_created + test_users_existing) > 0:
            print("   测试用户名: manager1(ops_admin), user1/user2(executive), viewer1(viewer)")
        else:
            print("   测试用户名: 未创建")
        print("   (默认密码需要在实际部署时设置)")

    except Exception as e:
        print(f"初始化失败: {str(e)}")
        import traceback

        traceback.print_exc()
if __name__ == "__main__":
    asyncio.run(main())
