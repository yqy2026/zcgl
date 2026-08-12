from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crud.query_builder import PartyFilter
from src.services.property_certificate.service import PropertyCertificateService


@pytest.mark.asyncio
async def test_list_adds_asset_filter_to_resolved_party_scope() -> None:
    """Asset filtering narrows, but never replaces, the caller's party scope."""
    db = MagicMock()
    service = PropertyCertificateService(db)
    resolved_scope = PartyFilter(party_ids=["party-1"])

    with (
        patch.object(
            service,
            "_resolve_party_filter",
            AsyncMock(return_value=resolved_scope),
        ),
        patch(
            "src.services.property_certificate.service.property_certificate_crud.get_multi",
            AsyncMock(return_value=[]),
        ) as get_multi,
    ):
        result = await service.list_certificates(
            skip=5,
            limit=10,
            asset_id="asset-1",
            current_user_id="user-1",
        )

    assert result == []
    get_multi.assert_awaited_once_with(
        db,
        skip=5,
        limit=10,
        asset_id="asset-1",
        party_filter=resolved_scope,
    )
