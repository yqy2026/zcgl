"""分层约束测试：excel export_ops 路由应走统一 ABAC 依赖。"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.documents.excel import export_ops as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_excel_export_ops_key_endpoints_should_use_require_authz() -> None:
    """excel 导出关键端点应接入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def export_excel[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"asset\"",
        r"async def export_selected_assets[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"asset\"",
        r"async def export_excel_async[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"asset\"",
        r"async def download_export_file[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"task\"[\s\S]*?resource_id=\"\{task_id\}\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern
