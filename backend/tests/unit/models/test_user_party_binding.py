"""User-party binding model unit tests for the ADR-0022 cutover."""

from src.models.user_party_binding import RelationType, UserPartyBinding


def test_relation_type_contains_only_owner_and_manager() -> None:
    assert {item.value for item in RelationType} == {"owner", "manager"}


def test_user_party_binding_has_no_primary_flag() -> None:
    assert "is_primary" not in UserPartyBinding.__table__.columns


def test_user_party_binding_constraints_encode_relation_and_validity() -> None:
    checks = {
        str(constraint.name): str(constraint.sqltext)
        for constraint in UserPartyBinding.__table__.constraints
        if constraint.__class__.__name__ == "CheckConstraint"
    }

    assert "ck_user_party_bindings_relation_type" in checks
    assert "owner" in checks["ck_user_party_bindings_relation_type"]
    assert "manager" in checks["ck_user_party_bindings_relation_type"]
    assert "ck_user_party_bindings_valid_range" in checks


def test_user_party_binding_creation_and_repr() -> None:
    binding = UserPartyBinding(
        user_id="user-1",
        party_id="party-1",
        relation_type=RelationType.MANAGER,
    )

    assert binding.user_id == "user-1"
    assert binding.party_id == "party-1"
    assert "manager" in repr(binding)
