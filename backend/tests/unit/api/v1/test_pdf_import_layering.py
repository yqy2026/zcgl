"""分层约束测试：pdf_import 包装路由应声明 ABAC 依赖。"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.documents import pdf_import as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_pdf_import_wrapper_module_should_import_authz_dependency() -> None:
    """pdf_import 包装路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_pdf_import_wrapper_include_routes_should_attach_require_authz() -> None:
    """pdf_import 包装路由 include_router 时应附带 require_authz 依赖。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"router\.include_router\([\s\S]*?pdf_upload\.router[\s\S]*?dependencies=\[\s*Depends\(\s*require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"rent_contract\"[\s\S]*?resource_context=_RENT_CONTRACT_CREATE_RESOURCE_CONTEXT",
        r"router\.include_router\([\s\S]*?pdf_sessions_module\.router[\s\S]*?dependencies=\[\s*Depends\(\s*require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"",
        r"router\.include_router\([\s\S]*?pdf_system\.router[\s\S]*?dependencies=\[\s*Depends\(\s*require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_pdf_import_wrapper_unscoped_create_context_should_be_defined() -> None:
    from src.api.v1.documents import pdf_import as module

    expected_sentinel = "__unscoped__:rent_contract:create"
    assert module._RENT_CONTRACT_CREATE_UNSCOPED_PARTY_ID == expected_sentinel
    assert module._RENT_CONTRACT_CREATE_RESOURCE_CONTEXT == {
        "party_id": expected_sentinel,
        "owner_party_id": expected_sentinel,
        "manager_party_id": expected_sentinel,
    }
