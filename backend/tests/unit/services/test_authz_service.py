from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.authz.context_builder import SubjectContext
from src.services.authz.service import AuthzService

pytestmark = pytest.mark.asyncio


async def test_get_capabilities_should_use_resource_perspective_registry() -> None:
    db = MagicMock()
    context_builder = MagicMock()
    context_builder.build_subject_context = AsyncMock(
        return_value=SubjectContext(
            user_id="user-1",
            owner_party_ids=["owner-party-1"],
            manager_party_ids=["manager-party-1"],
            headquarters_party_ids=[],
            role_ids=["role-1"],
        )
    )
    authz_crud = MagicMock()
    authz_crud.get_policies_by_role_ids = AsyncMock(
        return_value=[
            SimpleNamespace(
                enabled=True,
                effect="allow",
                rules=[
                    SimpleNamespace(resource_type="asset", action="read"),
                    SimpleNamespace(resource_type="project", action="read"),
                    SimpleNamespace(resource_type="user", action="read"),
                ],
            )
        ]
    )

    service = AuthzService(
        context_builder=context_builder,
        authz_crud=authz_crud,
    )

    with patch.object(service, "_get_user_role_ids", new=AsyncMock(return_value=["role-1"])):
        result = await service.get_capabilities(db, user_id="user-1")

    project_capability = next(
        item for item in result.capabilities if item.resource == "project"
    )
    user_capability = next(item for item in result.capabilities if item.resource == "user")

    assert project_capability.perspectives == ["manager"]
    assert user_capability.perspectives == []


async def test_get_capabilities_should_include_rbac_permission_when_abac_policy_missing() -> None:
    db = MagicMock()
    context_builder = MagicMock()
    context_builder.build_subject_context = AsyncMock(
        return_value=SubjectContext(
            user_id="user-1",
            owner_party_ids=[],
            manager_party_ids=["manager-party-1"],
            headquarters_party_ids=[],
            role_ids=["role-1"],
        )
    )
    authz_crud = MagicMock()
    authz_crud.get_policies_by_role_ids = AsyncMock(return_value=[])

    service = AuthzService(
        context_builder=context_builder,
        authz_crud=authz_crud,
    )

    with (
        patch.object(service, "_get_user_role_ids", new=AsyncMock(return_value=["role-1"])),
        patch.object(
            service,
            "_get_static_rbac_actions",
            new=AsyncMock(return_value={"project": {"read"}}),
        ),
    ):
        result = await service.get_capabilities(db, user_id="user-1")

    project_capability = next(
        item for item in result.capabilities if item.resource == "project"
    )
    assert project_capability.actions == ["read"]
    assert project_capability.perspectives == ["manager"]


async def test_check_access_should_fallback_to_rbac_when_abac_rule_missing() -> None:
    db = MagicMock()
    context_builder = MagicMock()
    context_builder.build_subject_context = AsyncMock(
        return_value=SubjectContext(
            user_id="user-1",
            owner_party_ids=[],
            manager_party_ids=["manager-party-1"],
            headquarters_party_ids=[],
            role_ids=["role-1"],
        )
    )
    authz_crud = MagicMock()
    authz_crud.get_policies_by_role_ids = AsyncMock(return_value=[])

    service = AuthzService(
        context_builder=context_builder,
        authz_crud=authz_crud,
    )

    with (
        patch.object(
            service,
            "_get_user_role_summary",
            new=AsyncMock(return_value={"role_ids": ["role-1"], "is_admin": False}),
        ),
        patch.object(
            service,
            "_has_static_rbac_permission",
            new=AsyncMock(return_value=True),
        ),
    ):
        result = await service.check_access(
            db,
            user_id="user-1",
            resource_type="project",
            action="read",
        )

    assert result.allowed is True
    assert result.reason_code == "rbac_permission_fallback"


async def test_get_capabilities_should_include_authenticated_notification_read_without_roles() -> None:
    db = MagicMock()
    context_builder = MagicMock()
    context_builder.build_subject_context = AsyncMock(
        return_value=SubjectContext(
            user_id="user-1",
            owner_party_ids=[],
            manager_party_ids=[],
            headquarters_party_ids=[],
            role_ids=[],
        )
    )
    authz_crud = MagicMock()
    authz_crud.get_policies_by_role_ids = AsyncMock(return_value=[])

    service = AuthzService(
        context_builder=context_builder,
        authz_crud=authz_crud,
    )

    with (
        patch.object(service, "_get_user_role_ids", new=AsyncMock(return_value=[])),
        patch.object(
            service,
            "_get_static_rbac_actions",
            new=AsyncMock(return_value={}),
        ),
    ):
        result = await service.get_capabilities(db, user_id="user-1")

    notification_capability = next(
        item for item in result.capabilities if item.resource == "notification"
    )
    assert notification_capability.actions == ["read"]
    assert notification_capability.perspectives == []


async def test_check_access_should_allow_authenticated_notification_read_without_policy() -> None:
    db = MagicMock()
    context_builder = MagicMock()
    context_builder.build_subject_context = AsyncMock(
        return_value=SubjectContext(
            user_id="user-1",
            owner_party_ids=[],
            manager_party_ids=[],
            headquarters_party_ids=[],
            role_ids=[],
        )
    )
    authz_crud = MagicMock()
    authz_crud.get_policies_by_role_ids = AsyncMock(return_value=[])

    service = AuthzService(
        context_builder=context_builder,
        authz_crud=authz_crud,
    )

    with (
        patch.object(
            service,
            "_get_user_role_summary",
            new=AsyncMock(return_value={"role_ids": [], "is_admin": False}),
        ),
        patch.object(
            service,
            "_has_static_rbac_permission",
            new=AsyncMock(return_value=False),
        ),
    ):
        result = await service.check_access(
            db,
            user_id="user-1",
            resource_type="notification",
            action="read",
        )

    assert result.allowed is True
    assert result.reason_code == "authenticated_default_permission"
