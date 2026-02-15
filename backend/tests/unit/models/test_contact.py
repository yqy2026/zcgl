"""Contact model unit tests."""

from src.models.contact import Contact, ContactType


def test_contact_type_enum_values() -> None:
    assert ContactType.PRIMARY == "primary"
    assert ContactType.FINANCE == "finance"
    assert ContactType.OPERATIONS == "operations"
    assert ContactType.LEGAL == "legal"
    assert ContactType.GENERAL == "general"


def test_contact_creation_and_repr() -> None:
    contact = Contact(
        entity_type="ownership",
        entity_id="ownership-1",
        name="Alice",
        contact_type=ContactType.PRIMARY,
        is_primary=True,
    )

    assert contact.entity_type == "ownership"
    assert contact.entity_id == "ownership-1"
    assert contact.name == "Alice"
    assert contact.contact_type == ContactType.PRIMARY
    assert contact.is_primary is True
    assert "Alice" in repr(contact)

