"""
End-to-end property certificate attachment tests (REQ-AST-005).

Covers the attachment lifecycle through the public API: multi-file upload
with per-file outcomes, listing, inline preview vs download, replacement,
and the last-attachment retention guard.
"""

from uuid import uuid4

import fitz
import pytest
from fastapi.testclient import TestClient

from tests.e2e.factories import (
    create_approved_legal_party,
    create_scoped_asset_via_api,
)

pytestmark = pytest.mark.e2e


def _pdf_bytes(label: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), label)
    data = doc.tobytes()
    doc.close()
    return data


def _create_certificate(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
    *,
    suffix: str,
) -> str:
    holder = create_approved_legal_party(
        db_session, suffix=suffix, name=f"附件权利人-{suffix}"
    )
    asset = create_scoped_asset_via_api(
        authenticated_client,
        db_session,
        suffix=suffix,
        holder_party_id=holder.id,
        csrf_headers=csrf_headers,
    )
    response = authenticated_client.post(
        "/api/v1/property-certificates",
        json={
            "certificate_number": f"E2E-ATT-{suffix}",
            "certificate_type": "real_estate",
            "registration_date": "2026-01-01",
            "property_address": f"附件地址-{suffix}",
            "asset_ids": [asset["id"]],
            "holder_party_ids": [holder.id],
        },
        headers=csrf_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_property_certificate_attachment_lifecycle_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Upload → list → preview/download → replace → delete with guards."""
    suffix = uuid4().hex[:8]
    certificate_id = _create_certificate(
        authenticated_client, csrf_headers, db_session, suffix=suffix
    )

    upload = authenticated_client.post(
        f"/api/v1/property-certificates/{certificate_id}/attachments",
        files=[
            ("files", ("cert-a.pdf", _pdf_bytes("cert-a"), "application/pdf")),
            ("files", ("cert-b.pdf", _pdf_bytes("cert-b"), "application/pdf")),
        ],
        headers=csrf_headers,
    )
    assert upload.status_code == 201, upload.text
    results = upload.json()["results"]
    assert len(results) == 2
    assert all("attachment" in item for item in results)
    first_attachment_id = results[0]["attachment"]["id"]

    listing = authenticated_client.get(
        f"/api/v1/property-certificates/{certificate_id}/attachments"
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 2

    preview = authenticated_client.get(
        f"/api/v1/property-certificates/{certificate_id}"
        f"/attachments/{first_attachment_id}/preview"
    )
    assert preview.status_code == 200, preview.text
    assert preview.content.startswith(b"%PDF-")
    assert "pdf" in preview.headers.get("content-type", "")

    download = authenticated_client.get(
        f"/api/v1/property-certificates/{certificate_id}"
        f"/attachments/{first_attachment_id}/download"
    )
    assert download.status_code == 200, download.text
    assert download.content.startswith(b"%PDF-")
    assert "cert-a.pdf" in download.headers.get("content-disposition", "")

    # Replacement produces a fresh attachment id for the same slot.
    replace = authenticated_client.put(
        f"/api/v1/property-certificates/{certificate_id}"
        f"/attachments/{first_attachment_id}",
        files={"file": ("cert-a-v2.pdf", _pdf_bytes("cert-a-v2"), "application/pdf")},
        headers=csrf_headers,
    )
    assert replace.status_code == 200, replace.text
    replaced_id = replace.json()["id"]
    assert replaced_id != first_attachment_id

    listing_after_replace = authenticated_client.get(
        f"/api/v1/property-certificates/{certificate_id}/attachments"
    )
    assert len(listing_after_replace.json()) == 2

    # Deleting down to the last attachment is blocked (422), then allowed
    # once two remain → one delete succeeds, the final one is rejected.
    delete_one = authenticated_client.delete(
        f"/api/v1/property-certificates/{certificate_id}"
        f"/attachments/{replaced_id}",
        headers=csrf_headers,
    )
    assert delete_one.status_code == 204

    final_listing = authenticated_client.get(
        f"/api/v1/property-certificates/{certificate_id}/attachments"
    )
    last_attachment_id = final_listing.json()[0]["id"]

    delete_last = authenticated_client.delete(
        f"/api/v1/property-certificates/{certificate_id}"
        f"/attachments/{last_attachment_id}",
        headers=csrf_headers,
    )
    assert delete_last.status_code == 422
    assert delete_last.json().get("error", {}).get("code") == "VALIDATION_ERROR"
    assert "final" in delete_last.json()["error"]["message"].lower()

    # Invalid files are reported per-file without failing the whole upload.
    invalid_upload = authenticated_client.post(
        f"/api/v1/property-certificates/{certificate_id}/attachments",
        files=[
            ("files", ("bad.txt", b"not a pdf", "application/pdf")),
        ],
        headers=csrf_headers,
    )
    assert invalid_upload.status_code == 201, invalid_upload.text
    invalid_results = invalid_upload.json()["results"]
    assert "error" in invalid_results[0]

    # Unknown certificates are a 404.
    missing = authenticated_client.get(
        f"/api/v1/property-certificates/{uuid4()}/attachments"
    )
    assert missing.status_code == 404
    assert missing.json().get("error", {}).get("code") == "RESOURCE_NOT_FOUND"

def test_certificate_attachment_upload_requires_csrf_header_e2e(
    authenticated_client,
) -> None:
    """E2E Admission Standard #2: mutations need the CSRF negative branch."""
    response = authenticated_client.post(
        "/api/v1/property-certificates/91ba61d4-d180-4219-b2e0-93d5d82310ab/attachments",
        files=[("files", ("a.pdf", b"%PDF-1.4", "application/pdf"))],
    )
    assert response.status_code == 403
