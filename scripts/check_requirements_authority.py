#!/usr/bin/env python3
"""Validate requirements documentation authority references.

This guard ensures the single SSOT model is maintained:
- Only canonical docs may declare authority.
- No legacy dual-spec references should reappear.

Run from repository root:
    python scripts/check_requirements_authority.py
"""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# Canonical docs allowed to define authority model directly.
CANONICAL_DOCS = {
    "docs/requirements-specification.md",
    "docs/features/requirements-appendix-fields-v0.3.md",
    "docs/features/requirements-appendix-modules.md",
    "docs/index.md",
}

# Legacy patterns that must not reappear (old dual-spec references).
LEGACY_PATTERNS = [
    re.compile(r"requirements-specification-0to1\.md"),
    re.compile(r"requirements-authority-matrix\.md"),
    re.compile(r"requirements-review-checklist\.md"),
]


def to_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> int:
    issues: list[str] = []

    for md in DOCS.rglob("*.md"):
        rel = to_rel(md)
        text = md.read_text(encoding="utf-8", errors="replace")

        # Skip archive subtree — historical files may reference old names.
        if rel.startswith("docs/archive/"):
            continue

        for pattern in LEGACY_PATTERNS:
            if pattern.search(text):
                issues.append(
                    f"{rel}: contains legacy reference -> {pattern.pattern}"
                )

    if issues:
        print("Requirements authority check failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Requirements authority check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
