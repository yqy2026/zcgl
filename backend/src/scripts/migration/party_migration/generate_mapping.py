"""Generate organization/ownership -> party mapping artifacts."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import sqlalchemy as sa

from ....core.exception_handler import ConfigurationError
from ....database_url import get_database_url

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(identifier: str) -> str:
    if not _IDENTIFIER_RE.fullmatch(identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier}")
    return identifier


@dataclass(frozen=True)
class MappingArtifact:
    generated_at: str
    org_to_party_map: dict[str, str]
    ownership_to_party_map: dict[str, str]
    unmatched_org_ids: list[str]
    unmatched_ownership_ids: list[str]


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _build_party_indexes(
    party_rows: list[dict[str, Any]],
    *,
    party_type: str,
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    external_ref_to_party_id: dict[str, str] = {}
    code_to_party_id: dict[str, str] = {}
    name_to_party_id: dict[str, str] = {}

    for row in party_rows:
        if normalize_text(row.get("party_type")) != normalize_text(party_type):
            continue

        party_id = str(row.get("id") or "").strip()
        if party_id == "":
            continue

        external_ref = normalize_text(row.get("external_ref"))
        if external_ref != "":
            external_ref_to_party_id.setdefault(external_ref, party_id)

        code = normalize_text(row.get("code"))
        if code != "":
            code_to_party_id.setdefault(code, party_id)

        name = normalize_text(row.get("name"))
        if name != "":
            name_to_party_id.setdefault(name, party_id)

    return external_ref_to_party_id, code_to_party_id, name_to_party_id


def build_mapping_for_rows(
    *,
    legacy_rows: list[dict[str, Any]],
    id_key: str,
    name_key: str,
    code_key: str,
    party_rows: list[dict[str, Any]],
    party_type: str,
) -> tuple[dict[str, str], list[str]]:
    external_ref_idx, code_idx, name_idx = _build_party_indexes(
        party_rows,
        party_type=party_type,
    )

    resolved_map: dict[str, str] = {}
    unmatched_ids: list[str] = []

    for row in legacy_rows:
        legacy_id = str(row.get(id_key) or "").strip()
        if legacy_id == "":
            continue

        party_id = external_ref_idx.get(normalize_text(legacy_id))
        if party_id is None:
            party_id = code_idx.get(normalize_text(row.get(code_key)))
        if party_id is None:
            party_id = name_idx.get(normalize_text(row.get(name_key)))

        if party_id is None:
            unmatched_ids.append(legacy_id)
            continue
        resolved_map[legacy_id] = party_id

    return resolved_map, sorted(unmatched_ids)


def build_mapping_artifact(
    *,
    organization_rows: list[dict[str, Any]],
    ownership_rows: list[dict[str, Any]],
    party_rows: list[dict[str, Any]],
) -> MappingArtifact:
    org_map, unmatched_org_ids = build_mapping_for_rows(
        legacy_rows=organization_rows,
        id_key="id",
        name_key="name",
        code_key="code",
        party_rows=party_rows,
        party_type="organization",
    )
    ownership_map, unmatched_ownership_ids = build_mapping_for_rows(
        legacy_rows=ownership_rows,
        id_key="id",
        name_key="name",
        code_key="code",
        party_rows=party_rows,
        party_type="legal_entity",
    )
    return MappingArtifact(
        generated_at=datetime.now(UTC).isoformat(),
        org_to_party_map=org_map,
        ownership_to_party_map=ownership_map,
        unmatched_org_ids=unmatched_org_ids,
        unmatched_ownership_ids=unmatched_ownership_ids,
    )


def _write_artifacts(output_dir: Path, artifact: MappingArtifact) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = asdict(artifact)
    (output_dir / "org_to_party_map.json").write_text(
        json.dumps(payload["org_to_party_map"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "ownership_to_party_map.json").write_text(
        json.dumps(payload["ownership_to_party_map"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "mapping_report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _fetch_rows(
    connection: sa.engine.Connection,
    table_name: str,
    columns: list[str],
) -> list[dict[str, Any]]:
    inspector = sa.inspect(connection)
    if not inspector.has_table(table_name):
        return []

    safe_table_name = _validate_identifier(table_name)
    selected_columns = ", ".join(_validate_identifier(column) for column in columns)
    statement = sa.text(
        f"SELECT {selected_columns} FROM {safe_table_name}"  # nosec B608 - identifiers validated with _validate_identifier
    )
    return [dict(row) for row in connection.execute(statement).mappings().all()]


def load_source_rows(
    database_url: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.connect() as conn:
            organizations = _fetch_rows(conn, "organizations", ["id", "name", "code"])
            ownerships = _fetch_rows(conn, "ownerships", ["id", "name", "code"])
            parties = _fetch_rows(
                conn,
                "parties",
                ["id", "party_type", "name", "code", "external_ref"],
            )
            return organizations, ownerships, parties
    finally:
        engine.dispose()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Database URL override. Default reads DATABASE_URL.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("migration-artifacts/party"),
        help="Directory for mapping artifacts.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build mapping in-memory and print summary only.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    database_url: str | None = args.database_url
    should_skip_db_lookup = (
        args.dry_run
        and database_url is None
        and os.getenv("DATABASE_URL")
        in (
            None,
            "",
        )
    )
    if database_url is None and not should_skip_db_lookup:
        try:
            database_url = get_database_url()
        except ConfigurationError:
            if not args.dry_run:
                raise
            database_url = None

    if database_url is None:
        organization_rows: list[dict[str, Any]] = []
        ownership_rows: list[dict[str, Any]] = []
        party_rows: list[dict[str, Any]] = []
        print("[DRY-RUN] DATABASE_URL 未配置，使用空数据集执行预检。")
    else:
        organization_rows, ownership_rows, party_rows = load_source_rows(database_url)

    artifact = build_mapping_artifact(
        organization_rows=organization_rows,
        ownership_rows=ownership_rows,
        party_rows=party_rows,
    )

    if args.dry_run:
        print(
            "[DRY-RUN] mapping generated:",
            f"org={len(artifact.org_to_party_map)}",
            f"ownership={len(artifact.ownership_to_party_map)}",
        )
        print(
            "[DRY-RUN] unmatched:",
            f"org={len(artifact.unmatched_org_ids)}",
            f"ownership={len(artifact.unmatched_ownership_ids)}",
        )
        return 0

    _write_artifacts(args.output_dir, artifact)
    print(f"Mapping artifacts written to: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
