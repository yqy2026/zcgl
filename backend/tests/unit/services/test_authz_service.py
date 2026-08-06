from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.abac import ABACEffect, ABACPolicy, ABACPolicyRule
from src.services.authz.cache import CacheLookupResult
from src.services.authz.context_builder import SubjectContext
from src.services.authz.engine import AuthzDecision
from src.services.authz.service import AuthzService

pytestmark = pytest.mark.asyncio


def test_decision_cache_ttl_is_capped_by_next_transition() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    subject = SubjectContext(
        user_id="user-1",
        owner_party_ids=["owner-1"],
        manager_party_ids=[],
        role_ids=[],
        next_transition_at=now + timedelta(seconds=30),
    )

    capped_ttl = AuthzService._decision_cache_ttl_seconds(
        subject,
        default_ttl=300,
    )
    assert 29 <= capped_ttl <= 30

    expired_subject = SubjectContext(
        user_id="user-1",
        owner_party_ids=["owner-1"],
        manager_party_ids=[],
        role_ids=[],
        next_transition_at=now - timedelta(seconds=1),
    )
    assert AuthzService._decision_cache_ttl_seconds(
        expired_subject,
        default_ttl=300,
    ) == 0


async def test_get_capabilities_should_use_resource_perspective_registry() -> None:
    db = MagicMock()
    context_builder = MagicMock()
    context_builder.build_subject_context = AsyncMock(
        return_value=SubjectContext(
            user_id="user-1",
            owner_party_ids=["owner-party-1"],
            manager_party_ids=["manager-party-1"],
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

    with patch.object(
        service,
        "_get_user_role_summary",
        new=AsyncMock(return_value={"role_ids": ["role-1"], "is_admin": False}),
    ):
        result = await service.get_capabilities(db, user_id="user-1")

    project_capability = next(
        item for item in result.capabilities if item.resource == "project"
    )
    user_capability = next(
        item for item in result.capabilities if item.resource == "user"
    )

    assert project_capability.perspectives == ["owner", "manager"]
    assert user_capability.perspectives == []


async def test_get_capabilities_should_include_rbac_permission_when_abac_policy_missing() -> (
    None
):
    db = MagicMock()
    context_builder = MagicMock()
    context_builder.build_subject_context = AsyncMock(
        return_value=SubjectContext(
            user_id="user-1",
            owner_party_ids=[],
            manager_party_ids=["manager-party-1"],
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


async def test_get_capabilities_should_include_authenticated_notification_read_without_roles() -> (
    None
):
    db = MagicMock()
    context_builder = MagicMock()
    context_builder.build_subject_context = AsyncMock(
        return_value=SubjectContext(
            user_id="user-1",
            owner_party_ids=[],
            manager_party_ids=[],
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


async def test_check_access_should_allow_authenticated_notification_read_without_policy() -> (
    None
):
    db = MagicMock()
    context_builder = MagicMock()
    context_builder.build_subject_context = AsyncMock(
        return_value=SubjectContext(
            user_id="user-1",
            owner_party_ids=[],
            manager_party_ids=[],
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


async def test_check_access_should_not_override_policy_deny_with_authenticated_default() -> None:
    db = MagicMock()
    context_builder = MagicMock()
    context_builder.build_subject_context = AsyncMock(
        return_value=SubjectContext(
            user_id="user-1",
            owner_party_ids=[],
            manager_party_ids=[],
            role_ids=["role-1"],
        )
    )
    deny_policy = ABACPolicy(name="deny-notification-read", effect=ABACEffect.DENY, priority=1)
    deny_policy.rules = [
        ABACPolicyRule(
            policy_id="policy-1",
            resource_type="notification",
            action="read",
            condition_expr={"==": [{"var": "action"}, "read"]},
        )
    ]
    authz_crud = MagicMock()
    authz_crud.get_policies_by_role_ids = AsyncMock(return_value=[deny_policy])

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
            new=AsyncMock(return_value=False),
        ),
        patch.object(
            service,
            "_has_matching_policy_rule",
            return_value=True,
        ),
        patch.object(
            service.engine,
            "evaluate_with_reason",
            return_value=AuthzDecision(allowed=False, reason_code="policy_deny"),
        ),
        patch.object(
            service.decision_cache,
            "lookup",
            return_value=CacheLookupResult(value=None, cache_hit=False, layer=None),
        ),
        patch.object(service.decision_cache, "set"),
    ):
        result = await service.check_access(
            db,
            user_id="user-1",
            resource_type="notification",
            action="read",
        )

    assert result.allowed is False
    assert result.reason_code == "policy_deny"


async def test_check_access_should_allow_in_log_only_mode_when_policy_denies() -> None:
    db = MagicMock()
    context_builder = MagicMock()
    context_builder.build_subject_context = AsyncMock(
        return_value=SubjectContext(
            user_id="user-1",
            owner_party_ids=["owner-1"],
            manager_party_ids=[],
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
            service.engine,
            "evaluate_with_reason",
            return_value=AuthzDecision(allowed=False, reason_code="policy_deny"),
        ),
        patch.object(
            service,
            "_has_matching_policy_rule",
            return_value=True,
        ),
        patch.object(
            service.decision_cache,
            "lookup",
            return_value=CacheLookupResult(value=None, cache_hit=False, layer=None),
        ),
        patch.object(service.decision_cache, "set"),
        patch.dict("os.environ", {"AUTHZ_LOG_ONLY_MODE": "1"}, clear=False),
    ):
        result = await service.check_access(
            db,
            user_id="user-1",
            resource_type="asset",
            action="read",
        )

    assert result.allowed is True
    assert result.reason_code == "authz_log_only_allow"
