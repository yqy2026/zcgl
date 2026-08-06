"""Regression tests for the Organization move receipt migration."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType


def _load_migration_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260806_organization_move_commit_receipts.py"
    )
    spec = spec_from_file_location("organization_move_receipts_migration", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_follows_user_transfer_receipts() -> None:
    module = _load_migration_module()

    assert module.revision == "20260806_organization_move_commit_receipts"
    assert module.down_revision == "20260806_user_organization_transfer_commit_receipts"


def test_upgrade_creates_durable_organization_move_receipt_table(monkeypatch) -> None:
    module = _load_migration_module()
    created_tables: list[str] = []
    created_indexes: list[tuple[str, str, list[str]]] = []

    monkeypatch.setattr(
        module.op, "create_table", lambda name, *args: created_tables.append(name)
    )
    monkeypatch.setattr(
        module.op,
        "create_index",
        lambda name, table_name, columns: created_indexes.append(
            (name, table_name, columns)
        ),
    )

    module.upgrade()

    assert created_tables == ["organization_move_commits"]
    assert created_indexes == [
        (
            "ix_organization_move_commits_organization_id",
            "organization_move_commits",
            ["organization_id"],
        )
    ]


def test_downgrade_removes_organization_move_receipt_table(monkeypatch) -> None:
    module = _load_migration_module()
    dropped_indexes: list[tuple[str, str]] = []
    dropped_tables: list[str] = []

    monkeypatch.setattr(
        module.op,
        "drop_index",
        lambda name, table_name: dropped_indexes.append((name, table_name)),
    )
    monkeypatch.setattr(
        module.op, "drop_table", lambda name: dropped_tables.append(name)
    )

    module.downgrade()

    assert dropped_indexes == [
        (
            "ix_organization_move_commits_organization_id",
            "organization_move_commits",
        )
    ]
    assert dropped_tables == ["organization_move_commits"]
