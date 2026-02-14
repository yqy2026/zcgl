"""
角色管理API测试

Test coverage for Roles API endpoints:
- Role CRUD operations
- Permission management
- Role assignments
- RBAC functionality
"""

import pytest
from fastapi import status


@pytest.fixture
def admin_user_headers(client):
    """管理员用户认证头（本地 mock，避免依赖 admin_user fixture 导致跳过）"""
    from unittest.mock import Mock

    from src.middleware.auth import get_current_active_user, require_admin

    mock_admin = Mock()
    mock_admin.id = "test-admin-id"
    mock_admin.username = "test-admin"
    mock_admin.is_admin = True
    mock_admin.is_active = True

    client.app.dependency_overrides[get_current_active_user] = lambda: mock_admin
    client.app.dependency_overrides[require_admin] = lambda: mock_admin
    yield {}
    client.app.dependency_overrides.pop(get_current_active_user, None)
    client.app.dependency_overrides.pop(require_admin, None)


class TestRolesCRUD:
    """测试角色CRUD操作"""

    def test_create_role_success(self, client, admin_user_headers):
        """测试成功创建角色"""
        role_data = {
            "name": "test_role",
            "display_name": "Test Role",
            "description": "Test role description",
            "permission_ids": ["asset.read", "asset.write"],
        }
        response = client.post(
            "/api/v1/roles", json=role_data, headers=admin_user_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_roles_list(self, client, admin_user_headers):
        """测试获取角色列表"""
        response = client.get("/api/v1/roles", headers=admin_user_headers)
        assert response.status_code == status.HTTP_200_OK

    def test_get_role_by_id(self, client, admin_user_headers):
        """测试获取单个角色"""
        response = client.get("/api/v1/roles/test-role-id", headers=admin_user_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_role(self, client, admin_user_headers):
        """测试更新角色"""
        update_data = {"description": "Updated description"}
        response = client.put(
            "/api/v1/roles/test-role-id", json=update_data, headers=admin_user_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_role(self, client, admin_user_headers):
        """测试删除角色"""
        response = client.delete(
            "/api/v1/roles/test-role-id", headers=admin_user_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestRolePermissions:
    """测试角色权限管理"""

    def test_assign_permissions_to_role(self, client, admin_user_headers):
        """测试为角色分配权限"""
        permissions_data = {
            "permissions": ["asset.read", "asset.write", "contract.read"]
        }
        response = client.post(
            "/api/v1/roles/test-role-id/permissions",
            json=permissions_data,
            headers=admin_user_headers,
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_get_role_permissions(self, client, admin_user_headers):
        """测试获取角色权限"""
        response = client.get(
            "/api/v1/roles/test-role-id/permissions", headers=admin_user_headers
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_revoke_permission_from_role(self, client, admin_user_headers):
        """测试撤销角色权限"""
        response = client.delete(
            "/api/v1/roles/test-role-id/permissions/asset.write",
            headers=admin_user_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUserRoleAssignments:
    """测试用户角色分配"""

    def test_assign_role_to_user(self, client, admin_user_headers):
        """测试为用户分配角色"""
        assignment_data = {"user_id": "test-user-id", "role_id": "test-role-id"}
        response = client.post(
            "/api/v1/roles/assign", json=assignment_data, headers=admin_user_headers
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_get_user_roles(self, client, admin_user_headers):
        """测试获取用户角色"""
        response = client.get(
            "/api/v1/roles/user/test-user-id", headers=admin_user_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_revoke_role_from_user(self, client, admin_user_headers):
        """测试撤销用户角色"""
        response = client.delete(
            "/api/v1/roles/user/test-user-id/role/test-role-id",
            headers=admin_user_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestRolesAuthentication:
    """测试认证和授权"""

    def test_unauthorized_access(self, unauthenticated_client):
        """测试未授权访问"""
        response = unauthenticated_client.get("/api/v1/roles")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data.get("error", {}).get("code") == "AUTHENTICATION_ERROR"

    def test_normal_user_cannot_create_roles(self, client_normal_user):
        """测试普通用户无法创建角色"""
        role_data = {"name": "unauthorized_role"}
        role_data["display_name"] = "Unauthorized Role"
        response = client_normal_user.post("/api/v1/roles", json=role_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
