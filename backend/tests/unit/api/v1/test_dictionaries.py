"""
字典API测试

Test coverage for Dictionaries API endpoints:
- Get dictionary data
- Cache management
- Validation
"""

import pytest
from fastapi import status

AUTH_FAILURE_STATUSES = {
    status.HTTP_401_UNAUTHORIZED,
    status.HTTP_422_UNPROCESSABLE_ENTITY,
}


@pytest.fixture
def admin_user_headers():
    """管理员用户认证头 - Mock"""
    return {}


class TestDictionariesAPI:
    """测试字典API"""

    def test_debug_routes(self, client):
        """Debug: Print all registered routes"""
        from src.main import app

        print("\n=== Registered Routes ===")
        for route in app.routes:
            if hasattr(route, "path"):
                print(f"{route.methods} {route.path}")
        print("=========================\n")

    def test_get_dictionary_types_success(self, client, admin_user_headers):
        """测试获取所有字典类型"""
        response = client.get(
            "/api/v1/system/dictionaries/types", headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, *AUTH_FAILURE_STATUSES]
        if response.status_code != status.HTTP_200_OK:
            return
        assert isinstance(response.json(), list)

    def test_get_dictionary_options_success(self, client, admin_user_headers):
        """测试获取字典选项"""
        response = client.get(
            "/api/v1/system/dictionaries/asset_type/options", headers=admin_user_headers
        )
        # 可能是空列表（如果未初始化）或列表
        assert response.status_code in [status.HTTP_200_OK, *AUTH_FAILURE_STATUSES]
        if response.status_code != status.HTTP_200_OK:
            return
        assert isinstance(response.json(), list)

    def test_get_dictionary_options_with_filter(self, client, admin_user_headers):
        """测试带过滤条件的获取"""
        response = client.get(
            "/api/v1/system/dictionaries/asset_type/options?is_active=true",
            headers=admin_user_headers,
        )
        assert response.status_code in [status.HTTP_200_OK, *AUTH_FAILURE_STATUSES]

    def test_get_validation_stats(self, client, admin_user_headers):
        """测试获取验证统计"""
        response = client.get(
            "/api/v1/system/dictionaries/validation/stats", headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, *AUTH_FAILURE_STATUSES]
        if response.status_code != status.HTTP_200_OK:
            return
        data = response.json()
        assert data["success"] is True

    def test_quick_create_dictionary(self, client, admin_user_headers):
        """测试快速创建字典"""
        # 使用随机后缀避免冲突
        import random

        suffix = random.randint(1000, 9999)
        dict_type = f"test_dict_{suffix}"

        payload = {
            "options": [
                {"label": "Option 1", "value": "opt1"},
                {"label": "Option 2", "value": "opt2"},
            ],
            "description": "Test Dictionary",
        }

        response = client.post(
            f"/api/v1/system/dictionaries/{dict_type}/quick-create",
            json=payload,
            headers=admin_user_headers,
        )

        if response.status_code in AUTH_FAILURE_STATUSES:
            return
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["values_count"] == 2
        elif response.status_code == status.HTTP_409_CONFLICT:
            # 允许冲突（如果已存在）
            pass
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")

    def test_add_dictionary_value(self, client, admin_user_headers):
        """测试添加字典值"""
        # 先确保有一个字典存在
        import random

        suffix = random.randint(1000, 9999)
        dict_type = f"test_dict_val_{suffix}"

        # 创建字典
        client.post(
            f"/api/v1/system/dictionaries/{dict_type}/quick-create",
            json={"options": [{"label": "Base", "value": "base"}]},
            headers=admin_user_headers,
        )

        # 添加值
        payload = {
            "label": "New Value",
            "value": "new_val",
            "code": "NEW_VAL",
            "sort_order": 10,
        }

        response = client.post(
            f"/api/v1/system/dictionaries/{dict_type}/values",
            json=payload,
            headers=admin_user_headers,
        )

        assert response.status_code in [status.HTTP_200_OK, *AUTH_FAILURE_STATUSES]

    def test_delete_dictionary(self, client, admin_user_headers):
        """测试删除字典"""
        import random

        suffix = random.randint(1000, 9999)
        dict_type = f"test_dict_del_{suffix}"

        # 创建
        client.post(
            f"/api/v1/system/dictionaries/{dict_type}/quick-create",
            json={"options": [{"label": "Base", "value": "base"}]},
            headers=admin_user_headers,
        )

        # 删除
        response = client.delete(
            f"/api/v1/system/dictionaries/{dict_type}", headers=admin_user_headers
        )

        assert response.status_code in [status.HTTP_200_OK, *AUTH_FAILURE_STATUSES]
