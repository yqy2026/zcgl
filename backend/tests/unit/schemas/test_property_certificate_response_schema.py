"""
Unit tests for property certificate response schema contract.
"""

from datetime import UTC, datetime
from types import SimpleNamespace

from src.schemas.property_certificate import (
    PropertyCertificateAttachmentResponse,
    PropertyCertificateResponse,
)


def test_property_certificate_response_schema_includes_owners_field() -> None:
    properties = PropertyCertificateResponse.model_json_schema().get("properties", {})
    assert "owners" in properties
    assert "attachments" in properties


def test_property_certificate_response_serializes_owner_list_from_attributes() -> None:
    owner = SimpleNamespace(
        id="owner-001",
        owner_type="individual",
        name="测试权利人",
        id_type="身份证",
        id_number="110101199001011234",
        phone="13800000000",
        address="测试地址",
        organization_id=None,
        asset_ids=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    certificate = SimpleNamespace(
        id="cert-001",
        certificate_number="CERT-001",
        certificate_type="real_estate",
        registration_date=None,
        property_address="测试地址",
        property_type=None,
        building_area=None,
        floor_info=None,
        land_area=None,
        land_use_type=None,
        land_use_term_start=None,
        land_use_term_end=None,
        co_ownership=None,
        restrictions=None,
        remarks=None,
        organization_id=None,
        asset_ids=[],
        extraction_confidence=None,
        extraction_source="manual",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        created_by="user-001",
        owners=[owner],
        attachments=[
            SimpleNamespace(
                id="att-001",
                file_name="cert.pdf",
                storage_key="property-certs/cert.pdf",
                content_type="application/pdf",
                file_size=1024,
                created_at=datetime.now(UTC),
            )
        ],
    )

    response = PropertyCertificateResponse.model_validate(certificate)
    dumped = response.model_dump()

    assert "owners" in dumped
    assert isinstance(dumped["owners"], list)
    assert dumped["owners"][0]["id"] == "owner-001"
    assert dumped["attachments"][0]["storage_key"] == "property-certs/cert.pdf"


def test_property_certificate_attachment_response_schema() -> None:
    attachment = PropertyCertificateAttachmentResponse.model_validate(
        SimpleNamespace(
            id="att-001",
            file_name="cert.pdf",
            storage_key="property-certs/cert.pdf",
            content_type="application/pdf",
            file_size=1024,
            created_at=datetime.now(UTC),
        )
    )

    assert attachment.id == "att-001"
    assert attachment.file_name == "cert.pdf"
