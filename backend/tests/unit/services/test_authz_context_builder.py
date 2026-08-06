from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.authz.context_builder import AuthzContextBuilder
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = pytest.mark.asyncio


class _ResolverStub:
    def __init__(self, scope: EffectivePartyScope) -> None:
        self.resolve = AsyncMock(return_value=scope)


class TestAuthzContextBuilder:
    async def test_should_build_context_from_unified_resolver(self) -> None:
        resolver = _ResolverStub(
            EffectivePartyScope(
                user_id="user-1",
                source="explicit",
                scope_mode="all",
                owner_party_ids=["owner-1"],
                manager_party_ids=["manager-1"],
            )
        )
        builder = AuthzContextBuilder(resolver=resolver)  # type: ignore[arg-type]

        context = await builder.build_subject_context(
            MagicMock(),
            user_id="user-1",
            role_ids=["role-2", "role-1"],
        )

        assert context.user_id == "user-1"
        assert context.owner_party_ids == ["owner-1"]
        assert context.manager_party_ids == ["manager-1"]
        assert context.role_ids == ["role-1", "role-2"]

    async def test_should_consume_organization_fallback_from_resolver(self) -> None:
        resolver = _ResolverStub(
            EffectivePartyScope(
                user_id="user-1",
                source="organization",
                scope_mode="owner",
                owner_party_ids=["owner-from-org"],
                organization_id="org-1",
            )
        )
        builder = AuthzContextBuilder(resolver=resolver)  # type: ignore[arg-type]

        context = await builder.build_subject_context(
            MagicMock(),
            user_id="user-1",
            role_ids=[],
        )

        assert context.owner_party_ids == ["owner-from-org"]
        assert context.manager_party_ids == []
