"""Party role model unit tests."""

from src.models.party_role import PartyRoleBinding, PartyRoleDef


def test_party_role_def_creation() -> None:
    role_def = PartyRoleDef(role_code="OWNER", scope_type="asset")

    assert role_def.role_code == "OWNER"
    assert role_def.scope_type == "asset"
    assert "OWNER" in repr(role_def)


def test_party_role_binding_creation() -> None:
    binding = PartyRoleBinding(
        party_id="party-1",
        role_def_id="role-1",
        scope_type="asset",
        scope_id="asset-1",
    )

    assert binding.party_id == "party-1"
    assert binding.role_def_id == "role-1"
    assert binding.scope_type == "asset"


def test_party_role_def_unique_constraint_exists() -> None:
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in PartyRoleDef.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }

    assert ("role_code", "scope_type") in unique_columns


def test_party_role_binding_scope_check_exists() -> None:
    check_constraints = [
        str(constraint.sqltext)
        for constraint in PartyRoleBinding.__table__.constraints
        if constraint.__class__.__name__ == "CheckConstraint"
    ]

    assert any("scope_type" in text and "scope_id" in text for text in check_constraints)
