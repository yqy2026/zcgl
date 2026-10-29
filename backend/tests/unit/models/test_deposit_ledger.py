"""Deposit storage preserves source facts and database-level invariants."""

from sqlalchemy import CheckConstraint, UniqueConstraint

from src.models.deposit_ledger import DepositLedgerEntry, DepositRecord


def test_deposit_entry_keeps_only_source_facts_and_has_optimistic_version():
    table = DepositLedgerEntry.__table__
    assert set(table.columns.keys()) == {
        "id",
        "contract_kind",
        "contract_id",
        "collector",
        "version",
    }
    assert DepositLedgerEntry.__mapper__.version_id_col is table.c.version
    assert any(
        isinstance(item, UniqueConstraint)
        and set(item.columns.keys()) == {"contract_kind", "contract_id"}
        for item in table.constraints
    )


def test_deposit_records_have_positive_append_only_facts_and_unique_reversals():
    table = DepositRecord.__table__
    checks = {
        str(item.sqltext)
        for item in table.constraints
        if isinstance(item, CheckConstraint)
    }
    assert "amount > 0" in checks
    assert any(
        "reverses_record_id IS NOT NULL" in item and "reason" in item for item in checks
    )
    assert any("offset_ledger_entry_id IS NOT NULL" in item for item in checks)
    reversal = next(
        item for item in table.indexes if item.name == "uq_deposit_records_reversal"
    )
    assert reversal.unique
    assert (
        str(reversal.dialect_options["postgresql"]["where"])
        == "reverses_record_id IS NOT NULL"
    )
    assert any(
        isinstance(item, UniqueConstraint)
        and list(item.columns.keys()) == ["idempotency_key"]
        for item in table.constraints
    )
    assert {fk.target_fullname for fk in table.foreign_keys} == {
        "deposit_ledger_entries.id",
        "attachments.id",
        "rent_ledger_entries.id",
        "contract_lifecycle_events.id",
        "deposit_records.id",
        "users.id",
    }
