"""Reconciliation checks for party migration."""

from __future__ import annotations

import argparse
from collections.abc import Callable

import sqlalchemy as sa

from ....database_url import get_database_url

DEFAULT_CHECKS = [
    "assets_owner_party_not_null",
    "assets_manager_party_not_null",
    "projects_manager_party_not_null",
    "rent_contracts_owner_party_not_null",
    "rent_contracts_manager_party_not_null",
    "rent_ledger_owner_party_not_null",
    "project_assets_integrity",
    "user_party_bindings_integrity",
    "role_party_scope_integrity",
    "certificate_party_relations_integrity",
    "abac_policy_binding_integrity",
]


def _table_exists(connection: sa.engine.Connection, table_name: str) -> bool:
    return sa.inspect(connection).has_table(table_name)


def _count_query(connection: sa.engine.Connection, sql_text: str) -> int:
    return int(connection.execute(sa.text(sql_text)).scalar() or 0)


def _result_label(failed_count: int) -> str:
    return "PASS" if failed_count == 0 else "FAIL"


def _check_assets_owner_party_not_null(connection: sa.engine.Connection) -> tuple[str, int]:
    if not _table_exists(connection, "assets"):
        return "SKIP", 0
    failed = _count_query(
        connection,
        """
        SELECT count(*)
        FROM assets
        WHERE ownership_id IS NOT NULL
          AND (owner_party_id IS NULL OR owner_party_id = '')
        """,
    )
    return _result_label(failed), failed


def _check_assets_manager_party_not_null(connection: sa.engine.Connection) -> tuple[str, int]:
    if not _table_exists(connection, "assets"):
        return "SKIP", 0
    failed = _count_query(
        connection,
        """
        SELECT count(*)
        FROM assets
        WHERE organization_id IS NOT NULL
          AND (manager_party_id IS NULL OR manager_party_id = '')
        """,
    )
    return _result_label(failed), failed


def _check_projects_manager_party_not_null(connection: sa.engine.Connection) -> tuple[str, int]:
    if not _table_exists(connection, "projects"):
        return "SKIP", 0
    failed = _count_query(
        connection,
        """
        SELECT count(*)
        FROM projects
        WHERE organization_id IS NOT NULL
          AND (manager_party_id IS NULL OR manager_party_id = '')
        """,
    )
    return _result_label(failed), failed


def _check_rent_contracts_owner_party_not_null(
    connection: sa.engine.Connection,
) -> tuple[str, int]:
    if not _table_exists(connection, "rent_contracts"):
        return "SKIP", 0
    failed = _count_query(
        connection,
        """
        SELECT count(*)
        FROM rent_contracts
        WHERE ownership_id IS NOT NULL
          AND (owner_party_id IS NULL OR owner_party_id = '')
        """,
    )
    return _result_label(failed), failed


def _check_rent_contracts_manager_party_not_null(
    connection: sa.engine.Connection,
) -> tuple[str, int]:
    if not _table_exists(connection, "rent_contracts"):
        return "SKIP", 0
    failed = _count_query(
        connection,
        """
        SELECT count(*)
        FROM rent_contracts
        WHERE manager_party_id IS NULL OR manager_party_id = ''
        """,
    )
    return _result_label(failed), failed


def _check_rent_ledger_owner_party_not_null(
    connection: sa.engine.Connection,
) -> tuple[str, int]:
    if not _table_exists(connection, "rent_ledger"):
        return "SKIP", 0
    failed = _count_query(
        connection,
        """
        SELECT count(*)
        FROM rent_ledger
        WHERE ownership_id IS NOT NULL
          AND (owner_party_id IS NULL OR owner_party_id = '')
        """,
    )
    return _result_label(failed), failed


def _check_project_assets_integrity(connection: sa.engine.Connection) -> tuple[str, int]:
    if not _table_exists(connection, "project_assets"):
        return "SKIP", 0
    failed = _count_query(
        connection,
        """
        SELECT count(*)
        FROM project_assets pa
        LEFT JOIN projects p ON p.id = pa.project_id
        LEFT JOIN assets a ON a.id = pa.asset_id
        WHERE p.id IS NULL OR a.id IS NULL
        """,
    )
    return _result_label(failed), failed


