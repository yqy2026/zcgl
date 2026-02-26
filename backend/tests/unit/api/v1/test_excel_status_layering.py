"""分层约束测试：excel status 路由应走统一 ABAC 依赖。"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.documents.excel import status as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_excel_status_key_endpoints_should_use_require_authz() -> None:
    """状态与历史端点应接入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def get_excel_task_status[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"task\"[\s\S]*?resource_id=\"\{task_id\}\"",
        r"async def get_excel_history[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"asset\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern
