"""Fee stamp archive migration backfills versions and stays reversible."""

import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.e2e


@pytest.fixture
def migration_context(test_database_url, monkeypatch):
    engine = create_engine(test_database_url)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                schema = f"fee_stamp_migration_{uuid4().hex}"
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
                connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                connection.execute(
                    text("CREATE TABLE management_fee_statements (id varchar PRIMARY KEY)")
                )
                connection.execute(text("""
                    CREATE TABLE attachments (
                        id varchar PRIMARY KEY, owner_type varchar NOT NULL,
                        owner_id varchar NOT NULL, created_by varchar NOT NULL,
                        created_at timestamp NOT NULL, storage_key varchar NOT NULL,
                        file_hash varchar NULL
                    )
                """))
                connection.execute(text("""
                    CREATE TABLE archive_documents (
                        id varchar(36) PRIMARY KEY,
                        document_type varchar(40) NOT NULL,
                        target_type varchar(40) NOT NULL,
                        target_id varchar NOT NULL,
                        attachment_id varchar NOT NULL UNIQUE,
                        document_version integer NOT NULL,
                        replaces_document_id varchar(36) NULL,
                        uploaded_by varchar(100) NOT NULL,
                        uploaded_at timestamp NOT NULL,
                        UNIQUE (target_type, target_id, document_type, document_version)
                    )
                """))
                migration_path = (
                    Path(__file__).resolve().parents[2]
                    / "alembic/versions/20261104_fee_stamp_archive.py"
                )
                spec = importlib.util.spec_from_file_location(
                    "fee_stamp_migration_under_test", migration_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                monkeypatch.setattr(
                    module, "op", Operations(MigrationContext.configure(connection))
                )
                yield connection, module
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def _seed(connection):
    connection.execute(text("INSERT INTO management_fee_statements VALUES ('st1')"))
    connection.execute(text("INSERT INTO management_fee_statements VALUES ('st2')"))
    connection.execute(text("""
        INSERT INTO attachments (id, owner_type, owner_id, created_by, created_at, storage_key)
        VALUES
            ('a1', 'management_fee_statement', 'st1', 'u1', '2026-10-01 10:00', 'k1'),
            ('a2', 'management_fee_statement', 'st1', 'u1', '2026-10-02 10:00', 'k2'),
            ('a3', 'management_fee_statement', 'st2', 'u2', '2026-10-03 10:00', 'k3'),
            ('a4', 'contract', 'c1', 'u3', '2026-10-04 10:00', 'k4')
    """))


def test_migration_backfills_versions_per_statement(migration_context):
    connection, migration = migration_context
    _seed(connection)
    migration.upgrade()
    rows = connection.execute(text("""
        SELECT target_id, document_version, attachment_id, replaces_document_id
        FROM archive_documents
        WHERE document_type = 'management_fee_statement'
        ORDER BY target_id, document_version
    """)).fetchall()
    v1_id = connection.execute(
        text(
            "SELECT id FROM archive_documents WHERE attachment_id = 'a1'"
        )
    ).scalar_one()
    assert rows == [
        ("st1", 1, "a1", None),
        ("st1", 2, "a2", v1_id),
        ("st2", 1, "a3", None),
    ]
    contract_rows = connection.execute(
        text("SELECT count(*) FROM archive_documents WHERE attachment_id = 'a4'")
    ).scalar_one()
    assert contract_rows == 0
    migration.downgrade()
    remaining = connection.execute(
        text("SELECT count(*) FROM archive_documents")
    ).scalar_one()
    assert remaining == 0


def test_migration_fails_loud_on_orphan_stamp_attachments(migration_context):
    connection, migration = migration_context
    _seed(connection)
    connection.execute(text("""
        INSERT INTO attachments (id, owner_type, owner_id, created_by, created_at, storage_key)
        VALUES ('orphan', 'management_fee_statement', 'missing', 'u1', '2026-10-05 10:00', 'k5')
    """))
    with pytest.raises(RuntimeError, match="missing statements"):
        migration.upgrade()
    backfilled = connection.execute(
        text("SELECT count(*) FROM archive_documents")
    ).scalar_one()
    assert backfilled == 0
