"""Party review status backfill migration tests."""

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
        / "20260315_party_review_status_backfill.py"
    )
    spec = spec_from_file_location("party_review_status_backfill", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_should_follow_party_soft_delete_review_log_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260312_party_soft_delete_review_log"


def test_upgrade_should_backfill_rejected_parties_to_draft() -> None:
    module = _load_migration_module()

    execute = Mock()
    module.op.execute = execute

    module.upgrade()

    execute.assert_called_once_with(
        "UPDATE parties SET review_status = 'draft' WHERE review_status = 'rejected'"
    )


def test_downgrade_should_be_noop() -> None:
    module = _load_migration_module()

    execute = Mock()
    module.op.execute = execute

    module.downgrade()

    execute.assert_not_called()
