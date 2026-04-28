#!/usr/bin/env python3
"""Validate requirements documentation authority references.

Checks performed:
1. Legacy dual-spec references must not reappear in active docs.
2. Code evidence paths declared in requirements-specification.md must exist.
3. docs/plans/ must not contain files with ✅-completed status (should be archived).
4. PRD/spec documents must not contain implementation evidence or code/test paths.
5. Traceability evidence paths must exist.
6. Legacy requirements entries must remain jump pages without code/test paths.

Run from repository root:
    python scripts/check_requirements_authority.py
"""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
PLANS = DOCS / "plans"
REQUIREMENTS_SPEC = DOCS / "requirements-specification.md"
PRD = DOCS / "prd.md"
SPECS = DOCS / "specs"
TRACEABILITY = DOCS / "traceability" / "requirements-trace.md"
LEGACY_JUMP_PAGES = [
    REQUIREMENTS_SPEC,
    DOCS / "features" / "requirements-appendix-fields.md",
    DOCS / "features" / "requirements-appendix-modules.md",
]

# Legacy patterns that must not reappear (old dual-spec references).
LEGACY_PATTERNS = [
    re.compile(r"requirements-specification-0to1\.md"),
    re.compile(r"requirements-authority-matrix\.md"),
    re.compile(r"requirements-review-checklist\.md"),
]

# Pattern to extract file paths from code-evidence blocks.
# Matches backtick-quoted paths like `backend/src/...` or `frontend/src/...`
_CODE_EVIDENCE_PATH_RE = re.compile(
    r"^[\s\-*]+`((?:backend|frontend|scripts|docs)/[^`]+)`\s*$",
    re.MULTILINE,
)

# Detect "代码证据" section start.
_CODE_EVIDENCE_SECTION_RE = re.compile(r"^[\s\-*]*代码证据[：:]", re.MULTILINE)

# Plans ✅ status markers — a plan file containing these should be archived.
_PLANS_COMPLETED_RE = re.compile(r"✅\s*(已完成|已实现|已采纳|Completed|Done)", re.IGNORECASE)

_TARGET_DOC_FORBIDDEN_PATTERNS = [
    ("代码证据", re.compile(r"代码证据")),
    ("测试证据", re.compile(r"测试证据")),
    ("As-Built", re.compile(r"As-Built", re.IGNORECASE)),
    ("backend/src path", re.compile(r"backend/src/")),
    ("frontend/src path", re.compile(r"frontend/src/")),
    ("backend/tests path", re.compile(r"backend/tests/")),
    ("frontend/tests path", re.compile(r"frontend/tests/")),
    ("frontend __tests__ path", re.compile(r"frontend/src/[^\s`]*__tests__")),
    ("当前实现", re.compile(r"当前实现")),
    ("技术方案", re.compile(r"技术方案")),
]

_LEGACY_ENTRY_FORBIDDEN_PATHS = [
    ("backend/src path", re.compile(r"backend/src/")),
    ("frontend/src path", re.compile(r"frontend/src/")),
    ("backend/tests path", re.compile(r"backend/tests/")),
    ("frontend/tests path", re.compile(r"frontend/tests/")),
    ("frontend __tests__ path", re.compile(r"frontend/src/[^\s`]*__tests__")),
]

_BACKTICK_PATH_RE = re.compile(r"`((?:backend|frontend|docs|scripts)/[^`]+)`")


def to_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


# ---------------------------------------------------------------------------
# Check 1: legacy reference guard (original check)
# ---------------------------------------------------------------------------

def check_legacy_references() -> list[str]:
    issues: list[str] = []
    for md in DOCS.rglob("*.md"):
        rel = to_rel(md)
        if rel.startswith("docs/archive/"):
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        for pattern in LEGACY_PATTERNS:
            if pattern.search(text):
                issues.append(f"{rel}: contains legacy reference -> {pattern.pattern}")
    return issues


# ---------------------------------------------------------------------------
# Check 2: code evidence dead-link detection
# ---------------------------------------------------------------------------

def _extract_evidence_paths(text: str) -> list[str]:
    """Extract file paths from all '代码证据' blocks in a markdown text."""
    paths: list[str] = []
    # Split at each code-evidence section marker and process what follows.
    parts = _CODE_EVIDENCE_SECTION_RE.split(text)
    for part in parts[1:]:  # parts[0] is text before first marker
        # Collect lines until we hit a blank line or a new heading / bullet section
        for line in part.splitlines():
            m = _CODE_EVIDENCE_PATH_RE.match(line)
            if m:
                paths.append(m.group(1))
            elif line.strip() == "":
                continue  # skip blank lines within block
            elif line.startswith("#") or (line.startswith("-") and not line.strip().startswith("- `")):
                break  # end of evidence block
    return paths


