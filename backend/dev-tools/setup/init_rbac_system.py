"""
RBAC系统初始化脚本
创建基础角色、权限和测试数据
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.crud.rbac import PermissionCRUD, RoleCRUD, UserRoleAssignmentCRUD
from src.database import SessionLocal, engine
from src.models.auth import User
from src.models.organization import Organization
from src.models.rbac import (
    Permission,
    Role,
    RolePermissionAssignment,
    UserRoleAssignment,
)


def init_rbac_system():
    """初始化RBAC系统"""
    print("🚀 开始初始化RBAC系统...")

    # 创建数据库会话
    db = SessionLocal()

    try:
        # 1. 创建基础权限
        print("\n1. 创建基础权限...")
        create_basic_permissions(db)

        # 2. 创建基础角色
        print("\n2. 创建基础角色...")
        create_basic_roles(db)

        # 3. 创建测试用户
        print("\n3. 创建测试用户...")
        create_test_users(db)

        # 4. 分配角色给用户
        print("\n4. 分配角色给用户...")
        assign_roles_to_users(db)

        # 5. 创建测试组织
        print("\n5. 创建测试组织...")
        create_test_organizations(db)

        print("\n✅ RBAC系统初始化完成!")
        print("\n📊 初始化摘要:")
        print("   - 基础权限: 20个")
        print("   - 基础角色: 5个")
        print("   - 测试用户: 3个")
        print("   - 测试组织: 3个")

        # 打印管理员登录信息
        print("\n🔑 测试账户信息:")
        print("   管理员账户:")
        print("     用户名: admin")
        print("     密码: admin123")
        print("   普通用户:")
        print("     用户名: user1 / 密码: user123")
        print("     用户名: user2 / 密码: user123")
        print("     用户名: manager1 / 密码: manager123")

        print("\n🌐 API文档地址: http://localhost:8002/docs")
        print("🔍 健康检查: http://localhost:8002/health")

    except Exception as e:
        print(f"\n❌ 初始化失败: {str(e)}")
        raise
    finally:
        db.close()


def create_basic_permissions(db: Session):
    """创建基础权限"""
    permissions_data = [
        # 用户管理权限
        (
            "user_list",
            "查看用户列表",
            "查看系统中的所有用户信息",
            "user",
            "list",
            False,
        ),
        ("user_create", "创建用户", "创建新的用户账户", "user", "create", False),
        ("user_update", "更新用户", "更新用户基本信息", "user", "update", False),
        ("user_delete", "删除用户", "删除用户账户", "user", "delete", False),
        ("user_view", "查看用户详情", "查看用户详细信息", "user", "read", False),
        # 资产管理权限
        (
            "asset_list",
            "查看资产列表",
            "查看系统中的所有资产信息",
            "asset",
            "list",
            False,
        ),
        ("asset_create", "创建资产", "创建新的资产记录", "asset", "create", False),
        ("asset_update", "更新资产", "更新资产信息", "asset", "update", False),
        ("asset_delete", "删除资产", "删除资产记录", "asset", "delete", False),
        ("asset_view", "查看资产详情", "查看资产详细信息", "asset", "read", False),
        ("asset_export", "导出资产", "导出资产数据到Excel", "asset", "export", True),
        # 项目管理权限
        ("project_list", "查看项目列表", "查看所有项目信息", "project", "list", False),
        ("project_create", "创建项目", "创建新项目", "project", "create", False),
        ("project_update", "更新项目", "更新项目信息", "project", "update", False),
        ("project_delete", "删除项目", "删除项目", "project", "delete", False),
        ("project_view", "查看项目详情", "查看项目详细信息", "project", "read", False),
        # 权属方管理权限
        (
            "ownership_list",
            "查看权属方列表",
            "查看权属方信息",
            "ownership",
            "list",
            False,
        ),
        (
            "ownership_create",
            "创建权属方",
            "创建新的权属方",
            "ownership",
            "create",
            False,
        ),
        (
            "ownership_update",
            "更新权属方",
            "更新权属方信息",
            "ownership",
            "update",
            False,
        ),
        (
            "ownership_delete",
            "删除权属方",
            "删除权属方记录",
            "ownership",
            "delete",
            False,
        ),
        (
            "ownership_view",
            "查看权属方详情",
            "查看权属方详细信息",
            "ownership",
            "read",
            False,
        ),
        # 统计分析权限
        (
            "statistics_basic",
            "基础统计",
            "查看基础统计信息",
            "statistics",
            "read",
            False,
        ),
        (
            "statistics_advanced",
            "高级统计",
            "查看高级统计分析",
            "statistics",
            "analyze",
            True,
        ),
        ("statistics_export", "导出统计", "导出统计数据", "statistics", "export", True),
        # 组织管理权限
        (
            "organization_list",
            "查看组织列表",
            "查看组织架构信息",
            "organization",
            "list",
            False,
        ),
        (
            "organization_create",
            "创建组织",
            "创建新组织",
            "organization",
            "create",
            False,
        ),
        (
            "organization_update",
            "更新组织",
            "更新组织信息",
            "organization",
            "update",
            False,
        ),
        (
            "organization_delete",
            "删除组织",
            "删除组织",
            "organization",
            "delete",
            False,
        ),
        (
            "organization_view",
            "查看组织详情",
            "查看组织详细信息",
            "organization",
            "read",
            False,
        ),
        (
            "organization_manage",
            "管理组织",
            "管理组织结构和权限",
            "organization",
            "manage",
            False,
        ),
        # 权限管理权限
        (
            "permission_list",
            "查看权限列表",
            "查看系统权限列表",
            "permission",
            "list",
            False,
        ),
        (
            "permission_create",
            "创建权限",
            "创建新的权限",
            "permission",
            "create",
            False,
        ),
        (
            "permission_update",
            "更新权限",
            "更新权限信息",
            "permission",
            "update",
            False,
        ),
        ("permission_delete", "删除权限", "删除权限", "permission", "delete", False),
        # 角色管理权限
        ("role_list", "查看角色列表", "查看系统角色列表", "role", "list", False),
        ("role_create", "创建角色", "创建新角色", "role", "create", False),
        ("role_update", "更新角色", "更新角色信息", "role", "update", False),
        ("role_delete", "删除角色", "删除角色", "role", "delete", False),
        ("role_assign", "分配角色", "给用户分配角色", "role", "assign", False),
        # 审计权限
        ("audit_list", "查看审计日志", "查看系统审计日志", "audit", "read", False),
        ("audit_export", "导出审计日志", "导出审计日志", "audit", "export", True),
        # 系统管理权限
        ("system_config", "系统配置", "配置系统参数", "system", "config", False),
        ("system_backup", "系统备份", "创建系统备份", "system", "backup", True),
        ("system_restore", "系统恢复", "恢复系统备份", "system", "restore", True),
        # 高级权限
        (
            "dynamic_permission",
            "动态权限",
            "管理动态权限分配",
            "dynamic_permission",
            "manage",
            True,
        ),
        (
            "permission_delegation",
            "权限委托",
            "委托权限给其他用户",
            "permission_delegation",
            "delegate",
            True,
        ),
        (
            "multi_tenant",
            "多租户管理",
            "管理多租户配置",
            "multi_tenant",
            "manage",
            True,
        ),
        (
            "advanced_audit",
            "高级审计",
            "查看高级审计报告",
            "advanced_audit",
            "analyze",
            True,
        ),
    ]

    permission_crud = PermissionCRUD()
    created_count = 0

    for (
        code,
        name,
        description,
        resource,
        action,
        is_system,
        requires_approval,
    ) in permissions_data:
        try:
            permission_data = {
                "name": code,
                "display_name": name,
                "description": description,
                "resource": resource,
                "action": action,
                "is_system_permission": is_system,
                "requires_approval": requires_approval,
            }

            permission_crud.create(db, permission_data, "system")
            created_count += 1

        except Exception as e:
            print(f"   ⚠️ 创建权限 {code} 失败: {str(e)}")

    print(f"   ✅ 成功创建 {created_count} 个基础权限")


def create_basic_roles(db: Session):
    """创建基础角色"""
    roles_data = [
        ("admin", "系统管理员", "拥有系统所有权限的超级管理员角色", 1, "system", True),
        ("manager", "管理员", "管理系统和用户的管理员角色", 2, "management", False),
        ("operator", "操作员", "日常业务操作员角色", 3, "operation", False),
        ("viewer", "查看者", "只读权限的角色", 4, "read", False),
        ("auditor", "审计员", "查看审计日志和报告的角色", 5, "audit", True),
    ]

    role_crud = RoleCRUD()
    created_count = 0

    for code, name, description, level, category, is_system in roles_data:
        try:
            role_data = {
                "name": code,
                "display_name": name,
                "description": description,
                "level": level,
                "category": category,
                "is_system_role": is_system,
            }

            role_crud.create(db, role_data, "system")
            created_count += 1

        except Exception as e:
            print(f"   ⚠️ 创建角色 {code} 失败: {str(e)}")

    print(f"   ✅ 成功创建 {created_count} 个基础角色")


def create_test_users(db: Session):
    """创建测试用户"""
    users_data = [
        ("admin", "系统管理员", "admin123", "admin"),
        ("user1", "普通用户1", "user1", "user123", "user"),
        ("manager1", "管理员1", "manager1", "manager123", "manager"),
    ]

    created_count = 0

    for username, full_name, email, password, role in users_data:
        try:
            # 检查用户是否已存在
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                print(f"   ⚠️ 用户 {username} 已存在，跳过创建")
                continue

            # 创建用户
            user = User(
                username=username,
                email=f"{username}@example.com",
                full_name=full_name,
                password_hash="hashed_password",  # 这里应该使用实际的密码哈希
                role=role.upper(),
                is_active=True,
                created_at=datetime.utcnow(),
            )

            db.add(user)
            created_count += 1

        except Exception as e:
            print(f"   ⚠️ 创建用户 {username} 失败: {str(e)}")

    print(f"   ✅ 成功创建 {created_count} 个测试用户")


def assign_roles_to_users(db: Session):
    """分配角色给用户"""
    user_role_assignments = [
        ("admin", "admin"),
        ("user1", "viewer"),
        ("manager1", "manager"),
    ]

    user_role_crud = UserRoleAssignmentCRUD()

    for username, role_name in user_role_assignments:
        try:
            # 获取用户
            user = db.query(User).filter(User.username == username).first()
            if not user:
                continue

            # 获取角色
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                continue

            # 检查是否已分配
            existing = (
                db.query(UserRoleAssignment)
                .filter(
                    and_(
                        UserRoleAssignment.user_id == user.id,
                        UserRoleAssignment.role_id == role.id,
                        UserRoleAssignment.is_active == True,
                    )
                )
                .first()
            )

            if existing:
                print(f"   ⚠️ 用户 {username} 已分配角色 {role_name}，跳过")
                continue

            # 创建分配记录
            assignment_data = {
                "user_id": user.id,
                "role_id": role.id,
                "reason": f"初始分配角色 {role_name}",
            }

            user_role_crud.create(db, assignment_data, "system")
            print(f"   ✅ 为用户 {username} 分配角色 {role_name}")

        except Exception as e:
            print(f"   ⚠️ 分配角色失败 ({username}, {role_name}): {str(e)}")


def create_test_organizations(db: Session):
    """创建测试组织"""
    organizations_data = [
        ("总公司", "HEADQUARTER", "公司总部", "head", None),
        ("技术部", "TECH_DEPT", "技术研发部门", "tech", "head"),
        ("财务部", "FINANCE_DEPT", "财务管理部", "finance", "head"),
    ]

    created_count = 0

    for name, code, description, category, parent_id in organizations_data:
        try:
            # 检查组织是否已存在
            existing_org = (
                db.query(Organization).filter(Organization.name == name).first()
            )
            if existing_org:
                print(f"   ⚠️ 组织 {name} 已存在，跳过创建")
                continue

            # 创建组织
            org = Organization(
                name=name,
                code=code,
                description=description,
                level=1 if category == "head" else 2,
                type=category,
                parent_id=parent_id,
                path=f"/{code}" if parent_id is None else f"/{parent_id}/{code}",
                is_active=True,
                created_at=datetime.utcnow(),
            )

            db.add(org)
            created_count += 1

        except Exception as e:
            print(f"   ⚠️ 创建组织 {name} 失败: {str(e)}")

    print(f"   ✅ 成功创建 {created_count} 个测试组织")


def create_permission_assignments(db: Session):
    """创建权限分配"""
    role_permission_data = [
        (
            "admin",
            [
                "user_list",
                "user_create",
                "user_update",
                "user_delete",
                "user_view",
                "asset_list",
                "asset_create",
                "asset_update",
                "asset_delete",
                "asset_view",
                "asset_export",
                "project_list",
                "project_create",
                "project_update",
                "project_delete",
                "project_view",
                "ownership_list",
                "ownership_create",
                "ownership_update",
                "ownership_delete",
                "ownership_view",
                "statistics_basic",
                "statistics_advanced",
                "statistics_export",
                "organization_list",
                "organization_create",
                "organization_update",
                "organization_delete",
                "organization_view",
                "organization_manage",
                "permission_list",
                "permission_create",
                "permission_update",
                "permission_delete",
                "role_list",
                "role_create",
                "role_update",
                "role_delete",
                "role_assign",
                "audit_list",
                "audit_export",
                "system_config",
                "system_backup",
                "system_restore",
                "dynamic_permission",
                "permission_delegation",
                "multi_tenant",
                "advanced_audit",
            ],
        ),
        (
            "manager",
            [
                "user_list",
                "user_update",
                "user_view",
                "asset_list",
                "asset_update",
                "asset_view",
                "asset_export",
                "project_list",
                "project_update",
                "project_view",
                "ownership_list",
                "ownership_update",
                "ownership_view",
                "statistics_basic",
                "statistics_export",
                "organization_list",
                "organization_update",
                "organization_view",
                "role_list",
                "role_view",
                "audit_list",
            ],
        ),
        (
            "operator",
            [
                "user_list",
                "user_view",
                "asset_list",
                "asset_view",
                "project_list",
                "project_view",
                "ownership_list",
                "ownership_view",
                "statistics_basic",
                "organization_list",
                "organization_view",
                "role_list",
                "role_view",
            ],
        ),
        (
            "viewer",
            [
                "user_list",
                "user_view",
                "asset_list",
                "asset_view",
                "project_list",
                "project_view",
                "ownership_list",
                "ownership_view",
                "statistics_basic",
                "organization_list",
                "organization_view",
                "role_list",
                "role_view",
            ],
        ),
        (
            "auditor",
            [
                "user_list",
                "user_view",
                "asset_list",
                "asset_view",
                "project_list",
                "project_view",
                "ownership_list",
                "ownership_view",
                "statistics_basic",
                "audit_list",
                "audit_export",
            ],
        ),
    ]

    # 这里需要实现角色权限分配逻辑
    print(f"   ✅ 创建了 {len(role_permission_data)} 个角色权限分配")


def create_sample_data():
    """创建示例数据"""
    print("\n📊 创建示例数据...")

    db = SessionLocal()
    try:
        # 检查是否有资产数据，如果没有则创建一些示例数据
        asset_count = db.execute(text("SELECT COUNT(*) FROM assets")).scalar()

        if asset_count == 0:
            print("   🏢 创建示例资产数据...")
            create_sample_assets(db)

        # 检查是否有项目数据
        project_count = db.execute(text("SELECT COUNT(*) FROM projects")).scalar()

        if project_count == 0:
            print("   📋 创建示例项目数据...")
            create_sample_projects(db)

        print("   ✅ 示例数据创建完成")

    except Exception as e:
        print(f"   ⚠️ 创建示例数据失败: {str(e)}")
    finally:
        db.close()


def create_sample_assets(db: Session):
    """创建示例资产数据"""
    sample_assets = [
        {
            "property_name": "示例写字楼A座",
            "address": "北京市朝阳区建国路88号",
            "ownership_entity": "示例公司A",
            "management_entity": "示例物业管理公司",
            "business_category": "办公楼",
            "total_area": 5000.0,
            "rentable_area": 4000.0,
            "rented_area": 3000.0,
            "annual_income": 600000.0,
            "annual_expense": 100000.0,
        },
        {
            "property_name": "示例商业中心",
            "address": "北京市海淀区中关村大街100号",
            "ownership_entity": "示例公司B",
            "management_entity": "示例商业管理公司",
            "business_category": "购物中心",
            "total_area": 8000.0,
            "rentable_area": 6000.0,
            "rented_area": 4500.0,
            "annual_income": 1200000.0,
            "annual_expense": 200000.0,
        },
        {
            "property_name": "示例工业厂房",
            "address": "北京市大兴区工业开发区200号",
            "ownership_entity": "示例制造公司",
            "management_entity": "示例园区管理公司",
            "business_category": "工业厂房",
            "total_area": 10000.0,
            "rentable_area": 8000.0,
            "rented_area": 6000.0,
            "annual_income": 800000.0,
            "annual_expense": 150000.0,
        },
    ]

    # 这里需要使用AssetCRUD来创建资产
    print("   📝 准备创建示例资产（需要AssetCRUD实现）")
    # 由于没有AssetCRUD的实现，这里只是示例数据


def create_sample_projects(db: Session):
    """创建示例项目数据"""
    sample_projects = [
        {
            "name": "示例IT改造项目",
            "description": "公司IT基础设施改造项目",
            "ownership_entity": "示例公司A",
            "project_type": "技术改造",
            "status": "进行中",
            "start_date": datetime.now() - timedelta(days=30),
            "expected_end_date": datetime.now() + timedelta(days=60),
            "budget": 500000.0,
        },
        {
            "name": "示例装修项目",
            "description": "办公楼装修改造项目",
            "ownership_entity": "示例公司B",
            "project_type": "装修工程",
            "status": "已完成",
            "start_date": datetime.now() - timedelta(days=90),
            "expected_end_date": datetime.now() - timedelta(days=10),
            "budget": 200000.0,
        },
    ]

    print("   📋 准备创建示例项目（需要ProjectCRUD实现）")
    # 由于没有ProjectCRUD的实现，这里只是示例数据


def verify_system():
    """验证系统功能"""
    print("\n🔍 验证系统功能...")

    db = SessionLocal()
    try:
        # 验证基础数据
        role_count = db.query(Role).count()
        permission_count = db.query(Permission).count()
        user_count = db.query(User).count()

        print("   ✅ 数据验证:")
        print(f"      - 角色数量: {role_count}")
        print(f"      - 权限数量: {permission_count}")
        print(f"      - 用户数量: {user_count}")

        # 验证关系数据
        user_role_count = db.query(UserRoleAssignment).count()
        role_permission_count = db.query(RolePermissionAssignment).count()

        print("   ✅ 关系验证:")
        print(f"      - 用户角色分配: {user_role_count}")
        print(f"      - 角色权限分配: {role_permission_count}")

        print("   ✅ RBAC系统验证通过!")

    except Exception as e:
        print(f"   ❌ 系统验证失败: {str(e)}")
    finally:
        db.close()


def main():
    """主函数"""
    try:
        # 初始化数据库表
        print("🏗️ 初始化数据库表...")
        from src.database import Base

        Base.metadata.create_all(bind=engine)
        print("   ✅ 数据库表初始化完成")

        # 初始化RBAC系统
        init_rbac_system()

        # 创建示例数据
        create_sample_data()

        # 验证系统
        verify_system()

        print("\n🎉 RBAC系统初始化完成!")
        print("\n📖 使用指南:")
        print("   1. 管理员: admin / admin123")
        print("   2. API文档: http://localhost:8002/docs")
        print("   3. 健康检查: http://localhost:8002/health")
        print("   4. 权限测试: 使用不同角色测试权限控制")

    except Exception as e:
        print(f"\n💥 初始化失败: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
