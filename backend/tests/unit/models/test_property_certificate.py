"""Property certificate model unit tests."""

from src.models.property_certificate import (
    CertificateType,
    OwnerType,
    PropertyCertificate,
    PropertyCertificateAttachment,
)


def test_property_certificate_enums() -> None:
    assert CertificateType.REAL_ESTATE == "real_estate"
    assert CertificateType.HOUSE_OWNERSHIP == "house_ownership"
    assert CertificateType.LAND_USE == "land_use"
    assert CertificateType.OTHER == "other"

    assert OwnerType.INDIVIDUAL == "individual"
    assert OwnerType.ORGANIZATION == "organization"
    assert OwnerType.JOINT == "joint"


def test_property_certificate_creation() -> None:
    certificate = PropertyCertificate(
        certificate_number="CERT-001",
        certificate_type=CertificateType.REAL_ESTATE,
    )

    assert certificate.certificate_number == "CERT-001"
    assert certificate.certificate_type == CertificateType.REAL_ESTATE


def test_property_certificate_attachment_creation() -> None:
    attachment = PropertyCertificateAttachment(
        certificate_id="cert-001",
        file_name="cert.pdf",
        storage_key="property-certs/cert.pdf",
        content_type="application/pdf",
        file_size=2048,
    )

    assert attachment.certificate_id == "cert-001"
    assert attachment.file_name == "cert.pdf"
    assert attachment.storage_key == "property-certs/cert.pdf"
