"""Tests for the asset-operations v5 cutover preflight."""

from __future__ import annotations

import sqlalchemy as sa

from src.scripts.migration.asset_operations_v5.preflight import (
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
    statements = (
        "CREATE TABLE parties (id TEXT PRIMARY KEY)",
        "CREATE TABLE projects (id TEXT PRIMARY KEY)",
        """
        CREATE TABLE assets (
            id TEXT PRIMARY KEY,
            asset_name TEXT,
            owner_party_id TEXT,
            address TEXT,
            actual_property_area NUMERIC,
            rentable_area NUMERIC,
            land_area NUMERIC,
            business_category TEXT,
            revenue_mode TEXT,
            operation_agreement_start_date DATE,
            data_status TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE project_assets (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            asset_id TEXT,
            valid_from DATETIME,
            valid_to DATETIME
        )
        """,
        "CREATE TABLE property_certificates (id TEXT PRIMARY KEY)",
        """
        CREATE TABLE property_cert_assets (
            certificate_id TEXT,
            asset_id TEXT
        )
        """,
        "CREATE TABLE contract_groups (contract_group_id TEXT PRIMARY KEY)",
        "CREATE TABLE contracts (contract_id TEXT PRIMARY KEY)",
        "CREATE TABLE contract_ledger_entries (entry_id TEXT PRIMARY KEY)",
        "CREATE TABLE operational_payment_flows (flow_id TEXT PRIMARY KEY)",
        "CREATE TABLE service_fee_ledgers (service_fee_entry_id TEXT PRIMARY KEY)",
    )
    for statement in statements:
        connection.execute(sa.text(statement))


def _insert_mappable_asset(connection: sa.engine.Connection) -> None:
    connection.execute(sa.text("INSERT INTO parties (id) VALUES ('party-1')"))
    connection.execute(sa.text("INSERT INTO projects (id) VALUES ('project-1')"))
    connection.execute(
        sa.text(
            """
            INSERT INTO assets (
                id, asset_name, owner_party_id, address,
                actual_property_area, rentable_area, land_area,
                business_category, revenue_mode,
                operation_agreement_start_date, data_status
            ) VALUES (
                'asset-1', 'Sensitive asset name', 'party-1', 'Sensitive address',
                100, 80, 10,
                'commercial', 'lease',
                '2026-01-01', '正常'
            )
            """
        )
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO project_assets (
                id, project_id, asset_id, valid_from, valid_to
            ) VALUES (
                'binding-1', 'project-1', 'asset-1', '2026-01-01', NULL
            )
            """
        )
    )


def test_preflight_fails_closed_when_required_source_tables_are_missing() -> None:
    connection = _create_connection()
    try:
        snapshot = collect_preflight(connection)
        evaluations = evaluate_preflight(snapshot)

        assert snapshot["missing_tables"]
        assert overall_result(evaluations) == "FAIL"
        assert evaluations[0].name == "required_source_schema_present"
        assert evaluations[0].status == "FAIL"
    finally:
        _close_connection(connection)


def test_preflight_is_read_only_and_omits_business_names_and_addresses() -> None:
    connection = _create_connection()
    try:
        _create_source_schema(connection)
        _insert_mappable_asset(connection)
        writes: list[str] = []

        @sa.event.listens_for(connection, "before_cursor_execute")
        def _capture_statements(
            _connection: sa.engine.Connection,
            _cursor: object,
            statement: str,
            _parameters: object,
            _context: object,
            _executemany: bool,
        ) -> None:
            keyword = statement.lstrip().split(maxsplit=1)[0].upper()
            if keyword in {"INSERT", "UPDATE", "DELETE", "ALTER", "DROP", "CREATE"}:
                writes.append(statement)

        snapshot = collect_preflight(connection)

        assert writes == []
        assert "Sensitive asset name" not in str(snapshot)
        assert "Sensitive address" not in str(snapshot)
        assert snapshot["asset_mapping_issues"] == []
        assert snapshot["row_counts"]["assets"] == 1
    finally:
        _close_connection(connection)


def test_preflight_reports_asset_mapping_gaps_by_id_and_issue_code() -> None:
    connection = _create_connection()
    try:
        _create_source_schema(connection)
        connection.execute(
            sa.text(
                """
                INSERT INTO assets (
                    id, asset_name, owner_party_id, address,
                    actual_property_area, rentable_area, land_area,
                    business_category, revenue_mode,
                    operation_agreement_start_date, data_status
                ) VALUES (
                    'asset-broken', 'Do not expose me', NULL, '',
                    50, 60, -1,
                    NULL, 'unknown-mode',
                    NULL, '正常'
                )
                """
            )
        )

        snapshot = collect_preflight(connection)

        assert snapshot["asset_mapping_issues"] == [
            {
                "asset_id": "asset-broken",
                "issue_codes": [
                    "acquisition_mode_unmapped",
                    "active_project_binding_missing",
                    "address_missing",
                    "area_invalid",
                    "managed_from_missing",
                    "owner_party_missing",
                    "usage_type_missing",
                ],
            }
        ]
        assert overall_result(evaluate_preflight(snapshot)) == "FAIL"
        assert "Do not expose me" not in str(snapshot)
    finally:
        _close_connection(connection)


def test_preflight_requires_explicit_review_for_legacy_operational_rows() -> None:
    connection = _create_connection()
    try:
        _create_source_schema(connection)
        _insert_mappable_asset(connection)
        connection.execute(
            sa.text("INSERT INTO contracts (contract_id) VALUES ('legacy-contract-1')")
        )
        connection.execute(
            sa.text(
                "INSERT INTO contract_ledger_entries (entry_id) "
                "VALUES ('legacy-ledger-1')"
            )
        )

        snapshot = collect_preflight(connection)
        evaluations = {item.name: item for item in evaluate_preflight(snapshot)}

        assert snapshot["row_counts"]["contracts"] == 1
        assert snapshot["row_counts"]["contract_ledger_entries"] == 1
        assert evaluations["legacy_operational_data_resolved"].status == "FAIL"
        assert evaluations["legacy_operational_data_resolved"].actual == 2
    finally:
        _close_connection(connection)


def test_preflight_passes_for_mappable_assets_without_legacy_operations() -> None:
    connection = _create_connection()
    try:
        _create_source_schema(connection)
        _insert_mappable_asset(connection)

        snapshot = collect_preflight(connection)
        evaluations = evaluate_preflight(snapshot)

        assert snapshot["missing_tables"] == []
        assert snapshot["asset_mapping_issues"] == []
        assert all(item.status == "PASS" for item in evaluations)
        assert overall_result(evaluations) == "PASS"
    finally:
        _close_connection(connection)
