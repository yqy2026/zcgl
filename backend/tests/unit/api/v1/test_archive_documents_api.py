from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.api.v1 import archive_documents as api
from src.schemas.archive_document import ArchiveDocumentListResponse
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = pytest.mark.unit


def test_archive_routes_require_asset_ops_read():
    for route in api.router.routes:
        checker = next(
            dep.call
            for dep in route.dependant.dependencies
            if type(dep.call).__name__ == "AuthzPermissionChecker"
        )
        assert checker.action == ("read" if "GET" in route.methods else "archive")
        assert checker.resource_type == "asset_ops"


def test_archive_list_binds_scope_and_rejects_unsupported_type(
    client: TestClient, monkeypatch
):
    scope = EffectivePartyScope(
        user_id="actor", source="unrestricted", scope_mode="unrestricted"
    )
    monkeypatch.setattr(
        api.party_scope_resolver, "resolve", AsyncMock(return_value=scope)
    )
    reader = AsyncMock(return_value=ArchiveDocumentListResponse(items=[]))
    monkeypatch.setattr(api.archive_document_query_service, "list_documents", reader)
    response = client.get(
        "/api/v1/archive/documents?target_type=property_certificate&target_id=cert&include_history=false"
    )
    assert response.status_code == 200
    assert reader.await_args.kwargs == {
        "certificate_id": "cert",
        "scope": scope,
        "include_history": False,
    }


def test_archive_list_dispatches_statement_pair(client: TestClient, monkeypatch):
    scope = EffectivePartyScope(
        user_id="actor", source="unrestricted", scope_mode="unrestricted"
    )
    monkeypatch.setattr(
        api.party_scope_resolver, "resolve", AsyncMock(return_value=scope)
    )
    reader = AsyncMock(return_value=ArchiveDocumentListResponse(items=[]))
    monkeypatch.setattr(
        api.archive_document_query_service, "list_statement", reader
    )
    response = client.get(
        "/api/v1/archive/documents?target_type=management_fee_statement"
        "&target_id=fee&document_type=management_fee_statement&include_history=false"
    )
    assert response.status_code == 200, response.text
    assert reader.await_args.kwargs == {
        "target_id": "fee",
        "scope": scope,
        "include_history": False,
    }
    assert (
        client.get(
            "/api/v1/archive/documents?target_type=management_fee_statement"
            "&target_id=fee&document_type=supplement"
        ).status_code
        == 422
    )


def test_archive_contract_scan_routes_dispatch_by_target(client, monkeypatch):
    scope = EffectivePartyScope(
        user_id="actor", source="unrestricted", scope_mode="unrestricted"
    )
    monkeypatch.setattr(
        api.party_scope_resolver, "resolve", AsyncMock(return_value=scope)
    )
    reader = AsyncMock(return_value=ArchiveDocumentListResponse(items=[]))
    monkeypatch.setattr(
        api.archive_document_query_service, "list_contract_scan", reader
    )
    response = client.get(
        "/api/v1/archive/documents?target_type=upstream_contract&target_id=c1"
        "&document_type=upstream_contract&include_history=false"
    )
    assert response.status_code == 200
    assert reader.await_args.kwargs == {
        "target_type": "upstream_contract",
        "target_id": "c1",
        "scope": scope,
        "include_history": False,
    }
    assert (
        client.get(
            "/api/v1/archive/documents?target_type=terminal_contract&target_id=c1&document_type=upstream_contract"
        ).status_code
        == 422
    )


def test_archive_upload_rejects_unsupported_or_empty_target(
    client: TestClient, monkeypatch
):
    writer = AsyncMock()
    monkeypatch.setattr(api.archive_document_query_service, "append_document", writer)
    scan_writer = AsyncMock()
    monkeypatch.setattr(
        api.archive_document_query_service, "append_contract_scan", scan_writer
    )
    for data in [
        {
            "target_type": "management_fee_statement",
            "target_id": "fee",
            "document_type": "management_fee_statement",
        },
        {
            "target_type": "terminal_contract",
            "target_id": "cert",
            "document_type": "property_certificate",
        },
        {
            "target_type": "upstream_contract",
            "target_id": "cert",
            "document_type": "supplement",
        },
        {
            "target_type": "property_certificate",
            "target_id": "",
            "document_type": "property_certificate",
        },
        {
            "target_type": "property_certificate",
            "target_id": "cert",
            "document_type": "other",
        },
    ]:
        response = client.post(
            "/api/v1/archive/documents",
            data=data,
            files={"file": ("scan.pdf", b"file", "application/pdf")},
        )
        assert response.status_code == 422, response.text
    writer.assert_not_called()
    scan_writer.assert_not_called()


