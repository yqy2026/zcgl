"""Party model unit tests for the ADR-0022 cutover."""

import src.models.party as party_model
from src.models.party import Party, PartyContact, PartyType


def _check_constraint_sql(model: type[object]) -> dict[str, str]:
    return {
        str(constraint.name): str(constraint.sqltext)
        for constraint in model.__table__.constraints  # type: ignore[attr-defined]
        if constraint.__class__.__name__ == "CheckConstraint"
    }


def test_party_type_contains_only_legal_entities_and_individuals() -> None:
    assert {item.value for item in PartyType} == {"legal_entity", "individual"}


def test_party_model_exposes_formal_identifier_storage() -> None:
    columns = Party.__table__.columns

    assert columns["identifier_type"].nullable is True
    assert columns["identifier_value"].nullable is True
    assert columns["identifier_fingerprint"].nullable is True


def test_party_constraints_encode_type_code_and_identifier_invariants() -> None:
    checks = _check_constraint_sql(Party)

    assert set(checks) >= {
        "ck_parties_party_type",
        "ck_parties_status",
        "ck_parties_code_format",
        "ck_parties_identifier_pair",
        "ck_parties_identifier_type",
        "ck_parties_identifier_fingerprint",
        "ck_parties_metadata_object",
    }
    assert "legal_entity" in checks["ck_parties_party_type"]
    assert "individual" in checks["ck_parties_party_type"]
    assert "LE-" in checks["ck_parties_code_format"]
    assert "NP-" in checks["ck_parties_code_format"]
    assert (
        "identifier_type IS NOT NULL AND party_type = 'individual'"
        in checks["ck_parties_identifier_fingerprint"]
    )


def test_party_code_and_identifier_uniqueness_are_database_enforced() -> None:
    unique_constraints = {
        str(constraint.name): tuple(column.name for column in constraint.columns)
        for constraint in Party.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    indexes = {index.name: index for index in Party.__table__.indexes}

    assert unique_constraints["uq_parties_code"] == ("code",)
    assert tuple(
        column.name for column in indexes["uq_parties_legal_identifier"].columns
    ) == ("identifier_type", "identifier_value")
    assert indexes["uq_parties_legal_identifier"].unique is True
    assert tuple(
        column.name
        for column in indexes["uq_parties_individual_identifier_fingerprint"].columns
    ) == ("identifier_type", "identifier_fingerprint")
    assert indexes["uq_parties_individual_identifier_fingerprint"].unique is True


def test_party_metadata_json_must_use_none_as_null() -> None:
    """metadata_json 的 JSONB 必须 none_as_null=True。

    回归（2026-08-14 验收）：默认 none_as_null=False 会把 Python None 编码为 JSON
    'null' 而非 SQL NULL，违反 ck_parties_metadata_object（jsonb_typeof(metadata)
    必须为 'object' 或 NULL），导致无 metadata 的主体创建主路径 500（REQ-PTY-001）。
    """
    column = Party.__table__.columns["metadata"]

    assert column.type.none_as_null is True


def test_party_hierarchy_is_not_part_of_the_model_contract() -> None:
    assert "PartyHierarchy" not in party_model.__all__
    assert not hasattr(party_model, "PartyHierarchy")
    assert "parent_links" not in Party.__mapper__.relationships
    assert "child_links" not in Party.__mapper__.relationships


def test_party_model_creation_and_repr() -> None:
    party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name="Legal Entity",
        code="LE-000001",
        identifier_type="unified_social_credit_code",
        identifier_value="91440101231229726P",
    )

    assert party.party_type == PartyType.LEGAL_ENTITY
    assert party.identifier_value == "91440101231229726P"
    assert "LE-000001" in repr(party)


def test_party_contact_creation() -> None:
    contact = PartyContact(
        party_id="party-1",
        contact_name="Primary Contact",
        contact_phone="13800000000",
        is_primary=True,
    )

    assert contact.party_id == "party-1"
    assert contact.contact_name == "Primary Contact"
    assert contact.is_primary is True
