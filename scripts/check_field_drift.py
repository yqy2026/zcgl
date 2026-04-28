#!/usr/bin/env python3
"""Field drift detector: compare domain model spec vs ORM model columns.

For each entity section in docs/specs/domain-model.md, collect non-derived
fields and compare with the corresponding ORM model.

Outputs an informational drift report. Does NOT fail the build (exit 0)
since spec may intentionally be ahead of implementation during 0→1 phase.
Promote to exit(1) once all ✅ entities are fully implemented.

Run from repository root:
    python scripts/check_field_drift.py
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
FIELD_SPEC = ROOT / "docs" / "specs" / "domain-model.md"
MODELS_DIR = ROOT / "backend" / "src" / "models"

# ---------------------------------------------------------------------------
# Entity → model file + ORM class name mapping.
# Extend this table as new entities are added to the field spec AND implemented.
# Entities in spec but not yet implemented in ORM should be omitted (they'll
# be listed as "no model mapping" and skipped cleanly).
# ---------------------------------------------------------------------------
ENTITY_MODEL_MAP: dict[str, tuple[str, str]] = {
    "Asset": ("asset.py", "Asset"),
    "Project": ("project.py", "Project"),
    "ContractGroup": ("contract_group.py", "ContractGroup"),
    "Contract": ("contract_group.py", "Contract"),
    "ContractRentTerm": ("contract_group.py", "ContractRentTerm"),
    "ContractLedgerEntry": ("contract_group.py", "ContractLedgerEntry"),
    "ServiceFeeLedger": ("contract_group.py", "ServiceFeeLedger"),
    "ContractAuditLog": ("contract_group.py", "ContractAuditLog"),
    "LeaseContractDetail": ("contract_group.py", "LeaseContractDetail"),
    "AgencyAgreementDetail": ("contract_group.py", "AgencyAgreementDetail"),
    "ContractRelation": ("contract_group.py", "ContractRelation"),
    "PropertyCertificate": ("property_certificate.py", "PropertyCertificate"),
    "Ownership": ("ownership.py", "Ownership"),
    "Party": ("party.py", "Party"),
    # CustomerProfile, AnalyticsMetrics not yet implemented as separate ORM models.
}

# Regex: field contract section heading, e.g. "### 4.1 Asset".
_SECTION_RE = re.compile(r"^###\s+4\.\d+\s+([A-Z]\w*)\s*$", re.MULTILINE)

# Regex: table row with a backtick-quoted field name as first column.
_FIELD_ROW_RE = re.compile(r"^\|\s*`([a-z][a-z0-9_]*)`\s*\|(.+)\|$", re.MULTILINE)

# Regex: detect derived status in last column or description column.
_DERIVED_RE = re.compile(r"派生")

# Regex: extract mapped_column attribute names from a Python model file.
# Matches patterns like:  field_name: Mapped[...] = mapped_column(
_MAPPED_COL_RE = re.compile(r"^\s{4}(\w+)\s*:\s*Mapped\[", re.MULTILINE)

# Regex: synonym declarations (also counts as a column alias).
_SYNONYM_RE = re.compile(r"^\s{4}(\w+)\s*=\s*synonym\(", re.MULTILINE)


class EntityDrift(NamedTuple):
    entity: str
    model_file: str
    spec_only: list[str]    # in spec, not in ORM
    orm_only: list[str]     # in ORM, not in spec
    matched: list[str]      # in both


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_spec_fields(text: str) -> dict[str, list[str]]:
    """Return {EntityName: [non-derived confirmed field names]} from spec."""
    result: dict[str, list[str]] = {}
    # Find all section headings and their positions.
    sections = list(_SECTION_RE.finditer(text))
    for i, match in enumerate(sections):
        entity = match.group(1)
        start = match.end()
        end = sections[i + 1].start() if i + 1 < len(sections) else len(text)
        section_text = text[start:end]

        fields: list[str] = []
        for row_match in _FIELD_ROW_RE.finditer(section_text):
            field_name = row_match.group(1)
            # Skip derived fields.
            if _DERIVED_RE.search(row_match.group(2)):
                continue
            fields.append(field_name)

        if fields:
            result[entity] = fields

    return result


def parse_orm_columns(model_file: Path, class_name: str | None = None) -> set[str]:
    """Return set of column attribute names from a SQLAlchemy model file.

    If class_name is provided, extract only columns from that specific class block.
    """
    if not model_file.exists():
        return set()
    text = model_file.read_text(encoding="utf-8", errors="replace")

    if class_name:
        # Find the class block: from "class ClassName(..." to the next "class " at column 0.
        class_start = re.search(
            rf"^class {re.escape(class_name)}\b", text, re.MULTILINE
        )
        if not class_start:
            return set()
        # Find next top-level class definition after this one.
        next_class = re.search(r"^class ", text[class_start.end():], re.MULTILINE)
        if next_class:
            text = text[class_start.start(): class_start.end() + next_class.start()]
        else:
            text = text[class_start.start():]

    columns = set(_MAPPED_COL_RE.findall(text))
    columns |= set(_SYNONYM_RE.findall(text))
    # Exclude private/dunder names and ORM relationship names (relationships
    # don't appear in _MAPPED_COL_RE but guard anyway).
    return {c for c in columns if not c.startswith("_")}


# ---------------------------------------------------------------------------
# Main diff logic
# ---------------------------------------------------------------------------

def compute_drifts() -> list[EntityDrift]:
    if not FIELD_SPEC.exists():
        print(f"[ERROR] Field spec not found: {FIELD_SPEC.relative_to(ROOT)}")
        return []

    text = FIELD_SPEC.read_text(encoding="utf-8", errors="replace")
    spec_entities = parse_spec_fields(text)

    drifts: list[EntityDrift] = []
    for entity, spec_fields in spec_entities.items():
        # Skip non-ASCII section names (e.g. Chinese section headings matched by \w+)
        if not entity.isascii() or not entity[0].isupper():
            continue

        mapping = ENTITY_MODEL_MAP.get(entity)
        if mapping is None:
            print(f"[SKIP] {entity}: no model mapping defined in ENTITY_MODEL_MAP")
            continue

        model_filename, class_name = mapping
        model_path = MODELS_DIR / model_filename
        orm_cols = parse_orm_columns(model_path, class_name)

        if not orm_cols:
            print(f"[SKIP] {entity}: model file or class not found -> {model_filename}::{class_name}")
            continue

        spec_set = set(spec_fields)
        spec_only = sorted(spec_set - orm_cols)
        orm_only = sorted(orm_cols - spec_set)
        matched = sorted(spec_set & orm_cols)

        drifts.append(EntityDrift(
            entity=entity,
            model_file=f"{model_filename}::{class_name}",
            spec_only=spec_only,
            orm_only=orm_only,
            matched=matched,
        ))

    return drifts


def main() -> int:
    print("=== Field Drift Report: spec vs ORM ===\n")
    drifts = compute_drifts()

    total_spec_only = 0
    total_orm_only = 0

    for drift in drifts:
        has_diff = drift.spec_only or drift.orm_only
        status = "DRIFT" if has_diff else "OK   "
        print(f"[{status}] {drift.entity} ({drift.model_file})")
        if drift.matched:
            print(f"         matched ({len(drift.matched)}): {', '.join(drift.matched)}")
        if drift.spec_only:
            print(f"         spec-only / not in ORM ({len(drift.spec_only)}): {', '.join(drift.spec_only)}")
            total_spec_only += len(drift.spec_only)
        if drift.orm_only:
            print(f"         orm-only / not in spec ({len(drift.orm_only)}): {', '.join(drift.orm_only)}")
            total_orm_only += len(drift.orm_only)
        print()

    print(f"Summary: {total_spec_only} spec-only fields (unimplemented or renamed), "
          f"{total_orm_only} orm-only columns (undocumented).")
    print()
    print("NOTE: spec-only fields may be planned-but-not-yet-implemented (normal during 0→1).")
    print("      orm-only columns may use different names than the spec (check for renames).")

    # Informational only — do not fail CI during 0→1 phase.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
