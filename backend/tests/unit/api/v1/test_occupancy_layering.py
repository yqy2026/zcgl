"""分层约束测试：occupancy 路由应接入统一鉴权依赖。"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.assets import occupancy as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_occupancy_module_should_not_import_asset_crud_directly() -> None:
    """occupancy 路由模块不应直接导入 asset CRUD。"""
    module_source = _read_module_source()
    assert "from ....crud.asset import asset_crud" not in module_source
    assert "asset_crud." not in module_source


def test_occupancy_module_should_import_authz_dependency() -> None:
    """occupancy 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_occupancy_endpoints_should_use_require_authz() -> None:
    """occupancy 关键读端点应接入 require_authz。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"def calculate_occupancy_rate[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"occupancy\"",
        r"def analyze_occupancy[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"occupancy\"",
        r"def get_occupancy_trends[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"occupancy\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern
