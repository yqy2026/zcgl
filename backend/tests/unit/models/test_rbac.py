"""RBAC model unit tests."""

from src.models.rbac import (
    Permission,
    PermissionAuditLog,
    PermissionGrant,
    ResourcePermission,
    Role,
    UserRoleAssignment,
    role_permissions,
)


def test_role_permissions_association_table_structure() -> None:
    assert role_permissions.name == "role_permissions"
    assert "role_id" in role_permissions.c
    assert "permission_id" in role_permissions.c


def test_role_and_permission_creation() -> None:
    role = Role(name="admin", display_name="管理员")
    permission = Permission(
        name="asset:view",
        display_name="查看资产",
        resource="asset",
        action="view",
    )

    assert role.name == "admin"
    assert role.display_name == "管理员"
    assert "admin" in repr(role)

    assert permission.name == "asset:view"
    assert permission.resource == "asset"
    assert permission.action == "view"
    assert permission.is_active is True
    assert "asset" in repr(permission)


def test_role_model_should_not_expose_legacy_organization_column() -> None:
    """Phase4 Step4: roles.organization_id 已删除，ORM 不应再映射该列。"""
    assert "organization_id" not in Role.__table__.columns.keys()


def test_assignment_and_grant_models_creation() -> None:
    assignment = UserRoleAssignment(user_id="user-1", role_id="role-1")
    grant = PermissionGrant(user_id="user-1", permission_id="perm-1")
    resource_permission = ResourcePermission(
        resource_type="asset",
        resource_id="asset-1",
        permission_level="write",
    )
    audit = PermissionAuditLog(action="grant")

    assert assignment.user_id == "user-1"
    assert assignment.role_id == "role-1"
    assert "user-1" in repr(assignment)

    assert grant.user_id == "user-1"
    assert grant.permission_id == "perm-1"
    assert "allow" in repr(grant)

    assert resource_permission.resource_type == "asset"
    assert resource_permission.resource_id == "asset-1"
    assert "asset:asset-1" in repr(resource_permission)

    assert audit.action == "grant"
    assert "grant" in repr(audit)
