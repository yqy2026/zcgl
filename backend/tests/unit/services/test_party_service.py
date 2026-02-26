from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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

        with patch(
            "src.services.authz.authz_event_bus.publish_invalidation"
        ) as mock_publish:
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

        with patch(
            "src.services.authz.authz_event_bus.publish_invalidation",
            side_effect=RuntimeError("boom"),
        ):
            result = await service.create_user_party_binding(
                db,
                obj_in=payload,
            )

        assert result is binding
