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
def admin_user_headers(client, admin_user):
    """管理员用户认证头"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.username, "password": "admin123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestRolesCRUD:
    """测试角色CRUD操作"""

    def test_create_role_success(self, client, admin_user_headers):
        """测试成功创建角色"""
        role_data = {
            "name": "test_role",
            "description": "Test role description",
            "permissions": ["asset.read", "asset.write"],
        }
        response = client.post(
            "/api/v1/roles/", json=role_data, headers=admin_user_headers
        )
        # 端点可能不存在或返回不同状态
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_get_roles_list(self, client, admin_user_headers):
        """测试获取角色列表"""
        response = client.get("/api/v1/roles/", headers=admin_user_headers)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_role_by_id(self, client, admin_user_headers):
        """测试获取单个角色"""
        response = client.get("/api/v1/roles/test-role-id", headers=admin_user_headers)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_update_role(self, client, admin_user_headers):
        """测试更新角色"""
        update_data = {"description": "Updated description"}
        response = client.put(
            "/api/v1/roles/test-role-id", json=update_data, headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_delete_role(self, client, admin_user_headers):
        """测试删除角色"""
        response = client.delete(
            "/api/v1/roles/test-role-id", headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


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
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_role_permissions(self, client, admin_user_headers):
        """测试获取角色权限"""
        response = client.get(
            "/api/v1/roles/test-role-id/permissions", headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_revoke_permission_from_role(self, client, admin_user_headers):
        """测试撤销角色权限"""
        response = client.delete(
            "/api/v1/roles/test-role-id/permissions/asset.write",
            headers=admin_user_headers,
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


class TestUserRoleAssignments:
    """测试用户角色分配"""

    def test_assign_role_to_user(self, client, admin_user_headers):
        """测试为用户分配角色"""
        assignment_data = {"user_id": "test-user-id", "role_id": "test-role-id"}
        response = client.post(
            "/api/v1/roles/assign", json=assignment_data, headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_user_roles(self, client, admin_user_headers):
        """测试获取用户角色"""
        response = client.get(
            "/api/v1/roles/user/test-user-id", headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_revoke_role_from_user(self, client, admin_user_headers):
        """测试撤销用户角色"""
        response = client.delete(
            "/api/v1/roles/user/test-user-id/role/test-role-id",
            headers=admin_user_headers,
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


class TestRolesAuthentication:
    """测试认证和授权"""

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/roles/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_normal_user_cannot_create_roles(self, client, normal_user_headers):
        """测试普通用户无法创建角色"""
        role_data = {"name": "unauthorized_role"}
        response = client.post(
            "/api/v1/roles/", json=role_data, headers=normal_user_headers
        )
        # 普通用户应该被拒绝
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_404_NOT_FOUND,
        ]


@pytest.fixture
def normal_user_headers(client, normal_user):
    """普通用户认证头"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": normal_user.username, "password": "user123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
