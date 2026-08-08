import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import PartyScopeForbiddenError
from src.crud.query_builder import PartyFilter
from src.middleware.auth import DataScopeContext
from src.services.party_scope import (
    build_party_filter_from_scope_context,
    resolve_user_party_filter,
)
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = pytest.mark.asyncio


class TestResolveUserPartyFilter:
    async def test_build_owner_filter_uses_owner_ids_only(self) -> None:
        context = DataScopeContext(
            scope_mode="owner",
            allowed_binding_types=["owner", "manager"],
            owner_party_ids=["owner-1"],
            manager_party_ids=["manager-1"],
            effective_party_ids=["owner-1"],
            source="header",
        )

        assert build_party_filter_from_scope_context(context) == PartyFilter(
            party_ids=["owner-1"],
            filter_mode="owner",
            owner_party_ids=["owner-1"],
            manager_party_ids=[],
        )

    async def test_build_manager_filter_uses_manager_ids_only(self) -> None:
        context = DataScopeContext(
            scope_mode="manager",
            allowed_binding_types=["owner", "manager"],
            owner_party_ids=["owner-1"],
            manager_party_ids=["manager-1"],
            effective_party_ids=["manager-1"],
            source="header",
        )

        assert build_party_filter_from_scope_context(context) == PartyFilter(
            party_ids=["manager-1"],
            filter_mode="manager",
            owner_party_ids=[],
            manager_party_ids=["manager-1"],
        )

    async def test_build_all_filter_keeps_owner_and_manager_separate(self) -> None:
        context = SimpleNamespace(
            scope_mode="all",
            owner_party_ids=["owner-1", "owner-1"],
            manager_party_ids=["manager-1"],
            effective_party_ids=[],
        )

        assert build_party_filter_from_scope_context(context) == PartyFilter(
            party_ids=["manager-1", "owner-1"],
            filter_mode="any",
            owner_party_ids=["owner-1"],
            manager_party_ids=["manager-1"],
        )

    async def test_explicit_filter_wins_without_resolving(self) -> None:
        explicit_filter = PartyFilter(party_ids=["party-1"])

        result = await resolve_user_party_filter(
            MagicMock(),
            current_user_id="user-1",
            party_filter=explicit_filter,
            logger=logging.getLogger(__name__),
        )

        assert result is explicit_filter

    async def test_missing_user_id_keeps_unscoped_internal_caller_behavior(
        self,
    ) -> None:
        result = await resolve_user_party_filter(
            MagicMock(),
            current_user_id=None,
            party_filter=None,
            logger=logging.getLogger(__name__),
        )

        assert result is None

    async def test_unrestricted_scope_bypasses_query_filter(self) -> None:
        scope = EffectivePartyScope(
            user_id="user-1",
            source="unrestricted",
            scope_mode="unrestricted",
        )
        with patch(
            "src.services.party_scope.party_scope_resolver.resolve",
            new=AsyncMock(return_value=scope),
        ):
            result = await resolve_user_party_filter(
                MagicMock(),
                current_user_id="user-1",
                party_filter=None,
                logger=logging.getLogger(__name__),
            )

        assert result is None

    async def test_denied_scope_raises_stable_forbidden(self) -> None:
        scope = EffectivePartyScope(
            user_id="user-1",
            source="none",
            scope_mode="none",
            error_code="PARTY_SCOPE_MISSING",
        )
        with patch(
            "src.services.party_scope.party_scope_resolver.resolve",
            new=AsyncMock(return_value=scope),
        ):
            with pytest.raises(PartyScopeForbiddenError) as exc_info:
                await resolve_user_party_filter(
                    MagicMock(),
                    current_user_id="user-1",
                    party_filter=None,
                    logger=logging.getLogger(__name__),
                )

        assert exc_info.value.status_code == 403
        assert exc_info.value.code == "PARTY_SCOPE_MISSING"

    async def test_denied_scope_can_skip_invalid_recipients(self) -> None:
        scope = EffectivePartyScope(
            user_id="user-1",
            source="none",
            scope_mode="none",
            error_code="PARTY_SCOPE_MISSING",
        )
        with patch(
            "src.services.party_scope.party_scope_resolver.resolve",
            new=AsyncMock(return_value=scope),
        ):
            result = await resolve_user_party_filter(
                MagicMock(),
                current_user_id="user-1",
                party_filter=None,
                logger=logging.getLogger(__name__),
                skip_invalid_scope=True,
            )

        assert result == PartyFilter(party_ids=[])

    async def test_manager_scope_maps_to_manager_filter(self) -> None:
        scope = EffectivePartyScope(
            user_id="user-1",
            source="organization",
            scope_mode="manager",
            manager_party_ids=["party-1"],
        )
        with patch(
            "src.services.party_scope.party_scope_resolver.resolve",
            new=AsyncMock(return_value=scope),
        ):
            result = await resolve_user_party_filter(
                MagicMock(),
                current_user_id="user-1",
                party_filter=None,
                logger=logging.getLogger(__name__),
            )

        assert result == PartyFilter(
            party_ids=["party-1"],
            filter_mode="manager",
            owner_party_ids=[],
            manager_party_ids=["party-1"],
        )

    async def test_all_scope_maps_to_any_filter(self) -> None:
        scope = EffectivePartyScope(
            user_id="user-1",
            source="explicit",
            scope_mode="all",
            owner_party_ids=["owner-party-1"],
            manager_party_ids=["manager-party-1"],
        )
        with patch(
            "src.services.party_scope.party_scope_resolver.resolve",
            new=AsyncMock(return_value=scope),
        ):
            result = await resolve_user_party_filter(
                MagicMock(),
                current_user_id="user-1",
                party_filter=None,
                logger=logging.getLogger(__name__),
            )

        assert result == PartyFilter(
            party_ids=["manager-party-1", "owner-party-1"],
            filter_mode="any",
            owner_party_ids=["owner-party-1"],
            manager_party_ids=["manager-party-1"],
        )
