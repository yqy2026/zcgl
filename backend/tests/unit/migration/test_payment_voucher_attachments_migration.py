"""Tests for generic payment-voucher attachment storage migration."""

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
        / "20260713_payment_voucher_attachments.py"
    )
    spec = spec_from_file_location("payment_voucher_attachments", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_attachment_migration_creates_generic_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    create_calls: list[dict[str, Any]] = []
    index_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        module.op,
        "create_table",
        lambda table, *columns, **_kwargs: create_calls.append(
            {"table": table, "columns": columns}
        ),
    )
    monkeypatch.setattr(
        module.op,
        "create_index",
        lambda name, table, columns, **_kwargs: index_calls.append(
            {"name": name, "table": table, "columns": columns}
        ),
    )

    module._create_attachments_table()

    assert create_calls[0]["table"] == "attachments"
    column_names = {
        column.name
        for column in create_calls[0]["columns"]
        if hasattr(column, "name")
    }
    assert {
        "id",
        "owner_type",
        "owner_id",
        "file_name",
        "file_type",
        "file_size",
        "file_hash",
        "storage_key",
        "created_by",
        "created_at",
    } <= column_names
    assert {call["name"] for call in index_calls} >= {
        "ix_attachments_owner",
        "ix_attachments_file_hash",
    }


def test_attachment_migration_follows_lifecycle_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260713_payment_flow_lifecycle_audit"


def test_attachment_migration_downgrade_fails_loud() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="payment voucher attachments"):
        module.downgrade()
