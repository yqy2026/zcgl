"""Tests for property certificate extraction preview validator."""

from src.models.property_certificate import CertificateType
from src.services.property_certificate.validator import PropertyCertificateValidator


def test_validate_extracted_fields_reports_preview_errors() -> None:
    result = PropertyCertificateValidator.validate_extracted_fields(
        {"certificate_number": "AB"},
        CertificateType.REAL_ESTATE,
    )

    assert not result.is_valid()
    assert "必填字段缺失: property_address" in result.errors
    assert "证书编号格式不正确" in result.errors


def test_validate_extracted_fields_keeps_area_as_warning() -> None:
    result = PropertyCertificateValidator.validate_extracted_fields(
        {
            "certificate_number": "CERT-001",
            "property_address": "Building 1",
            "building_area": "not-a-number",
        },
        CertificateType.REAL_ESTATE,
    )

    assert result.is_valid()
    assert "building_area 格式可能不正确" in result.warnings
