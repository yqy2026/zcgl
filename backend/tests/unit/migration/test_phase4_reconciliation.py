"""Tests for Phase4 reconciliation script compatibility."""

from __future__ import annotations

import sqlalchemy as sa

from src.scripts.migration.party_migration.reconciliation import (
    _check_assets_manager_party_not_null,
    _check_assets_owner_party_not_null,
    _check_projects_manager_party_not_null,
    _check_rent_contracts_manager_party_not_null,
    _check_rent_contracts_owner_party_not_null,
    _check_rent_ledger_owner_party_not_null,
)


def _create_connection() -> sa.engine.Connection:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    connection = engine.connect()
    connection.info["_test_engine"] = engine
    return connection


def _close_connection(connection: sa.engine.Connection) -> None:
    engine = connection.info.pop("_test_engine")
    connection.close()
    engine.dispose()


def test_reconciliation_checks_pass_after_step4_column_drop() -> None:
    connection = _create_connection()
    try:
        connection.execute(
            sa.text(
                """
                CREATE TABLE assets (
                    id TEXT PRIMARY KEY,
                    owner_party_id TEXT NOT NULL,
                    manager_party_id TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            sa.text(
                """
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    manager_party_id TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            sa.text(
                """
                CREATE TABLE rent_contracts (
                    id TEXT PRIMARY KEY,
                    owner_party_id TEXT NOT NULL,
                    manager_party_id TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            sa.text(
                """
                CREATE TABLE rent_ledger (
                    id TEXT PRIMARY KEY,
                    owner_party_id TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO assets (id, owner_party_id, manager_party_id)
                VALUES ('a1', 'owner-1', 'manager-1')
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO projects (id, manager_party_id)
                VALUES ('p1', 'manager-1')
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO rent_contracts (id, owner_party_id, manager_party_id)
                VALUES ('c1', 'owner-1', 'manager-1')
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO rent_ledger (id, owner_party_id)
                VALUES ('l1', 'owner-1')
                """
            )
        )

        assert _check_assets_owner_party_not_null(connection) == ("PASS", 0)
        assert _check_assets_manager_party_not_null(connection) == ("PASS", 0)
        assert _check_projects_manager_party_not_null(connection) == ("PASS", 0)
        assert _check_rent_contracts_owner_party_not_null(connection) == ("PASS", 0)
        assert _check_rent_contracts_manager_party_not_null(connection) == ("PASS", 0)
        assert _check_rent_ledger_owner_party_not_null(connection) == ("PASS", 0)
    finally:
        _close_connection(connection)


def test_reconciliation_checks_fail_when_party_columns_are_empty() -> None:
    connection = _create_connection()
    try:
        connection.execute(
            sa.text(
                """
                CREATE TABLE assets (
                    id TEXT PRIMARY KEY,
                    owner_party_id TEXT,
                    manager_party_id TEXT
                )
                """
            )
        )
        connection.execute(
            sa.text(
                """
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    manager_party_id TEXT
                )
                """
            )
        )
        connection.execute(
            sa.text(
                """
                CREATE TABLE rent_contracts (
                    id TEXT PRIMARY KEY,
                    owner_party_id TEXT,
                    manager_party_id TEXT
                )
                """
            )
        )
        connection.execute(
            sa.text(
                """
                CREATE TABLE rent_ledger (
                    id TEXT PRIMARY KEY,
                    owner_party_id TEXT
                )
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO assets (id, owner_party_id, manager_party_id)
                VALUES ('a1', NULL, '')
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO projects (id, manager_party_id)
                VALUES ('p1', NULL)
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO rent_contracts (id, owner_party_id, manager_party_id)
                VALUES ('c1', NULL, '')
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO rent_ledger (id, owner_party_id)
                VALUES ('l1', '')
                """
            )
        )

        assert _check_assets_owner_party_not_null(connection) == ("FAIL", 1)
        assert _check_assets_manager_party_not_null(connection) == ("FAIL", 1)
        assert _check_projects_manager_party_not_null(connection) == ("FAIL", 1)
        assert _check_rent_contracts_owner_party_not_null(connection) == ("FAIL", 1)
        assert _check_rent_contracts_manager_party_not_null(connection) == ("FAIL", 1)
        assert _check_rent_ledger_owner_party_not_null(connection) == ("FAIL", 1)
    finally:
        _close_connection(connection)


def test_reconciliation_checks_skip_when_required_columns_missing() -> None:
    connection = _create_connection()
    try:
        connection.execute(
            sa.text(
                """
                CREATE TABLE assets (
                    id TEXT PRIMARY KEY
                )
                """
            )
        )
        assert _check_assets_owner_party_not_null(connection) == ("SKIP", 0)
        assert _check_assets_manager_party_not_null(connection) == ("SKIP", 0)
    finally:
        _close_connection(connection)
