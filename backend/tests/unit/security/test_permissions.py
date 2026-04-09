from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import BaseBusinessError
from src.security.permissions import (
    require_any_role,
    require_asset_edit,
    require_asset_view,
)

pytestmark = pytest.mark.asyncio


async def test_require_any_role_allows_matching_role() -> None:
    checker = require_any_role(["system_admin", "perm_admin"])
    current_user = MagicMock(id="user-1")
    db = MagicMock()
    mock_rbac = MagicMock()
    mock_rbac.get_user_roles = AsyncMock(
        return_value=[
            SimpleNamespace(name="perm_admin"),
            SimpleNamespace(name="viewer"),
        ]
    )

    with patch("src.security.permissions.RBACService", return_value=mock_rbac):
        result = await checker(current_user=current_user, db=db)

    assert result is current_user


async def test_require_any_role_rejects_when_no_roles_match() -> None:
    checker = require_any_role(["system_admin", "perm_admin"])
    current_user = MagicMock(id="user-1")
    db = MagicMock()
    mock_rbac = MagicMock()
    mock_rbac.get_user_roles = AsyncMock(
        return_value=[
            SimpleNamespace(name="viewer"),
            SimpleNamespace(name="executive"),
        ]
    )

    with patch("src.security.permissions.RBACService", return_value=mock_rbac):
        with pytest.raises(BaseBusinessError) as exc_info:
            await checker(current_user=current_user, db=db)

    assert getattr(exc_info.value, "status_code", None) == 403


async def test_require_asset_view_uses_canonical_read_action() -> None:
    checker = require_asset_view()
    current_user = MagicMock(id="user-1")
    db = MagicMock()
    mock_rbac = MagicMock()
    mock_rbac.check_user_permission = AsyncMock(return_value=True)

    with patch("src.security.permissions.RBACService", return_value=mock_rbac):
        result = await checker(current_user=current_user, db=db)

    assert result is current_user
    mock_rbac.check_user_permission.assert_awaited_once_with(
        user_id="user-1",
        resource="asset",
        action="read",
    )


async def test_require_asset_edit_uses_canonical_update_action() -> None:
    checker = require_asset_edit()
    current_user = MagicMock(id="user-1")
    db = MagicMock()
    mock_rbac = MagicMock()
    mock_rbac.check_user_permission = AsyncMock(return_value=True)

    with patch("src.security.permissions.RBACService", return_value=mock_rbac):
        result = await checker(current_user=current_user, db=db)

    assert result is current_user
    mock_rbac.check_user_permission.assert_awaited_once_with(
        user_id="user-1",
        resource="asset",
        action="update",
    )
