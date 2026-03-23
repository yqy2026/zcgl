"""Migration-layer hygiene checks for legacy contract artifacts."""

from __future__ import annotations

import ast
from pathlib import Path


def test_selected_migration_files_should_not_keep_raw_legacy_contract_table_literal() -> None:
    migration_root = Path(__file__).resolve().parents[3]
    retired_table_name = "_".join(("rent", "contracts"))
    target_files = [
        migration_root / "src/scripts/migration/party_migration/reconciliation.py",
        migration_root / "src/scripts/migration/party_migration/phase4_no_go_snapshot.py",
        migration_root / "src/scripts/migration/party_migration/backfill_business_tables.py",
        migration_root / "tests/unit/migration/test_phase4_reconciliation.py",
        migration_root / "tests/unit/migration/test_phase4_no_go_snapshot.py",
        migration_root / "tests/unit/migration/test_backfill.py",
        migration_root / "tests/unit/migration/test_phase4_migrations.py",
        migration_root / "tests/integration/test_postgresql_migration.py",
    ]

    for path in target_files:
        file_text = path.read_text(encoding="utf-8")
        assert retired_table_name not in file_text


def test_alembic_env_should_not_import_retired_contract_model_module() -> None:
    migration_root = Path(__file__).resolve().parents[3]
    env_path = migration_root / "alembic" / "env.py"
    retired_module_name = "_".join(("rent", "contract"))
    tree = ast.parse(env_path.read_text(encoding="utf-8"))

    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "src.models":
            continue
        imported_names.update(alias.name for alias in node.names)

    assert retired_module_name not in imported_names


def test_legacy_v2_migration_fix_script_should_not_import_retired_contract_model() -> None:
    backend_root = Path(__file__).resolve().parents[3]
    script_path = backend_root / "scripts" / "v2_migration_fix.py"
    retired_module_name = ".".join(("src", "models", "_".join(("rent", "contract"))))
    tree = ast.parse(script_path.read_text(encoding="utf-8"))

    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)

    assert retired_module_name not in imported_modules
