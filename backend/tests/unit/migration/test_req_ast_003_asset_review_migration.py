"""REQ-AST-003 迁移安全测试。"""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock


def _load_migration_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260311_req_ast_003_asset_review.py"
    )
    spec = spec_from_file_location("req_ast_003_asset_review", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_should_follow_party_review_fields_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260311_party_review_fields"


def test_upgrade_should_create_review_log_table_and_backfill_status() -> None:
    module = _load_migration_module()

    create_table = Mock()
    create_index = Mock()
    execute = Mock()
    module.op.create_table = create_table
    module.op.create_index = create_index
    module.op.execute = execute

    module.upgrade()

    create_table.assert_called_once()
    assert create_table.call_args.args[0] == "asset_review_logs"
    create_index.assert_called_once_with(
        "ix_asset_review_logs_asset_id",
        "asset_review_logs",
        ["asset_id"],
        unique=False,
    )
    execute.assert_any_call(
        "UPDATE assets SET review_status = 'reversed' WHERE review_status = 'rejected'"
    )


def test_downgrade_should_drop_table_and_restore_status_value() -> None:
    module = _load_migration_module()

    drop_table = Mock()
    drop_index = Mock()
    execute = Mock()
    module.op.drop_table = drop_table
    module.op.drop_index = drop_index
    module.op.execute = execute

    module.downgrade()

    execute.assert_any_call(
        "UPDATE assets SET review_status = 'rejected' WHERE review_status = 'reversed'"
    )
    drop_index.assert_called_once_with(
        "ix_asset_review_logs_asset_id",
        table_name="asset_review_logs",
    )
    drop_table.assert_called_once_with("asset_review_logs")
