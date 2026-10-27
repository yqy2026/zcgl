"""Read-only preflight for the asset-operations v5 cutover."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Any

import sqlalchemy as sa

from ....database_url import get_database_url

_REQUIRED_COLUMNS = {
    "assets": {
        "id",
        "owner_party_id",
        "address",
        "actual_property_area",
        "rentable_area",
        "land_area",
        "business_category",
        "revenue_mode",
        "operation_agreement_start_date",
        "data_status",
    },
    "contract_groups": {"contract_group_id"},
    "contract_ledger_entries": {"entry_id"},
    "contracts": {"contract_id"},
    "operational_payment_flows": {"flow_id"},
    "parties": {"id"},
    "project_assets": {"project_id", "asset_id", "valid_to"},
    "projects": {"id"},
    "property_cert_assets": {"certificate_id", "asset_id"},
    "property_certificates": {"id"},
    "service_fee_ledgers": {"service_fee_entry_id"},
}
_ROW_COUNT_TABLES = tuple(sorted(_REQUIRED_COLUMNS))
_LEGACY_OPERATIONAL_TABLES = (
    "contract_groups",
    "contracts",
    "contract_ledger_entries",
    "operational_payment_flows",
    "service_fee_ledgers",
)
_ACQUISITION_MODE_VALUES = {
    "agency",
    "lease",
    "leased",
    "managed",
    "owned",
    "代理",
    "委托",
    "承租",
    "租赁",
    "自持",
    "自有",
}


@dataclass(frozen=True)
class GateEvaluation:
    """One cutover gate result."""

    name: str
    status: str
    actual: int
    expected: str


def _count(connection: sa.engine.Connection, table_name: str) -> int:
    preparer = connection.dialect.identifier_preparer
    quoted_table = preparer.quote(table_name)
    return int(
        connection.execute(
            sa.text(f"SELECT COUNT(*) FROM {quoted_table}")  # nosec B608
        ).scalar()
        or 0
    )


def _collect_missing_columns(
    inspector: sa.Inspector,
    present_tables: set[str],
) -> dict[str, list[str]]:
    missing_columns: dict[str, list[str]] = {}
    for table_name, required_columns in _REQUIRED_COLUMNS.items():
        if table_name not in present_tables:
            continue
        actual_columns = {
            str(column["name"]) for column in inspector.get_columns(table_name)
        }
        missing = sorted(required_columns - actual_columns)
        if missing:
            missing_columns[table_name] = missing
    return missing_columns


def _collect_asset_mapping_issues(
    connection: sa.engine.Connection,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        sa.text(
            """
            SELECT
                a.id,
                a.owner_party_id,
                a.address,
                a.actual_property_area,
                a.rentable_area,
                a.land_area,
                a.business_category,
                a.revenue_mode,
                a.operation_agreement_start_date,
                CASE
                    WHEN a.owner_party_id IS NULL OR NOT EXISTS (
                        SELECT 1 FROM parties p WHERE p.id = a.owner_party_id
                    ) THEN 1 ELSE 0
                END AS owner_missing,
                (
                    SELECT COUNT(*)
                    FROM project_assets pa
                    JOIN projects p ON p.id = pa.project_id
                    WHERE pa.asset_id = a.id AND pa.valid_to IS NULL
                ) AS active_project_count
            FROM assets a
            WHERE a.data_status = '正常'
            ORDER BY a.id
            """
        )
    ).mappings()

    issues: list[dict[str, Any]] = []
    for row in rows:
        issue_codes: list[str] = []
        if int(row["owner_missing"] or 0) > 0:
            issue_codes.append("owner_party_missing")

        project_count = int(row["active_project_count"] or 0)
        if project_count == 0:
            issue_codes.append("active_project_binding_missing")
        elif project_count > 1:
            issue_codes.append("active_project_binding_multiple")

        if row["address"] is None or str(row["address"]).strip() == "":
            issue_codes.append("address_missing")

        building_area = row["actual_property_area"]
        rentable_area = row["rentable_area"]
        land_area = row["land_area"]
        if (
            building_area is None
            or rentable_area is None
            or float(building_area) < 0
            or float(rentable_area) < 0
            or float(rentable_area) > float(building_area)
            or (land_area is not None and float(land_area) < 0)
        ):
            issue_codes.append("area_invalid")

        if (
            row["business_category"] is None
            or str(row["business_category"]).strip() == ""
        ):
            issue_codes.append("usage_type_missing")

        revenue_mode = str(row["revenue_mode"] or "").strip().lower()
        if revenue_mode not in _ACQUISITION_MODE_VALUES:
            issue_codes.append("acquisition_mode_unmapped")

        if row["operation_agreement_start_date"] is None:
            issue_codes.append("managed_from_missing")

        if issue_codes:
            issues.append(
                {
                    "asset_id": str(row["id"]),
                    "issue_codes": sorted(issue_codes),
                }
            )
    return issues


def _empty_snapshot(missing_tables: list[str]) -> dict[str, Any]:
    return {
        "missing_tables": missing_tables,
        "missing_columns": {},
        "row_counts": {table_name: 0 for table_name in _ROW_COUNT_TABLES},
        "asset_mapping_issues": [],
    }


def collect_preflight(connection: sa.engine.Connection) -> dict[str, Any]:
    """Collect privacy-safe source facts without modifying the database."""

    inspector = sa.inspect(connection)
    present_tables = set(inspector.get_table_names())
    missing_tables = sorted(set(_REQUIRED_COLUMNS) - present_tables)
    if missing_tables:
        return _empty_snapshot(missing_tables)

    missing_columns = _collect_missing_columns(inspector, present_tables)
    row_counts = {
        table_name: _count(connection, table_name) for table_name in _ROW_COUNT_TABLES
    }
    return {
        "missing_tables": [],
        "missing_columns": missing_columns,
        "row_counts": row_counts,
        "asset_mapping_issues": (
            [] if missing_columns else _collect_asset_mapping_issues(connection)
        ),
    }


def evaluate_preflight(snapshot: dict[str, Any]) -> list[GateEvaluation]:
    """Evaluate cutover inputs with fail-closed results."""

    missing_column_count = sum(
        len(columns) for columns in snapshot.get("missing_columns", {}).values()
    )
    row_counts = snapshot.get("row_counts", {})
    legacy_operational_count = sum(
        int(row_counts.get(table_name, 0)) for table_name in _LEGACY_OPERATIONAL_TABLES
    )
    metrics = (
        (
            "required_source_schema_present",
            len(snapshot.get("missing_tables", [])) + missing_column_count,
        ),
        (
            "legacy_asset_mapping_ready",
            len(snapshot.get("asset_mapping_issues", [])),
        ),
        ("legacy_operational_data_resolved", legacy_operational_count),
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
    """Return the aggregate gate result."""

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
