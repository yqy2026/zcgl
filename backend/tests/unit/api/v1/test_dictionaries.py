"""
字典API测试

Test coverage for Dictionaries API endpoints:
- Get dictionary data
- Cache management
- Validation
"""

from uuid import uuid4

import pytest
from fastapi import status


@pytest.fixture
def admin_user_headers():
    """管理员用户认证头 - Mock"""
    return {}


class TestDictionariesAPI:
    """测试字典API"""

    def test_debug_routes(self, client):
        """验证字典路由已注册。"""
        from src.main import app

        registered_paths = {
            route.path for route in app.routes if hasattr(route, "path")
        }
        assert "/api/v1/system/dictionaries/types" in registered_paths
        assert "/api/v1/system/dictionaries/{dict_type}/options" in registered_paths

    def test_get_dictionary_types_success(self, client, admin_user_headers):
        """测试获取所有字典类型"""
        response = client.get(
            "/api/v1/system/dictionaries/types", headers=admin_user_headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_get_dictionary_options_success(self, client, admin_user_headers):
        """测试获取字典选项"""
        response = client.get(
            "/api/v1/system/dictionaries/asset_type/options", headers=admin_user_headers
        )
        # 可能是空列表（如果未初始化）或有值列表
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_get_dictionary_options_with_filter(self, client, admin_user_headers):
        """测试带过滤条件的获取"""
        response = client.get(
            "/api/v1/system/dictionaries/asset_type/options?is_active=true",
            headers=admin_user_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_get_validation_stats(self, client, admin_user_headers):
        """测试获取验证统计"""
        response = client.get(
            "/api/v1/system/dictionaries/validation/stats", headers=admin_user_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    def test_quick_create_dictionary(self, client, admin_user_headers):
        """测试快速创建字典"""
        dict_type = f"test_dict_{uuid4().hex}"

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

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["values_count"] == 2

    def test_add_dictionary_value(self, client, admin_user_headers):
        """测试添加字典值"""
        dict_type = f"test_dict_val_{uuid4().hex}"

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

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data.get("message") == "字典值添加成功"
        assert response_data.get("value_id")

    def test_delete_dictionary(self, client, admin_user_headers):
        """测试删除字典"""
        dict_type = f"test_dict_del_{uuid4().hex}"

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

        assert response.status_code == status.HTTP_200_OK
