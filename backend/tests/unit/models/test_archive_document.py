"""Archive metadata references files instead of duplicating them."""

import pytest

from src.models.archive_document import ArchiveDocument

pytestmark = pytest.mark.unit


def test_archive_has_no_duplicate_file_facts():
    table = ArchiveDocument.__table__
    assert {"attachment_id", "replaces_document_id", "document_version"} <= set(
        table.columns.keys()
    )
    assert not {"storage_key", "file_hash", "file_name"} & set(table.columns.keys())
    assert any(fk.ondelete == "RESTRICT" for fk in table.c.attachment_id.foreign_keys)


def test_replacement_cannot_fork_or_cross_business_targets():
    table = ArchiveDocument.__table__
    unique_sets = {
        tuple(c.columns.keys())
        for c in table.constraints
        if c.__class__.__name__ == "UniqueConstraint"
    }
    assert ("replaces_document_id",) in unique_sets
    replacement = next(
        c
        for c in table.foreign_key_constraints
        if c.name == "fk_archive_documents_replacement_target"
    )
    assert list(replacement.column_keys) == [
        "replaces_document_id",
        "target_type",
        "target_id",
        "document_type",
    ]
    assert replacement.ondelete == "RESTRICT"
