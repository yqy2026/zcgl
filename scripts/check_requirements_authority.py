#!/usr/bin/env python3
"""Validate requirements documentation authority references.

Checks performed:
1. Legacy dual-spec references must not reappear in active docs.
2. Code evidence paths declared in requirements-specification.md must exist.
3. docs/plans/ files must be indexed and must not contain completed status.
4. PRD/spec documents must not contain implementation evidence or code/test paths.
5. Traceability evidence paths must exist.
6. Legacy requirements entries must remain jump pages without code/test paths.
7. PRD mechanics tokens must stay in the domain model.
8. Every active docs/issues report must be indexed exactly once by README.
9. Local links in active docs and archive indexes must resolve.
10. Documentation filenames must follow the repository naming convention.

Run from repository root:
    python scripts/check_requirements_authority.py
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
PLANS = DOCS / "plans"
ISSUES = DOCS / "issues"
ISSUES_INDEX = ISSUES / "README.md"
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
_PLANS_COMPLETED_RE = re.compile(
    r"✅\s*(已完成|已实现|已采纳|Completed|Done)", re.IGNORECASE
)

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

# PRD must stay product-altitude. These field-level mechanics tokens belong in
# docs/specs/domain-model.md (the single mechanics home), not in prd.md. Chosen
# to be unambiguous mechanics (near-zero false-positive risk in product prose).
_PRD_MECHANICS_TOKENS = [
    ("file-size limit", re.compile(r"\d+\s*MB")),
    ("file-type whitelist (JPG/JPEG)", re.compile(r"\bJPE?G\b")),
    ("ocr_prefill enum value", re.compile(r"ocr_prefill_(?:confirmed|corrected)")),
    ("manual_after_ocr_miss enum value", re.compile(r"manual_after_ocr_miss")),
    ("field_sources column name", re.compile(r"field_sources")),
]

_ACTIVE_ISSUE_LINK_RE = re.compile(r"\]\(\./([^/)]+\.md)\)")
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*]\((?P<target><[^>]+>|[^)\s]+)")
_DOC_FILENAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.[a-z0-9]+$")
_ADR_FILENAME_RE = re.compile(r"^ADR-\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")


def to_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def display_path(path: Path) -> str:
    try:
        return to_rel(path)
    except ValueError:
        return path.as_posix()


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
            elif line.startswith("#") or (
                line.startswith("-") and not line.strip().startswith("- `")
            ):
                break  # end of evidence block
    return paths


def check_code_evidence_links() -> list[str]:
    issues: list[str] = []
    if not REQUIREMENTS_SPEC.exists():
        issues.append(
            f"requirements-specification.md not found at {to_rel(REQUIREMENTS_SPEC)}"
        )
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
# Check 3: active plan index coverage and completed-status detection
# ---------------------------------------------------------------------------


def check_plans_residual(
    plans_dir: Path = PLANS,
    index_path: Path | None = None,
) -> list[str]:
    issues: list[str] = []
    if not plans_dir.exists():
        return issues
    resolved_index = index_path or plans_dir / "README.md"
    if not resolved_index.exists():
        return [f"{display_path(resolved_index)}: required plan index missing"]

    index_text = resolved_index.read_text(encoding="utf-8", errors="replace")
    indexed_paths: set[Path] = set()
    for match in _MARKDOWN_LINK_RE.finditer(index_text):
        target = match.group("target").strip("<>")
        if target.startswith(("http://", "https://", "mailto:", "#", "/")):
            continue
        target_path = (
            resolved_index.parent / unquote(target.split("#", 1)[0])
        ).resolve()
        try:
            indexed_paths.add(target_path.relative_to(plans_dir.resolve()))
        except ValueError:
            continue

    plan_paths: set[Path] = set()
    for md in plans_dir.rglob("*.md"):
        if md.name.lower() == "readme.md":
            continue
        relative_path = md.relative_to(plans_dir)
        plan_paths.add(relative_path)
        text = md.read_text(encoding="utf-8", errors="replace")
        if _PLANS_COMPLETED_RE.search(text):
            issues.append(
                f"{display_path(md)}: contains completed (✅) status — should be moved "
                "to docs/archive/backend-plans/"
            )

    issues.extend(
        f"{display_path(plans_dir / path)}: active plan is not indexed"
        for path in sorted(plan_paths - indexed_paths)
    )
    issues.extend(
        f"{display_path(resolved_index)}: active plan index points to missing file -> "
        f"{path.as_posix()}"
        for path in sorted(indexed_paths - plan_paths)
    )
    return issues


# ---------------------------------------------------------------------------
# Check 4: target docs must not carry implementation evidence
# ---------------------------------------------------------------------------


def _line_number(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _check_forbidden_patterns(
    path: Path, patterns: list[tuple[str, re.Pattern[str]]]
) -> list[str]:
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
            issues.append(
                f"{to_rel(TRACEABILITY)}:{line}: dead traceability path -> {rel_path}"
            )
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
# Check 7: PRD must not carry domain-model mechanics tokens
# ---------------------------------------------------------------------------


def check_prd_no_mechanics_tokens() -> list[str]:
    """PRD stays product-altitude; field-level mechanics belong in domain-model."""
    if not PRD.exists():
        return [f"{to_rel(PRD)}: required document missing"]

    text = PRD.read_text(encoding="utf-8", errors="replace")
    issues: list[str] = []
    for label, pattern in _PRD_MECHANICS_TOKENS:
        for match in pattern.finditer(text):
            line = _line_number(text, match.start())
            issues.append(
                f"{to_rel(PRD)}:{line}: PRD carries mechanics token "
                f"({label}: '{match.group()}') — move it to "
                f"docs/specs/domain-model.md and reference it"
            )
    return issues


# ---------------------------------------------------------------------------
# Check 8: active issue reports and their index must stay in sync
# ---------------------------------------------------------------------------


def check_issue_index_coverage(
    issues_dir: Path = ISSUES,
    index_path: Path = ISSUES_INDEX,
) -> list[str]:
    if not issues_dir.exists():
        return [f"{to_rel(issues_dir)}: required directory missing"]
    if not index_path.exists():
        return [f"{to_rel(index_path)}: required issue index missing"]

    index_text = index_path.read_text(encoding="utf-8", errors="replace")
    indexed_name_list = _ACTIVE_ISSUE_LINK_RE.findall(index_text)
    indexed_names = set(indexed_name_list)
    report_names = {
        path.name
        for path in issues_dir.glob("*.md")
        if path.name.lower() != "readme.md"
    }

    issues = [
        f"{display_path(issues_dir / name)}: active issue report is not indexed"
        for name in sorted(report_names - indexed_names)
    ]
    issues.extend(
        f"{display_path(index_path)}: active issue index points to missing file -> {name}"
        for name in sorted(indexed_names - report_names)
    )
    seen_names: set[str] = set()
    duplicate_names = sorted(
        {
            name
            for name in indexed_name_list
            if name in seen_names or seen_names.add(name)
        }
    )
    issues.extend(
        f"{display_path(index_path)}: active issue index duplicates file -> {name}"
        for name in duplicate_names
    )
    return issues


# ---------------------------------------------------------------------------
# Check 9: local Markdown links in maintained documents must resolve
# ---------------------------------------------------------------------------


def _maintained_markdown_files(docs_dir: Path) -> list[Path]:
    archive_dir = docs_dir / "archive"
    files = [path for path in docs_dir.rglob("*.md") if archive_dir not in path.parents]
    if archive_dir.exists():
        files.extend(archive_dir.rglob("README.md"))
    return sorted(set(files))


def check_local_markdown_links(
    docs_dir: Path = DOCS,
    repo_root: Path | None = None,
) -> list[str]:
    issues: list[str] = []
    if not docs_dir.exists():
        return [f"{display_path(docs_dir)}: required docs directory missing"]
    resolved_root = (repo_root or docs_dir.parent).resolve()

    for source in _maintained_markdown_files(docs_dir):
        text = source.read_text(encoding="utf-8", errors="replace")
        for match in _MARKDOWN_LINK_RE.finditer(text):
            raw_target = match.group("target").strip("<>")
            if raw_target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = unquote(raw_target.split("#", 1)[0])
            if not target:
                continue
            resolved = (
                resolved_root / target.lstrip("/")
                if target.startswith("/")
                else source.parent / target
            ).resolve()
            if not resolved.exists():
                line = _line_number(text, match.start())
                issues.append(
                    f"{display_path(source)}:{line}: broken local link -> {raw_target}"
                )
    return issues


# ---------------------------------------------------------------------------
# Check 10: documentation filenames must follow repository conventions
# ---------------------------------------------------------------------------


def check_document_filenames(docs_dir: Path = DOCS) -> list[str]:
    issues: list[str] = []
    if not docs_dir.exists():
        return [f"{display_path(docs_dir)}: required docs directory missing"]

    for path in sorted(item for item in docs_dir.rglob("*") if item.is_file()):
        if path.name == "README.md" or _ADR_FILENAME_RE.fullmatch(path.name):
            continue
        if not _DOC_FILENAME_RE.fullmatch(path.name):
            issues.append(
                f"{display_path(path)}: filename must use lowercase letters, digits, "
                "dots, and hyphens"
            )
    return issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Check 11: critical-domain REQ rows must carry backend e2e evidence
# ---------------------------------------------------------------------------

# REQs whose behavior is money-flow, state-machine, or data-scope critical:
# their traceability rows must reference at least one backend/tests/e2e path
# (docs/guides/testing-standards.md admission rule).
#
# 维护责任：这是准入规则的**强制最小清单**（规则文本更宽——「凡涉及资金流/
# 状态机/数据范围的需求」）。新增此类 REQ 时必须同步把编号加进本清单；
# 列序依赖 trace 表格的第 2/5 列（产品状态/测试证据），列结构变更时需同步。
_CRITICAL_E2E_REQS: frozenset[str] = frozenset(
    {
        "REQ-RNT-001",
        "REQ-RNT-005",
        "REQ-RNT-006",
        "REQ-AST-003",
        "REQ-AST-005",
        "REQ-PTY-001",
        "REQ-PTY-002",
        "REQ-AUTH-001",
        "REQ-AUTH-002",
        "REQ-AUTH-003",
        "REQ-SYS-001",
        "REQ-PRJ-001",
        "REQ-PRJ-002",
        "REQ-PRJ-003",
        "REQ-DOC-001",
        "REQ-ANA-001",
    }
)


def check_critical_reqs_have_e2e_evidence() -> list[str]:
    if not TRACEABILITY.exists():
        return [f"{to_rel(TRACEABILITY)}: required document missing"]

    issues: list[str] = []
    seen: set[str] = set()
    for line in TRACEABILITY.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or not cells[0].startswith("REQ-"):
            continue
        req_id = cells[0]
        if req_id not in _CRITICAL_E2E_REQS:
            continue
        seen.add(req_id)
        # Removed REQs (产品状态 col shows 已移除) are out of scope.
        product_status = cells[1] if len(cells) > 1 else ""
        if product_status == "已移除":
            continue
        evidence = cells[4] if len(cells) > 4 else ""
        if "backend/tests/e2e/" not in evidence:
            issues.append(
                f"{to_rel(TRACEABILITY)}: {req_id} is a critical-domain REQ "
                f"(money flow / state machine / data scope) but its test "
                f"evidence cites no backend/tests/e2e path"
            )

    missing_rows = sorted(_CRITICAL_E2E_REQS - seen)
    for req_id in missing_rows:
        issues.append(
            f"{to_rel(TRACEABILITY)}: {req_id} is listed as a critical-domain "
            f"REQ but has no traceability row at all"
        )
    return issues


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

    print("=== Check 3: active plan index and archive status ===")
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

    print("=== Check 7: PRD mechanics-token guard ===")
    issues = check_prd_no_mechanics_tokens()
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(f"  FAIL  {i}")
    else:
        print("  PASS")

    print("=== Check 8: active issue index coverage ===")
    issues = check_issue_index_coverage()
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(f"  FAIL  {i}")
    else:
        print("  PASS")

    print("=== Check 9: maintained Markdown local links ===")
    issues = check_local_markdown_links()
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(f"  FAIL  {i}")
    else:
        print("  PASS")

    print("=== Check 10: documentation filename convention ===")
    issues = check_document_filenames()
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(f"  FAIL  {i}")
    else:
        print("  PASS")

    print("=== Check 11: critical-domain REQ e2e evidence ===")
    issues = check_critical_reqs_have_e2e_evidence()
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
