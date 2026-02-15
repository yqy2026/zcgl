"""Property certificate model unit tests."""

from src.models.property_certificate import (
    CertificateType,
    OwnerType,
    PropertyCertificate,
    PropertyOwner,
    property_certificate_owners,
)


def test_property_certificate_enums() -> None:
    assert CertificateType.REAL_ESTATE == "real_estate"
    assert CertificateType.HOUSE_OWNERSHIP == "house_ownership"
    assert CertificateType.LAND_USE == "land_use"
    assert CertificateType.OTHER == "other"

    assert OwnerType.INDIVIDUAL == "individual"
    assert OwnerType.ORGANIZATION == "organization"
    assert OwnerType.JOINT == "joint"


def test_property_owner_and_certificate_creation() -> None:
    owner = PropertyOwner(owner_type=OwnerType.INDIVIDUAL, name="张三")
    certificate = PropertyCertificate(
        certificate_number="CERT-001",
        certificate_type=CertificateType.REAL_ESTATE,
    )

    assert owner.owner_type == OwnerType.INDIVIDUAL
    assert owner.name == "张三"
    assert certificate.certificate_number == "CERT-001"
    assert certificate.certificate_type == CertificateType.REAL_ESTATE


def test_property_certificate_owners_association_table() -> None:
    assert property_certificate_owners.name == "property_certificate_owners"
    assert "certificate_id" in property_certificate_owners.c
    assert "owner_id" in property_certificate_owners.c

