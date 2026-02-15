"""Ownership model unit tests."""

from src.models.ownership import Ownership


def test_ownership_creation_and_repr() -> None:
    ownership = Ownership(name="Acme Holdings", code="OWN-001")

    assert ownership.name == "Acme Holdings"
    assert ownership.code == "OWN-001"
    assert "Acme Holdings" in repr(ownership)
    assert "OWN-001" in repr(ownership)


def test_ownership_table_name() -> None:
    assert Ownership.__tablename__ == "ownerships"

