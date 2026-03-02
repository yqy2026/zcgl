"""Property certificate model unit tests."""

from src.models.property_certificate import (
    CertificateType,
    OwnerType,
    PropertyCertificate,
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
