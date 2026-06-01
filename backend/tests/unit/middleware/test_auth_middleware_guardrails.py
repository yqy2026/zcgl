"""Guardrails for splitting src.middleware.auth without semantic drift."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import ModuleType
from uuid import uuid4

import jwt
import pytest

from src.core.config import settings
from src.middleware import auth as auth_module
from src.middleware.auth import get_current_user
from src.security.token_blacklist import blacklist_manager

pytestmark = pytest.mark.asyncio


class _UserStub:
    def __init__(
        self,
        *,
        user_id: str,
        username: str = "tester",
        is_active: bool = True,
        is_locked: bool = False,
    ) -> None:
        self.id = user_id
        self.username = username
        self.is_active = is_active
        self._is_locked = is_locked

    def is_locked_now(self) -> bool:
        return self._is_locked


class _ResultStub:
    def __init__(self, user: _UserStub | None) -> None:
        self._user = user

    def scalars(self) -> _ResultStub:
        return self

    def first(self) -> _UserStub | None:
        return self._user


class _DBStub:
    def __init__(self, user: _UserStub | None = None) -> None:
        self.user = user
        self.execute_calls = 0

    async def execute(self, *_args, **_kwargs) -> _ResultStub:
        self.execute_calls += 1
        return _ResultStub(self.user)


def _build_access_token(user_id: str, username: str = "tester") -> tuple[str, str, int]:
    now = datetime.now(UTC)
    exp = now + timedelta(hours=1)
    jti = f"auth-split-{uuid4().hex}"
    payload = {
        "sub": user_id,
        "username": username,
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": jti,
        "aud": settings.JWT_AUDIENCE,
        "iss": settings.JWT_ISSUER,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti, payload["exp"]


@pytest.fixture(autouse=True)
def clear_blacklist() -> None:
    blacklist_manager.clear_blacklist()
    yield
    blacklist_manager.clear_blacklist()


def test_auth_middleware_public_entrypoints_remain_stable() -> None:
    """Split modules must not silently break route imports from middleware.auth."""
    assert isinstance(auth_module, ModuleType)

    for name in (
        "get_current_user",
        "get_current_user_from_cookie",
        "get_current_active_user",
        "get_optional_current_user",
        "require_authz",
        "AuthzContext",
        "require_data_scope_context",
        "DataScopeContext",
        "audit_action",
        "SecurityConfig",
    ):
        assert hasattr(auth_module, name), name

    assert callable(auth_module.require_authz(action="read", resource_type="asset"))
    assert callable(auth_module.require_data_scope_context())


def test_auth_middleware_legacy_checkers_are_not_public_entrypoints() -> None:
    """Legacy RBAC helpers must not return to the auth facade."""
    for name in (
        "PermissionChecker",
        "require_permissions",
        "OrganizationPermissionChecker",
        "require_organization_access",
        "RBACPermissionChecker",
        "require_permission",
        "ResourcePermissionChecker",
        "require_resource_permission",
        "RoleBasedAccessChecker",
        "require_roles",
        "can_edit_contract",
        "get_user_rbac_permissions",
    ):
        assert not hasattr(auth_module, name), name


async def test_get_current_user_rejects_missing_cookie_without_db_lookup() -> None:
    db = _DBStub()

    with pytest.raises(Exception) as exc_info:
        await get_current_user(auth_token=None, db=db)

    assert getattr(exc_info.value, "status_code", None) == 401
    assert db.execute_calls == 0


async def test_get_current_user_accepts_valid_cookie_token() -> None:
    user = _UserStub(user_id="user-cookie")
    db = _DBStub(user)
    token, _jti, _exp = _build_access_token("user-cookie")

    result = await get_current_user(auth_token=token, db=db)

    assert result is user
    assert db.execute_calls == 1


async def test_get_current_user_rejects_blacklisted_token_before_db_lookup() -> None:
    db = _DBStub(_UserStub(user_id="user-blacklisted"))
    token, jti, exp = _build_access_token("user-blacklisted")
    blacklist_manager.add_token(jti, exp)

    with pytest.raises(Exception) as exc_info:
        await get_current_user(auth_token=token, db=db)

    assert getattr(exc_info.value, "status_code", None) == 401
    assert db.execute_calls == 0


async def test_get_current_user_rejects_disabled_user() -> None:
    user = _UserStub(user_id="user-disabled", is_active=False)
    db = _DBStub(user)
    token, _jti, _exp = _build_access_token("user-disabled")

    with pytest.raises(Exception) as exc_info:
        await get_current_user(auth_token=token, db=db)

    assert getattr(exc_info.value, "status_code", None) == 401
    assert db.execute_calls == 1


async def test_get_current_user_rejects_locked_user() -> None:
    user = _UserStub(user_id="user-locked", is_locked=True)
    db = _DBStub(user)
    token, _jti, _exp = _build_access_token("user-locked")

    with pytest.raises(Exception) as exc_info:
        await get_current_user(auth_token=token, db=db)

    assert getattr(exc_info.value, "status_code", None) == 401
    assert db.execute_calls == 1
