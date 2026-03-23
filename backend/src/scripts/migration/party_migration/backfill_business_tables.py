"""Backfill business tables with party columns."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import sqlalchemy as sa

from ....database_url import get_database_url

LEGACY_CONTRACTS_TABLE = "_".join(("rent", "contracts"))
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(identifier: str) -> str:
    if not _IDENTIFIER_RE.fullmatch(identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier}")
    return identifier


def _load_mapping(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return {
        str(key).strip(): str(value).strip()
        for key, value in payload.items()
        if str(key).strip() != "" and str(value).strip() != ""
    }


def _column_exists(
    connection: sa.engine.Connection,
    table_name: str,
    column_name: str,
) -> bool:
    inspector = sa.inspect(connection)
    if not inspector.has_table(table_name):
        return False
    columns = inspector.get_columns(table_name)
    return any(str(column.get("name")) == column_name for column in columns)


def _count_pending_updates(
    connection: sa.engine.Connection,
    *,
    table_name: str,
    source_column: str,
    target_column: str,
    legacy_id: str,
) -> int:
    safe_table_name = _validate_identifier(table_name)
    safe_source_column = _validate_identifier(source_column)
    safe_target_column = _validate_identifier(target_column)
    dynamic_table = sa.table(
        safe_table_name,
        sa.column(safe_source_column),
        sa.column(safe_target_column),
    )
    source_expr = getattr(dynamic_table.c, safe_source_column)
    target_expr = getattr(dynamic_table.c, safe_target_column)
    stmt = (
        sa.select(sa.func.count())
        .select_from(dynamic_table)
        .where(
            source_expr == sa.bindparam("legacy_id"),
            sa.or_(target_expr.is_(None), target_expr == ""),
        )
    )
    return int(connection.execute(stmt, {"legacy_id": legacy_id}).scalar() or 0)


def _apply_mapping_updates(
    connection: sa.engine.Connection,
    *,
    table_name: str,
    source_column: str,
    target_column: str,
    mapping: dict[str, str],
    dry_run: bool,
) -> int:
    if not mapping:
        return 0

    if not _column_exists(connection, table_name, source_column):
        return 0
    if not _column_exists(connection, table_name, target_column):
        return 0

    affected_rows = 0
    for legacy_id, party_id in mapping.items():
        if dry_run:
            affected_rows += _count_pending_updates(
                connection,
                table_name=table_name,
                source_column=source_column,
                target_column=target_column,
                legacy_id=legacy_id,
            )
            continue

        safe_table_name = _validate_identifier(table_name)
        safe_source_column = _validate_identifier(source_column)
        safe_target_column = _validate_identifier(target_column)
        dynamic_table = sa.table(
            safe_table_name,
            sa.column(safe_source_column),
            sa.column(safe_target_column),
        )
        source_expr = getattr(dynamic_table.c, safe_source_column)
        target_expr = getattr(dynamic_table.c, safe_target_column)
        stmt = (
            sa.update(dynamic_table)
            .where(
                source_expr == sa.bindparam("legacy_id"),
                sa.or_(target_expr.is_(None), target_expr == ""),
            )
            .values({safe_target_column: sa.bindparam("party_id")})
        )
        result = connection.execute(
            stmt,
            {"party_id": party_id, "legacy_id": legacy_id},
        )
        affected_rows += int(result.rowcount or 0)

    return affected_rows


def _backfill_role_scope(
    connection: sa.engine.Connection,
    *,
    org_to_party_map: dict[str, str],
    dry_run: bool,
) -> int:
    if not org_to_party_map:
        return 0
    if not _column_exists(connection, "roles", "scope"):
        return 0
    if not _column_exists(connection, "roles", "scope_id"):
        return 0

    if dry_run:
        return int(
            connection.execute(
                sa.text("SELECT count(*) FROM roles WHERE scope = 'organization'")
            ).scalar()
            or 0
        )

    updated_rows = 0
    stmt_scope = sa.text(
        """
        UPDATE roles
        SET scope = 'party'
        WHERE scope = 'organization'
        """
    )
    updated_rows += int(connection.execute(stmt_scope).rowcount or 0)

    for org_id, party_id in org_to_party_map.items():
        stmt_scope_id = sa.text(
            """
            UPDATE roles
            SET scope_id = :party_id
            WHERE scope_id = :org_id
              AND (scope = 'party' OR scope = 'party_subtree')
            """
        )
        updated_rows += int(
            connection.execute(
                stmt_scope_id,
                {"org_id": org_id, "party_id": party_id},
            ).rowcount
            or 0
        )
    return updated_rows


def _build_operations(
    *,
    org_to_party_map: dict[str, str],
    ownership_to_party_map: dict[str, str],
) -> list[tuple[str, str, str, str, dict[str, str]]]:
    return [
        (
            "assets.owner_party_id",
            "assets",
            "ownership_id",
            "owner_party_id",
            ownership_to_party_map,
        ),
        (
            "assets.manager_party_id",
            "assets",
            "organization_id",
            "manager_party_id",
            org_to_party_map,
        ),
        (
            "legacy_contracts.owner_party_id",
            LEGACY_CONTRACTS_TABLE,
            "ownership_id",
            "owner_party_id",
            ownership_to_party_map,
        ),
        (
            "rent_ledger.owner_party_id",
            "rent_ledger",
            "ownership_id",
            "owner_party_id",
            ownership_to_party_map,
        ),
        (
            "projects.manager_party_id",
            "projects",
            "organization_id",
            "manager_party_id",
            org_to_party_map,
        ),
        (
            "roles.party_id",
            "roles",
            "organization_id",
            "party_id",
            org_to_party_map,
        ),
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL override. Default reads DATABASE_URL.",
    )
    parser.add_argument(
        "--mapping-dir",
        type=Path,
        default=Path("migration-artifacts/party"),
        help="Directory containing org_to_party_map.json and ownership_to_party_map.json.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    database_url = args.database_url or get_database_url()

    org_to_party_map = _load_mapping(args.mapping_dir / "org_to_party_map.json")
    ownership_to_party_map = _load_mapping(
        args.mapping_dir / "ownership_to_party_map.json"
    )

    engine = sa.create_engine(database_url, future=True)
    summary: dict[str, int] = {}
    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                operations = _build_operations(
                    org_to_party_map=org_to_party_map,
                    ownership_to_party_map=ownership_to_party_map,
                )

                for (
                    summary_key,
                    table_name,
                    source_column,
                    target_column,
                    mapping,
                ) in operations:
                    summary[summary_key] = _apply_mapping_updates(
                        conn,
                        table_name=table_name,
                        source_column=source_column,
                        target_column=target_column,
                        mapping=mapping,
                        dry_run=args.dry_run,
                    )

                summary["roles.scope_scope_id"] = _backfill_role_scope(
                    conn,
                    org_to_party_map=org_to_party_map,
                    dry_run=args.dry_run,
                )

                if args.dry_run:
                    transaction.rollback()
                else:
                    transaction.commit()
            except Exception:
                transaction.rollback()
                raise
    finally:
        engine.dispose()

    mode = "DRY-RUN" if args.dry_run else "EXEC"
    print(f"[{mode}] backfill_business_tables")
    for key, value in summary.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
