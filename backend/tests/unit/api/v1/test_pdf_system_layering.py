"""分层约束测试：pdf_system 路由应走统一 ABAC 依赖。"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.documents import pdf_system as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_pdf_system_key_read_endpoints_should_use_require_authz() -> None:
    """pdf 系统信息关键读端点应接入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"def get_system_info[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"",
        r"async def health_check[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"",
        r"def get_pdf_import_sessions[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern
