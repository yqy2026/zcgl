from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.api.v1 import asset_units as api
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = pytest.mark.unit


def test_options_require_write_and_apply_query_validation(client, monkeypatch):
    route = next(
        r for r in api.router.routes if r.path.endswith("/property-certificate-options")
    )
    checker = next(
        d.call
        for d in route.dependant.dependencies
        if type(d.call).__name__ == "AuthzPermissionChecker"
    )
    assert checker.action == "write"
    assert checker.resource_type == "asset_ops"
    reader = AsyncMock(return_value=([], 0))
    monkeypatch.setattr(
        api,
        "asset_unit_certificate_service",
        SimpleNamespace(list_options_for_unit=reader),
    )
    monkeypatch.setattr(
        api.party_scope_resolver,
        "resolve",
        AsyncMock(
            return_value=EffectivePartyScope(
                user_id="reader", source="unrestricted", scope_mode="unrestricted"
            )
        ),
    )
    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}, {"q": "a" * 101}):
        assert (
            client.get(
                "/api/v1/asset-units/unit/property-certificate-options", params=params
            ).status_code
            == 422
        )
    reader.assert_not_awaited()
    response = client.get(
        "/api/v1/asset-units/unit/property-certificate-options",
        params={"q": "证", "limit": 5, "offset": 2},
    )
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}
    assert reader.await_args.kwargs["query"] == "证"
    assert reader.await_args.kwargs["offset"] == 2
