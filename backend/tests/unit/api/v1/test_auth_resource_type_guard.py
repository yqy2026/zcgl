"""Guard: auth routes must not regress to asset-scoped ABAC resources."""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


AUTH_API_ROOT = Path(__file__).resolve().parents[4] / "src" / "api" / "v1" / "auth"


def _iter_auth_route_files() -> list[Path]:
    return sorted(path for path in AUTH_API_ROOT.rglob("*.py") if path.name != "__init__.py")


def test_auth_routes_should_not_use_asset_resource_type_for_require_authz() -> None:
    """
    Auth domain routes must not use asset-scoped ABAC resources.

    This prevents copy-paste regressions where non-asset endpoints are gated by
    `resource_type="asset"` and accidentally depend on unrelated permissions.
    """

    pattern = re.compile(
        r"require_authz\([\s\S]*?resource_type\s*=\s*\"asset\"[\s\S]*?\)"
    )
    violations: list[str] = []

    for file_path in _iter_auth_route_files():
        content = file_path.read_text(encoding="utf-8")
        if pattern.search(content):
            violations.append(str(file_path.relative_to(AUTH_API_ROOT.parent.parent.parent)))

    assert violations == [], (
        "auth route modules must not use require_authz(...resource_type='asset'). "
        f"violations: {violations}"
    )
