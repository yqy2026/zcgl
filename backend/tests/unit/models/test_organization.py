"""Organization model unit tests for the ADR-0022 cutover."""

from src.models.organization import (
    Organization,
    OrganizationHistory,
    OrganizationPartyScopeCommit,
    RepresentedPartyPerspective,
)


def test_represented_party_perspective_values() -> None:
    assert {item.value for item in RepresentedPartyPerspective} == {
        "owner",
        "manager",
    }


def test_organization_represented_party_columns_and_fk() -> None:
    columns = Organization.__table__.columns
    foreign_keys = {
        foreign_key.target_fullname
        for foreign_key in columns["represented_party_id"].foreign_keys
    }

    assert columns["represented_party_id"].nullable is True
    assert columns["represented_party_perspective"].nullable is True
    assert foreign_keys == {"parties.id"}


def test_organization_represented_party_pair_is_database_enforced() -> None:
    checks = {
        str(constraint.name): str(constraint.sqltext)
        for constraint in Organization.__table__.constraints
        if constraint.__class__.__name__ == "CheckConstraint"
    }

    assert "ck_organizations_represented_party_pair" in checks
    assert "represented_party_id" in checks["ck_organizations_represented_party_pair"]
    assert "owner" in checks["ck_organizations_represented_party_perspective"]
    assert "manager" in checks["ck_organizations_represented_party_perspective"]


def test_organization_code_is_unique_in_its_own_namespace() -> None:
    unique_constraints = {
        str(constraint.name): tuple(column.name for column in constraint.columns)
        for constraint in Organization.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }

    assert unique_constraints["uq_organizations_code"] == ("code",)


def test_organization_parent_child_relationship() -> None:
    parent = Organization(name="Headquarters", code="ORG-HQ", type="headquarter")
    child = Organization(name="Branch", code="ORG-BR", type="branch")
    child.parent = parent

    assert child.parent is parent
    assert child in parent.children


def test_organization_history_creation_and_repr() -> None:
    history = OrganizationHistory(organization_id="org-1", action="update")

    assert history.organization_id == "org-1"
    assert "update" in repr(history)


def test_party_scope_commit_has_durable_idempotency_contract() -> None:
    columns = OrganizationPartyScopeCommit.__table__.columns
    unique_constraints = {
        str(constraint.name): tuple(column.name for column in constraint.columns)
        for constraint in OrganizationPartyScopeCommit.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }

    assert columns["result_data"].nullable is False
    assert columns["idempotency_key"].nullable is False
    assert unique_constraints["uq_organization_party_scope_commit_request"] == (
        "organization_id",
        "actor_id",
        "idempotency_key",
    )
