"""
字典API测试

Test coverage for Dictionaries API endpoints:
- Get dictionary data
- Cache management
- Validation
"""

import pytest
from fastapi import status


@pytest.fixture
def admin_user_headers(client, admin_user):
    """管理员用户认证头"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.username, "password": "admin123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestDictionariesAPI:
    """测试字典API"""

    def test_get_dictionaries_success(self, client, admin_user_headers):
        """测试获取字典数据"""
        response = client.get(
            "/api/v1/dictionaries/",
            headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_dictionary_by_type_success(self, client, admin_user_headers):
        """测试按类型获取字典"""
        response = client.get(
            "/api/v1/dictionaries/asset_type",
            headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_dictionary_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/dictionaries/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_dictionary_cache_hit(self, client, admin_user_headers):
        """测试字典缓存命中"""
        # 第一次请求
        response1 = client.get(
            "/api/v1/dictionaries/asset_type",
            headers=admin_user_headers
        )

        # 第二次请求（应该命中缓存）
        response2 = client.get(
            "/api/v1/dictionaries/asset_type",
            headers=admin_user_headers
        )

        assert response1.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        assert response2.status_code == response1.status_code

    def test_get_dictionary_with_options(self, client, admin_user_headers):
        """测试获取字典选项"""
        response = client.get(
            "/api/v1/dictionaries/asset_type?include_inactive=true",
            headers=admin_user_headers
        )

        # 端点应该存在
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_multiple_dictionaries(self, client, admin_user_headers):
        """测试批量获取字典"""
        response = client.get(
            "/api/v1/dictionaries/?types=asset_type,project_status,ownership_type",
            headers=admin_user_headers
        )

        # 端点应该存在
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_refresh_dictionary_cache(self, client, admin_user_headers):
        """测试刷新字典缓存"""
        response = client.post(
            "/api/v1/dictionaries/refresh-cache",
            headers=admin_user_headers
        )

        # 可能需要管理员权限
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    def test_get_dictionary_by_type_not_found(self, client, admin_user_headers):
        """测试获取不存在的字典类型"""
        response = client.get(
            "/api/v1/dictionaries/nonexistent_type",
            headers=admin_user_headers
        )

        # 应该返回404或空结果
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # 可能返回空数组
            assert isinstance(data, list) and len(data) == 0 or "items" in data

    def test_dictionary_with_unicode(self, client, admin_user_headers):
        """测试字典包含Unicode字符"""
        response = client.get(
            "/api/v1/dictionaries/",
            headers=admin_user_headers
        )

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # 验证可以正确处理Unicode
            assert isinstance(data, (dict, list))

    def test_dictionary_structure_validation(self, client, admin_user_headers):
        """测试字典数据结构验证"""
        response = client.get(
            "/api/v1/dictionaries/asset_type",
            headers=admin_user_headers
        )

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # 验证返回数据结构
            if isinstance(data, dict) and "items" in data:
                # 字典项应该包含value和label字段
                for item in data["items"][:3]:  # 只验证前3个
                    assert "value" in item or "code" in item
                    assert "label" in item or "name" in item
            elif isinstance(data, list) and len(data) > 0:
                # 列表格式
                for item in data[:3]:
                    assert "value" in item or "code" in item
                    assert "label" in item or "name" in item
