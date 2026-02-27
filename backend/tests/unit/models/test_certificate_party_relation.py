"""Certificate-party relation model unit tests."""

from src.models.certificate_party_relation import (
    CertificatePartyRelation,
    CertificateRelationRole,
)


def test_certificate_relation_role_enum_uses_lowercase_values() -> None:
    relation_role_type = CertificatePartyRelation.__table__.c.relation_role.type

    assert relation_role_type.enums == [
        member.value for member in CertificateRelationRole
    ]
