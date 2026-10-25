"""Regression tests for the asset-operations v5 contract schema migration."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest


def _load_migration_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20261023_asset_operations_v5_contracts.py"
    )
    spec = spec_from_file_location("asset_operations_v5_contracts", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_follows_asset_unit_revision() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20261023_asset_operations_v5_asset_units"


def test_migration_creates_contract_fact_tables_and_overlap_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    table_calls: dict[str, tuple[object, ...]] = {}
    execute_calls: list[str] = []
    monkeypatch.setattr(
        module.op,
        "create_table",
        lambda name, *items, **_kwargs: table_calls.setdefault(name, items),
    )
    monkeypatch.setattr(module.op, "create_index", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        module.op,
        "execute",
        lambda statement: execute_calls.append(str(statement)),
    )

    module.upgrade()

    assert set(table_calls) == {
        "upstream_contracts",
        "terminal_contracts",
        "upstream_contract_asset_units",
        "terminal_contract_asset_units",
        "contract_rent_schedules",
        "contract_lifecycle_events",
    }
    terminal_columns = {
        item.name
        for item in table_calls["terminal_contracts"]
        if isinstance(item, module.sa.Column)
    }
    assert {
        "contract_mode",
        "tenant_party_id",
        "lessor_party_id",
        "upstream_contract_id",
        "rent_collector",
        "scan_document_id",
        "version",
    } <= terminal_columns
    assert any(
        "ex_terminal_contract_asset_units_unit_period" in statement
        and "EXCLUDE USING gist" in statement
        for statement in execute_calls
    )


def test_migration_downgrade_fails_loud() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="irreversible"):
        module.downgrade()


def test_contract_write_receipt_migration_is_a_single_forward_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20261024_asset_contract_write_receipts.py"
    )
    spec = spec_from_file_location("asset_contract_write_receipts", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    table_calls: dict[str, tuple[object, ...]] = {}
    monkeypatch.setattr(
        module.op,
        "create_table",
        lambda name, *items, **_kwargs: table_calls.setdefault(name, items),
    )
    monkeypatch.setattr(module.op, "create_index", lambda *_args, **_kwargs: None)

    module.upgrade()

    assert module.down_revision == "20261024_asset_operations_v5_permissions"
    columns = {
        item.name
        for item in table_calls["asset_contract_write_receipts"]
        if isinstance(item, module.sa.Column)
    }
    assert {
        "actor_id",
        "command_kind",
        "idempotency_key",
        "request_fingerprint",
        "result_data",
        "created_at",
    } <= columns
