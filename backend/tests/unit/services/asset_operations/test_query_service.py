"""Public query seam for asset-operations v5."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import PartyScopeForbiddenError
from src.services.asset_operations.query_service import AssetOperationsQueryService
from src.services.party_scope_resolver import EffectivePartyScope


@pytest.mark.asyncio
async def test_missing_party_scope_is_403_not_an_empty_asset_unit_list() -> None:
    repository = MagicMock()
    repository.list = AsyncMock(return_value=([], 0))
    service = AssetOperationsQueryService(asset_unit_repository=repository)

    with pytest.raises(PartyScopeForbiddenError) as error:
        await service.list_asset_units(
            MagicMock(),
            scope=EffectivePartyScope(
                user_id="user-1",
                source="none",
                scope_mode="none",
                error_code="PARTY_SCOPE_MISSING",
            ),
        )

    assert error.value.status_code == 403
    assert error.value.code == "PARTY_SCOPE_MISSING"
    repository.list.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scope",
    [
        EffectivePartyScope(
            user_id="user-1",
            source="none",
            scope_mode="none",
            owner_party_ids=["owner-1"],
        ),
        EffectivePartyScope(
            user_id="user-1",
            source="explicit",
            scope_mode="owner",
            manager_party_ids=["manager-1"],
        ),
        EffectivePartyScope(
            user_id="user-1",
            source="explicit",
            scope_mode="manager",
            owner_party_ids=["owner-1"],
        ),
    ],
)
async def test_scope_mode_requires_ids_on_its_own_axis(
    scope: EffectivePartyScope,
) -> None:
    repository = MagicMock()
    repository.list = AsyncMock(return_value=([], 0))
    service = AssetOperationsQueryService(asset_unit_repository=repository)

    with pytest.raises(PartyScopeForbiddenError) as error:
        await service.list_asset_units(MagicMock(), scope=scope)

    assert error.value.status_code == 403
    assert error.value.code == "PARTY_SCOPE_MISSING"
    repository.list.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_scope_blocks_all_asset_and_contract_query_entrypoints() -> None:
    asset_repository = MagicMock()
    asset_repository.get = AsyncMock(return_value=None)
    contract_repository = MagicMock()
    contract_repository.list_upstream = AsyncMock(return_value=([], 0))
    contract_repository.get_upstream = AsyncMock(return_value=None)
    contract_repository.list_terminal = AsyncMock(return_value=([], 0))
    contract_repository.get_terminal = AsyncMock(return_value=None)
    service = AssetOperationsQueryService(
        asset_unit_repository=asset_repository,
        asset_contract_repository=contract_repository,
    )
    scope = EffectivePartyScope(
        user_id="user-1",
        source="none",
        scope_mode="none",
        error_code="PARTY_SCOPE_MISSING",
    )
    db = MagicMock()

    with pytest.raises(PartyScopeForbiddenError):
        await service.get_asset_unit(db, unit_id="unit-1", scope=scope)
    with pytest.raises(PartyScopeForbiddenError):
        await service.list_upstream_contracts(db, scope=scope)
    with pytest.raises(PartyScopeForbiddenError):
        await service.get_upstream_contract(db, contract_id="upstream-1", scope=scope)
    with pytest.raises(PartyScopeForbiddenError):
        await service.list_terminal_contracts(db, scope=scope)
    with pytest.raises(PartyScopeForbiddenError):
        await service.get_terminal_contract(db, contract_id="terminal-1", scope=scope)

    asset_repository.get.assert_not_awaited()
    contract_repository.list_upstream.assert_not_awaited()
    contract_repository.get_upstream.assert_not_awaited()
    contract_repository.list_terminal.assert_not_awaited()
    contract_repository.get_terminal.assert_not_awaited()
