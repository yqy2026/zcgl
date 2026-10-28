from pathlib import Path

import pytest

from scripts.maintenance.api_consistency_check import APIConsistencyChecker, APIEndpoint

pytestmark = pytest.mark.unit


def write_routes(root: Path, relative: str, source: str) -> None:
    target = root / "src/api/v1" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")


def test_nested_router_aliases_and_prefixes_are_composed(tmp_path):
    write_routes(
        tmp_path,
        "__init__.py",
        """
from fastapi import APIRouter
from .auth.auth import router as auth_router
api_router = APIRouter()
api_router.include_router(auth_router, prefix='/auth')
""",
    )
    write_routes(
        tmp_path,
        "auth/auth.py",
        """
from .modules import router as modules_router
router = modules_router
""",
    )
    write_routes(
        tmp_path,
        "auth/modules/__init__.py",
        """
from fastapi import APIRouter
from . import credentials
router = APIRouter()
router.include_router(credentials.router, prefix='/credentials')
""",
    )
    write_routes(
        tmp_path,
        "auth/modules/credentials.py",
        """
from fastapi import APIRouter
router = APIRouter(prefix='/password')
@router.post('/expired')
async def change(): pass
""",
    )
    endpoints = APIConsistencyChecker(
        str(tmp_path), str(tmp_path)
    ).extract_backend_endpoints()
    assert "POST:/auth/credentials/password/expired" in endpoints
    assert "POST:/expired" not in endpoints


def test_only_registered_routes_count_and_missing_endpoints_still_fail(tmp_path):
    write_routes(
        tmp_path,
        "__init__.py",
        """
from fastapi import APIRouter
from . import registered
api_router = APIRouter()
""",
    )
    for name in ("registered", "unmounted"):
        write_routes(
            tmp_path,
            f"{name}.py",
            f"""
from fastapi import APIRouter
router = APIRouter(prefix='/{name}')
@router.get('/items')
async def items(): pass
route_registry.register_router(router, prefix='/api/v1')
""",
        )
    checker = APIConsistencyChecker(str(tmp_path), str(tmp_path))
    endpoints = checker.extract_backend_endpoints()
    assert "GET:/registered/items" in endpoints
    assert "GET:/unmounted/items" not in endpoints
    checker.check_path_consistency(
        endpoints,
        {
            "GET:/unmounted/items": APIEndpoint("/unmounted/items", "GET"),
        },
    )
    assert any(issue.severity == "critical" for issue in checker.issues)


def test_repository_expired_password_route_is_found():
    backend = Path(__file__).resolve().parents[3]
    checker = APIConsistencyChecker(str(backend), str(backend.parent / "frontend"))
    assert "POST:/auth/expired-password" in checker.extract_backend_endpoints()


def test_unresolved_mounted_router_fails_loud(tmp_path):
    write_routes(
        tmp_path,
        "__init__.py",
        """
from fastapi import APIRouter
api_router = APIRouter()
api_router.include_router(missing_router)
""",
    )
    with pytest.raises(ValueError, match="missing_router"):
        APIConsistencyChecker(str(tmp_path), str(tmp_path)).extract_backend_endpoints()


def test_syntax_error_is_critical_instead_of_hiding_routes(tmp_path):
    write_routes(
        tmp_path,
        "__init__.py",
        "from fastapi import APIRouter\napi_router = APIRouter()",
    )
    write_routes(tmp_path, "broken.py", "def broken(")
    checker = APIConsistencyChecker(str(tmp_path), str(tmp_path))
    checker.extract_backend_endpoints()
    assert any(
        issue.issue_type == "extraction_error" and issue.severity == "critical"
        for issue in checker.issues
    )
