"""
Property Certificate Model Unit Tests
"""

import pytest
from datetime import date

from src.models.property_certificate import PropertyCertificate, CertificateType


def test_create_property_certificate(db_session):
    """测试创建产权证"""
    cert = PropertyCertificate(
        certificate_number="京房权证朝字第12345号",
        certificate_type=CertificateType.REAL_ESTATE,
        registration_date=date(2020, 1, 15),
        property_address="北京市朝阳区建国路123号",
        property_type="住宅"
    )
    db_session.add(cert)
    db_session.commit()

    assert cert.id is not None
    assert cert.certificate_number == "京房权证朝字第12345号"
    assert cert.certificate_type == CertificateType.REAL_ESTATE


def test_certificate_unique_number(db_session):
    """测试证书编号唯一性"""
    cert1 = PropertyCertificate(
        certificate_number="TEST001",
        certificate_type=CertificateType.OTHER
    )
    db_session.add(cert1)
    db_session.commit()

    cert2 = PropertyCertificate(
        certificate_number="TEST001",  # Duplicate!
        certificate_type=CertificateType.OTHER
    )
    db_session.add(cert2)

    with pytest.raises(Exception):  # IntegrityError
        db_session.commit()
