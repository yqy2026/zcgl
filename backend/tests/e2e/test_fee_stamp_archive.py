"""Fee stamps expose version history through the unified archive entry."""

import io
from uuid import uuid4

import pytest
from PIL import Image

from src.api.v1 import archive_documents as archive_api
from src.api.v1 import management_fee_statements as fee_api
from src.services.party_scope_resolver import EffectivePartyScope
from tests.e2e.test_management_fee_e2e import _seed_fee_sources

pytestmark = pytest.mark.e2e


def _image(color):
    content = io.BytesIO()
    Image.new("RGB", (24, 24), color).save(content, format="PNG")
    return content.getvalue()


def _body(response):
    body = response.json()
    return body.get("data", body)


def test_fee_stamp_archive_versions_via_unified_entry(
    authenticated_client,
    csrf_headers,
    db_session,
    tmp_path,
    monkeypatch,
):
    from src.services.asset_operations.management_fee_upload_service import (
        management_fee_upload_service,
    )
    from src.services.property_certificate.attachment_service import (
        property_certificate_attachment_service,
    )

    monkeypatch.setattr(management_fee_upload_service, "uploads_root", tmp_path)
    monkeypatch.setattr(
        property_certificate_attachment_service, "uploads_root", tmp_path
    )
    client = authenticated_client
    facts = _seed_fee_sources(db_session, client._user_id)
    statement_id = facts["statement_id"]
    owner_scope = {"owner_party_ids": [facts["owner_id"]]}

    async def resolve(db, *, user_id):
        return EffectivePartyScope(
            user_id=user_id, source="explicit", scope_mode="owner", **owner_scope
        )

    monkeypatch.setattr(archive_api.party_scope_resolver, "resolve", resolve)
    monkeypatch.setattr(fee_api.party_scope_resolver, "resolve", resolve)

    list_params = {
        "target_type": "management_fee_statement",
        "target_id": statement_id,
        "document_type": "management_fee_statement",
    }
    empty = _body(client.get("/api/v1/archive/documents", params=list_params))
    assert empty["items"] == []

    first = client.post(
        f"/api/v1/management-fee-statements/{statement_id}/stamped-document",
        files={"file": ("stamp.png", _image("red"), "image/png")},
        data={"expected_version": 1},
        headers=csrf_headers,
    )
    assert first.status_code == 200, first.text
    assert _body(first)["version"] == 2

    listed = _body(client.get("/api/v1/archive/documents", params=list_params))
    assert [item["document_version"] for item in listed["items"]] == [1]
    assert listed["items"][0]["is_current"] is True
    first_document = listed["items"][0]

    second = client.post(
        f"/api/v1/management-fee-statements/{statement_id}/stamped-document",
        files={"file": ("stamp2.png", _image("blue"), "image/png")},
        data={"expected_version": 2},
        headers=csrf_headers,
    )
    assert second.status_code == 200, second.text
    assert _body(second)["version"] == 3

    history = _body(client.get("/api/v1/archive/documents", params=list_params))
    versions = {item["document_version"]: item for item in history["items"]}
    assert set(versions) == {1, 2}
    assert versions[2]["replaces_document_id"] == versions[1]["id"]
    assert versions[1]["is_current"] is False
    assert versions[2]["is_current"] is True

    old = client.get(
        f"/api/v1/archive/documents/{versions[1]['id']}/content"
    )
    assert old.status_code == 200, old.text
    assert old.content == _image("red")
    current = client.get(
        f"/api/v1/archive/documents/{versions[2]['id']}/content"
    )
    assert current.content == _image("blue")

    # The unified write entrance stays closed: stamps bind through the fee
    # command (version + business event), not the generic archive upload.
    rejected = client.post(
        "/api/v1/archive/documents",
        data=list_params,
        files={"file": ("stamp.png", _image("green"), "image/png")},
        headers=csrf_headers,
    )
    assert rejected.status_code == 422, rejected.text
    stale_replace = client.post(
        f"/api/v1/archive/documents/{versions[2]['id']}/replacement",
        files={"file": ("stamp.png", _image("green"), "image/png")},
        headers=csrf_headers,
    )
    assert stale_replace.status_code == 404, stale_replace.text

    async def hidden(db, *, user_id):
        return EffectivePartyScope(
            user_id=user_id,
            source="explicit",
            scope_mode="owner",
            owner_party_ids=[str(uuid4())],
        )

    monkeypatch.setattr(archive_api.party_scope_resolver, "resolve", hidden)
    assert (
        client.get("/api/v1/archive/documents", params=list_params).status_code == 404
    )
    assert (
        client.get(
            f"/api/v1/archive/documents/{first_document['id']}/content"
        ).status_code
        == 404
    )
