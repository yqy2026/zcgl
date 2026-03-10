"""Tests for Phase4 No-Go SQL snapshot script."""

from __future__ import annotations

import sqlalchemy as sa

from src.scripts.migration.party_migration.phase4_no_go_snapshot import (
    LEGACY_CONTRACTS_TABLE,
    collect_snapshot,
    evaluate_snapshot,
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


def _create_phase4_tables(connection: sa.engine.Connection) -> None:
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
            f"""
            CREATE TABLE {LEGACY_CONTRACTS_TABLE} (
                id TEXT PRIMARY KEY,
                owner_party_id TEXT,
                manager_party_id TEXT,
                tenant_party_id TEXT
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
            CREATE TABLE roles (
                id TEXT PRIMARY KEY,
                name TEXT
            )
            """
        )
    )
    connection.execute(
        sa.text(
            """
            CREATE TABLE abac_policies (
                id TEXT PRIMARY KEY,
                name TEXT
            )
            """
        )
    )
    connection.execute(
        sa.text(
            """
            CREATE TABLE abac_role_policies (
                role_id TEXT,
                policy_id TEXT
            )
            """
        )
    )


def test_snapshot_and_gate_pass_for_decision_a() -> None:
    connection = _create_connection()
    try:
        _create_phase4_tables(connection)
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
                f"""
                INSERT INTO {LEGACY_CONTRACTS_TABLE} (id, owner_party_id, manager_party_id, tenant_party_id)
                VALUES ('c1', 'owner-1', 'manager-1', 'tenant-1')
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
                INSERT INTO roles (id, name) VALUES ('r1', 'user')
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO abac_policies (id, name) VALUES ('p1', 'dual_party_viewer')
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO abac_role_policies (role_id, policy_id) VALUES ('r1', 'p1')
                """
            )
        )

        snapshot = collect_snapshot(connection)
        evaluations = evaluate_snapshot(snapshot, tenant_decision="A")

        assert snapshot["subject_table"] == "null"
        assert snapshot["subject_count"] == 0
        assert snapshot["assets_owner_null"] == 0
        assert snapshot["assets_manager_null"] == 0
        assert snapshot["legacy_contract_owner_null"] == 0
        assert snapshot["legacy_contract_manager_null"] == 0
        assert "_".join(("rc", "owner", "null")) not in snapshot
        assert "_".join(("rc", "manager", "null")) not in snapshot
        assert snapshot["ledger_owner_null"] == 0
        assert snapshot["projects_manager_null"] == 0
        assert snapshot["tenant_null_count"] == 0
        assert snapshot["tenant_total_count"] == 1
        assert snapshot["user_dual_party_viewer_mapping_count"] == 1
        assert all(item.status == "PASS" for item in evaluations)
        assert overall_result(evaluations) == "PASS"
    finally:
        _close_connection(connection)


def test_snapshot_gate_fails_when_required_metrics_not_met() -> None:
    connection = _create_connection()
    try:
        _create_phase4_tables(connection)
        connection.execute(
            sa.text(
                """
                CREATE TABLE abac_policy_subjects (
                    id TEXT PRIMARY KEY
                )
                """
            )
        )
        connection.execute(
            sa.text("INSERT INTO abac_policy_subjects (id) VALUES ('s1')")
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO assets (id, owner_party_id, manager_party_id)
                VALUES ('a1', NULL, 'manager-1')
                """
            )
        )
        connection.execute(
            sa.text(
                f"""
                INSERT INTO {LEGACY_CONTRACTS_TABLE} (id, owner_party_id, manager_party_id, tenant_party_id)
                VALUES ('c1', 'owner-1', 'manager-1', NULL)
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
        connection.execute(
            sa.text(
                """
                INSERT INTO projects (id, manager_party_id)
                VALUES ('p1', 'manager-1')
                """
            )
        )

        snapshot = collect_snapshot(connection)
        evaluations = evaluate_snapshot(snapshot, tenant_decision="A")
        failed = {item.name for item in evaluations if item.status == "FAIL"}

        assert "subject_count_zero" in failed
        assert "assets_owner_null_zero" in failed
        assert "legacy_contract_owner_null_zero" not in failed
        assert "legacy_contract_manager_null_zero" not in failed
        assert "tenant_null_zero_when_decision_a" in failed
        assert "user_dual_party_viewer_mapping_ge_1" in failed
        assert overall_result(evaluations) == "FAIL"
    finally:
        _close_connection(connection)


def test_decision_b_skips_tenant_not_null_gate() -> None:
    connection = _create_connection()
    try:
        _create_phase4_tables(connection)
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
                f"""
                INSERT INTO {LEGACY_CONTRACTS_TABLE} (id, owner_party_id, manager_party_id, tenant_party_id)
                VALUES ('c1', 'owner-1', 'manager-1', NULL)
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
        connection.execute(
            sa.text(
                """
                INSERT INTO projects (id, manager_party_id)
                VALUES ('p1', 'manager-1')
                """
            )
        )
        connection.execute(sa.text("INSERT INTO roles (id, name) VALUES ('r1', 'user')"))
        connection.execute(
            sa.text("INSERT INTO abac_policies (id, name) VALUES ('p1', 'dual_party_viewer')")
        )
        connection.execute(
            sa.text("INSERT INTO abac_role_policies (role_id, policy_id) VALUES ('r1', 'p1')")
        )

        snapshot = collect_snapshot(connection)
        evaluations = evaluate_snapshot(snapshot, tenant_decision="B")
        results_by_gate = {item.name: item.status for item in evaluations}

        assert snapshot["tenant_null_count"] == 1
        assert results_by_gate["tenant_decision_declared"] == "PASS"
        assert results_by_gate["tenant_null_zero_when_decision_a"] == "SKIP"
        assert overall_result(evaluations) == "PASS"
    finally:
        _close_connection(connection)


def test_unset_tenant_decision_is_fail_closed() -> None:
    connection = _create_connection()
    try:
        _create_phase4_tables(connection)
        snapshot = collect_snapshot(connection)
        evaluations = evaluate_snapshot(snapshot, tenant_decision=None)
        results_by_gate = {item.name: item.status for item in evaluations}

        assert results_by_gate["tenant_decision_declared"] == "FAIL"
        assert overall_result(evaluations) == "FAIL"
    finally:
        _close_connection(connection)
