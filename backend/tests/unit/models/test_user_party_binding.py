"""User-party binding model unit tests."""

from src.models.user_party_binding import RelationType, UserPartyBinding


def test_relation_type_enum_values() -> None:
    assert RelationType.OWNER.value == "owner"
    assert RelationType.MANAGER.value == "manager"
    assert RelationType.HEADQUARTERS.value == "headquarters"


def test_user_party_binding_creation() -> None:
    binding = UserPartyBinding(
        user_id="user-1",
        party_id="party-1",
        relation_type=RelationType.OWNER,
        is_primary=True,
    )

    assert binding.user_id == "user-1"
    assert binding.party_id == "party-1"
    assert binding.relation_type == RelationType.OWNER
    assert binding.is_primary is True


def test_user_party_binding_repr_contains_relation_type() -> None:
    binding = UserPartyBinding(
        user_id="user-1",
        party_id="party-1",
        relation_type=RelationType.MANAGER,
    )

    assert "manager" in repr(binding)
