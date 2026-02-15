"""Organization model unit tests."""

from src.models.organization import Organization, OrganizationHistory


def test_organization_parent_child_relationship() -> None:
    parent = Organization(name="Headquarters", code="ORG-HQ", type="headquarter")
    child = Organization(name="Branch", code="ORG-BR", type="branch")
    child.parent = parent

    assert child.parent is parent
    assert child in parent.children


def test_organization_repr_contains_name() -> None:
    org = Organization(name="Operations", code="ORG-OPS", type="department")
    assert "Operations" in repr(org)


def test_organization_history_creation_and_repr() -> None:
    history = OrganizationHistory(organization_id="org-1", action="update")

    assert history.organization_id == "org-1"
    assert history.action == "update"
    assert "update" in repr(history)

