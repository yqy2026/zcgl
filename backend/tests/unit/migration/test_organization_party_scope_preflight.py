"""Tests for the Organization/Party scope cutover preflight."""

from __future__ import annotations

import sqlalchemy as sa

from src.scripts.migration.party_migration.organization_party_scope_preflight import (
    collect_preflight,
    evaluate_preflight,
    overall_result,
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


def _create_source_schema(connection: sa.engine.Connection) -> None:
    connection.execute(
        sa.text(
            """
            CREATE TABLE parties (
                id TEXT PRIMARY KEY,
                party_type TEXT NOT NULL,
                name TEXT NOT NULL,
                code TEXT NOT NULL,
                metadata TEXT
            )
            """
        )
    )
    connection.execute(
        sa.text(
            """
            CREATE TABLE organizations (
                id TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                status TEXT NOT NULL,
                parent_id TEXT REFERENCES organizations(id)
            )
            """
        )
    )
    connection.execute(
        sa.text(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                is_active BOOLEAN NOT NULL,
                default_organization_id TEXT REFERENCES organizations(id)
            )
            """
        )
    )
    connection.execute(
        sa.text(
            """
            CREATE TABLE party_hierarchy (
                id TEXT PRIMARY KEY,
                parent_party_id TEXT REFERENCES parties(id),
                child_party_id TEXT REFERENCES parties(id)
            )
            """
        )
    )
    connection.execute(
        sa.text(
            """
            CREATE TABLE user_party_bindings (
                id TEXT PRIMARY KEY,
                party_id TEXT REFERENCES parties(id),
                relation_type TEXT NOT NULL
            )
            """
        )
    )
    connection.execute(
        sa.text(
            """
            CREATE TABLE assets (
                id TEXT PRIMARY KEY,
                owner_party_id TEXT REFERENCES parties(id),
                manager_party_id TEXT REFERENCES parties(id)
            )
            """
        )
    )


def test_preflight_reports_legacy_party_references_without_sensitive_metadata() -> None:
    connection = _create_connection()
    try:
        _create_source_schema(connection)
        connection.execute(
            sa.text(
                """
                INSERT INTO parties (id, party_type, name, code, metadata)
                VALUES (
                    'party-legacy',
                    'organization',
                    'Legacy owner',
                    'OLD-1',
                    '{"national_id": "440101199001011234"}'
                )
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO assets (id, owner_party_id, manager_party_id)
                VALUES ('asset-1', 'party-legacy', 'party-legacy')
                """
            )
        )

        snapshot = collect_preflight(connection)
        legacy_party = snapshot["legacy_parties"][0]

        assert legacy_party == {
            "id": "party-legacy",
            "party_type": "organization",
            "name": "Legacy owner",
            "reference_counts": {
                "assets.manager_party_id": 1,
                "assets.owner_party_id": 1,
            },
        }
        assert "metadata" not in str(snapshot)
        assert "440101199001011234" not in str(snapshot)
        assert overall_result(evaluate_preflight(snapshot)) == "FAIL"
    finally:
        _close_connection(connection)


def test_preflight_fails_closed_for_every_unresolved_cutover_input() -> None:
    connection = _create_connection()
    try:
        _create_source_schema(connection)
        connection.execute(
            sa.text(
                """
                INSERT INTO parties (id, party_type, name, code)
                VALUES ('party-legal', 'legal_entity', 'Legal owner', 'OLD-CODE')
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO party_hierarchy (id, parent_party_id, child_party_id)
                VALUES ('hierarchy-1', 'party-legal', 'party-legal')
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO user_party_bindings (id, party_id, relation_type)
                VALUES ('binding-1', 'party-legal', 'headquarters')
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO users (id, is_active, default_organization_id)
                VALUES ('user-unclassified', true, NULL)
                """
            )
        )

        snapshot = collect_preflight(connection)
        failed = {
            evaluation.name
            for evaluation in evaluate_preflight(snapshot)
            if evaluation.status == "FAIL"
        }

        assert failed >= {
            "party_hierarchy_empty",
            "headquarters_bindings_empty",
            "organizationless_users_classified",
            "party_codes_cutover_ready",
        }
        assert snapshot["unclassified_users"] == [
            {
                "id": "user-unclassified",
                "is_active": True,
                "organization_id": None,
            }
        ]
    finally:
        _close_connection(connection)


def test_preflight_passes_for_clean_source_data() -> None:
    connection = _create_connection()
    try:
        _create_source_schema(connection)
        connection.execute(
            sa.text(
                """
                INSERT INTO organizations (id, code, status, parent_id)
                VALUES ('org-1', 'ORG-1', 'active', NULL)
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO users (id, is_active, default_organization_id)
                VALUES ('user-human', true, 'org-1')
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO parties (id, party_type, name, code)
                VALUES
                    ('party-legal', 'legal_entity', 'Legal owner', 'LE-000001'),
                    ('party-person', 'individual', 'Natural person', 'NP-000001')
                """
            )
        )

        snapshot = collect_preflight(connection)
        evaluations = evaluate_preflight(snapshot)

        assert snapshot["legacy_parties"] == []
        assert snapshot["unclassified_users"] == []
        assert all(item.status == "PASS" for item in evaluations)
        assert overall_result(evaluations) == "PASS"
    finally:
        _close_connection(connection)


def test_preflight_rejects_organization_cycles_and_inactive_user_ancestor_chain() -> (
    None
):
    connection = _create_connection()
    try:
        _create_source_schema(connection)
        connection.execute(
            sa.text(
                """
                INSERT INTO organizations (id, code, status, parent_id)
                VALUES
                    ('org-root', 'ROOT', 'inactive', NULL),
                    ('org-child', 'CHILD', 'active', 'org-root'),
                    ('org-cycle-a', 'CYCLE-A', 'active', 'org-cycle-b'),
                    ('org-cycle-b', 'CYCLE-B', 'active', 'org-cycle-a')
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO users (id, is_active, default_organization_id)
                VALUES ('user-broken-chain', true, 'org-child')
                """
            )
        )

        snapshot = collect_preflight(connection)
        failed = {
            evaluation.name
            for evaluation in evaluate_preflight(snapshot)
            if evaluation.status == "FAIL"
        }

        assert snapshot["organization_cycle_ids"] == ["org-cycle-a", "org-cycle-b"]
        assert snapshot["invalid_active_user_chain_ids"] == ["user-broken-chain"]
        assert failed >= {
            "organization_hierarchy_acyclic",
            "active_user_organization_chains_valid",
        }
    finally:
        _close_connection(connection)
