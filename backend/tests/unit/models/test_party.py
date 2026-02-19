"""Party model unit tests."""

from src.models.party import Party, PartyContact, PartyHierarchy, PartyType


def test_party_type_enum_values() -> None:
    assert PartyType.ORGANIZATION.value == "organization"
    assert PartyType.LEGAL_ENTITY.value == "legal_entity"


def test_party_model_creation_and_repr() -> None:
    party = Party(party_type=PartyType.ORGANIZATION, name="总部", code="HQ")

    assert party.party_type == PartyType.ORGANIZATION
    assert party.name == "总部"
    assert party.code == "HQ"
    assert "HQ" in repr(party)


def test_party_unique_constraint_exists() -> None:
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in Party.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }

    assert ("party_type", "code") in unique_columns


def test_party_hierarchy_constraints_exist() -> None:
    check_constraints = [
        str(constraint.sqltext)
        for constraint in PartyHierarchy.__table__.constraints
        if constraint.__class__.__name__ == "CheckConstraint"
    ]

    assert any("parent_party_id" in text and "child_party_id" in text for text in check_constraints)


def test_party_contact_creation() -> None:
    contact = PartyContact(
        party_id="party-1",
        contact_name="张三",
        contact_phone="13800000000",
        is_primary=True,
    )

    assert contact.party_id == "party-1"
    assert contact.contact_name == "张三"
    assert contact.is_primary is True
