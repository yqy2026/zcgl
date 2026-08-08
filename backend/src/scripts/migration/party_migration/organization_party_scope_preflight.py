"""Read-only gate for the Organization/Party scope model cutover."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from typing import Any

import sqlalchemy as sa

from ....database_url import get_database_url

_REQUIRED_TABLES = {
    "organizations",
    "parties",
    "party_hierarchy",
    "user_party_bindings",
    "users",
}
_PARTY_CODE_PATTERNS = {
    "legal_entity": re.compile(r"^LE-\d{6}$"),
    "individual": re.compile(r"^NP-\d{6}$"),
}


@dataclass(frozen=True)
class GateEvaluation:
    """One cutover gate result."""

    name: str
    status: str
    actual: int
    expected: str


def _count(connection: sa.engine.Connection, sql: str) -> int:
    return int(connection.execute(sa.text(sql)).scalar() or 0)


def _columns(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {str(column["name"]) for column in inspector.get_columns(table_name)}


def _party_reference_counts(
    connection: sa.engine.Connection,
    inspector: sa.Inspector,
    party_id: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table_name in inspector.get_table_names():
        for foreign_key in inspector.get_foreign_keys(table_name):
            if foreign_key.get("referred_table") != "parties":
                continue
            constrained_columns = foreign_key.get("constrained_columns") or []
            if len(constrained_columns) != 1:
                continue
            column_name = str(constrained_columns[0])
            quoted_table = inspector.bind.dialect.identifier_preparer.quote(table_name)
            quoted_column = inspector.bind.dialect.identifier_preparer.quote(
                column_name
            )
            count = int(
                connection.execute(
                    sa.text(
                        f"SELECT COUNT(*) FROM {quoted_table} "  # nosec B608 - identifiers come from Inspector
                        f"WHERE {quoted_column} = :party_id"
                    ),
                    {"party_id": party_id},
                ).scalar()
                or 0
            )
            if count > 0:
                counts[f"{table_name}.{column_name}"] = count
    return dict(sorted(counts.items()))


def _collect_legacy_parties(
    connection: sa.engine.Connection,
    inspector: sa.Inspector,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        sa.text(
            """
            SELECT id, party_type, name
            FROM parties
            WHERE party_type = 'organization'
            ORDER BY id
            """
        )
    ).mappings()
    return [
        {
            "id": str(row["id"]),
            "party_type": str(row["party_type"]),
            "name": str(row["name"]),
            "reference_counts": _party_reference_counts(
                connection,
                inspector,
                str(row["id"]),
            ),
        }
        for row in rows
    ]


def _collect_unclassified_users(
    connection: sa.engine.Connection,
    inspector: sa.Inspector,
) -> list[dict[str, Any]]:
    columns = _columns(inspector, "users")
    organization_column = (
        "organization_id" if "organization_id" in columns else "default_organization_id"
    )
    account_type_expression = "account_type" if "account_type" in columns else "NULL"
    rows = connection.execute(
        sa.text(
            f"""
            SELECT id, is_active, {organization_column} AS organization_id,
                   {account_type_expression} AS account_type
            FROM users
            WHERE {organization_column} IS NULL
              AND ({account_type_expression} IS NULL
                   OR {account_type_expression} NOT IN ('service', 'system'))
            ORDER BY id
            """  # nosec B608 - column names are selected from a fixed allowlist
        )
    ).mappings()
    return [
        {
            "id": str(row["id"]),
            "is_active": bool(row["is_active"]),
            "organization_id": None,
        }
        for row in rows
    ]


def _collect_invalid_party_code_ids(
    connection: sa.engine.Connection,
) -> list[str]:
    rows = connection.execute(
        sa.text(
            """
            SELECT id, party_type, code
            FROM parties
            WHERE party_type IN ('legal_entity', 'individual')
            ORDER BY id
            """
        )
    ).mappings()
    invalid_ids: list[str] = []
    seen_codes: set[str] = set()
    duplicate_codes: set[str] = set()
    for row in rows:
        code = str(row["code"])
        pattern = _PARTY_CODE_PATTERNS[str(row["party_type"])]
        if pattern.fullmatch(code) is None:
            invalid_ids.append(str(row["id"]))
        if code in seen_codes:
            duplicate_codes.add(code)
        seen_codes.add(code)
    if duplicate_codes:
        duplicate_rows = connection.execute(
            sa.text("SELECT id, code FROM parties ORDER BY id")
        ).mappings()
        invalid_ids.extend(
            str(row["id"])
            for row in duplicate_rows
            if str(row["code"]) in duplicate_codes
        )
    return sorted(set(invalid_ids))


def _collect_organization_chain_issues(
    connection: sa.engine.Connection,
    inspector: sa.Inspector,
) -> tuple[list[str], list[str]]:
    organization_columns = _columns(inspector, "organizations")
    deleted_expression = (
        "is_deleted" if "is_deleted" in organization_columns else "false"
    )
    organization_rows = connection.execute(
        sa.text(
            f"""
            SELECT id, parent_id, status, {deleted_expression} AS is_deleted
            FROM organizations
            """  # nosec B608 - expression comes from a fixed allowlist
        )
    ).mappings()
    organizations = {
        str(row["id"]): {
            "parent_id": str(row["parent_id"])
            if row["parent_id"] is not None
            else None,
            "status": str(row["status"]),
            "is_deleted": bool(row["is_deleted"]),
        }
        for row in organization_rows
    }

    cycle_ids: set[str] = set()
    for organization_id in organizations:
        path: list[str] = []
        path_positions: dict[str, int] = {}
        current_id: str | None = organization_id
        while current_id is not None and current_id in organizations:
            if current_id in path_positions:
                cycle_ids.update(path[path_positions[current_id] :])
                break
            path_positions[current_id] = len(path)
            path.append(current_id)
            parent_value = organizations[current_id]["parent_id"]
            current_id = parent_value if isinstance(parent_value, str) else None

    user_columns = _columns(inspector, "users")
    organization_column = (
        "organization_id"
        if "organization_id" in user_columns
        else "default_organization_id"
    )
    user_rows = connection.execute(
        sa.text(
            f"""
            SELECT id, {organization_column} AS organization_id
            FROM users
            WHERE is_active = true AND {organization_column} IS NOT NULL
            ORDER BY id
            """  # nosec B608 - column name comes from a fixed allowlist
        )
    ).mappings()
    invalid_user_ids: list[str] = []
    for user_row in user_rows:
        current_id = str(user_row["organization_id"])
        visited: set[str] = set()
        valid = True
        while current_id is not None:
            organization = organizations.get(current_id)
            if (
                organization is None
                or current_id in visited
                or organization["status"] != "active"
                or organization["is_deleted"]
            ):
                valid = False
                break
            visited.add(current_id)
            parent_value = organization["parent_id"]
            current_id = parent_value if isinstance(parent_value, str) else None
        if not valid:
            invalid_user_ids.append(str(user_row["id"]))

    return sorted(cycle_ids), invalid_user_ids


def collect_preflight(connection: sa.engine.Connection) -> dict[str, Any]:
    """Collect privacy-safe source-data facts without changing the database."""

    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())
    missing_tables = sorted(_REQUIRED_TABLES - tables)
    if missing_tables:
        return {
            "missing_tables": missing_tables,
            "legacy_parties": [],
            "party_hierarchy_count": 0,
            "headquarters_binding_count": 0,
            "unclassified_users": [],
            "invalid_party_code_ids": [],
            "duplicate_organization_code_count": 0,
            "organization_cycle_ids": [],
            "invalid_active_user_chain_ids": [],
        }

    organization_cycle_ids, invalid_active_user_chain_ids = (
        _collect_organization_chain_issues(connection, inspector)
    )

    return {
        "missing_tables": [],
        "legacy_parties": _collect_legacy_parties(connection, inspector),
        "party_hierarchy_count": _count(
            connection, "SELECT COUNT(*) FROM party_hierarchy"
        ),
        "headquarters_binding_count": _count(
            connection,
            """
            SELECT COUNT(*)
            FROM user_party_bindings
            WHERE relation_type = 'headquarters'
            """,
        ),
        "unclassified_users": _collect_unclassified_users(connection, inspector),
        "invalid_party_code_ids": _collect_invalid_party_code_ids(connection),
        "duplicate_organization_code_count": _count(
            connection,
            """
            SELECT COUNT(*)
            FROM (
                SELECT code
                FROM organizations
                GROUP BY code
                HAVING COUNT(*) > 1
            ) AS duplicate_codes
            """,
        ),
        "organization_cycle_ids": organization_cycle_ids,
        "invalid_active_user_chain_ids": invalid_active_user_chain_ids,
    }


def evaluate_preflight(snapshot: dict[str, Any]) -> list[GateEvaluation]:
    """Evaluate all cutover inputs fail-closed."""

    metrics = (
        ("required_source_schema_present", len(snapshot["missing_tables"])),
        ("legacy_organization_parties_resolved", len(snapshot["legacy_parties"])),
        ("party_hierarchy_empty", int(snapshot["party_hierarchy_count"])),
        (
            "headquarters_bindings_empty",
            int(snapshot["headquarters_binding_count"]),
        ),
        (
            "organizationless_users_classified",
            len(snapshot["unclassified_users"]),
        ),
        ("party_codes_cutover_ready", len(snapshot["invalid_party_code_ids"])),
        (
            "organization_codes_unique",
            int(snapshot["duplicate_organization_code_count"]),
        ),
        (
            "organization_hierarchy_acyclic",
            len(snapshot["organization_cycle_ids"]),
        ),
        (
            "active_user_organization_chains_valid",
            len(snapshot["invalid_active_user_chain_ids"]),
        ),
    )
    return [
        GateEvaluation(
            name=name,
            status="PASS" if actual == 0 else "FAIL",
            actual=actual,
            expected="=0",
        )
        for name, actual in metrics
    ]


def overall_result(evaluations: list[GateEvaluation]) -> str:
    return "FAIL" if any(item.status == "FAIL" for item in evaluations) else "PASS"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--enforce", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    engine = sa.create_engine(args.database_url or get_database_url(), future=True)
    try:
        with engine.connect() as connection:
            snapshot = collect_preflight(connection)
    finally:
        engine.dispose()

    evaluations = evaluate_preflight(snapshot)
    payload = {
        "snapshot": snapshot,
        "gate_results": [asdict(item) for item in evaluations],
        "result": overall_result(evaluations),
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for item in evaluations:
            print(
                f"gate.{item.name}={item.status} "
                f"actual={item.actual} expected={item.expected}"
            )
        print(f"result={payload['result']}")
        print(json.dumps(snapshot, ensure_ascii=False, sort_keys=True))
    return 1 if args.enforce and payload["result"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
