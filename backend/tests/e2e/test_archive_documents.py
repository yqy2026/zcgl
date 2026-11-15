"""v5 scope is rechecked for private files, independent of old cert permissions."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.api.v1 import archive_documents as api
from src.models.archive_document import ArchiveDocument
from src.models.attachment import Attachment
from src.services.party_scope_resolver import EffectivePartyScope
from src.services.property_certificate.attachment_service import (
    property_certificate_attachment_service,
)
from tests.e2e.test_asset_unit_certificates import (
    certificate_facts as _certificate_facts,
)

certificate_facts = _certificate_facts
pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("mode", ["owner", "manager", "unrestricted"])
def test_scoped_archive_list_and_history_download(
    authenticated_client, certificate_facts, db_session, monkeypatch, tmp_path, mode
):
    facts = certificate_facts
    cert = facts["current"]
    document_id, file_id = str(uuid4()), str(uuid4())
    content = b"private historical scan"
    (tmp_path / "scan.pdf").write_bytes(content)
    monkeypatch.setattr(
        property_certificate_attachment_service, "uploads_root", tmp_path
    )
    scope = EffectivePartyScope(
        user_id="reader",
        source="explicit",
        scope_mode=mode,
        owner_party_ids=[facts["owner"]],
        manager_party_ids=[facts["manager"]],
    )
    resolver = AsyncMock(return_value=scope)
    monkeypatch.setattr(api.party_scope_resolver, "resolve", resolver)
    monkeypatch.setattr(
        api.archive_document_query_service,
        "clock",
        lambda: datetime(2026, 11, 2, 12, tzinfo=UTC),
    )
    db_session.add(
        Attachment(
            id=file_id,
            owner_type="property_certificate",
            owner_id=cert,
            file_name="历史证照.pdf",
            file_type="pdf",
            file_size=len(content),
            storage_key="scan.pdf",
            created_by="reader",
        )
    )
    db_session.flush()
    db_session.add(
        ArchiveDocument(
            id=document_id,
            attachment_id=file_id,
            target_type="property_certificate",
            target_id=cert,
            document_type="property_certificate",
            document_version=1,
            uploaded_by="reader",
            uploaded_at=datetime(2026, 11, 2),
        )
    )
    db_session.flush()
    replacement_file = str(uuid4())
    db_session.add(
        Attachment(
            id=replacement_file,
            owner_type="property_certificate",
            owner_id=cert,
            file_name="现行证照.pdf",
            file_type="pdf",
            file_size=3,
            storage_key="replacement.pdf",
            created_by="reader",
        )
    )
    db_session.flush()
    db_session.add(
        ArchiveDocument(
            id=str(uuid4()),
            attachment_id=replacement_file,
            target_type="property_certificate",
            target_id=cert,
            document_type="property_certificate",
            document_version=2,
            replaces_document_id=document_id,
            uploaded_by="reader",
            uploaded_at=datetime(2026, 11, 3),
        )
    )
    db_session.commit()
    response = authenticated_client.get(
        f"/api/v1/archive/documents?target_type=property_certificate&target_id={cert}"
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["id"] == document_id
    assert response.json()["items"][0]["is_current"] is False
    assert len(response.json()["items"]) == 2
    assert "storage_key" not in response.text and "uploaded_by" not in response.text
    download = authenticated_client.get(
        f"/api/v1/archive/documents/{document_id}/content"
    )
    assert download.status_code == 200, download.text
    assert download.content == content
    assert download.headers["cache-control"] == "private, no-store"
    assert download.headers["content-type"] == "application/pdf"
    resolver.return_value = EffectivePartyScope(
        user_id="reader",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=[str(uuid4())],
    )
    denied = authenticated_client.get(
        f"/api/v1/archive/documents/{document_id}/content"
    )
    assert denied.status_code == 404
    assert content.decode() not in denied.text


def test_future_only_certificate_does_not_grant_archive_access(
    authenticated_client, certificate_facts, monkeypatch
):
    facts = certificate_facts
    monkeypatch.setattr(
        api.archive_document_query_service,
        "clock",
        lambda: datetime(2026, 11, 2, 12, tzinfo=UTC),
    )
    monkeypatch.setattr(
        api.party_scope_resolver,
        "resolve",
        AsyncMock(
            return_value=EffectivePartyScope(
                user_id="reader",
                source="explicit",
                scope_mode="owner",
                owner_party_ids=[facts["owner"]],
            )
        ),
    )
    response = authenticated_client.get(
        f"/api/v1/archive/documents?target_type=property_certificate&target_id={facts['future']}"
    )
    assert response.status_code == 404


def test_upload_replace_preserves_private_history_and_rejects_stale_duplicate(
    authenticated_client, certificate_facts, monkeypatch, tmp_path, csrf_headers
):
    from tests.e2e.test_certificate_archive_versions import png

    authenticated_client.headers.update(csrf_headers)
    cert = certificate_facts["current"]
    scope = EffectivePartyScope(
        user_id="writer", source="unrestricted", scope_mode="unrestricted"
    )
    resolver = AsyncMock(return_value=scope)
    monkeypatch.setattr(api.party_scope_resolver, "resolve", resolver)
    monkeypatch.setattr(
        property_certificate_attachment_service, "uploads_root", tmp_path
    )
    data = {
        "target_type": "property_certificate",
        "target_id": cert,
        "document_type": "property_certificate",
    }
    first = authenticated_client.post(
        "/api/v1/archive/documents",
        data=data,
        files={"file": ("original.png", png(64), "image/png")},
    )
    assert first.status_code == 201, first.text
    original = first.json()
    assert original["is_current"] is True
    assert "storage_key" not in original and "uploaded_by" not in original
    path = f"/api/v1/archive/documents/{original['id']}/replacement"
    replacement = authenticated_client.post(
        path, files={"file": ("new.png", png(128), "image/png")}
    )
    assert replacement.status_code == 201, replacement.text
    assert replacement.json()["replaces_document_id"] == original["id"]
    assert replacement.json()["document_version"] == 2
    stale = authenticated_client.post(
        path, files={"file": ("stale.png", png(192), "image/png")}
    )
    assert stale.status_code == 409 and "ARCHIVE_VERSION_STALE" in stale.text
    duplicate = authenticated_client.post(
        "/api/v1/archive/documents",
        data=data,
        files={"file": ("copy.png", png(64), "image/png")},
    )
    assert (
        duplicate.status_code == 409 and "ARCHIVE_DUPLICATE_CONTENT" in duplicate.text
    )
    download = authenticated_client.get(
        f"/api/v1/archive/documents/{original['id']}/content"
    )
    assert download.status_code == 200 and download.content == png(64)
    resolver.return_value = EffectivePartyScope(
        user_id="writer",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=[str(uuid4())],
    )
    denied = authenticated_client.post(
        "/api/v1/archive/documents",
        data=data,
        files={"file": ("hidden.png", png(192), "image/png")},
    )
    assert denied.status_code == 404
    denied_replace = authenticated_client.post(
        f"/api/v1/archive/documents/{replacement.json()['id']}/replacement",
        files={"file": ("hidden.png", png(192), "image/png")},
    )
    assert denied_replace.status_code == 404
