"""Backfill role data-policy package bindings."""

from __future__ import annotations

import argparse
import uuid
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa

from ....database_url import get_database_url

POLICY_PACKAGE_TO_NAME: dict[str, str] = {
    "platform_admin": "platform_admin",
    "asset_owner_operator": "asset_owner_operator",
    "asset_manager_operator": "asset_manager_operator",
    "dual_party_viewer": "dual_party_viewer",
    "project_manager_operator": "project_manager_operator",
    "audit_viewer": "audit_viewer",
    "no_data_access": "no_data_access",
}


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _table_exists(connection: sa.engine.Connection, table_name: str) -> bool:
    return sa.inspect(connection).has_table(table_name)


def _choose_policy_package(role: dict[str, Any]) -> str:
    name = _normalize_text(role.get("name"))
    category = _normalize_text(role.get("category"))
    display_name = _normalize_text(role.get("display_name"))
    token = " ".join([name, category, display_name])

    if "admin" in token:
        return "platform_admin"
    if "audit" in token or "审计" in token:
        return "audit_viewer"
    if "project" in token or "项目" in token:
        return "project_manager_operator"
    if "owner" in token or "产权" in token:
        return "asset_owner_operator"
    if "manager" in token or "运营" in token:
        return "asset_manager_operator"
    if "viewer" in token or "read" in token or "只读" in token:
        return "dual_party_viewer"
    return "no_data_access"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL override. Default reads DATABASE_URL.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    database_url = args.database_url or get_database_url()

    policy_name_to_id = dict(POLICY_PACKAGE_TO_NAME)

    engine = sa.create_engine(database_url, future=True)
    scanned = 0
    updated = 0
    skipped = 0
    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                if (
                    not _table_exists(conn, "roles")
                    or not _table_exists(conn, "abac_policies")
                    or not _table_exists(conn, "abac_role_policies")
                ):
                    if args.dry_run:
                        transaction.rollback()
                    else:
                        transaction.commit()
                    print("[SKIP] roles/abac_* table missing")
                    return 0

                policy_rows = conn.execute(
                    sa.text("SELECT id, name FROM abac_policies")
                ).mappings().all()
                policy_by_name = {str(row["name"]): str(row["id"]) for row in policy_rows}

                template_policy_ids = [
                    policy_by_name[name]
                    for name in policy_name_to_id.values()
                    if name in policy_by_name
                ]

                role_rows = conn.execute(
                    sa.text(
                        """
                        SELECT id, name, display_name, category, is_system_role
                        FROM roles
                        """
                    )
                ).mappings().all()
                scanned = len(role_rows)

                role_policy_table = sa.table(
                    "abac_role_policies",
                    sa.column("role_id", sa.String()),
                    sa.column("policy_id", sa.String()),
                )
                delete_template_stmt = sa.delete(role_policy_table).where(
                    role_policy_table.c.role_id == sa.bindparam("role_id"),
                    role_policy_table.c.policy_id.in_(
                        sa.bindparam("template_policy_ids", expanding=True)
                    ),
                )

                now = _utcnow_naive()
                for role in role_rows:
                    role_id = str(role["id"])
                    package_code = _choose_policy_package(role)
                    policy_name = policy_name_to_id.get(package_code)
                    if policy_name is None or policy_name not in policy_by_name:
                        skipped += 1
                        continue
                    policy_id = policy_by_name[policy_name]

                    if template_policy_ids:
                        conn.execute(
                            delete_template_stmt,
                            {
                                "role_id": role_id,
                                "template_policy_ids": template_policy_ids,
                            },
                        )

                    updated += 1
                    if args.dry_run:
                        continue

                    conn.execute(
                        sa.text(
                            """
                            INSERT INTO abac_role_policies (
                                id, role_id, policy_id, enabled, created_at, updated_at
                            ) VALUES (
                                :id, :role_id, :policy_id, :enabled, :created_at, :updated_at
                            )
                            """
                        ),
                        {
                            "id": str(uuid.uuid4()),
                            "role_id": role_id,
                            "policy_id": policy_id,
                            "enabled": True,
                            "created_at": now,
                            "updated_at": now,
                        },
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
    print(
        f"[{mode}] backfill_role_policies scanned={scanned} updated={updated} skipped={skipped}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
