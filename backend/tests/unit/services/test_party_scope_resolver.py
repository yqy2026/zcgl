"""Decision-matrix tests for the single effective Party scope resolver."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.party_scope_resolver import PartyScopeResolver

NOW = datetime(2026, 8, 4, 9, 0, 0)


def _repository() -> MagicMock:
    repository = MagicMock()
    repository.load_role_names = AsyncMock(return_value=[])
    repository.load_user = AsyncMock(
        return_value={
            "id": "user-1",
            "account_type": "human",
            "organization_id": "org-child",
        }
    )
    repository.load_bindings = AsyncMock(return_value=[])
    repository.load_organization = AsyncMock()
    return repository


@pytest.mark.asyncio
async def test_builtin_admin_is_unrestricted_but_perm_admin_is_not() -> None:
    admin_repository = _repository()
    admin_repository.load_role_names.return_value = ["admin"]
    admin_scope = await PartyScopeResolver(
        repository=admin_repository,
        clock=lambda: NOW,
    ).resolve(MagicMock(), user_id="user-1")

    perm_repository = _repository()
    perm_repository.load_role_names.return_value = ["perm_admin"]
    perm_repository.load_organization.side_effect = [
        {
            "id": "org-child",
            "parent_id": None,
            "status": "active",
            "is_deleted": False,
            "represented_party_id": "party-owner",
            "represented_party_perspective": "owner",
            "party_type": "legal_entity",
            "party_status": "active",
            "party_review_status": "approved",
        }
    ]
    perm_scope = await PartyScopeResolver(
        repository=perm_repository,
        clock=lambda: NOW,
    ).resolve(MagicMock(), user_id="user-1")

    assert admin_scope.source == "unrestricted"
    assert admin_scope.scope_mode == "unrestricted"
    assert perm_scope.source == "organization"
    assert perm_scope.owner_party_ids == ["party-owner"]


@pytest.mark.asyncio
async def test_current_explicit_bindings_override_organization_and_keep_both_views() -> (
    None
):
    repository = _repository()
    repository.load_bindings.return_value = [
        {
            "id": "binding-owner",
            "party_id": "party-owner",
            "relation_type": "owner",
            "valid_from": NOW - timedelta(days=1),
            "valid_to": None,
            "party_status": "active",
            "party_review_status": "approved",
        },
        {
            "id": "binding-manager",
            "party_id": "party-manager",
            "relation_type": "manager",
            "valid_from": NOW - timedelta(days=1),
            "valid_to": NOW + timedelta(days=3),
            "party_status": "active",
            "party_review_status": "approved",
        },
    ]

    scope = await PartyScopeResolver(
        repository=repository,
        clock=lambda: NOW,
    ).resolve(MagicMock(), user_id="user-1")

    assert scope.source == "explicit"
    assert scope.scope_mode == "all"
    assert scope.owner_party_ids == ["party-owner"]
    assert scope.manager_party_ids == ["party-manager"]
    assert scope.next_transition_at == NOW + timedelta(days=3)
    repository.load_organization.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_current_binding_inherits_nearest_active_ancestor() -> None:
    repository = _repository()
    repository.load_bindings.return_value = [
        {
            "id": "expired",
            "party_id": "old-party",
            "relation_type": "owner",
            "valid_from": NOW - timedelta(days=10),
            "valid_to": NOW - timedelta(days=1),
            "party_status": "active",
            "party_review_status": "approved",
        }
    ]
    repository.load_organization.side_effect = [
        {
            "id": "org-child",
            "parent_id": "org-parent",
            "status": "active",
            "is_deleted": False,
            "represented_party_id": None,
            "represented_party_perspective": None,
            "party_type": None,
            "party_status": None,
            "party_review_status": None,
        },
        {
            "id": "org-parent",
            "parent_id": None,
            "status": "active",
            "is_deleted": False,
            "represented_party_id": "party-manager",
            "represented_party_perspective": "manager",
            "party_type": "legal_entity",
            "party_status": "active",
            "party_review_status": "approved",
        },
    ]

    scope = await PartyScopeResolver(
        repository=repository,
        clock=lambda: NOW,
    ).resolve(MagicMock(), user_id="user-1")

    assert scope.source == "organization"
    assert scope.source_organization_id == "org-parent"
    assert scope.manager_party_ids == ["party-manager"]


@pytest.mark.asyncio
async def test_invalid_direct_relationship_blocks_ancestor_fallback() -> None:
    repository = _repository()
    repository.load_organization.return_value = {
        "id": "org-child",
        "parent_id": "org-parent",
        "status": "active",
        "is_deleted": False,
        "represented_party_id": "party-draft",
        "represented_party_perspective": "owner",
        "party_type": "legal_entity",
        "party_status": "active",
        "party_review_status": "draft",
    }

    scope = await PartyScopeResolver(
        repository=repository,
        clock=lambda: NOW,
    ).resolve(MagicMock(), user_id="user-1")

    assert scope.error_code == "PARTY_SCOPE_INVALID_PARTY"
    assert scope.owner_party_ids == []
    repository.load_organization.assert_awaited_once()


@pytest.mark.asyncio
async def test_service_account_never_inherits_organization_scope() -> None:
    repository = _repository()
    repository.load_user.return_value = {
        "id": "service-1",
        "account_type": "service",
        "organization_id": None,
    }

    scope = await PartyScopeResolver(
        repository=repository,
        clock=lambda: NOW,
    ).resolve(MagicMock(), user_id="service-1")

    assert scope.error_code == "PARTY_SCOPE_MISSING"
    repository.load_bindings.assert_not_awaited()
    repository.load_organization.assert_not_awaited()