def check_code_evidence_links() -> list[str]:
    issues: list[str] = []
    if not REQUIREMENTS_SPEC.exists():
        issues.append(f"requirements-specification.md not found at {to_rel(REQUIREMENTS_SPEC)}")
        return issues

    text = REQUIREMENTS_SPEC.read_text(encoding="utf-8", errors="replace")
    paths = _extract_evidence_paths(text)

    for rel_path in paths:
        full_path = ROOT / rel_path
        if not full_path.exists():
            issues.append(
                f"docs/requirements-specification.md: dead code evidence link -> {rel_path}"
            )
    return issues


# ---------------------------------------------------------------------------
# Check 3: plans/ completed-status residual detection
# ---------------------------------------------------------------------------

def check_plans_residual() -> list[str]:
    issues: list[str] = []
    if not PLANS.exists():
        return issues

    for md in PLANS.glob("*.md"):
        if md.name.lower() == "readme.md":
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        if _PLANS_COMPLETED_RE.search(text):
            issues.append(
                f"docs/plans/{md.name}: contains completed (✅) status — should be moved to docs/archive/backend-plans/"
            )
    return issues


# ---------------------------------------------------------------------------
# Check 4: target docs must not carry implementation evidence
# ---------------------------------------------------------------------------

def _line_number(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _check_forbidden_patterns(path: Path, patterns: list[tuple[str, re.Pattern[str]]]) -> list[str]:
    if not path.exists():
        return [f"{to_rel(path)}: required document missing"]

    text = path.read_text(encoding="utf-8", errors="replace")
    issues: list[str] = []
    for label, pattern in patterns:
        for match in pattern.finditer(text):
            line = _line_number(text, match.start())
            issues.append(f"{to_rel(path)}:{line}: forbidden {label}")
    return issues


def check_target_doc_purity() -> list[str]:
    issues: list[str] = []
    issues.extend(_check_forbidden_patterns(PRD, _TARGET_DOC_FORBIDDEN_PATTERNS))

    if not SPECS.exists():
        issues.append(f"{to_rel(SPECS)}: required directory missing")
        return issues

    for md in sorted(SPECS.glob("*.md")):
        issues.extend(_check_forbidden_patterns(md, _TARGET_DOC_FORBIDDEN_PATTERNS))
    return issues


# ---------------------------------------------------------------------------
# Check 5: traceability evidence paths must exist
# ---------------------------------------------------------------------------

def check_traceability_paths() -> list[str]:
    if not TRACEABILITY.exists():
        return [f"{to_rel(TRACEABILITY)}: required document missing"]

    text = TRACEABILITY.read_text(encoding="utf-8", errors="replace")
    issues: list[str] = []
    for match in _BACKTICK_PATH_RE.finditer(text):
        rel_path = match.group(1)
        full_path = ROOT / rel_path
        if not full_path.exists():
            line = _line_number(text, match.start())
            issues.append(f"{to_rel(TRACEABILITY)}:{line}: dead traceability path -> {rel_path}")
    return issues


# ---------------------------------------------------------------------------
# Check 6: legacy requirements entries must stay jump pages
# ---------------------------------------------------------------------------

def check_legacy_requirements_entries() -> list[str]:
    issues: list[str] = []
    for path in LEGACY_JUMP_PAGES:
        issues.extend(_check_forbidden_patterns(path, _LEGACY_ENTRY_FORBIDDEN_PATHS))
        if not path.exists():
            continue

        text = path.read_text(encoding="utf-8", errors="replace")
        if "兼容跳转页" not in text:
            issues.append(f"{to_rel(path)}: must remain a compatibility jump page")
    return issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    all_issues: list[str] = []

    print("=== Check 1: Legacy reference guard ===")
    issues = check_legacy_references()
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(f"  FAIL  {i}")
    else:
        print("  PASS")

    print("=== Check 2: Code evidence dead-link detection ===")
    issues = check_code_evidence_links()
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(f"  FAIL  {i}")
    else:
        print("  PASS")

    print("=== Check 3: plans/ completed-status residual ===")
    issues = check_plans_residual()
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(f"  WARN  {i}")
    else:
        print("  PASS")

    print("=== Check 4: PRD/spec implementation evidence guard ===")
    issues = check_target_doc_purity()
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(f"  FAIL  {i}")
    else:
        print("  PASS")

    print("=== Check 5: traceability path existence ===")
    issues = check_traceability_paths()
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(f"  FAIL  {i}")
    else:
        print("  PASS")

    print("=== Check 6: legacy requirements jump-page guard ===")
    issues = check_legacy_requirements_entries()
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(f"  FAIL  {i}")
    else:
        print("  PASS")

    if all_issues:
        print(f"\ndocs-lint: {len(all_issues)} issue(s) found.")
        return 1

    print("\ndocs-lint: all checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
