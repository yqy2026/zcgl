"""
End-to-end tests for property certificate import endpoints.
"""

from __future__ import annotations

import io
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.models.associations import property_cert_assets
from src.models.certificate_party_relation import (
    CertificatePartyRelation,
    CertificateRelationRole,
)
from src.models.party import Party, PartyType
from src.services.property_certificate.service import PropertyCertificateService
from tests.e2e.factories import (
    create_asset_ownership as _create_asset_ownership,
)
from tests.e2e.factories import (
    create_asset_payload as _create_asset_payload,
)

pytestmark = pytest.mark.e2e

_MINIMAL_CERT_FILE_BYTES = b"fake-property-certificate-content"


def test_property_certificate_upload_confirm_and_list_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    certificate_number = f"E2E-PC-{uuid4().hex[:8]}"
    property_address = f"E2E地址-{uuid4().hex[:8]}"

    async def fake_extract_from_file(self, file_path: str, filename: str) -> dict[str, object]:
        _ = self, file_path, filename
        return {
            "success": True,
            "data": {
                "certificate_number": certificate_number,
                "certificate_type": "other",
                "property_address": property_address,
            },
            "confidence": 0.91,
            "raw_response": {},
            "extraction_method": "mock",
            "filename": filename,
        }

    monkeypatch.setattr(
        PropertyCertificateService,
        "extract_from_file",
        fake_extract_from_file,
    )

    upload_response = authenticated_client.post(
        "/api/v1/property-certificates/upload",
        files={
            "file": (
                "certificate.pdf",
                io.BytesIO(_MINIMAL_CERT_FILE_BYTES),
                "application/pdf",
            )
        },
        headers=csrf_headers,
    )

    assert upload_response.status_code == 200
    upload_payload = upload_response.json()
    session_id = upload_payload.get("session_id")
    assert isinstance(session_id, str)
    assert session_id.strip() != ""
    assert upload_payload.get("certificate_type") == "property_cert"
    extracted_data = upload_payload.get("extracted_data", {})
    assert isinstance(extracted_data, dict)
    assert extracted_data.get("certificate_number") == certificate_number
    assert extracted_data.get("property_address") == property_address

    confirm_response = authenticated_client.post(
        "/api/v1/property-certificates/confirm-import",
        json={
            "session_id": session_id,
            "extracted_data": extracted_data,
            "asset_ids": [],
            "asset_link_id": None,
            "should_create_new_asset": True,
            "owners": [],
        },
        headers=csrf_headers,
    )

    assert confirm_response.status_code == 200
    confirm_payload = confirm_response.json()
    assert confirm_payload.get("status") == "success"
    certificate_id = confirm_payload.get("certificate_id")
    assert isinstance(certificate_id, str)
    assert certificate_id.strip() != ""

    detail_response = authenticated_client.get(
        f"/api/v1/property-certificates/{certificate_id}",
        headers=csrf_headers,
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload.get("id") == certificate_id
    assert detail_payload.get("certificate_number") == certificate_number
    assert detail_payload.get("property_address") == property_address

    list_response = authenticated_client.get(
        "/api/v1/property-certificates/",
        headers=csrf_headers,
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert isinstance(list_payload, list)
    assert any(item.get("id") == certificate_id for item in list_payload)


def test_property_certificate_confirm_import_is_idempotent_by_certificate_number_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    certificate_number = f"E2E-PC-IDEMPOTENT-{uuid4().hex[:8]}"
    confirm_body = {
        "session_id": f"session-{uuid4().hex[:12]}",
        "extracted_data": {
            "certificate_number": certificate_number,
            "certificate_type": "other",
            "property_address": f"E2E地址-{uuid4().hex[:8]}",
        },
        "asset_ids": [],
        "asset_link_id": None,
        "should_create_new_asset": True,
        "owners": [],
    }

    first_confirm = authenticated_client.post(
        "/api/v1/property-certificates/confirm-import",
        json=confirm_body,
        headers=csrf_headers,
    )
    second_confirm = authenticated_client.post(
        "/api/v1/property-certificates/confirm-import",
        json=confirm_body,
        headers=csrf_headers,
    )

    assert first_confirm.status_code == 200
    assert second_confirm.status_code == 200
    first_payload = first_confirm.json()
    second_payload = second_confirm.json()
    assert first_payload.get("status") == "success"
    assert second_payload.get("status") == "success"
    assert first_payload.get("certificate_id") == second_payload.get("certificate_id")

    list_response = authenticated_client.get(
        "/api/v1/property-certificates/",
        headers=csrf_headers,
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert isinstance(list_payload, list)
    matched_items = [
        item for item in list_payload if item.get("certificate_number") == certificate_number
    ]
    assert len(matched_items) == 1


def test_property_certificate_upload_rejects_oversized_file_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    oversized_file_bytes = b"1" * ((10 * 1024 * 1024) + 1)
    response = authenticated_client.post(
        "/api/v1/property-certificates/upload",
        files={
            "file": (
                "oversized-certificate.pdf",
                io.BytesIO(oversized_file_bytes),
                "application/pdf",
            )
        },
        headers=csrf_headers,
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload.get("success") is False
    assert payload.get("message") == "文件大小超过限制 (10MB)"
    error = payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "HTTP_400"
    assert error.get("message") == "文件大小超过限制 (10MB)"


def test_property_certificate_upload_rejects_unsupported_extension_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    response = authenticated_client.post(
        "/api/v1/property-certificates/upload",
        files={
            "file": (
                "invalid-certificate.txt",
                io.BytesIO(b"not-a-certificate-file"),
                "text/plain",
            )
        },
        headers=csrf_headers,
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload.get("success") is False
    message = str(payload.get("message", ""))
    assert "不支持的文件类型" in message
    error = payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "HTTP_400"


def test_property_certificate_confirm_import_rejects_blank_certificate_number_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    response = authenticated_client.post(
        "/api/v1/property-certificates/confirm-import",
        json={
            "session_id": f"session-{uuid4().hex[:12]}",
            "extracted_data": {
                "certificate_number": "   ",
                "certificate_type": "other",
                "property_address": f"E2E地址-{uuid4().hex[:8]}",
            },
            "asset_ids": [],
            "asset_link_id": None,
            "should_create_new_asset": True,
            "owners": [],
        },
        headers=csrf_headers,
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload.get("success") is False
    error = payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "VALIDATION_ERROR"
    details = error.get("details", {})
    assert isinstance(details, dict)
    field_errors = details.get("field_errors", {})
    assert isinstance(field_errors, dict)
    certificate_errors = field_errors.get("certificate_number")
    assert isinstance(certificate_errors, list)
    assert any("缺少证书编号" in str(item) for item in certificate_errors)


def test_property_certificate_confirm_import_ignores_asset_links_when_create_new_asset_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_asset_ownership(db_session, suffix)
    asset_payload = _create_asset_payload(
        suffix=f"{suffix}-pc-link",
        ownership_id=ownership.id,
    )

    create_asset_response = authenticated_client.post(
        "/api/v1/assets",
        json=asset_payload,
        headers=csrf_headers,
    )
    assert create_asset_response.status_code == 201
    created_asset_id = create_asset_response.json().get("id")
    assert isinstance(created_asset_id, str)
    assert created_asset_id.strip() != ""

    certificate_number = f"E2E-PC-CREATE-NEW-{uuid4().hex[:8]}"
    confirm_response = authenticated_client.post(
        "/api/v1/property-certificates/confirm-import",
        json={
            "session_id": f"session-{uuid4().hex[:12]}",
            "extracted_data": {
                "certificate_number": certificate_number,
                "certificate_type": "other",
                "property_address": f"E2E地址-{uuid4().hex[:8]}",
            },
            "asset_ids": [created_asset_id],
            "asset_link_id": created_asset_id,
            "should_create_new_asset": True,
            "owners": [],
        },
        headers=csrf_headers,
    )
    assert confirm_response.status_code == 200
    confirm_payload = confirm_response.json()
    assert confirm_payload.get("status") == "success"
    certificate_id = confirm_payload.get("certificate_id")
    assert isinstance(certificate_id, str)
    assert certificate_id.strip() != ""

    linked_asset_rows = db_session.execute(
        select(property_cert_assets.c.asset_id).where(
            property_cert_assets.c.certificate_id == certificate_id
        )
    ).scalars()
    linked_asset_ids = {str(asset_id) for asset_id in linked_asset_rows}
    assert created_asset_id not in linked_asset_ids


def test_property_certificate_confirm_import_links_asset_when_existing_asset_selected_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_asset_ownership(db_session, suffix)
    asset_payload = _create_asset_payload(
        suffix=f"{suffix}-pc-link-existing",
        ownership_id=ownership.id,
    )

    create_asset_response = authenticated_client.post(
        "/api/v1/assets",
        json=asset_payload,
        headers=csrf_headers,
    )
    assert create_asset_response.status_code == 201
    created_asset_id = create_asset_response.json().get("id")
    assert isinstance(created_asset_id, str)
    assert created_asset_id.strip() != ""

    certificate_number = f"E2E-PC-LINK-ASSET-{uuid4().hex[:8]}"
    confirm_response = authenticated_client.post(
        "/api/v1/property-certificates/confirm-import",
        json={
            "session_id": f"session-{uuid4().hex[:12]}",
            "extracted_data": {
                "certificate_number": certificate_number,
                "certificate_type": "other",
                "property_address": f"E2E地址-{uuid4().hex[:8]}",
            },
            "asset_ids": [],
            "asset_link_id": created_asset_id,
            "should_create_new_asset": False,
            "owners": [],
        },
        headers=csrf_headers,
    )
    assert confirm_response.status_code == 200
    confirm_payload = confirm_response.json()
    assert confirm_payload.get("status") == "success"
    certificate_id = confirm_payload.get("certificate_id")
    assert isinstance(certificate_id, str)
    assert certificate_id.strip() != ""

    linked_asset_rows = db_session.execute(
        select(property_cert_assets.c.asset_id).where(
            property_cert_assets.c.certificate_id == certificate_id
        )
    ).scalars()
    linked_asset_ids = {str(asset_id) for asset_id in linked_asset_rows}
    assert created_asset_id in linked_asset_ids


def test_property_certificate_confirm_import_trims_asset_link_id_before_linking_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    ownership = _create_asset_ownership(db_session, suffix)
    asset_payload = _create_asset_payload(
        suffix=f"{suffix}-pc-link-trimmed",
        ownership_id=ownership.id,
    )

    create_asset_response = authenticated_client.post(
        "/api/v1/assets",
        json=asset_payload,
        headers=csrf_headers,
    )
    assert create_asset_response.status_code == 201
    created_asset_id = create_asset_response.json().get("id")
    assert isinstance(created_asset_id, str)
    assert created_asset_id.strip() != ""

    certificate_number = f"E2E-PC-LINK-ASSET-TRIM-{uuid4().hex[:8]}"
    confirm_response = authenticated_client.post(
        "/api/v1/property-certificates/confirm-import",
        json={
            "session_id": f"session-{uuid4().hex[:12]}",
            "extracted_data": {
                "certificate_number": certificate_number,
                "certificate_type": "other",
                "property_address": f"E2E地址-{uuid4().hex[:8]}",
            },
            "asset_ids": [],
            "asset_link_id": f"  {created_asset_id}  ",
            "should_create_new_asset": False,
            "owners": [],
        },
        headers=csrf_headers,
    )
    assert confirm_response.status_code == 200
    confirm_payload = confirm_response.json()
    assert confirm_payload.get("status") == "success"
    certificate_id = confirm_payload.get("certificate_id")
    assert isinstance(certificate_id, str)
    assert certificate_id.strip() != ""

    linked_asset_rows = db_session.execute(
        select(property_cert_assets.c.asset_id).where(
            property_cert_assets.c.certificate_id == certificate_id
        )
    ).scalars()
    linked_asset_ids = {str(asset_id) for asset_id in linked_asset_rows}
    assert linked_asset_ids == {created_asset_id}


def test_property_certificate_confirm_import_maps_owner_parties_with_single_primary_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    owner_party_primary = Party(
        party_type=PartyType.LEGAL_ENTITY.value,
        name=f"E2E权利主体A-{suffix}",
        code=f"E2E-OWNER-A-{suffix}",
        external_ref=f"owner-a-{suffix}",
        status="active",
    )
    owner_party_secondary = Party(
        party_type=PartyType.LEGAL_ENTITY.value,
        name=f"E2E权利主体B-{suffix}",
        code=f"E2E-OWNER-B-{suffix}",
        external_ref=f"owner-b-{suffix}",
        status="active",
    )
    db_session.add(owner_party_primary)
    db_session.add(owner_party_secondary)
    db_session.commit()
    db_session.refresh(owner_party_primary)
    db_session.refresh(owner_party_secondary)

    certificate_number = f"E2E-PC-OWNERS-{uuid4().hex[:8]}"
    confirm_response = authenticated_client.post(
        "/api/v1/property-certificates/confirm-import",
        json={
            "session_id": f"session-{uuid4().hex[:12]}",
            "extracted_data": {
                "certificate_number": certificate_number,
                "certificate_type": "other",
                "property_address": f"E2E地址-{uuid4().hex[:8]}",
            },
            "asset_ids": [],
            "asset_link_id": None,
            "should_create_new_asset": True,
            "owners": [
                {"party_id": "   "},
                {"party_id": owner_party_primary.id},
                {"party_id": owner_party_secondary.id},
            ],
        },
        headers=csrf_headers,
    )
    assert confirm_response.status_code == 200
    confirm_payload = confirm_response.json()
    assert confirm_payload.get("status") == "success"
    certificate_id = confirm_payload.get("certificate_id")
    assert isinstance(certificate_id, str)
    assert certificate_id.strip() != ""

    owner_relations = db_session.execute(
        select(CertificatePartyRelation).where(
            CertificatePartyRelation.certificate_id == certificate_id,
            CertificatePartyRelation.relation_role == CertificateRelationRole.OWNER,
        )
    ).scalars()
    owner_relation_list = list(owner_relations)
    assert len(owner_relation_list) == 2

    owner_party_ids = {relation.party_id for relation in owner_relation_list}
    assert owner_party_primary.id in owner_party_ids
    assert owner_party_secondary.id in owner_party_ids

    primary_relations = [relation for relation in owner_relation_list if relation.is_primary]
    assert len(primary_relations) == 1
    assert primary_relations[0].party_id == owner_party_primary.id


def test_property_certificate_confirm_import_keeps_existing_relations_on_retry_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    suffix = uuid4().hex[:8]
    owner_party_initial = Party(
        party_type=PartyType.LEGAL_ENTITY.value,
        name=f"E2E初始权利主体-{suffix}",
        code=f"E2E-OWNER-INITIAL-{suffix}",
        external_ref=f"owner-initial-{suffix}",
        status="active",
    )
    owner_party_retry = Party(
        party_type=PartyType.LEGAL_ENTITY.value,
        name=f"E2E重试权利主体-{suffix}",
        code=f"E2E-OWNER-RETRY-{suffix}",
        external_ref=f"owner-retry-{suffix}",
        status="active",
    )
    db_session.add(owner_party_initial)
    db_session.add(owner_party_retry)
    db_session.commit()
    db_session.refresh(owner_party_initial)
    db_session.refresh(owner_party_retry)

    ownership = _create_asset_ownership(db_session, suffix)
    asset_payload = _create_asset_payload(
        suffix=f"{suffix}-retry-link",
        ownership_id=ownership.id,
    )
    create_asset_response = authenticated_client.post(
        "/api/v1/assets",
        json=asset_payload,
        headers=csrf_headers,
    )
    assert create_asset_response.status_code == 201
    created_asset_id = create_asset_response.json().get("id")
    assert isinstance(created_asset_id, str)
    assert created_asset_id.strip() != ""

    certificate_number = f"E2E-PC-RETRY-KEEP-{uuid4().hex[:8]}"
    first_confirm = authenticated_client.post(
        "/api/v1/property-certificates/confirm-import",
        json={
            "session_id": f"session-{uuid4().hex[:12]}",
            "extracted_data": {
                "certificate_number": certificate_number,
                "certificate_type": "other",
                "property_address": f"E2E地址-{uuid4().hex[:8]}",
            },
            "asset_ids": [],
            "asset_link_id": None,
            "should_create_new_asset": True,
            "owners": [{"party_id": owner_party_initial.id}],
        },
        headers=csrf_headers,
    )
    assert first_confirm.status_code == 200
    first_payload = first_confirm.json()
    first_certificate_id = first_payload.get("certificate_id")
    assert isinstance(first_certificate_id, str)
    assert first_certificate_id.strip() != ""

    second_confirm = authenticated_client.post(
        "/api/v1/property-certificates/confirm-import",
        json={
            "session_id": f"session-{uuid4().hex[:12]}",
            "extracted_data": {
                "certificate_number": certificate_number,
                "certificate_type": "other",
                "property_address": f"E2E地址-重试-{uuid4().hex[:8]}",
            },
            "asset_ids": [],
            "asset_link_id": created_asset_id,
            "should_create_new_asset": False,
            "owners": [{"party_id": owner_party_retry.id}],
        },
        headers=csrf_headers,
    )
    assert second_confirm.status_code == 200
    second_payload = second_confirm.json()
    second_certificate_id = second_payload.get("certificate_id")
    assert second_certificate_id == first_certificate_id

    owner_relations = db_session.execute(
        select(CertificatePartyRelation).where(
            CertificatePartyRelation.certificate_id == first_certificate_id,
            CertificatePartyRelation.relation_role == CertificateRelationRole.OWNER,
        )
    ).scalars()
    owner_relation_list = list(owner_relations)
    assert len(owner_relation_list) == 1
    assert owner_relation_list[0].party_id == owner_party_initial.id
    assert owner_relation_list[0].is_primary is True

    linked_asset_rows = db_session.execute(
        select(property_cert_assets.c.asset_id).where(
            property_cert_assets.c.certificate_id == first_certificate_id
        )
    ).scalars()
    linked_asset_ids = {str(asset_id) for asset_id in linked_asset_rows}
    assert linked_asset_ids == set()


def test_property_certificate_confirm_import_parses_mixed_date_formats_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    certificate_number = f"E2E-PC-DATE-FORMATS-{uuid4().hex[:8]}"
    confirm_response = authenticated_client.post(
        "/api/v1/property-certificates/confirm-import",
        json={
            "session_id": f"session-{uuid4().hex[:12]}",
            "extracted_data": {
                "certificate_number": certificate_number,
                "certificate_type": "other",
                "property_address": f"E2E日期地址-{uuid4().hex[:8]}",
                "registration_date": "2026/03/04",
                "land_use_term_start": "2026年01月01日",
                "land_use_term_end": "2026-12-31",
            },
            "asset_ids": [],
            "asset_link_id": None,
            "should_create_new_asset": True,
            "owners": [],
        },
        headers=csrf_headers,
    )

    assert confirm_response.status_code == 200
    confirm_payload = confirm_response.json()
    assert confirm_payload.get("status") == "success"
    certificate_id = confirm_payload.get("certificate_id")
    assert isinstance(certificate_id, str)
    assert certificate_id.strip() != ""

    detail_response = authenticated_client.get(
        f"/api/v1/property-certificates/{certificate_id}",
        headers=csrf_headers,
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload.get("registration_date") == "2026-03-04"
    assert detail_payload.get("land_use_term_start") == "2026-01-01"
    assert detail_payload.get("land_use_term_end") == "2026-12-31"


def test_property_certificate_confirm_import_rejects_invalid_date_format_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    response = authenticated_client.post(
        "/api/v1/property-certificates/confirm-import",
        json={
            "session_id": f"session-{uuid4().hex[:12]}",
            "extracted_data": {
                "certificate_number": f"E2E-PC-INVALID-DATE-{uuid4().hex[:8]}",
                "certificate_type": "other",
                "property_address": f"E2E日期异常地址-{uuid4().hex[:8]}",
                "registration_date": "2026-13-01",
            },
            "asset_ids": [],
            "asset_link_id": None,
            "should_create_new_asset": True,
            "owners": [],
        },
        headers=csrf_headers,
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload.get("success") is False
    error = payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "VALIDATION_ERROR"
    details = error.get("details", {})
    assert isinstance(details, dict)
    field_errors = details.get("field_errors", {})
    assert isinstance(field_errors, dict)
    registration_date_errors = field_errors.get("registration_date")
    assert isinstance(registration_date_errors, list)
    assert any("日期格式无效" in str(item) for item in registration_date_errors)


def test_property_certificate_confirm_import_is_idempotent_across_sessions_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    certificate_number = f"E2E-PC-RETRY-{uuid4().hex[:8]}"
    extracted_data = {
        "certificate_number": certificate_number,
        "certificate_type": "other",
        "property_address": f"E2E地址-{uuid4().hex[:8]}",
    }

    first_confirm = authenticated_client.post(
        "/api/v1/property-certificates/confirm-import",
        json={
            "session_id": f"session-{uuid4().hex[:12]}",
            "extracted_data": extracted_data,
            "asset_ids": [],
            "asset_link_id": None,
            "should_create_new_asset": True,
            "owners": [],
        },
        headers=csrf_headers,
    )
    second_confirm = authenticated_client.post(
        "/api/v1/property-certificates/confirm-import",
        json={
            "session_id": f"session-{uuid4().hex[:12]}",
            "extracted_data": extracted_data,
            "asset_ids": [],
            "asset_link_id": None,
            "should_create_new_asset": True,
            "owners": [],
        },
        headers=csrf_headers,
    )

    assert first_confirm.status_code == 200
    assert second_confirm.status_code == 200
    first_payload = first_confirm.json()
    second_payload = second_confirm.json()
    assert first_payload.get("status") == "success"
    assert second_payload.get("status") == "success"
    assert first_payload.get("certificate_id") == second_payload.get("certificate_id")


def test_property_certificate_upload_can_retry_after_oversized_rejection_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oversized_file_bytes = b"1" * ((10 * 1024 * 1024) + 1)
    failed_response = authenticated_client.post(
        "/api/v1/property-certificates/upload",
        files={
            "file": (
                "oversized-certificate.pdf",
                io.BytesIO(oversized_file_bytes),
                "application/pdf",
            )
        },
        headers=csrf_headers,
    )
    assert failed_response.status_code == 400

    certificate_number = f"E2E-PC-RECOVERY-{uuid4().hex[:8]}"

    async def fake_extract_from_file(self, file_path: str, filename: str) -> dict[str, object]:
        _ = self, file_path, filename
        return {
            "success": True,
            "data": {
                "certificate_number": certificate_number,
                "certificate_type": "other",
                "property_address": f"E2E地址-{uuid4().hex[:8]}",
            },
            "confidence": 0.88,
            "raw_response": {},
            "extraction_method": "mock",
            "filename": filename,
        }

    monkeypatch.setattr(
        PropertyCertificateService,
        "extract_from_file",
        fake_extract_from_file,
    )

    success_response = authenticated_client.post(
        "/api/v1/property-certificates/upload",
        files={
            "file": (
                "certificate.pdf",
                io.BytesIO(_MINIMAL_CERT_FILE_BYTES),
                "application/pdf",
            )
        },
        headers=csrf_headers,
    )

    assert success_response.status_code == 200
    success_payload = success_response.json()
    session_id = success_payload.get("session_id")
    assert isinstance(session_id, str)
    assert session_id.strip() != ""
    extracted_data = success_payload.get("extracted_data", {})
    assert isinstance(extracted_data, dict)
    assert extracted_data.get("certificate_number") == certificate_number


def test_property_certificate_confirm_import_remains_single_record_after_rapid_retries_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    certificate_number = f"E2E-PC-RAPID-{uuid4().hex[:8]}"
    extracted_data = {
        "certificate_number": certificate_number,
        "certificate_type": "other",
        "property_address": f"E2E地址-{uuid4().hex[:8]}",
    }

    certificate_ids: list[str] = []
    for _ in range(5):
        response = authenticated_client.post(
            "/api/v1/property-certificates/confirm-import",
            json={
                "session_id": f"session-{uuid4().hex[:12]}",
                "extracted_data": extracted_data,
                "asset_ids": [],
                "asset_link_id": None,
                "should_create_new_asset": True,
                "owners": [],
            },
            headers=csrf_headers,
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("status") == "success"
        certificate_id = payload.get("certificate_id")
        assert isinstance(certificate_id, str)
        assert certificate_id.strip() != ""
        certificate_ids.append(certificate_id)

    assert len(set(certificate_ids)) == 1

    list_response = authenticated_client.get(
        "/api/v1/property-certificates/",
        headers=csrf_headers,
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert isinstance(list_payload, list)
    matched_items = [
        item for item in list_payload if item.get("certificate_number") == certificate_number
    ]
    assert len(matched_items) == 1
