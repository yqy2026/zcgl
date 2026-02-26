"""分层约束测试：financial_stats 路由应走统一 ABAC 依赖。"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.analytics.statistics_modules import financial_stats as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_financial_stats_module_should_import_authz_dependency() -> None:
    """financial_stats 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_financial_summary_endpoint_should_use_require_authz() -> None:
    """财务汇总端点应接入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    pattern = (
        r"async def get_financial_summary[\s\S]*?require_authz\("
        r"[\s\S]*?action=\"read\"[\s\S]*?resource_type=\"analytics\""
    )
    assert re.search(pattern, module_source), pattern
