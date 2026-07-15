"""Tests for the payment-flow lifecycle and voucher audit migration."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


def _load_migration_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260713_payment_flow_lifecycle_audit.py"
    )
    spec = spec_from_file_location("payment_flow_lifecycle_audit", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lifecycle_migration_adds_traceability_and_concurrency_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    added_columns: list[str] = []
    foreign_keys: list[dict[str, Any]] = []
    unique_constraints: list[dict[str, Any]] = []
    check_constraints: list[dict[str, str]] = []

    monkeypatch.setattr(
        module.op,
        "add_column",
        lambda _table, column: added_columns.append(str(column.name)),
    )
    monkeypatch.setattr(
        module.op,
        "create_foreign_key",
        lambda name, source, target, local, remote: foreign_keys.append(
            {
                "name": name,
                "source": source,
                "target": target,
                "local": local,
                "remote": remote,
            }
        ),
    )
    monkeypatch.setattr(
        module.op,
        "create_unique_constraint",
        lambda name, table, columns: unique_constraints.append(
            {"name": name, "table": table, "columns": columns}
        ),
    )
    monkeypatch.setattr(
        module.op,
        "create_check_constraint",
        lambda name, _table, condition: check_constraints.append(
            {"name": name, "condition": condition}
        ),
    )
    monkeypatch.setattr(module.op, "create_index", lambda *_args, **_kwargs: None)

    module._add_lifecycle_fields()

    assert added_columns == [
        "corrected_from_flow_id",
        "status_changed_by",
        "status_changed_at",
        "status_change_reason",
    ]
    assert foreign_keys[0]["target"] == "operational_payment_flows"
    assert foreign_keys[0]["local"] == ["corrected_from_flow_id"]
    assert unique_constraints[0]["columns"] == ["corrected_from_flow_id"]
    assert "status_change_reason IS NOT NULL" in check_constraints[0]["condition"]
    assert "btrim(status_changed_by) <> ''" in check_constraints[0]["condition"]
    assert "btrim(status_change_reason) <> ''" in check_constraints[0]["condition"]


def test_lifecycle_migration_follows_ledger_authorization_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260710_ledger_authorization"


def test_lifecycle_migration_downgrade_fails_loud() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="payment flow lifecycle"):
        module.downgrade()
