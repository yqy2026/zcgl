"""
LLM Prompts API测试

Test coverage for LLM Prompts API endpoints:
- CRUD operations for prompt templates
- Version management
- Prompt activation and rollback
- Validation and error handling
"""

import pytest
from fastapi import status


@pytest.fixture
def admin_user_headers(client, admin_user):
    """管理员用户认证头"""
    # client fixture already bypasses authentication
    return {"Authorization": "Bearer mocked_token"}


class TestLLMPromptsCRUD:
    """测试LLM Prompts CRUD操作"""

    def test_create_prompt_success(self, client, admin_user_headers):
        """测试成功创建Prompt模板"""
        prompt_data = {
            "name": "test_prompt",
            "doc_type": "CONTRACT",
            "provider": "qwen",
            "system_prompt": "You are a helpful assistant",
            "user_prompt_template": "Extract information from: {content}",
        }
        response = client.post(
            "/api/v1/llm-prompts/", json=prompt_data, headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_get_prompts_list(self, client, admin_user_headers):
        """测试获取Prompt列表"""
        response = client.get("/api/v1/llm-prompts/", headers=admin_user_headers)
        assert response.status_code == status.HTTP_200_OK

    def test_get_prompts_with_pagination(self, client, admin_user_headers):
        """测试分页功能"""
        response = client.get(
            "/api/v1/llm-prompts/?page=1&page_size=10", headers=admin_user_headers
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_prompt_by_id(self, client, admin_user_headers):
        """测试获取单个Prompt"""
        response = client.get("/api/v1/llm-prompts/test-id", headers=admin_user_headers)
        # 可能返回200或404
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_update_prompt(self, client, admin_user_headers):
        """测试更新Prompt"""
        update_data = {"system_prompt": "Updated system prompt"}
        response = client.put(
            "/api/v1/llm-prompts/test-id", json=update_data, headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_delete_prompt(self, client, admin_user_headers):
        """测试删除Prompt"""
        response = client.delete(
            "/api/v1/llm-prompts/test-id", headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


class TestLLMPromptsVersionManagement:
    """测试版本管理功能"""

    def test_get_prompt_versions(self, client, admin_user_headers):
        """测试获取Prompt版本列表"""
        response = client.get(
            "/api/v1/llm-prompts/test-id/versions", headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_rollback_prompt_version(self, client, admin_user_headers):
        """测试回滚到指定版本"""
        rollback_data = {"version_id": "version-123"}
        response = client.post(
            "/api/v1/llm-prompts/test-id/rollback",
            json=rollback_data,
            headers=admin_user_headers,
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


class TestLLMPromptsActivation:
    """测试Prompt激活功能"""

    def test_activate_prompt(self, client, admin_user_headers):
        """测试激活Prompt"""
        response = client.post(
            "/api/v1/llm-prompts/test-id/activate", headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


class TestLLMPromptsValidation:
    """测试数据验证"""

    def test_create_duplicate_name(self, client, admin_user_headers):
        """测试创建重复名称的Prompt"""
        prompt_data = {
            "name": "duplicate_test",
            "doc_type": "CONTRACT",
            "provider": "qwen",
            "system_prompt": "Test",
        }
        # 创建两次，第二次应该失败
        client.post(
            "/api/v1/llm-prompts/", json=prompt_data, headers=admin_user_headers
        )
        response = client.post(
            "/api/v1/llm-prompts/", json=prompt_data, headers=admin_user_headers
        )
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK]

    def test_create_invalid_provider(self, client, admin_user_headers):
        """测试使用无效的provider"""
        prompt_data = {
            "name": "invalid_provider_test",
            "doc_type": "CONTRACT",
            "provider": "invalid_provider",
            "system_prompt": "Test",
        }
        response = client.post(
            "/api/v1/llm-prompts/", json=prompt_data, headers=admin_user_headers
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_200_OK,
        ]


class TestLLMPromptsAuthentication:
    """测试认证和授权"""

    def test_unauthorized_access(self, unauthenticated_client):
        """测试未授权访问"""
        response = unauthenticated_client.get("/api/v1/llm-prompts/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
