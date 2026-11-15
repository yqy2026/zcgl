"""Archive totals and matrix use current property scope in PostgreSQL."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.api.v1 import archive_matrix as api
from src.models.asset_unit import PropertyCertificateAssetUnit
from src.services.party_scope_resolver import EffectivePartyScope
from tests.e2e.test_asset_unit_certificates import (
    certificate_facts as _certificate_facts,
)

certificate_facts = _certificate_facts
pytestmark = pytest.mark.e2e


def test_current_matrix_scope_shared_certificate_and_pagination(
    authenticated_client, certificate_facts, db_session, monkeypatch
):
    f = certificate_facts
    db_session.add(
        PropertyCertificateAssetUnit(
            certificate_id=f["current"],
            asset_unit_id=f["visible_unit"],
            effective_from=date(2020, 1, 1),
        )
    )
    db_session.commit()
    monkeypatch.setattr(api.archive_matrix_service, "clock", lambda: date(2026, 11, 3))
    scope = EffectivePartyScope(
        user_id="matrix-reader",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=[f["owner"]],
    )
    monkeypatch.setattr(
        api.party_scope_resolver, "resolve", AsyncMock(return_value=scope)
    )
    response = authenticated_client.get("/api/v1/archive/completion")
    assert response.status_code == 200, response.text
    body = response.json()
    if "data" in body:
        body = body["data"]
    cert = next(
        r for r in body["categories"] if r["document_type"] == "property_certificate"
    )
    assert cert["required"] == 2
    assert cert["existing"] == 0
    assert body["unlinked_unit_count"] == 0
    matrix = authenticated_client.get("/api/v1/archive/matrix?limit=1").json()
    if "data" in matrix:
        matrix = matrix["data"]
    assert matrix["total"] == 2
    assert len(matrix["items"]) == 1
    assert matrix["items"][0]["unit_id"] != f["hidden_unit"]
    assert f["hidden_unit"] not in str(matrix)
    assert matrix["items"][0]["categories"][3]["required"] == 0
