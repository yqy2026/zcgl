"""Party soft delete and review log migration tests."""

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
        / "20260312_party_soft_delete_review_log.py"
    )
    spec = spec_from_file_location("party_soft_delete_review_log", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_should_follow_asset_review_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260311_req_ast_003_asset_review"


def test_upgrade_should_add_deleted_at_and_create_review_log_table_when_missing() -> None:
    module = _load_migration_module()

    add_column = Mock()
    create_table = Mock()
    get_bind = Mock(return_value=object())
    inspector = Mock()
    inspector.get_table_names.return_value = []
    module.op.add_column = add_column
    module.op.create_table = create_table
    module.op.get_bind = get_bind
    module.inspect = Mock(return_value=inspector)

    module.upgrade()

    add_column.assert_called_once()
    assert add_column.call_args.args[0] == "parties"
    assert add_column.call_args.args[1].name == "deleted_at"
    create_table.assert_called_once()
    assert create_table.call_args.args[0] == "party_review_logs"


def test_upgrade_should_skip_review_log_table_creation_when_table_exists() -> None:
    module = _load_migration_module()

    create_table = Mock()
    inspector = Mock()
    inspector.get_table_names.return_value = ["party_review_logs"]
    module.op.add_column = Mock()
    module.op.create_table = create_table
    module.op.get_bind = Mock(return_value=object())
    module.inspect = Mock(return_value=inspector)

    module.upgrade()

    create_table.assert_not_called()


def test_downgrade_should_drop_review_log_table_and_deleted_at() -> None:
    module = _load_migration_module()

    drop_table = Mock()
    drop_column = Mock()
    module.op.drop_table = drop_table
    module.op.drop_column = drop_column

    module.downgrade()

    drop_table.assert_called_once_with("party_review_logs")
    drop_column.assert_called_once_with("parties", "deleted_at")
