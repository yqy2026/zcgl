"""
Rebuild asset search index for encrypted fields.

Usage:
    python scripts/maintenance/rebuild_asset_search_index.py --batch-size 500 --commit-every 500
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def _setup_path() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend_root))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rebuild asset_search_index for encrypted fields (e.g. address)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only scan assets, do not write to database.",
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
        help="Commit after this many assets (ignored in dry-run).",
    )
    return parser


async def main() -> int:
    _setup_path()
    args = _build_parser().parse_args()

    from sqlalchemy import select

    from src.core.search_index import SEARCH_INDEX_FIELDS
    from src.crud.asset import asset_crud
    from src.database import async_session_scope
    from src.models.asset import Asset

    handler = asset_crud.sensitive_data_handler
    if not handler.encryption_enabled:
        print("Encryption disabled; search index rebuild skipped.")
        return 1

    scanned = 0
    updated = 0

    async with async_session_scope() as db:
        stmt = select(Asset).execution_options(yield_per=args.batch_size)
        stream = await db.stream_scalars(stmt)
        async for asset in stream:
            scanned += 1
            asset_crud._decrypt_asset_object(asset)
            data = {field: getattr(asset, field, None) for field in SEARCH_INDEX_FIELDS}

            if not args.dry_run:
                await asset_crud._refresh_search_index_entries(
                    db, asset_id=asset.id, data=data
                )
                updated += 1
                if updated % args.commit_every == 0:
                    await db.commit()

        if not args.dry_run:
            await db.commit()

    print(
        "Rebuild completed:",
        f"scanned={scanned}",
        f"updated={updated}",
        f"dry_run={args.dry_run}",
        sep=" ",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
