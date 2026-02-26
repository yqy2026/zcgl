"""Backfill user_party_bindings from user defaults and role scope."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import sqlalchemy as sa

from ....database_url import get_database_url


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _table_exists(connection: sa.engine.Connection, table_name: str) -> bool:
    return sa.inspect(connection).has_table(table_name)


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
        help="Directory containing org_to_party_map.json.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    database_url = args.database_url or get_database_url()
    org_to_party_map = _load_mapping(args.mapping_dir / "org_to_party_map.json")

    engine = sa.create_engine(database_url, future=True)
    inserted = 0
    scanned = 0
    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                required_tables = [
                    "users",
                    "roles",
                    "user_role_assignments",
                    "user_party_bindings",
                ]
                if not all(_table_exists(conn, table_name) for table_name in required_tables):
                    if args.dry_run:
                        transaction.rollback()
                    else:
                        transaction.commit()
                    print("[SKIP] users/roles/user_role_assignments/user_party_bindings table missing")
                    return 0

                role_party_rows = conn.execute(
                    sa.text(
                        """
                        SELECT ura.user_id, r.party_id
                        FROM user_role_assignments AS ura
                        JOIN roles AS r ON r.id = ura.role_id
                        WHERE ura.is_active = true
                          AND r.party_id IS NOT NULL
                        """
                    )
                ).mappings().all()
                default_org_rows = conn.execute(
                    sa.text(
                        """
                        SELECT id AS user_id, default_organization_id
                        FROM users
                        WHERE default_organization_id IS NOT NULL
                        """
                    )
                ).mappings().all()

                user_to_parties: dict[str, set[str]] = {}
                for row in role_party_rows:
                    user_to_parties.setdefault(str(row["user_id"]), set()).add(
                        str(row["party_id"])
                    )
                for row in default_org_rows:
                    user_id = str(row["user_id"])
                    org_id = str(row["default_organization_id"])
                    mapped_party_id = org_to_party_map.get(org_id)
                    if mapped_party_id is None:
                        continue
                    user_to_parties.setdefault(user_id, set()).add(mapped_party_id)

                scanned = len(user_to_parties)
                now = _utcnow_naive()
                for user_id, party_ids in user_to_parties.items():
                    sorted_parties = sorted(party_ids)
                    for index, party_id in enumerate(sorted_parties):
                        exists = conn.execute(
                            sa.text(
                                """
                                SELECT 1
                                FROM user_party_bindings
                                WHERE user_id = :user_id
                                  AND party_id = :party_id
                                  AND relation_type = 'manager'
                                  AND valid_to IS NULL
                                LIMIT 1
                                """
                            ),
                            {"user_id": user_id, "party_id": party_id},
                        ).scalar_one_or_none()
                        if exists is not None:
                            continue

                        inserted += 1
                        if args.dry_run:
                            continue

                        conn.execute(
                            sa.text(
                                """
                                INSERT INTO user_party_bindings (
                                    id, user_id, party_id, relation_type,
                                    is_primary, valid_from, valid_to, created_at, updated_at
                                ) VALUES (
                                    :id, :user_id, :party_id, :relation_type,
                                    :is_primary, :valid_from, :valid_to, :created_at, :updated_at
                                )
                                """
                            ),
                            {
                                "id": str(uuid.uuid4()),
                                "user_id": user_id,
                                "party_id": party_id,
                                "relation_type": "manager",
                                "is_primary": index == 0,
                                "valid_from": now,
                                "valid_to": None,
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
    print(f"[{mode}] backfill_user_bindings users={scanned} inserted={inserted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
