"""Tests for property-certificate attachments and asset-code hardening migration."""

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
        / "20260620_property_certificate_attachments_asset_code.py"
    )
    spec = spec_from_file_location(
        "property_certificate_attachments_asset_code_migration",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeBind:
    def __init__(self) -> None:
        self.executed_sql: list[str] = []

    def execute(self, statement: Any) -> None:
        self.executed_sql.append(str(getattr(statement, "text", statement)))


class FakeInspector:
    def __init__(self, attachments_exists: bool = False) -> None:
        self.attachments_exists = attachments_exists

    def has_table(self, table_name: str) -> bool:
        if table_name == "property_certificate_attachments":
            return self.attachments_exists
        return table_name in {"assets", "property_certificates"}

    def get_columns(self, table_name: str) -> list[dict[str, Any]]:
        if table_name == "assets":
            return [
                {"name": "id", "nullable": False},
                {"name": "asset_code", "nullable": True},
            ]
        if table_name == "property_certificates":
            return [{"name": "id", "nullable": False}]
        return []

    def get_indexes(self, table_name: str) -> list[dict[str, str]]:
        if table_name == "property_certificate_attachments":
            return []
        return []


def test_migration_should_follow_party_rejected_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260620_party_rejected_review_status"


def test_upgrade_creates_attachment_table_and_hardens_asset_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    bind = FakeBind()
    create_table_calls: list[dict[str, Any]] = []
    create_index_calls: list[dict[str, Any]] = []
    alter_column_calls: list[dict[str, Any]] = []

    monkeypatch.setattr(module.op, "get_bind", lambda: bind)
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: FakeInspector())
    monkeypatch.setattr(
        module.op,
        "create_table",
        lambda table_name, *columns, **kwargs: create_table_calls.append(
            {"table_name": table_name, "columns": columns, **kwargs}
        ),
    )
    monkeypatch.setattr(
        module.op,
        "create_index",
        lambda index_name, table_name, columns, **kwargs: create_index_calls.append(
            {
                "index_name": index_name,
                "table_name": table_name,
                "columns": columns,
                **kwargs,
            }
        ),
    )
    monkeypatch.setattr(
        module.op,
        "alter_column",
        lambda table_name, column_name, **kwargs: alter_column_calls.append(
            {"table_name": table_name, "column_name": column_name, **kwargs}
        ),
    )

    module.upgrade()

    assert create_table_calls[0]["table_name"] == "property_certificate_attachments"
    assert {call["index_name"] for call in create_index_calls} >= {
        "ix_property_certificate_attachments_certificate_id",
        "ix_property_certificate_attachments_storage_key",
    }
    assert any(
        "AST-LEGACY-" in sql and "UPDATE assets" in sql for sql in bind.executed_sql
    )
    assert len(alter_column_calls) == 1
    assert alter_column_calls[0]["table_name"] == "assets"
    assert alter_column_calls[0]["column_name"] == "asset_code"
    assert isinstance(alter_column_calls[0]["existing_type"], module.sa.String)
    assert alter_column_calls[0]["existing_type"].length == 50
    assert alter_column_calls[0]["nullable"] is False


def test_downgrade_is_fail_loud() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="not downgraded"):
        module.downgrade()
