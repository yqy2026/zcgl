from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import ResourceNotFoundError
from src.services.asset_operations.asset_unit_certificate_service import (
    AssetUnitCertificateService,
)
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_options_use_visible_unit_owner_and_one_business_clock():
    repository = MagicMock(list_options=AsyncMock(return_value=(["cert"], 1)))
    units = MagicMock(
        get=AsyncMock(return_value=SimpleNamespace(owner_party_id="owner"))
    )
    service = AssetUnitCertificateService(
        units=units,
        repository=repository,
        clock=lambda: datetime(2026, 11, 2, 18, tzinfo=UTC),
    )
    scope = EffectivePartyScope(
        user_id="reader",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner"],
    )
    result = await service.list_options_for_unit(
        MagicMock(), unit_id="unit", scope=scope, query="  证号  ", offset=2, limit=5
    )
    assert result == (["cert"], 1)
    values = repository.list_options.await_args.kwargs
    assert values["owner_party_id"] == "owner"
    assert values["as_of"].isoformat() == "2026-11-03"
    assert values["at"] == datetime(2026, 11, 2, 18)
    assert values["query"] == "证号"


async def test_options_do_not_query_invisible_unit_candidates():
    repository = MagicMock(list_options=AsyncMock())
    service = AssetUnitCertificateService(
        units=MagicMock(get=AsyncMock(return_value=None)), repository=repository
    )
    scope = EffectivePartyScope(
        user_id="reader", source="unrestricted", scope_mode="unrestricted"
    )
    with pytest.raises(ResourceNotFoundError):
        await service.list_options_for_unit(MagicMock(), unit_id="unit", scope=scope)
    repository.list_options.assert_not_called()
