#!/usr/bin/env python3
"""Validate Alembic migration file naming conventions.

Policy:
1. New migration files must use `YYYYMMDD_description.py`.
2. Historical hash-prefixed files are allowed via explicit allowlist.
"""

from __future__ import annotations

import re
from pathlib import Path

DATE_PREFIX_PATTERN = re.compile(r"^\d{8}_[a-z0-9_]+\.py$")

# Legacy files kept for historical compatibility.
LEGACY_ALLOWED_NAMES = {
    "345d5f07ee41_merge_heads_before_ocr_cleanup.py",
    "752cb03b2555_add_asset_high_frequency_query_indexes.py",
    "8f37856a3aae_standardize_contract_status_to_enum.py",
    "b5a7c4d9e2f1_add_search_trgm_indexes.py",
    "c6fd8148eb25_remove_deprecated_ocr_fields.py",
    "ca5d6adb0012_add_management_entity_to_asset.py",
    "e4c9e4968dd7_initial_schema_creation.py",
}


def _iter_migration_files(versions_dir: Path) -> list[str]:
    return sorted(
        file_path.name
        for file_path in versions_dir.glob("*.py")
        if file_path.name != "__init__.py"
    )


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[2]
    versions_dir = backend_dir / "alembic" / "versions"
    if not versions_dir.exists():
        print(f"[ERROR] Alembic versions directory not found: {versions_dir}")
        return 2

    all_files = _iter_migration_files(versions_dir)
    invalid_files: list[str] = []
    legacy_files: list[str] = []
    compliant_files: list[str] = []

    for file_name in all_files:
        if DATE_PREFIX_PATTERN.match(file_name):
            compliant_files.append(file_name)
            continue
        if file_name in LEGACY_ALLOWED_NAMES:
            legacy_files.append(file_name)
            continue
        invalid_files.append(file_name)

    if invalid_files:
        print("[ERROR] Found migration filenames violating naming policy:")
        for file_name in invalid_files:
            print(f"  - {file_name}")
        print(
            "\nExpected format for new files: YYYYMMDD_description.py "
            "(lowercase snake_case)."
        )
        return 1

    print(
        "[OK] Alembic migration naming check passed "
        f"(compliant={len(compliant_files)}, legacy={len(legacy_files)})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
