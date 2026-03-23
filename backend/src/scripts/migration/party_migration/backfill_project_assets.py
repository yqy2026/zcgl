"""Backfill project_assets from legacy assets.project_id."""

from __future__ import annotations

import argparse
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa

from ....database_url import get_database_url


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _table_exists(connection: sa.engine.Connection, table_name: str) -> bool:
    return sa.inspect(connection).has_table(table_name)


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

    engine = sa.create_engine(database_url, future=True)
    inserted = 0
    scanned = 0
    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                if not _table_exists(conn, "assets") or not _table_exists(
                    conn, "project_assets"
                ):
                    if args.dry_run:
                        transaction.rollback()
                    else:
                        transaction.commit()
                    print("[SKIP] assets/project_assets table missing")
                    return 0

                asset_rows = (
                    conn.execute(
                        sa.text(
                            """
                        SELECT id, project_id
                        FROM assets
                        WHERE project_id IS NOT NULL
                          AND project_id <> ''
                        """
                        )
                    )
                    .mappings()
                    .all()
                )
                scanned = len(asset_rows)

                now = _utcnow_naive()
                for row in asset_rows:
                    project_id = str(row["project_id"])
                    asset_id = str(row["id"])
                    exists = conn.execute(
                        sa.text(
                            """
                            SELECT 1
                            FROM project_assets
                            WHERE project_id = :project_id
                              AND asset_id = :asset_id
                            LIMIT 1
                            """
                        ),
                        {"project_id": project_id, "asset_id": asset_id},
                    ).scalar_one_or_none()
                    if exists is not None:
                        continue

                    inserted += 1
                    if args.dry_run:
                        continue

                    conn.execute(
                        sa.text(
                            """
                            INSERT INTO project_assets (
                                id, project_id, asset_id, valid_from, created_at, updated_at
                            ) VALUES (
                                :id, :project_id, :asset_id, :valid_from, :created_at, :updated_at
                            )
                            """
                        ),
                        {
                            "id": str(uuid.uuid4()),
                            "project_id": project_id,
                            "asset_id": asset_id,
                            "valid_from": now,
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
    print(f"[{mode}] backfill_project_assets scanned={scanned} inserted={inserted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
