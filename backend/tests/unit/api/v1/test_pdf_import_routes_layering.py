"""分层约束测试：pdf_import_routes 兼容路由应走统一 ABAC 依赖。"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.documents import pdf_import_routes as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_pdf_import_routes_key_endpoints_should_use_require_authz() -> None:
    """pdf 导入兼容路由关键端点应接入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"def get_pdf_import_info[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"",
        r"def get_pdf_import_sessions[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"",
        r"def upload_pdf_for_import[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"rent_contract\"[\s\S]*?resource_context=_RENT_CONTRACT_CREATE_RESOURCE_CONTEXT",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_pdf_import_routes_unscoped_create_context_should_be_defined() -> None:
    from src.api.v1.documents import pdf_import_routes as module

    expected_sentinel = "__unscoped__:rent_contract:create"
    assert module._RENT_CONTRACT_CREATE_UNSCOPED_PARTY_ID == expected_sentinel
    assert module._RENT_CONTRACT_CREATE_RESOURCE_CONTEXT == {
        "party_id": expected_sentinel,
        "owner_party_id": expected_sentinel,
        "manager_party_id": expected_sentinel,
    }
