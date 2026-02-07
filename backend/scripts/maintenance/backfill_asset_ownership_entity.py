"""
Backfill Asset.ownership_id from legacy Asset.ownership_entity.

Strategy (safe):
- If ownership_id is missing and ownership_entity exists:
  - Match Ownership.name and set ownership_id.
  - If no match, record as error, skip.
- If ownership_id already exists: leave as-is.

Note: This script should be run before dropping the legacy ownership_entity column.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from pathlib import Path
from typing import Any


def _setup_path() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend_root))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill Asset.ownership_id using legacy ownership_entity values."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report changes, do not write to database.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Yield-per batch size for asset scan.",
    )
    parser.add_argument(
        "--commit-every",
        type=int,
        default=500,
        help="Commit after this many updates (ignored in dry-run).",
    )
    parser.add_argument(
        "--report",
        type=str,
        default="",
        help="Optional CSV report path for mismatches/errors.",
    )
    return parser


def _write_report(rows: list[dict[str, Any]], path: str) -> None:
    if not rows or not path:
        return
    report_path = Path(path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


async def main() -> int:
    _setup_path()
    args = _build_parser().parse_args()

    from sqlalchemy import select, text

    from src.database import async_session_scope
    from src.models.ownership import Ownership

    report_rows: list[dict[str, Any]] = []
    updated = 0
    unchanged = 0
    missing_ownership = 0
    scanned = 0

    try:
        async with async_session_scope() as db:
            column_check = await db.execute(
                text(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'assets' AND column_name = 'ownership_entity'
                    """
                )
            )
            if column_check.first() is None:
                print("assets.ownership_entity column not found; nothing to backfill.")
                return 0

            ownership_result = await db.execute(select(Ownership.id, Ownership.name))
            ownership_map = {oid: name for oid, name in ownership_result.all()}
            name_to_id = {name: oid for oid, name in ownership_map.items()}

            stmt = text(
                """
                SELECT id, ownership_id, ownership_entity
                FROM assets
                WHERE ownership_entity IS NOT NULL
                  AND ownership_entity != ''
                  AND ownership_id IS NULL
                """
            )
            result = await db.execute(stmt)
            rows = result.mappings().all()
            for asset in rows:
                scanned += 1
                ownership_entity = asset.get("ownership_entity")
                ownership_id = name_to_id.get(ownership_entity)
                if not ownership_id:
                    missing_ownership += 1
                    report_rows.append(
                        {
                            "asset_id": asset.get("id"),
                            "ownership_id": asset.get("ownership_id"),
                            "ownership_entity": ownership_entity,
                            "action": "skipped",
                            "reason": "ownership_name_not_found",
                        }
                    )
                    continue

                if not args.dry_run:
                    await db.execute(
                        text(
                            "UPDATE assets SET ownership_id = :ownership_id WHERE id = :asset_id"
                        ),
                        {"ownership_id": ownership_id, "asset_id": asset.get("id")},
                    )
                updated += 1
                report_rows.append(
                    {
                        "asset_id": asset.get("id"),
                        "ownership_id": ownership_id,
                        "ownership_entity": ownership_entity,
                        "action": "updated" if not args.dry_run else "would_update",
                        "reason": "ownership_id_backfilled",
                    }
                )
                if not args.dry_run and updated % args.commit_every == 0:
                    await db.commit()

            if not args.dry_run:
                await db.commit()

        _write_report(report_rows, args.report)

        print(
            "Backfill completed:",
            f"scanned={scanned}",
            f"updated={updated}",
            f"unchanged={unchanged}",
            f"missing_ownership={missing_ownership}",
            f"dry_run={args.dry_run}",
            sep=" ",
        )
        if args.report:
            print(f"Report written to: {Path(args.report).resolve()}")
        return 0
    except Exception as exc:
        print(f"Backfill failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
