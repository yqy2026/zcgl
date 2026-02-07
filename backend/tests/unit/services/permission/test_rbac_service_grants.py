"""Tests for unified permission grant checks in RBACService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.core.exception_handler import InvalidRequestError
from src.schemas.rbac import PermissionCheckRequest, PermissionGrantUpdate
from src.services.permission.rbac_service import RBACService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def rbac_service(mock_db):
    return RBACService(mock_db)


@pytest.fixture
def sample_user():
    user = Mock()
    user.id = "user-1"
    user.username = "test-user"
    user.is_active = True
    return user


def _make_grant(
    grant_id: str,
    *,
    effect: str = "allow",
    scope: str = "global",
    scope_id: str | None = None,
    conditions: dict | None = None,
    priority: int = 100,
):
    grant = Mock()
    grant.id = grant_id
    grant.effect = effect
    grant.scope = scope
    grant.scope_id = scope_id
    grant.conditions = conditions
    grant.priority = priority
    grant.created_at = datetime.now(UTC)
    return grant


async def test_check_permission_allows_by_permission_grant(
    rbac_service, sample_user
):
    request = PermissionCheckRequest(resource="asset", action="create")

    with patch.object(
        rbac_service.user_crud, "get_async", new=AsyncMock(return_value=sample_user)
    ):
        with patch.object(
            rbac_service, "get_user_roles", new=AsyncMock(return_value=[])
        ):
            with patch.object(
                rbac_service,
                "_user_has_admin_permission",
                new=AsyncMock(return_value=False),
            ):
                with patch.object(
                    rbac_service,
                    "_get_matching_permission_grants",
                    new=AsyncMock(return_value=[_make_grant("g-allow")]),
                ):
                    result = await rbac_service.check_permission("user-1", request)

    assert result.has_permission is True
    assert "grant_g-allow" in result.granted_by


async def test_check_permission_deny_grant_takes_precedence(
    rbac_service, sample_user
):
    request = PermissionCheckRequest(resource="asset", action="delete")
    allow_grant = _make_grant("g-allow", effect="allow", priority=200)
    deny_grant = _make_grant("g-deny", effect="deny", priority=100)

    with patch.object(
        rbac_service.user_crud, "get_async", new=AsyncMock(return_value=sample_user)
    ):
        with patch.object(
            rbac_service, "get_user_roles", new=AsyncMock(return_value=[])
        ):
            with patch.object(
                rbac_service,
                "_user_has_admin_permission",
                new=AsyncMock(return_value=False),
            ):
                with patch.object(
                    rbac_service,
                    "_get_matching_permission_grants",
                    new=AsyncMock(return_value=[allow_grant, deny_grant]),
                ):
                    result = await rbac_service.check_permission("user-1", request)

    assert result.has_permission is False
    assert result.reason == "命中拒绝授权"


async def test_check_permission_grant_scope_and_condition_must_match(
    rbac_service, sample_user
):
    request = PermissionCheckRequest(
        resource="asset",
        action="update",
        resource_id="asset-1",
        context={"organization_id": "org-1", "department": "finance"},
    )
    matching_grant = _make_grant(
        "g-match",
        scope="organization",
        scope_id="org-1",
        conditions={"department": "finance"},
    )
    mismatch_grant = _make_grant(
        "g-mismatch",
        scope="organization",
        scope_id="org-2",
        conditions={"department": "finance"},
    )

    with patch.object(
        rbac_service.user_crud, "get_async", new=AsyncMock(return_value=sample_user)
    ):
        with patch.object(
            rbac_service, "get_user_roles", new=AsyncMock(return_value=[])
        ):
            with patch.object(
                rbac_service,
                "_user_has_admin_permission",
                new=AsyncMock(return_value=False),
            ):
                with patch.object(
                    rbac_service,
                    "_get_matching_permission_grants",
                    new=AsyncMock(return_value=[mismatch_grant, matching_grant]),
                ):
                    result = await rbac_service.check_permission("user-1", request)

    assert result.has_permission is True
    assert result.granted_by == ["grant_g-match"]


async def test_grant_permission_to_user_rejects_invalid_effect(
    rbac_service, sample_user
):
    with patch.object(
        rbac_service.user_crud, "get_async", new=AsyncMock(return_value=sample_user)
    ):
        with patch(
            "src.services.permission.rbac_service.permission_crud.get",
            new=AsyncMock(return_value=Mock(id="perm-1")),
        ):
            with pytest.raises(InvalidRequestError):
                await rbac_service.grant_permission_to_user(
                    user_id="user-1",
                    permission_id="perm-1",
                    grant_type="direct",
                    granted_by="admin-1",
                    effect="invalid-effect",
                )


async def test_update_permission_grant_sets_revoke_fields_when_deactivating(
    rbac_service,
):
    existing_grant = _make_grant("g-1", effect="allow")
    existing_grant.starts_at = None
    existing_grant.expires_at = None
    existing_grant.scope = "global"
    existing_grant.scope_id = None
    existing_grant.priority = 100
    existing_grant.is_active = True
    existing_grant.reason = "old reason"

    updated_grant = _make_grant("g-1", effect="allow")
    updated_grant.is_active = False
    updated_grant.revoked_by = "admin-1"

    with patch(
        "src.services.permission.rbac_service.permission_grant_crud.get",
        new=AsyncMock(return_value=existing_grant),
    ):
        with patch(
            "src.services.permission.rbac_service.permission_grant_crud.update",
            new=AsyncMock(return_value=updated_grant),
        ) as update_mock:
            with patch.object(
                rbac_service, "_create_permission_audit_log", new=AsyncMock()
            ):
                result = await rbac_service.update_permission_grant(
                    grant_id="g-1",
                    grant_data=PermissionGrantUpdate(is_active=False),
                    updated_by="admin-1",
                )

    assert result.is_active is False
    update_payload = update_mock.await_args.kwargs["obj_in"]
    assert update_payload["is_active"] is False
    assert update_payload["revoked_by"] == "admin-1"
    assert "revoked_at" in update_payload


async def test_list_permission_grants_returns_items_and_total(rbac_service):
    grant = _make_grant("g-1")
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [grant]

    count_result = MagicMock()
    count_result.scalar.return_value = 1

    rbac_service.db.execute = AsyncMock(side_effect=[list_result, count_result])

    grants, total = await rbac_service.list_permission_grants(
        skip=0, limit=20, user_id="user-1"
    )

    assert total == 1
    assert len(grants) == 1
    assert grants[0].id == "g-1"
