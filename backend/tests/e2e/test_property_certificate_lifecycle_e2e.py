"""
End-to-end property certificate lifecycle tests (REQ-AST-005 / REQ-DOC-001).

Covers the public property-certificate CRUD surface: create with linked
assets + approved holders, list/detail round-trip, data-quality warning
derivation, global certificate-number uniqueness, update, and delete.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.e2e.factories import (
    create_approved_legal_party,
    create_scoped_asset_via_api,
)

pytestmark = pytest.mark.e2e


def _create_certificate(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    *,
    certificate_number: str,
    asset_id: str,
    holder_party_id: str,
    property_address: str,
    building_area: str = "1000.5",
    land_area: str = "500.25",
) -> dict[str, object]:
    response = authenticated_client.post(
        "/api/v1/property-certificates",
        json={
            "certificate_number": certificate_number,
            "certificate_type": "real_estate",
            "registration_date": "2020-05-01",
            "property_address": property_address,
            "building_area": building_area,
            "land_area": land_area,
            "asset_ids": [asset_id],
            "holder_party_ids": [holder_party_id],
        },
        headers=csrf_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_property_certificate_lifecycle_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """Create → list → detail → warning → update → delete."""
    suffix = uuid4().hex[:8]
    holder = create_approved_legal_party(
        db_session, suffix=suffix, name=f"权利人-{suffix}"
    )
    asset = create_scoped_asset_via_api(
        authenticated_client,
        db_session,
        suffix=suffix,
        holder_party_id=holder.id,
        csrf_headers=csrf_headers,
    )
    asset_id = asset.get("id")
    assert isinstance(asset_id, str)

    certificate_number = f"E2E-BDC-{suffix}"
    created = _create_certificate(
        authenticated_client,
        csrf_headers,
        certificate_number=certificate_number,
        asset_id=asset_id,
        holder_party_id=holder.id,
        property_address=f"E2E产权地址-{suffix}",
    )
    certificate_id = created.get("id")
    assert isinstance(certificate_id, str) and certificate_id != ""
    assert created.get("certificate_number") == certificate_number
    assert created.get("asset_ids") == [asset_id]
    assert created.get("holder_party_ids") == [holder.id]

    # Missing land-use fields on a real-estate certificate derive a warning.
    warnings = created.get("data_quality_warnings", [])
    assert isinstance(warnings, list)
    assert any(
        isinstance(w, dict) and w.get("risk_type") == "incomplete_certificate_info"
        for w in warnings
    )

    # Detail round-trip.
    detail_response = authenticated_client.get(
        f"/api/v1/property-certificates/{certificate_id}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail.get("id") == certificate_id
    assert detail.get("property_address") == f"E2E产权地址-{suffix}"

    # List contains the created certificate.
    list_response = authenticated_client.get("/api/v1/property-certificates")
    assert list_response.status_code == 200
    listed = list_response.json()
    assert isinstance(listed, list)
    assert any(item.get("id") == certificate_id for item in listed)

    # Update the address and verify it round-trips.
    update_response = authenticated_client.put(
        f"/api/v1/property-certificates/{certificate_id}",
        json={"property_address": f"E2E改址-{suffix}"},
        headers=csrf_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json().get("property_address") == f"E2E改址-{suffix}"

    updated_detail = authenticated_client.get(
        f"/api/v1/property-certificates/{certificate_id}"
    )
    assert updated_detail.status_code == 200
    assert updated_detail.json().get("property_address") == f"E2E改址-{suffix}"

    # Delete then confirm 404.
    delete_response = authenticated_client.delete(
        f"/api/v1/property-certificates/{certificate_id}",
        headers=csrf_headers,
    )
    assert delete_response.status_code == 200
    after_delete = authenticated_client.get(
        f"/api/v1/property-certificates/{certificate_id}"
    )
    assert after_delete.status_code == 404


def test_property_certificate_number_must_be_globally_unique_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """The same certificate number cannot be created twice."""
    suffix = uuid4().hex[:8]
    holder = create_approved_legal_party(
        db_session, suffix=suffix, name=f"重号权利人-{suffix}"
    )
    asset = create_scoped_asset_via_api(
        authenticated_client,
        db_session,
        suffix=suffix,
        holder_party_id=holder.id,
        csrf_headers=csrf_headers,
    )
    asset_id = asset.get("id")
    assert isinstance(asset_id, str)

    certificate_number = f"E2E-BDC-DUP-{suffix}"
    _create_certificate(
        authenticated_client,
        csrf_headers,
        certificate_number=certificate_number,
        asset_id=asset_id,
        holder_party_id=holder.id,
        property_address=f"E2E重号地址-{suffix}",
    )

    duplicate_response = authenticated_client.post(
        "/api/v1/property-certificates",
        json={
            "certificate_number": certificate_number,
            "certificate_type": "real_estate",
            "property_address": f"E2E重复地址-{suffix}",
            "asset_ids": [asset_id],
            "holder_party_ids": [holder.id],
        },
        headers=csrf_headers,
    )
    assert duplicate_response.status_code == 422
    payload = duplicate_response.json()
    assert payload.get("success") is False
    error = payload.get("error", {})
    assert isinstance(error, dict)
    field_errors = error.get("details", {}).get("field_errors", {})
    assert isinstance(field_errors, dict)
    assert "certificate_number" in field_errors


def test_property_certificate_requires_asset_and_approved_holder_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """The write gate rejects certificates without assets or holders."""
    suffix = uuid4().hex[:8]
    holder = create_approved_legal_party(
        db_session, suffix=suffix, name=f"门禁权利人-{suffix}"
    )
    asset = create_scoped_asset_via_api(
        authenticated_client,
        db_session,
        suffix=suffix,
        holder_party_id=holder.id,
        csrf_headers=csrf_headers,
    )
    asset_id = asset.get("id")
    assert isinstance(asset_id, str)

    # No assets, no holders.
    missing_both = authenticated_client.post(
        "/api/v1/property-certificates",
        json={
            "certificate_number": f"E2E-BDC-GATE-{suffix}",
            "certificate_type": "real_estate",
            "property_address": f"E2E门禁地址-{suffix}",
            "asset_ids": [],
            "holder_party_ids": [],
        },
        headers=csrf_headers,
    )
    assert missing_both.status_code == 422
    field_errors = (
        missing_both.json().get("error", {}).get("details", {}).get("field_errors", {})
    )
    assert "asset_ids" in field_errors
    assert "holder_party_ids" in field_errors

    # Assets present but no approved holder.
    missing_holder = authenticated_client.post(
        "/api/v1/property-certificates",
        json={
            "certificate_number": f"E2E-BDC-GATE2-{suffix}",
            "certificate_type": "real_estate",
            "property_address": f"E2E门禁地址2-{suffix}",
            "asset_ids": [asset_id],
            "holder_party_ids": [],
        },
        headers=csrf_headers,
    )
    assert missing_holder.status_code == 422
    field_errors = (
        missing_holder.json()
        .get("error", {})
        .get("details", {})
        .get("field_errors", {})
    )
    assert "holder_party_ids" in field_errors

    # A draft (non-approved) holder must also be rejected.
    draft_holder = create_approved_legal_party(
        db_session,
        suffix=f"{suffix}d",
        name=f"草稿权利人-{suffix}",
        review_status="draft",
    )
    draft_holder_response = authenticated_client.post(
        "/api/v1/property-certificates",
        json={
            "certificate_number": f"E2E-BDC-GATE3-{suffix}",
            "certificate_type": "real_estate",
            "property_address": f"E2E门禁地址3-{suffix}",
            "asset_ids": [asset_id],
            "holder_party_ids": [draft_holder.id],
        },
        headers=csrf_headers,
    )
    # 未过审主体被 OperationNotAllowedError 拒绝（400）
    assert draft_holder_response.status_code == 400
    payload = draft_holder_response.json()
    assert payload.get("success") is False
    error = payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "OPERATION_NOT_ALLOWED"
    assert error.get("details", {}).get("reason") == "party_review_not_approved"

def test_certificate_creation_requires_csrf_header_e2e(authenticated_client) -> None:
    """E2E Admission Standard #2: mutations need the CSRF negative branch."""
    response = authenticated_client.post(
        "/api/v1/property-certificates",
        json={"certificate_number": "E2E-CSRF"},
    )
    assert response.status_code == 403
