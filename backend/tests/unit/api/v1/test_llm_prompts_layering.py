"""分层约束测试：llm_prompts 路由应接入统一 ABAC 依赖。"""

import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

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
        r"async def create_prompt[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"llm_prompt\"[\s\S]*?resource_context=_resolve_llm_prompt_create_resource_context",
        r"async def get_prompts[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"llm_prompt\"",
        r"async def get_prompt[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"llm_prompt\"[\s\S]*?resource_id=\"\{prompt_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def update_prompt[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"llm_prompt\"[\s\S]*?resource_id=\"\{prompt_id\}\"",
        r"async def activate_prompt[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"llm_prompt\"[\s\S]*?resource_id=\"\{prompt_id\}\"",
        r"async def rollback_prompt[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"llm_prompt\"[\s\S]*?resource_id=\"\{prompt_id\}\"",
        r"async def get_prompt_versions[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"llm_prompt\"[\s\S]*?resource_id=\"\{prompt_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def get_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"llm_prompt\"",
        r"async def collect_feedback[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"llm_prompt\"[\s\S]*?resource_context=_resolve_llm_prompt_create_resource_context",
    ]

    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


@pytest.mark.asyncio
async def test_llm_prompt_create_authz_context_should_include_party_scope_fields() -> None:
    from src.api.v1.llm_prompts import _resolve_llm_prompt_create_resource_context

    request = MagicMock()
    request.json = AsyncMock(
        return_value={
            "party_id": "party-001",
            "organization_id": "org-001",
        }
    )

    result = await _resolve_llm_prompt_create_resource_context(request)

    assert result == {
        "organization_id": "org-001",
        "party_id": "party-001",
        "owner_party_id": "party-001",
        "manager_party_id": "party-001",
    }


@pytest.mark.asyncio
async def test_llm_prompt_create_authz_context_should_fallback_to_unscoped_sentinel() -> None:
    from src.api.v1.llm_prompts import (
        _LLM_PROMPT_CREATE_UNSCOPED_PARTY_ID,
        _resolve_llm_prompt_create_resource_context,
    )

    request = MagicMock()
    request.json = AsyncMock(return_value={})

    result = await _resolve_llm_prompt_create_resource_context(request)

    assert result == {
        "party_id": _LLM_PROMPT_CREATE_UNSCOPED_PARTY_ID,
        "owner_party_id": _LLM_PROMPT_CREATE_UNSCOPED_PARTY_ID,
        "manager_party_id": _LLM_PROMPT_CREATE_UNSCOPED_PARTY_ID,
    }
