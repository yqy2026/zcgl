"""Exercise archive migration SQL inside a rollback-only private PG schema."""

import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.e2e


@pytest.fixture
def migration_context(test_database_url, monkeypatch):
    engine = create_engine(test_database_url)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                schema = f"archive_migration_{uuid4().hex}"
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
                connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                connection.execute(
                    text("CREATE TABLE property_certificates (id varchar PRIMARY KEY)")
                )
                connection.execute(
                    text("""
                    CREATE TABLE attachments (
                        id varchar PRIMARY KEY, owner_type varchar NOT NULL,
                        owner_id varchar NOT NULL, created_by varchar NOT NULL,
                        created_at timestamp NOT NULL, storage_key varchar NOT NULL,
                        file_hash varchar NULL
                    )
                """)
                )
                migration_path = (
                    Path(__file__).resolve().parents[2]
                    / "alembic/versions/20261102_archive_documents.py"
                )
                spec = importlib.util.spec_from_file_location(
                    "archive_migration_under_test", migration_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                monkeypatch.setattr(
                    module, "op", Operations(MigrationContext.configure(connection))
                )
                yield connection, schema, module
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def _seed(connection, orphan=False):
    if not orphan:
        connection.execute(text("INSERT INTO property_certificates VALUES ('cert')"))
    connection.execute(
        text("""
        INSERT INTO attachments
        VALUES ('b', 'property_certificate', 'cert', 'actor-b', '2026-11-02 09:00:00', 'private/b.pdf', NULL),
               ('a', 'property_certificate', 'cert', 'actor-a', '2026-11-02 09:00:00', 'private/a.pdf', 'hash-a')
    """)
    )


@pytest.mark.parametrize("orphan", [False, True])
def test_backfill_preserves_files_and_orphan_owner_blocks_before_ddl(
    migration_context, orphan
):
    connection, schema, migration = migration_context
    _seed(connection, orphan)
    before = connection.execute(text("SELECT * FROM attachments ORDER BY id")).all()
    if orphan:
        with pytest.raises(
            RuntimeError, match="2 certificate attachments have missing owners"
        ):
            migration.upgrade()
        assert "archive_documents" not in inspect(connection).get_table_names(
            schema=schema
        )
    else:
        migration.upgrade()
        rows = connection.execute(
            text("""
            SELECT attachment_id, document_version, uploaded_by, uploaded_at,
                   target_type, target_id, replaces_document_id
            FROM archive_documents ORDER BY document_version
        """)
        ).all()
        assert [row.attachment_id for row in rows] == ["a", "b"]
        assert [row.document_version for row in rows] == [1, 2]
        assert [row.uploaded_by for row in rows] == ["actor-a", "actor-b"]
        assert all(row.uploaded_at == before[0].created_at for row in rows)
        assert all(
            row.target_type == "property_certificate"
            and row.target_id == "cert"
            and row.replaces_document_id is None
            for row in rows
        )
        columns = {
            column["name"]
            for column in inspect(connection).get_columns(
                "archive_documents", schema=schema
            )
        }
        assert not {"storage_key", "file_hash", "file_name"} & columns
        migration.downgrade()
        assert "archive_documents" not in inspect(connection).get_table_names(
            schema=schema
        )
    assert (
        connection.execute(text("SELECT * FROM attachments ORDER BY id")).all()
        == before
    )


def test_real_constraints_reject_cross_target_forks_and_file_deletion(
    migration_context,
):
    connection, _schema, migration = migration_context
    _seed(connection)
    migration.upgrade()
    predecessor = connection.execute(
        text("SELECT id FROM archive_documents WHERE attachment_id = 'a'")
    ).scalar_one()
    for attachment_id in ("c", "d", "e"):
        connection.execute(
            text("""
            INSERT INTO attachments VALUES (:id, 'property_certificate', 'cert', 'actor', now(), :key, NULL)
        """),
            {"id": attachment_id, "key": f"private/{attachment_id}.pdf"},
        )
    insert = text("""
        INSERT INTO archive_documents VALUES
        (:id, 'property_certificate', 'property_certificate', :target, :attachment,
         :version, :previous, 'actor', now())
    """)
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(
            insert,
            {
                "id": str(uuid4()),
                "target": "other",
                "attachment": "c",
                "version": 1,
                "previous": predecessor,
            },
        )
    connection.execute(
        insert,
        {
            "id": str(uuid4()),
            "target": "cert",
            "attachment": "c",
            "version": 3,
            "previous": predecessor,
        },
    )
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(
            insert,
            {
                "id": str(uuid4()),
                "target": "cert",
                "attachment": "d",
                "version": 4,
                "previous": predecessor,
            },
        )
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(text("DELETE FROM attachments WHERE id = 'a'"))
