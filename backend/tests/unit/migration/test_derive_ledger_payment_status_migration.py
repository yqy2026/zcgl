"""Tests for deriving ledger payment status from paid amounts."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest
import sqlalchemy as sa


def _load_migration_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260620_derive_ledger_payment_status.py"
    )
    spec = spec_from_file_location("derive_ledger_payment_status", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_should_follow_scan_document_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260620_contract_number_project_scan_documents"


def test_upgrade_should_normalize_non_voided_rows_by_paid_amount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    metadata = sa.MetaData()

    contract_ledger_table = sa.Table(
        "contract_ledger_entries",
        metadata,
        sa.Column("entry_id", sa.String, primary_key=True),
        sa.Column("payment_status", sa.String, nullable=False),
        sa.Column("amount_due", sa.Numeric(15, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(15, 2), nullable=False),
    )
    service_fee_ledger_table = sa.Table(
        "service_fee_ledgers",
        metadata,
        sa.Column("service_fee_entry_id", sa.String, primary_key=True),
        sa.Column("payment_status", sa.String, nullable=False),
        sa.Column("amount_due", sa.Numeric(15, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(15, 2), nullable=False),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            contract_ledger_table.insert(),
            [
                {
                    "entry_id": "rent_paid_zero",
                    "payment_status": "paid",
                    "amount_due": 100,
                    "paid_amount": 0,
                },
                {
                    "entry_id": "rent_partial",
                    "payment_status": "unpaid",
                    "amount_due": 100,
                    "paid_amount": 1,
                },
                {
                    "entry_id": "rent_voided",
                    "payment_status": "voided",
                    "amount_due": 100,
                    "paid_amount": 100,
                },
            ],
        )
        connection.execute(
            service_fee_ledger_table.insert(),
            [
                {
                    "service_fee_entry_id": "fee_paid",
                    "payment_status": "partial",
                    "amount_due": 10,
                    "paid_amount": 10,
                },
            ],
        )

        monkeypatch.setattr(module.op, "get_bind", lambda: connection)

        module.upgrade()

        rent_statuses = dict(
            connection.execute(
                sa.select(
                    contract_ledger_table.c.entry_id,
                    contract_ledger_table.c.payment_status,
                )
            ).all()
        )
        fee_statuses = dict(
            connection.execute(
                sa.select(
                    service_fee_ledger_table.c.service_fee_entry_id,
                    service_fee_ledger_table.c.payment_status,
                )
            ).all()
        )

    assert rent_statuses == {
        "rent_paid_zero": "unpaid",
        "rent_partial": "partial",
        "rent_voided": "voided",
    }
    assert fee_statuses == {"fee_paid": "paid"}


def test_downgrade_is_fail_loud() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="derived ledger payment status"):
        module.downgrade()
