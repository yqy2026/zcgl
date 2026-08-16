"""
End-to-end global search tests (REQ-SCH-001).

Covers /api/v1/search over a seeded asset and project population:
typed result groups, the mandatory query parameter, and empty-result
behavior for blank or non-matching queries.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.models.party import Party, PartyReviewStatus, PartyType
from src.models.user_party_binding import RelationType, UserPartyBinding
from tests.e2e.factories import (
    create_asset_ownership as _create_ownership,
)
from tests.e2e.factories import (
    create_asset_payload as _create_asset_payload,
)

pytestmark = pytest.mark.e2e


def _search(authenticated_client: TestClient, query: str):
    return authenticated_client.get("/api/v1/search", params={"q": query})


def test_global_search_returns_typed_groups_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Seeded asset and project surface in their typed result groups."""
    suffix = uuid4().hex[:8]
    token = f"sz{suffix}"

    # Party-scoped asset creation (owner binding for the admin session).
    ownership = _create_ownership(db_session, suffix)
    party = (
        db_session.query(Party)
        .filter(
            Party.party_type == PartyType.LEGAL_ENTITY,
            Party.external_ref == ownership.id,
        )
        .one_or_none()
    )
    if party is None:
        party = Party(
            party_type=PartyType.LEGAL_ENTITY,
            name=ownership.name,
            code=f"LE-{uuid4().int % 1_000_000:06d}",
            external_ref=ownership.id,
            status="active",
            review_status=PartyReviewStatus.APPROVED.value,
        )
        db_session.add(party)
        db_session.flush()
    user_id = getattr(authenticated_client, "_user_id")
    db_session.add(
        UserPartyBinding(
            user_id=user_id,
            party_id=party.id,
            relation_type=RelationType.OWNER,
        )
    )
    db_session.commit()

    asset_response = authenticated_client.post(
        "/api/v1/assets",
        json={
            **_create_asset_payload(
                suffix=token,
                ownership_id=party.external_ref or party.id,
                name_prefix="E2E搜索资产",
            ),
            "owner_party_id": party.id,
            "manager_party_id": party.id,
        },
        headers=csrf_headers,
    )
    assert asset_response.status_code == 201, asset_response.text
    asset_id = asset_response.json()["id"]

    project_response = authenticated_client.post(
        "/api/v1/projects",
        json={
            "project_name": f"E2E搜索项目-{token}",
            "status": "planning",
            "manager_party_id": party.id,
            "data_status": "正常",
        },
        headers=csrf_headers,
    )
    assert project_response.status_code == 200, project_response.text
    project_id = project_response.json()["id"]

    results = _search(authenticated_client, token)
    assert results.status_code == 200, results.text
    payload = results.json()
    assert payload.get("success") is True
    data = payload.get("data", {})
    assert data.get("query") == token
    assert data.get("total", 0) >= 2

    hits = {(item["object_type"], item["object_id"]) for item in data["items"]}
    assert ("asset", asset_id) in hits
    assert ("project", project_id) in hits

    groups = {g["object_type"]: g["count"] for g in data.get("groups", [])}
    assert groups.get("asset", 0) >= 1
    assert groups.get("project", 0) >= 1


def test_global_search_query_guards_e2e(
    authenticated_client: TestClient,
) -> None:
    """The query is mandatory; blanks and misses answer empty, not errors."""
    missing = authenticated_client.get("/api/v1/search")
    assert missing.status_code == 422

    blank = _search(authenticated_client, "   ")
    assert blank.status_code == 200, blank.text
    blank_data = blank.json().get("data", {})
    assert blank_data.get("total") == 0
    assert blank_data.get("items") == []

    no_hit = _search(authenticated_client, f"no-such-token-{uuid4().hex[:8]}")
    assert no_hit.status_code == 200
    assert no_hit.json().get("data", {}).get("total") == 0

def test_search_requires_authentication_e2e(client) -> None:
    """Read-only suite: the analogous negative branch is anonymous 401."""
    response = client.get("/api/v1/search", params={"q": "anonymous"})
    assert response.status_code == 401