def test_archive_upload_dispatches_contract_scan(client: TestClient, monkeypatch):
    from src.schemas.archive_document import ArchiveDocumentItem

    scope = EffectivePartyScope(
        user_id="actor", source="unrestricted", scope_mode="unrestricted"
    )
    monkeypatch.setattr(
        api.party_scope_resolver, "resolve", AsyncMock(return_value=scope)
    )
    item = ArchiveDocumentItem(
        id="d",
        attachment_id="a",
        document_type="upstream_contract",
        target_type="upstream_contract",
        target_id="c1",
        file_name="scan.pdf",
        content_type="application/pdf",
        file_size=4,
        document_version=1,
        replaces_document_id=None,
        uploaded_at="2026-11-04T00:00:00Z",
        is_current=True,
    )
    writer = AsyncMock(return_value=item)
    monkeypatch.setattr(
        api.archive_document_query_service, "append_contract_scan", writer
    )
    response = client.post(
        "/api/v1/archive/documents",
        data={
            "target_type": "upstream_contract",
            "target_id": "c1",
            "document_type": "upstream_contract",
        },
        files={"file": ("scan.pdf", b"file", "application/pdf")},
    )
    assert response.status_code == 201, response.text
    assert writer.await_args.kwargs["target_type"] == "upstream_contract"
    assert writer.await_args.kwargs["target_id"] == "c1"
    assert writer.await_args.kwargs["scope"] is scope


def _make_pdf(path):
    import fitz

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "scan page")
    document.save(str(path))
    document.close()


def _download_result(tmp_path, file_type: str):
    from src.models.attachment import Attachment
    from src.services.property_certificate.attachment_service import (
        PropertyCertificateAttachmentDownload,
    )

    pdf_path = tmp_path / "scan.pdf"
    _make_pdf(pdf_path)
    attachment = Attachment(
        file_name="scan.pdf",
        file_type=file_type,
        storage_key="contracts/scan.pdf",
        file_size=pdf_path.stat().st_size,
        owner_type="contract",
        owner_id="c1",
        created_by="actor",
    )
    return PropertyCertificateAttachmentDownload(
        attachment=attachment, path=pdf_path
    )


def test_archive_thumbnail_renders_pdf_first_page_as_png(
    client: TestClient, monkeypatch, tmp_path
):
    scope = EffectivePartyScope(
        user_id="actor", source="unrestricted", scope_mode="unrestricted"
    )
    monkeypatch.setattr(
        api.party_scope_resolver, "resolve", AsyncMock(return_value=scope)
    )
    reader = AsyncMock(return_value=_download_result(tmp_path, "pdf"))
    monkeypatch.setattr(
        api.archive_document_query_service, "prepare_thumbnail", reader
    )
    response = client.get("/api/v1/archive/documents/doc-1/thumbnail")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert reader.await_args.kwargs["document_id"] == "doc-1"
    assert reader.await_args.kwargs["scope"] is scope


def test_archive_thumbnail_rejects_non_pdf_archives(
    client: TestClient, monkeypatch, tmp_path
):
    scope = EffectivePartyScope(
        user_id="actor", source="unrestricted", scope_mode="unrestricted"
    )
    monkeypatch.setattr(
        api.party_scope_resolver, "resolve", AsyncMock(return_value=scope)
    )
    monkeypatch.setattr(
        api.archive_document_query_service,
        "prepare_thumbnail",
        AsyncMock(return_value=_download_result(tmp_path, "png")),
    )
    response = client.get("/api/v1/archive/documents/doc-1/thumbnail")
    assert response.status_code == 404
