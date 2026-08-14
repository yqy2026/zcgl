"""Property certificate model unit tests."""

from src.models.property_certificate import CertificateType, PropertyCertificate


def test_property_certificate_enums() -> None:
    assert CertificateType.REAL_ESTATE == "real_estate"
    assert CertificateType.HOUSE_OWNERSHIP == "house_ownership"
    assert CertificateType.LAND_USE == "land_use"
    assert CertificateType.OTHER == "other"


def test_property_certificate_creation() -> None:
    certificate = PropertyCertificate(
        certificate_number="CERT-001",
        certificate_type=CertificateType.REAL_ESTATE,
    )

    assert certificate.certificate_number == "CERT-001"
    assert certificate.certificate_type == CertificateType.REAL_ESTATE


def test_certificate_type_column_is_plain_string_not_pg_enum() -> None:
    """certificate_type 列必须是 String(50)，而不是 SQLAlchemy 原生枚举。

    回归（2026-08-14 验收 D10）：model 曾声明 SQLEnum(CertificateType)（PG 原生枚举），
    而全部迁移中该列均为 String，数据库无 certificatetype 类型，完整合法输入的 INSERT
    必炸（UndefinedObjectError: type certificatetype does not exist）。列类型必须与
    迁移/契约一致；Python 枚举仅作校验。
    """
    from sqlalchemy import Enum as SQLEnum
    from sqlalchemy import String

    column = PropertyCertificate.__table__.c.certificate_type
    assert isinstance(column.type, String)
    assert column.type.length == 50
    assert not isinstance(column.type, SQLEnum)
