"""分层约束测试：excel template 路由应走统一 ABAC 依赖。"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.documents.excel import template as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_excel_template_endpoint_should_use_require_authz() -> None:
    """模板下载端点应接入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    expected_pattern = (
        r"async def download_template[\s\S]*?require_authz\("
        r"[\s\S]*?action=\"read\"[\s\S]*?resource_type=\"asset\""
    )
    assert re.search(expected_pattern, module_source), expected_pattern
