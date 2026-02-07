"""Unit tests for unified permission grant APIs in roles router."""

import asyncio
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from src.core.exception_handler import PermissionDeniedError
from src.schemas.rbac import PermissionGrantCreate, PermissionGrantUpdate

pytestmark = pytest.mark.api


def _make_grant(
    grant_id: str = "grant-1",
    *,
    user_id: str = "user-1",
    permission_id: str = "perm-1",
    effect: str = "allow",
):
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=grant_id,
        user_id=user_id,
        permission_id=permission_id,
        grant_type="direct",
        effect=effect,
        scope="global",
        scope_id=None,
        conditions=None,
        starts_at=None,
        expires_at=None,
        priority=100,
        is_active=True,
        source_type=None,
        source_id=None,
        granted_by="admin-1",
        reason="test",
        created_at=now,
        updated_at=now,
        revoked_at=None,
        revoked_by=None,
    )


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def admin_user():
    return SimpleNamespace(id="admin-1")


def _parse_json_response(response):
    return json.loads(response.body)


@patch("src.api.v1.auth.roles.RBACService")
def test_create_permission_grant_success(mock_service_cls, mock_db, admin_user):
    from src.api.v1.auth import roles as roles_module

    grant = _make_grant()
    mock_service = MagicMock()
    mock_service.grant_permission_to_user = AsyncMock(return_value=grant)
    mock_service_cls.return_value = mock_service

    payload = PermissionGrantCreate(
        user_id="user-1",
        permission_id="perm-1",
        grant_type="direct",
        effect="allow",
    )
    result = asyncio.run(
        roles_module.create_permission_grant(
            grant_data=payload, db=mock_db, current_user=admin_user
        )
    )

    assert result.id == "grant-1"
    assert result.effect == "allow"
    mock_service.grant_permission_to_user.assert_awaited_once()


@patch("src.api.v1.auth.roles.RBACService")
def test_get_permission_grants_success(mock_service_cls, mock_db, admin_user):
    from src.api.v1.auth import roles as roles_module

    grant = _make_grant()
    mock_service = MagicMock()
    mock_service.list_permission_grants = AsyncMock(return_value=([grant], 1))
    mock_service_cls.return_value = mock_service

    response = asyncio.run(
        roles_module.get_permission_grants(
            page=1,
            page_size=20,
            user_id=None,
            permission_id=None,
            grant_type=None,
            effect=None,
            scope=None,
            is_active=None,
            db=mock_db,
            current_user=admin_user,
        )
    )

    assert response.status_code == status.HTTP_200_OK
    payload = _parse_json_response(response)
    assert payload["data"]["pagination"]["total"] == 1
    assert payload["data"]["items"][0]["id"] == "grant-1"


@patch("src.api.v1.auth.roles.RBACService")
def test_update_permission_grant_success(mock_service_cls, mock_db, admin_user):
    from src.api.v1.auth import roles as roles_module

    updated_grant = _make_grant(effect="deny")
    mock_service = MagicMock()
    mock_service.update_permission_grant = AsyncMock(return_value=updated_grant)
    mock_service_cls.return_value = mock_service

    payload = PermissionGrantUpdate(effect="deny", priority=200)
    result = asyncio.run(
        roles_module.update_permission_grant(
            grant_id="grant-1",
            grant_data=payload,
            db=mock_db,
            current_user=admin_user,
        )
    )

    assert result.id == "grant-1"
    assert result.effect == "deny"
    assert result.priority == 100


@patch("src.api.v1.auth.roles.RBACService")
def test_revoke_permission_grant_success(mock_service_cls, mock_db, admin_user):
    from src.api.v1.auth import roles as roles_module

    mock_service = MagicMock()
    mock_service.revoke_permission_grant = AsyncMock(return_value=True)
    mock_service_cls.return_value = mock_service

    result = asyncio.run(
        roles_module.revoke_permission_grant(
            grant_id="grant-1",
            db=mock_db,
            current_user=admin_user,
        )
    )

    assert result["success"] is True
    assert result["grant_id"] == "grant-1"


@patch("src.api.v1.auth.roles.RBACService")
def test_get_user_permissions_summary_forbidden_for_other_user(
    mock_service_cls, mock_db
):
    from src.api.v1.auth import roles as roles_module

    normal_user = SimpleNamespace(id="user-self")
    mock_service = MagicMock()
    mock_service.check_user_permission = AsyncMock(return_value=False)
    mock_service_cls.return_value = mock_service

    with pytest.raises(PermissionDeniedError):
        asyncio.run(
            roles_module.get_user_permissions_summary(
                user_id="another-user",
                db=mock_db,
                current_user=normal_user,
            )
        )
