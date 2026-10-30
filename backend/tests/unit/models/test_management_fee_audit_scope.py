"""Whole-statement audit scope never exposes partially visible owner totals."""

from sqlalchemy.dialects import postgresql

from src.crud.business_change_event import fee_statement_ids_for_scope
from src.services.party_scope_resolver import EffectivePartyScope


def test_empty_owner_scope_cannot_read_fee_audit():
    scope = EffectivePartyScope(user_id="actor", source="explicit", scope_mode="owner")
    sql = str(fee_statement_ids_for_scope(scope).compile(dialect=postgresql.dialect()))
    assert "WHERE false" in sql


def test_manager_audit_scope_requires_all_agreements_not_just_any_one():
    scope = EffectivePartyScope(
        user_id="actor",
        source="explicit",
        scope_mode="manager",
        manager_party_ids=["manager"],
    )
    query = fee_statement_ids_for_scope(scope)
    sql = str(query.compile(dialect=postgresql.dialect()))
    assert "NOT (EXISTS" in sql
    assert "operator_party_id NOT IN" in sql
    assert "management_agreement" in query.compile().params.values()


def test_owner_audit_scope_uses_owner_axis_and_preserves_statement_identity():
    scope = EffectivePartyScope(
        user_id="actor",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner"],
    )
    query = fee_statement_ids_for_scope(scope)
    sql = str(query.compile(dialect=postgresql.dialect()))
    assert "management_fee_statements.owner_party_id IN" in sql
    assert list(query.selected_columns.keys()) == ["id"]
