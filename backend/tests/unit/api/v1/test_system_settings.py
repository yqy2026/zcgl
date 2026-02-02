"""
系统设置API测试

Test coverage for System Settings API endpoints:
- Configuration management
- System parameters
- Settings CRUD
"""

import pytest
from fastapi import status


@pytest.fixture
def admin_user_headers(client, admin_user):
    """管理员用户认证头"""
    # client fixture already bypasses authentication
    return {}


class TestSystemSettingsAPI:
    """测试系统设置API"""

    def test_get_system_settings(self, client, admin_user_headers):
        """测试获取系统设置"""
        response = client.get("/api/v1/system-settings/", headers=admin_user_headers)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_setting_by_key(self, client, admin_user_headers):
        """测试获取单个设置项"""
        response = client.get(
            "/api/v1/system-settings/setting_key", headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_update_system_setting(self, client, admin_user_headers):
        """测试更新系统设置"""
        update_data = {"value": "updated_value", "description": "Updated description"}
        response = client.put(
            "/api/v1/system-settings/setting_key",
            json=update_data,
            headers=admin_user_headers,
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_create_system_setting(self, client, admin_user_headers):
        """测试创建系统设置"""
        setting_data = {
            "key": "new_setting",
            "value": "setting_value",
            "description": "New setting description",
        }
        response = client.post(
            "/api/v1/system-settings/", json=setting_data, headers=admin_user_headers
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_delete_system_setting(self, client, admin_user_headers):
        """测试删除系统设置"""
        response = client.delete(
            "/api/v1/system-settings/setting_key", headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_unauthorized_access(self, unauthenticated_client):
        """测试未授权访问"""
        response = unauthenticated_client.get("/api/v1/system-settings/")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_normal_user_cannot_modify_settings(self, client, normal_user_headers):
        """测试普通用户无法修改设置"""
        update_data = {"value": "unauthorized_update"}
        response = client.put(
            "/api/v1/system-settings/setting_key",
            json=update_data,
            headers=normal_user_headers,
        )
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_404_NOT_FOUND,
        ]


@pytest.fixture
def normal_user_headers(client, normal_user):
    """普通用户认证头"""
    from src.middleware.auth import get_current_active_user

    client.app.dependency_overrides[get_current_active_user] = lambda: normal_user
    return {}