def _check_user_party_bindings_integrity(
    connection: sa.engine.Connection,
) -> tuple[str, int]:
    if not _table_exists(connection, "user_party_bindings"):
        return "SKIP", 0
    failed = _count_query(
        connection,
        """
        SELECT count(*)
        FROM user_party_bindings upb
        LEFT JOIN users u ON u.id = upb.user_id
        LEFT JOIN parties p ON p.id = upb.party_id
        WHERE u.id IS NULL OR p.id IS NULL
        """,
    )
    return _result_label(failed), failed


def _check_role_party_scope_integrity(connection: sa.engine.Connection) -> tuple[str, int]:
    if not _table_exists(connection, "roles"):
        return "SKIP", 0
    failed = _count_query(
        connection,
        """
        SELECT count(*)
        FROM roles
        WHERE scope NOT IN ('global', 'party', 'party_subtree')
           OR (scope IN ('party', 'party_subtree') AND (scope_id IS NULL OR scope_id = ''))
        """,
    )
    return _result_label(failed), failed


def _check_certificate_party_relations_integrity(
    connection: sa.engine.Connection,
) -> tuple[str, int]:
    if not _table_exists(connection, "certificate_party_relations"):
        return "SKIP", 0
    failed = _count_query(
        connection,
        """
        SELECT count(*)
        FROM certificate_party_relations cpr
        LEFT JOIN property_certificates pc ON pc.id = cpr.certificate_id
        LEFT JOIN parties p ON p.id = cpr.party_id
        WHERE pc.id IS NULL OR p.id IS NULL
        """,
    )
    return _result_label(failed), failed


def _check_abac_policy_binding_integrity(
    connection: sa.engine.Connection,
) -> tuple[str, int]:
    if not _table_exists(connection, "abac_role_policies"):
        return "SKIP", 0
    failed = _count_query(
        connection,
        """
        SELECT count(*)
        FROM abac_role_policies arp
        LEFT JOIN roles r ON r.id = arp.role_id
        LEFT JOIN abac_policies ap ON ap.id = arp.policy_id
        WHERE r.id IS NULL OR ap.id IS NULL
        """,
    )
    return _result_label(failed), failed


CHECK_RUNNERS: dict[str, Callable[[sa.engine.Connection], tuple[str, int]]] = {
    "assets_owner_party_not_null": _check_assets_owner_party_not_null,
    "assets_manager_party_not_null": _check_assets_manager_party_not_null,
    "projects_manager_party_not_null": _check_projects_manager_party_not_null,
    "rent_contracts_owner_party_not_null": _check_rent_contracts_owner_party_not_null,
    "rent_contracts_manager_party_not_null": _check_rent_contracts_manager_party_not_null,
    "rent_ledger_owner_party_not_null": _check_rent_ledger_owner_party_not_null,
    "project_assets_integrity": _check_project_assets_integrity,
    "user_party_bindings_integrity": _check_user_party_bindings_integrity,
    "role_party_scope_integrity": _check_role_party_scope_integrity,
    "certificate_party_relations_integrity": _check_certificate_party_relations_integrity,
    "abac_policy_binding_integrity": _check_abac_policy_binding_integrity,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL override. Default reads DATABASE_URL.",
    )
    parser.add_argument("--mode", default="dry-run", help="Execution mode label")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    database_url = args.database_url or get_database_url()

    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.connect() as conn:
            failed_total = 0
            for check_name in DEFAULT_CHECKS:
                runner = CHECK_RUNNERS[check_name]
                status, failed_count = runner(conn)
                if status == "FAIL":
                    failed_total += 1
                if status == "SKIP":
                    print(f"SKIP {check_name}")
                else:
                    print(f"{status} {check_name} failed_count={failed_count}")
    finally:
        engine.dispose()

    print(f"mode={args.mode}")
    return 1 if failed_total > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
