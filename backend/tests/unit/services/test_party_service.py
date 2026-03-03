from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import OperationNotAllowedError
from src.crud.query_builder import PartyFilter
from src.schemas.party import UserPartyBindingCreate, UserPartyBindingUpdate
from src.services.party.service import PartyService

pytestmark = pytest.mark.asyncio


class TestPartyServiceUserScopeInvalidation:
    async def test_create_user_party_binding_publishes_scope_invalidation(self) -> None:
        db = MagicMock()
        binding = SimpleNamespace(user_id="user-1")
        party_crud = MagicMock()
        party_crud.create_user_party_binding = AsyncMock(return_value=binding)
        service = PartyService(data_access=party_crud)

        payload = MagicMock()
        payload.model_dump.return_value = {
            "user_id": "user-1",
            "party_id": "party-1",
            "relation_type": "owner",
        }

        with (
            patch.object(service, "_assert_user_exists", AsyncMock(return_value=None)),
            patch.object(service, "_assert_party_exists", AsyncMock(return_value=None)),
            patch("src.services.authz.authz_event_bus.publish_invalidation") as mock_publish,
        ):
            result = await service.create_user_party_binding(
                db,
                obj_in=payload,
            )

        assert result is binding
        mock_publish.assert_called_once_with(
            event_type="authz.user_scope.updated",
            payload={"user_id": "user-1"},
        )

    async def test_create_user_party_binding_does_not_fail_when_publish_errors(self) -> None:
        db = MagicMock()
        binding = SimpleNamespace(user_id="user-1")
        party_crud = MagicMock()
        party_crud.create_user_party_binding = AsyncMock(return_value=binding)
        service = PartyService(data_access=party_crud)

        payload = MagicMock()
        payload.model_dump.return_value = {
            "user_id": "user-1",
            "party_id": "party-1",
            "relation_type": "owner",
        }

        with (
            patch.object(service, "_assert_user_exists", AsyncMock(return_value=None)),
            patch.object(service, "_assert_party_exists", AsyncMock(return_value=None)),
            patch(
                "src.services.authz.authz_event_bus.publish_invalidation",
                side_effect=RuntimeError("boom"),
            ),
        ):
            result = await service.create_user_party_binding(
                db,
                obj_in=payload,
            )

        assert result is binding


class TestPartyServiceScopeAndBindingBehavior:
    async def test_get_parties_should_apply_resolved_party_scope(self) -> None:
        db = MagicMock()
        party_crud = MagicMock()
        party_crud.get_parties = AsyncMock(return_value=[])
        service = PartyService(data_access=party_crud)

        mock_resolve_filter = AsyncMock(return_value=PartyFilter(party_ids=["party-1"]))
        with patch(
            "src.services.party.service.resolve_user_party_filter",
            mock_resolve_filter,
        ):
            await service.get_parties(db, current_user_id="user-1")

        mock_resolve_filter.assert_awaited_once_with(
            db,
            current_user_id="user-1",
            party_filter=None,
            logger=ANY,
            allow_legacy_default_organization_fallback=False,
        )
        party_crud.get_parties.assert_awaited_once_with(
            db,
            skip=0,
            limit=100,
            party_type=None,
            status=None,
            search=None,
            scoped_party_ids=["party-1"],
        )

    async def test_get_parties_should_not_scope_when_filter_resolver_returns_none(self) -> None:
        db = MagicMock()
        party_crud = MagicMock()
        party_crud.get_parties = AsyncMock(return_value=[])
        service = PartyService(data_access=party_crud)

        with patch(
            "src.services.party.service.resolve_user_party_filter",
            AsyncMock(return_value=None),
        ):
            await service.get_parties(db, current_user_id="admin-user")

        party_crud.get_parties.assert_awaited_once_with(
            db,
            skip=0,
            limit=100,
            party_type=None,
            status=None,
            search=None,
            scoped_party_ids=None,
        )

    async def test_update_user_party_binding_should_clear_existing_primary_when_needed(
        self,
    ) -> None:
        db = MagicMock()
        binding = SimpleNamespace(
            id="binding-1",
            user_id="user-1",
            party_id="party-1",
            relation_type="owner",
            is_primary=False,
            valid_from=SimpleNamespace(),
            valid_to=None,
        )
        updated_binding = SimpleNamespace(id="binding-1", user_id="user-1")
        party_crud = MagicMock()
        party_crud.get_user_binding = AsyncMock(return_value=binding)
        party_crud.clear_primary_bindings_for_relation = AsyncMock(return_value=1)
        party_crud.update_user_party_binding = AsyncMock(return_value=updated_binding)
        service = PartyService(data_access=party_crud)

        with (
            patch.object(service, "_assert_user_exists", AsyncMock(return_value=None)),
            patch.object(
                service,
                "_publish_user_scope_invalidation",
                AsyncMock(return_value=None),
            ) as mock_publish,
        ):
            await service.update_user_party_binding(
                db,
                user_id="user-1",
                binding_id="binding-1",
                obj_in=UserPartyBindingUpdate.model_validate({"is_primary": True}),
            )

        party_crud.clear_primary_bindings_for_relation.assert_awaited_once_with(
            db,
            user_id="user-1",
            relation_type="owner",
            exclude_binding_id="binding-1",
            commit=False,
        )
        party_crud.update_user_party_binding.assert_awaited_once()
        mock_publish.assert_awaited_once_with("user-1")

    async def test_close_user_party_binding_should_publish_scope_invalidation(self) -> None:
        from datetime import UTC, datetime, timedelta

        db = MagicMock()
        now = datetime.now(UTC).replace(tzinfo=None)
        binding = SimpleNamespace(
            id="binding-1",
            user_id="user-1",
            valid_from=now - timedelta(days=1),
            valid_to=None,
        )
        party_crud = MagicMock()
        party_crud.get_user_binding = AsyncMock(return_value=binding)
        party_crud.update_user_party_binding = AsyncMock(return_value=binding)
        service = PartyService(data_access=party_crud)

        with (
            patch.object(service, "_assert_user_exists", AsyncMock(return_value=None)),
            patch.object(
                service,
                "_publish_user_scope_invalidation",
                AsyncMock(return_value=None),
            ) as mock_publish,
        ):
            closed = await service.close_user_party_binding(
                db,
                user_id="user-1",
                binding_id="binding-1",
            )

        assert closed is True
        party_crud.update_user_party_binding.assert_awaited_once()
        mock_publish.assert_awaited_once_with("user-1")

    async def test_create_user_party_binding_should_reject_invalid_time_range(self) -> None:
        from datetime import UTC, datetime, timedelta

        db = MagicMock()
        party_crud = MagicMock()
        party_crud.create_user_party_binding = AsyncMock()
        service = PartyService(data_access=party_crud)

        payload = UserPartyBindingCreate(
            user_id="user-1",
            party_id="party-1",
            relation_type="owner",
            valid_to=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1),
        )

        with (
            patch.object(service, "_assert_user_exists", AsyncMock(return_value=None)),
            patch.object(service, "_assert_party_exists", AsyncMock(return_value=None)),
        ):
            with pytest.raises(OperationNotAllowedError) as exc_info:
                await service.create_user_party_binding(
                    db,
                    obj_in=payload,
                )

        assert "失效时间不能早于生效时间" in str(exc_info.value)
        party_crud.create_user_party_binding.assert_not_called()
