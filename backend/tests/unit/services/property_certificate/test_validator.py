from src.models.property_certificate import CertificateType
from src.services.property_certificate.validator import PropertyCertificateValidator


def test_validate_real_estate_cert_success():
    """测试验证不动产权证成功"""
    data = {
        "certificate_number": "京房权证朝字第12345号",
        "property_address": "北京市朝阳区建国路123号",
        "registration_date": "2020-01-15"
    }
    result = PropertyCertificateValidator.validate_extracted_fields(
        data, CertificateType.REAL_ESTATE
    )

    assert result.is_valid()
    assert len(result.errors) == 0


def test_validate_missing_required_field():
    """测试必填字段缺失"""
    data = {
        "certificate_number": "TEST001"
        # Missing property_address
    }
    result = PropertyCertificateValidator.validate_extracted_fields(
        data, CertificateType.REAL_ESTATE
    )

    assert not result.is_valid()
    assert "必填字段缺失: property_address" in result.errors


def test_validate_invalid_certificate_number():
    """测试无效证书编号"""
    data = {
        "certificate_number": "AB",  # Too short
        "property_address": "Test"
    }
    result = PropertyCertificateValidator.validate_extracted_fields(
        data, CertificateType.REAL_ESTATE
    )

    assert not result.is_valid()
    assert "证书编号格式不正确" in result.errors


def test_validate_date_logic_error():
    """测试日期逻辑错误"""
    data = {
        "certificate_number": "TEST001",
        "property_address": "Test",
        "land_use_term_start": "2025-01-01",
        "land_use_term_end": "2024-01-01"  # End before start!
    }
    result = PropertyCertificateValidator.validate_extracted_fields(
        data, CertificateType.REAL_ESTATE
    )

    assert not result.is_valid()
    assert "土地使用终止日期必须晚于起始日期" in result.errors
