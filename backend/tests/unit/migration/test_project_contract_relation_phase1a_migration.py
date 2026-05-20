"""Tests for Phase 1a project-centered contract relation migration."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType


def _load_migration_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260513_project_contract_relation_phase1a.py"
    )
    spec = spec_from_file_location("project_contract_relation_phase1a", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_adds_nullable_project_id_to_contract_groups(monkeypatch) -> None:
    module = _load_migration_module()
    operations: list[tuple[str, tuple, dict]] = []

    def record(name: str):
        def _inner(*args, **kwargs):
            operations.append((name, args, kwargs))

        return _inner

    monkeypatch.setattr(module.op, "add_column", record("add_column"))
    monkeypatch.setattr(module.op, "create_index", record("create_index"))
    monkeypatch.setattr(module.op, "create_foreign_key", record("create_foreign_key"))

    module.upgrade()

    add_column_ops = [op for op in operations if op[0] == "add_column"]
    assert len(add_column_ops) == 1
    _, add_args, _ = add_column_ops[0]
    table_name, column = add_args
    assert table_name == "contract_groups"
    assert column.name == "project_id"
    assert column.nullable is True

    assert (
        "create_index",
        ("ix_contract_groups_project_id", "contract_groups", ["project_id"]),
        {},
    ) in operations
    assert (
        "create_foreign_key",
        (
            "fk_contract_groups_project_id",
            "contract_groups",
            "projects",
            ["project_id"],
            ["id"],
        ),
        {},
    ) in operations


def test_migration_is_appended_to_current_alembic_head() -> None:
    module = _load_migration_module()

    assert module.revision == "20260513_project_contract_relation_phase1a"
    assert module.down_revision == "20260408_phase3_role_redefinition"
