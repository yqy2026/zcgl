"""Phase4 No-Go SQL snapshot and gate evaluation."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa

from ....database_url import get_database_url

VALID_TENANT_DECISIONS = {"A", "B"}


@dataclass(frozen=True)
class GateEvaluation:
    """Single gate result for Phase4 No-Go checks."""

    name: str
    status: str
    actual: str
    expected: str


def _table_exists(connection: sa.engine.Connection, table_name: str) -> bool:
    return sa.inspect(connection).has_table(table_name)


def _column_exists(
    connection: sa.engine.Connection,
    table_name: str,
    column_name: str,
) -> bool:
    if not _table_exists(connection, table_name):
        return False
    inspector = sa.inspect(connection)
    return any(
        str(column.get("name")) == column_name
        for column in inspector.get_columns(table_name)
    )


def _count_query(connection: sa.engine.Connection, sql_text: str) -> int:
    return int(connection.execute(sa.text(sql_text)).scalar() or 0)


def _count_table_rows(
    connection: sa.engine.Connection,
    table_name: str,
) -> int | None:
    if not _table_exists(connection, table_name):
        return None
    return _count_query(connection, f"SELECT COUNT(*) FROM {table_name}")


def _count_null_or_empty(
    connection: sa.engine.Connection,
    table_name: str,
    column_name: str,
) -> int | None:
    if not _column_exists(connection, table_name, column_name):
        return None
    return _count_query(
        connection,
        f"""
        SELECT COUNT(*)
        FROM {table_name}
        WHERE {column_name} IS NULL OR {column_name} = ''
        """,
    )


def _count_user_dual_party_viewer_mapping(connection: sa.engine.Connection) -> int | None:
    if not _table_exists(connection, "roles"):
        return None
    if not _column_exists(connection, "roles", "name"):
        return None
    if not _table_exists(connection, "abac_role_policies"):
        return None
    if not _table_exists(connection, "abac_policies"):
        return None
    if not _column_exists(connection, "abac_policies", "name"):
        return None
    return _count_query(
        connection,
        """
        SELECT COUNT(*)
        FROM roles r
        JOIN abac_role_policies rp ON rp.role_id = r.id
        JOIN abac_policies p ON p.id = rp.policy_id
        WHERE r.name = 'user' AND p.name = 'dual_party_viewer'
        """,
    )


def collect_snapshot(connection: sa.engine.Connection) -> dict[str, int | str | None]:
    """Collect Phase4 No-Go SQL metrics from current schema/data."""

    subject_exists = _table_exists(connection, "abac_policy_subjects")

    return {
        "subject_table": "abac_policy_subjects" if subject_exists else "null",
        "subject_count": _count_table_rows(connection, "abac_policy_subjects")
        if subject_exists
        else 0,
        "assets_owner_null": _count_null_or_empty(connection, "assets", "owner_party_id"),
        "assets_manager_null": _count_null_or_empty(connection, "assets", "manager_party_id"),
        "rc_owner_null": _count_null_or_empty(connection, "rent_contracts", "owner_party_id"),
        "rc_manager_null": _count_null_or_empty(connection, "rent_contracts", "manager_party_id"),
        "ledger_owner_null": _count_null_or_empty(connection, "rent_ledger", "owner_party_id"),
        "projects_manager_null": _count_null_or_empty(connection, "projects", "manager_party_id"),
        "tenant_null_count": _count_null_or_empty(connection, "rent_contracts", "tenant_party_id"),
        "tenant_total_count": _count_table_rows(connection, "rent_contracts"),
        "user_dual_party_viewer_mapping_count": _count_user_dual_party_viewer_mapping(
            connection
        ),
    }


def _value_as_int(value: int | str | None) -> int | None:
    return value if isinstance(value, int) else None


def _format_value(value: int | str | None) -> str:
    if value is None:
        return "MISSING"
    return str(value)


def _eval_equals(
    name: str,
    value: int | str | None,
    expected: int,
) -> GateEvaluation:
    actual_int = _value_as_int(value)
    if actual_int is None:
        return GateEvaluation(
            name=name,
            status="FAIL",
            actual=_format_value(value),
            expected=f"={expected}",
        )
    status = "PASS" if actual_int == expected else "FAIL"
    return GateEvaluation(
        name=name,
        status=status,
        actual=str(actual_int),
        expected=f"={expected}",
    )


def _eval_ge(
    name: str,
    value: int | str | None,
    expected: int,
) -> GateEvaluation:
    actual_int = _value_as_int(value)
    if actual_int is None:
        return GateEvaluation(
            name=name,
            status="FAIL",
            actual=_format_value(value),
            expected=f">={expected}",
        )
    status = "PASS" if actual_int >= expected else "FAIL"
    return GateEvaluation(
        name=name,
        status=status,
        actual=str(actual_int),
        expected=f">={expected}",
    )


def evaluate_snapshot(
    snapshot: dict[str, int | str | None],
    tenant_decision: str | None,
) -> list[GateEvaluation]:
    """Evaluate snapshot against Phase4 No-Go gate thresholds."""

    evaluations = [
        _eval_equals("subject_count_zero", snapshot.get("subject_count"), 0),
        _eval_equals("assets_owner_null_zero", snapshot.get("assets_owner_null"), 0),
        _eval_equals("assets_manager_null_zero", snapshot.get("assets_manager_null"), 0),
        _eval_equals("rc_owner_null_zero", snapshot.get("rc_owner_null"), 0),
        _eval_equals("rc_manager_null_zero", snapshot.get("rc_manager_null"), 0),
        _eval_equals("ledger_owner_null_zero", snapshot.get("ledger_owner_null"), 0),
        _eval_equals("projects_manager_null_zero", snapshot.get("projects_manager_null"), 0),
        _eval_ge(
            "user_dual_party_viewer_mapping_ge_1",
            snapshot.get("user_dual_party_viewer_mapping_count"),
            1,
        ),
    ]

    if tenant_decision in VALID_TENANT_DECISIONS:
        evaluations.append(
            GateEvaluation(
                name="tenant_decision_declared",
                status="PASS",
                actual=tenant_decision,
                expected="A|B",
            )
        )
    else:
        evaluations.append(
            GateEvaluation(
                name="tenant_decision_declared",
                status="FAIL",
                actual=tenant_decision or "unset",
                expected="A|B",
            )
        )

    if tenant_decision == "A":
        evaluations.append(
            _eval_equals(
                "tenant_null_zero_when_decision_a",
                snapshot.get("tenant_null_count"),
                0,
            )
        )
    elif tenant_decision == "B":
        evaluations.append(
            GateEvaluation(
                name="tenant_null_zero_when_decision_a",
                status="SKIP",
                actual=_format_value(snapshot.get("tenant_null_count")),
                expected="SKIP_WHEN_DECISION_B",
            )
        )
    else:
        evaluations.append(
            GateEvaluation(
                name="tenant_null_zero_when_decision_a",
                status="FAIL",
                actual=_format_value(snapshot.get("tenant_null_count")),
                expected="=0 (when decision=A)",
            )
        )

    return evaluations


def overall_result(evaluations: list[GateEvaluation]) -> str:
    return "FAIL" if any(item.status == "FAIL" for item in evaluations) else "PASS"


def _render_text(
    snapshot: dict[str, int | str | None],
    evaluations: list[GateEvaluation],
    tenant_decision: str | None,
    generated_at_utc: str,
) -> str:
    lines = [
        f"generated_at_utc={generated_at_utc}",
        f"tenant_decision={tenant_decision or 'unset'}",
    ]
    for key in sorted(snapshot.keys()):
        lines.append(f"{key}={_format_value(snapshot[key])}")
    for item in evaluations:
        lines.append(
            f"gate.{item.name}={item.status} actual={item.actual} expected={item.expected}"
        )
    lines.append(f"result={overall_result(evaluations)}")
    return "\n".join(lines)


def _render_markdown(
    snapshot: dict[str, int | str | None],
    evaluations: list[GateEvaluation],
    tenant_decision: str | None,
    generated_at_utc: str,
) -> str:
    lines = [
        "# Phase4 No-Go SQL Snapshot",
        "",
        f"- generated_at_utc: `{generated_at_utc}`",
        f"- tenant_decision: `{tenant_decision or 'unset'}`",
        f"- result: `{overall_result(evaluations)}`",
        "",
        "## Snapshot",
        "| metric | value |",
        "|---|---|",
    ]
    for key in sorted(snapshot.keys()):
        lines.append(f"| `{key}` | `{_format_value(snapshot[key])}` |")
    lines.extend(
        [
            "",
            "## Gate Results",
            "| gate | status | actual | expected |",
            "|---|---|---|---|",
        ]
    )
    for item in evaluations:
        lines.append(
            f"| `{item.name}` | `{item.status}` | `{item.actual}` | `{item.expected}` |"
        )
    return "\n".join(lines)


def _render_json(
    snapshot: dict[str, int | str | None],
    evaluations: list[GateEvaluation],
    tenant_decision: str | None,
    generated_at_utc: str,
) -> str:
    payload: dict[str, Any] = {
        "generated_at_utc": generated_at_utc,
        "tenant_decision": tenant_decision,
        "snapshot": snapshot,
        "gate_results": [asdict(item) for item in evaluations],
        "result": overall_result(evaluations),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL override. Default reads DATABASE_URL.",
    )
    parser.add_argument(
        "--tenant-decision",
        default=os.getenv("PHASE4_TENANT_NOT_NULL_DECISION"),
        help="Tenant decision in Phase4: A (enforce NOT NULL) or B (keep nullable).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "markdown", "json"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="Exit with non-zero when any gate is FAIL.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    tenant_decision = args.tenant_decision
    if tenant_decision is not None and tenant_decision not in VALID_TENANT_DECISIONS:
        parser.error(
            f"Invalid tenant decision: {tenant_decision}. Must be one of A/B or unset."
        )

    database_url = args.database_url or get_database_url()
    generated_at_utc = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.connect() as connection:
            snapshot = collect_snapshot(connection)
    finally:
        engine.dispose()

    evaluations = evaluate_snapshot(snapshot, tenant_decision=tenant_decision)
    if args.format == "markdown":
        output = _render_markdown(
            snapshot,
            evaluations,
            tenant_decision=tenant_decision,
            generated_at_utc=generated_at_utc,
        )
    elif args.format == "json":
        output = _render_json(
            snapshot,
            evaluations,
            tenant_decision=tenant_decision,
            generated_at_utc=generated_at_utc,
        )
    else:
        output = _render_text(
            snapshot,
            evaluations,
            tenant_decision=tenant_decision,
            generated_at_utc=generated_at_utc,
        )

    print(output)
    if args.enforce and overall_result(evaluations) != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
