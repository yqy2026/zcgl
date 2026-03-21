"""Match free-text management_entity to parties."""

from __future__ import annotations

import argparse
import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import sqlalchemy as sa

from ....database_url import get_database_url


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _table_exists(connection: sa.engine.Connection, table_name: str) -> bool:
    return sa.inspect(connection).has_table(table_name)


def _best_party_match(
    entity_name: str,
    party_rows: list[dict[str, str]],
    *,
    min_similarity: float,
) -> tuple[str | None, float]:
    normalized_entity = _normalize_text(entity_name)
    if normalized_entity == "":
        return None, 0.0

    best_party_id: str | None = None
    best_score = 0.0
    for row in party_rows:
        party_name = _normalize_text(row.get("name"))
        if party_name == "":
            continue
        if normalized_entity == party_name:
            return row["id"], 1.0

        score = SequenceMatcher(None, normalized_entity, party_name).ratio()
        if score > best_score:
            best_party_id = row["id"]
            best_score = score

    if best_party_id is None or best_score < min_similarity:
        return None, best_score
    return best_party_id, best_score


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL override. Default reads DATABASE_URL.",
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.7,
        help="Minimum similarity threshold (0-1).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("migration-artifacts/party/management_entity_matches.json"),
        help="Output JSON path for match report.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    database_url = args.database_url or get_database_url()

    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.connect() as conn:
            if not _table_exists(conn, "parties"):
                print("[SKIP] parties table missing")
                return 0

            party_rows = [
                {"id": str(row["id"]), "name": str(row["name"])}
                for row in conn.execute(
                    sa.text("SELECT id, name FROM parties WHERE name IS NOT NULL")
                )
                .mappings()
                .all()
            ]

            entity_values: set[str] = set()
            if _table_exists(conn, "assets"):
                rows = (
                    conn.execute(
                        sa.text(
                            """
                        SELECT DISTINCT management_entity
                        FROM assets
                        WHERE management_entity IS NOT NULL
                          AND management_entity <> ''
                        """
                        )
                    )
                    .scalars()
                    .all()
                )
                entity_values.update(str(value) for value in rows)

            if _table_exists(conn, "projects"):
                rows = (
                    conn.execute(
                        sa.text(
                            """
                        SELECT DISTINCT management_entity
                        FROM projects
                        WHERE management_entity IS NOT NULL
                          AND management_entity <> ''
                        """
                        )
                    )
                    .scalars()
                    .all()
                )
                entity_values.update(str(value) for value in rows)
    finally:
        engine.dispose()

    matches: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    for entity_name in sorted(entity_values):
        party_id, score = _best_party_match(
            entity_name,
            party_rows,
            min_similarity=float(args.min_similarity),
        )
        if party_id is None:
            unmatched.append({"management_entity": entity_name, "score": score})
            continue
        matches.append(
            {
                "management_entity": entity_name,
                "party_id": party_id,
                "score": round(score, 4),
            }
        )

    if not args.dry_run:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(
                {
                    "matched_count": len(matches),
                    "unmatched_count": len(unmatched),
                    "matches": matches,
                    "unmatched": unmatched,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    mode = "DRY-RUN" if args.dry_run else "EXEC"
    print(
        f"[{mode}] management_entity_matcher matched={len(matches)} unmatched={len(unmatched)}"
    )
    if not args.dry_run:
        print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
