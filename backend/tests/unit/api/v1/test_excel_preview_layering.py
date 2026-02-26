"""分层约束测试：excel preview 路由应走统一 ABAC 依赖。"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.documents.excel import preview as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_excel_preview_key_endpoints_should_use_require_authz() -> None:
    """excel 预览关键端点应接入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def preview_excel_advanced[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"asset\"[\s\S]*?resource_context=_ASSET_CREATE_RESOURCE_CONTEXT",
        r"async def preview_excel[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"asset\"[\s\S]*?resource_context=_ASSET_CREATE_RESOURCE_CONTEXT",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_excel_preview_unscoped_create_context_should_be_defined() -> None:
    from src.api.v1.documents.excel import preview as module

    expected_sentinel = "__unscoped__:asset:create"
    assert module._ASSET_CREATE_UNSCOPED_PARTY_ID == expected_sentinel
    assert module._ASSET_CREATE_RESOURCE_CONTEXT == {
        "party_id": expected_sentinel,
        "owner_party_id": expected_sentinel,
        "manager_party_id": expected_sentinel,
    }
