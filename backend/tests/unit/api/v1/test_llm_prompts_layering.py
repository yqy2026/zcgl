"""分层约束测试：llm_prompts 路由应接入统一 ABAC 依赖。"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1 import llm_prompts as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_llm_prompts_module_should_import_authz_dependency() -> None:
    """llm_prompts 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_llm_prompts_endpoints_should_use_require_authz() -> None:
    """llm_prompts 关键端点应接入 require_authz。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def create_prompt[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"llm_prompt\"",
        r"async def get_prompts[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"llm_prompt\"",
        r"async def get_prompt[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"llm_prompt\"[\s\S]*?resource_id=\"\{prompt_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def update_prompt[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"llm_prompt\"[\s\S]*?resource_id=\"\{prompt_id\}\"",
        r"async def activate_prompt[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"llm_prompt\"[\s\S]*?resource_id=\"\{prompt_id\}\"",
        r"async def rollback_prompt[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"llm_prompt\"[\s\S]*?resource_id=\"\{prompt_id\}\"",
        r"async def get_prompt_versions[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"llm_prompt\"[\s\S]*?resource_id=\"\{prompt_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def get_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"llm_prompt\"",
        r"async def collect_feedback[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"llm_prompt\"",
    ]

    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_llm_prompt_should_not_define_fake_create_scope_context() -> None:
    from src.api.v1 import llm_prompts as module

    assert not hasattr(module, "_LLM_PROMPT_CREATE_UNSCOPED_PARTY_ID")
    assert not hasattr(module, "_resolve_llm_prompt_create_resource_context")
