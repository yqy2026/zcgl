"""Management fee storage enforces snapshot and live-statement invariants."""

from datetime import datetime

import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.exc import IntegrityError

from src.models.asset_contract import AssetContractWriteReceipt
from src.models.management_fee_statement import (
    ManagementFeeStatement,
    ManagementFeeStatementLine,
)

pytestmark = pytest.mark.unit


def statement(statement_id="st-1", **changes):
    values = dict(
        id=statement_id,
        owner_party_id="owner-1",
        period="2026-10",
        statement_number=statement_id,
        version=1,
    )
    values.update(changes)
    return values


def test_drafts_store_no_derived_status_or_amounts_and_have_version_lock():
    table = ManagementFeeStatement.__table__
    assert ManagementFeeStatement.__mapper__.version_id_col is table.c.version
    engine = create_engine("sqlite://")
    table.create(engine)
    with engine.begin() as conn:
        conn.execute(insert(table).values(**statement()))
        row = conn.execute(table.select()).mappings().one()
        assert row["status"] is None
        assert row["base_amount"] is None
        assert row["fee_amount"] is None


def test_only_one_live_statement_per_owner_month_but_superseded_history_remains():
    table = ManagementFeeStatement.__table__
    engine = create_engine("sqlite://")
    table.create(engine)
    snapshot = dict(
        status="superseded",
        stamped_document_id="doc-1",
        confirmed_by="actor-1",
        confirmed_at=datetime(2026, 11, 1),
        base_amount=0,
        fee_amount=0,
        upstream_contract_ids=[],
    )
    with engine.begin() as conn:
        conn.execute(insert(table).values(**statement("old", **snapshot)))
        conn.execute(insert(table).values(**statement("new")))
        with pytest.raises(IntegrityError):
            conn.execute(insert(table).values(**statement("duplicate")))


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "collecting"},
        {"status": "confirmed"},
        {"base_amount": 100},
        {"upstream_contract_ids": []},
        {"version": 0},
        {"period": "2026-13"},
        {"period": "2026-0a"},
        {"period": "20a6-10"},
        {"predecessor_statement_id": "st-1"},
        {"successor_statement_id": "st-1"},
    ],
)
def test_invalid_statement_facts_are_rejected(changes):
    table = ManagementFeeStatement.__table__
    engine = create_engine("sqlite://")
    table.create(engine)
    with engine.begin() as conn, pytest.raises(IntegrityError):
        conn.execute(insert(table).values(**statement(**changes)))


def test_management_fee_receipts_fit_command_column():
    column = AssetContractWriteReceipt.__table__.c.command_kind
    assert column.type.length == 64
    checks = " ".join(
        str(c.sqltext) for c in column.table.constraints if hasattr(c, "sqltext")
    )
    for command in (
        "defer_management_fee_line",
        "confirm_management_fee_statement",
        "supersede_management_fee_statement",
    ):
        assert command in checks
        assert len(command) <= column.type.length


def line(**changes):
    values = dict(
        id="line-1",
        statement_id="st-1",
        line_kind="current",
        upstream_contract_id="up-1",
        terminal_contract_id="tm-1",
        rent_ledger_entry_id="rent-1",
        asset_unit_ids=["unit-1"],
        tenant_name_snapshot="租户甲",
        rent_period="2026-10",
        scheduled_rent=10000,
        owner_received_amount=4000,
        counted_record_ids=["receipt-1"],
        received_on=None,
        fee_rate=0.1,
        fee_amount=400,
        deferred_amount=6000,
        deferral_reason="截止日未到账，自动顺延",
    )
    values.update(changes)
    return values


@pytest.mark.parametrize(
    "changes",
    [
        {"fee_rate": -0.1},
        {"fee_rate": 1.1},
        {"fee_amount": -1},
        {"deferred_amount": -1},
        {"deferral_reason": None},
        {"deferral_reason": "  "},
        {"carried_from_statement_id": "st-old"},
        {"line_kind": "unknown"},
        {"rent_period": "2026-0a"},
        {"rent_period": "20a6-10"},
    ],
)
def test_invalid_line_snapshot_is_rejected(changes):
    table = ManagementFeeStatementLine.__table__
    engine = create_engine("sqlite://")
    table.create(engine)
    with engine.begin() as conn, pytest.raises(IntegrityError):
        conn.execute(insert(table).values(**line(**changes)))


def test_each_obligation_occurs_only_once_in_a_statement_snapshot():
    table = ManagementFeeStatementLine.__table__
    engine = create_engine("sqlite://")
    table.create(engine)
    with engine.begin() as conn:
        conn.execute(insert(table).values(**line()))
        with pytest.raises(IntegrityError):
            conn.execute(insert(table).values(**line(id="line-2")))


def test_confirmed_statement_requires_complete_nonnegative_snapshot():
    table = ManagementFeeStatement.__table__
    engine = create_engine("sqlite://")
    table.create(engine)
    snapshot = dict(
        status="confirmed",
        stamped_document_id="doc-1",
        confirmed_by="actor-1",
        confirmed_at=datetime(2026, 11, 1),
        base_amount=4000,
        fee_amount=400,
        upstream_contract_ids=["up-1"],
    )
    with engine.begin() as conn:
        conn.execute(insert(table).values(**statement(**snapshot)))
        row = conn.execute(table.select()).mappings().one()
        assert row["fee_amount"] == 400
        assert row["upstream_contract_ids"] == ["up-1"]
        with pytest.raises(IntegrityError):
            conn.execute(
                insert(table).values(
                    **statement(
                        "bad", period="2026-11", **{**snapshot, "fee_amount": -1}
                    )
                )
            )
