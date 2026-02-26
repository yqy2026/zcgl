import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crud.query_builder import PartyFilter
from src.services.party_scope import resolve_user_party_filter

pytestmark = pytest.mark.asyncio


class TestResolveUserPartyFilter:
    async def test_should_return_explicit_party_filter(self) -> None:
        db = MagicMock()
        explicit_filter = PartyFilter(party_ids=["party-1"])

        result = await resolve_user_party_filter(
            db,
            current_user_id="user-1",
            party_filter=explicit_filter,
            logger=logging.getLogger(__name__),
        )

        assert result is explicit_filter

    async def test_should_return_none_when_current_user_id_missing(self) -> None:
        db = MagicMock()

        result = await resolve_user_party_filter(
            db,
            current_user_id=None,
            party_filter=None,
            logger=logging.getLogger(__name__),
        )

        assert result is None

    async def test_should_fallback_to_mapped_party_scope_when_no_party_bindings(
        self,
    ) -> None:
        db = MagicMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = "org-legacy"
        db.execute = AsyncMock(return_value=execute_result)

        with patch(
            "src.services.party_scope.party_crud.get_user_bindings",
            new=AsyncMock(return_value=[]),
        ), patch(
            "src.services.party_scope.party_crud.resolve_organization_party_id",
            new=AsyncMock(return_value="party-legacy"),
        ), patch(
            "src.services.party_scope._has_unrestricted_party_scope_access",
            new=AsyncMock(return_value=False),
        ):
            result = await resolve_user_party_filter(
                db,
                current_user_id="user-1",
                party_filter=None,
                logger=logging.getLogger(__name__),
            )

        assert result == PartyFilter(party_ids=["party-legacy"])

    async def test_should_fail_closed_when_legacy_org_not_mapped_to_party(self) -> None:
        db = MagicMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = "org-legacy"
        db.execute = AsyncMock(return_value=execute_result)

        with patch(
            "src.services.party_scope.party_crud.get_user_bindings",
            new=AsyncMock(return_value=[]),
        ), patch(
            "src.services.party_scope.party_crud.resolve_organization_party_id",
            new=AsyncMock(return_value=None),
        ), patch(
            "src.services.party_scope._has_unrestricted_party_scope_access",
            new=AsyncMock(return_value=False),
        ):
            result = await resolve_user_party_filter(
                db,
                current_user_id="user-1",
                party_filter=None,
                logger=logging.getLogger(__name__),
            )

        assert result == PartyFilter(party_ids=[])

    async def test_should_bypass_privileged_user_before_legacy_org_fallback(
        self,
    ) -> None:
        db = MagicMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = "org-legacy"
        db.execute = AsyncMock(return_value=execute_result)

        with patch(
            "src.services.party_scope.party_crud.get_user_bindings",
            new=AsyncMock(return_value=[]),
        ), patch(
            "src.services.party_scope._has_unrestricted_party_scope_access",
            new=AsyncMock(return_value=True),
        ):
            result = await resolve_user_party_filter(
                db,
                current_user_id="user-1",
                party_filter=None,
                logger=logging.getLogger(__name__),
            )

        assert result is None

    async def test_should_fail_closed_when_no_bindings_and_no_legacy_org(self) -> None:
        db = MagicMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=execute_result)

        with patch(
            "src.services.party_scope.party_crud.get_user_bindings",
            new=AsyncMock(return_value=[]),
        ), patch(
            "src.services.party_scope._has_unrestricted_party_scope_access",
            new=AsyncMock(return_value=False),
        ):
            result = await resolve_user_party_filter(
                db,
                current_user_id="user-1",
                party_filter=None,
                logger=logging.getLogger(__name__),
            )

        assert result == PartyFilter(party_ids=[])

    async def test_should_bypass_filter_for_privileged_user_without_scope(self) -> None:
        db = MagicMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=execute_result)

        with patch(
            "src.services.party_scope.party_crud.get_user_bindings",
            new=AsyncMock(return_value=[]),
        ), patch(
            "src.services.party_scope._has_unrestricted_party_scope_access",
            new=AsyncMock(return_value=True),
        ):
            result = await resolve_user_party_filter(
                db,
                current_user_id="user-1",
                party_filter=None,
                logger=logging.getLogger(__name__),
            )

        assert result is None

    async def test_should_bypass_filter_when_global_read_permission_present(self) -> None:
        db = MagicMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=execute_result)

        with patch(
            "src.services.party_scope.party_crud.get_user_bindings",
            new=AsyncMock(return_value=[]),
        ), patch("src.services.permission.rbac_service.RBACService") as mock_rbac_service:
            service_instance = mock_rbac_service.return_value
            service_instance.is_admin = AsyncMock(return_value=False)
            service_instance.check_permission = AsyncMock(
                return_value=SimpleNamespace(has_permission=True)
            )

            result = await resolve_user_party_filter(
                db,
                current_user_id="user-1",
                party_filter=None,
                logger=logging.getLogger(__name__),
            )

        assert result is None
        service_instance.is_admin.assert_awaited_once_with("user-1")
        service_instance.check_permission.assert_awaited_once()

    async def test_should_keep_relation_specific_scope_for_manager_binding(self) -> None:
        db = MagicMock()
        binding = MagicMock()
        binding.party_id = "party-1"
        binding.relation_type = "manager"

        with patch(
            "src.services.party_scope.party_crud.get_user_bindings",
            new=AsyncMock(return_value=[binding]),
        ):
            result = await resolve_user_party_filter(
                db,
                current_user_id="user-1",
                party_filter=None,
                logger=logging.getLogger(__name__),
            )

        assert result is not None
        assert result.filter_mode == "manager"
