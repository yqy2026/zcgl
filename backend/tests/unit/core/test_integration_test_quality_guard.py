"""Guard rails for integration test quality regressions."""

from __future__ import annotations

import re
from pathlib import Path

_FORBIDDEN_RULES: tuple[tuple[str, str], ...] = (
    (
        "avoid_non_contract_404_assertion",
        r"assert\s+response\.status_code\s*!=\s*404",
    ),
    (
        "avoid_broad_status_bucket_assertion",
        r"assert\s+response\.status_code\s+in\s*[\[\(]",
    ),
    (
        "avoid_swallowing_exception_with_pass",
        r"except\s+Exception:\s*\n\s+pass",
    ),
)

_EXCLUDED_FILE_NAMES = {"conftest.py"}
_QUALITY_GUARD_DIRS = ("integration", "e2e")
_UNIT_API_GUARD_DIR = Path("unit/api/v1")
_UNIT_API_FORBIDDEN_RULES: tuple[tuple[str, str], ...] = (
    (
        "avoid_swallowing_exception_with_pass",
        r"except\s+Exception:\s*\n\s+pass",
    ),
)


def _quality_guard_test_files() -> list[Path]:
    tests_dir = Path(__file__).resolve().parents[2]
    files: list[Path] = []
    for directory_name in _QUALITY_GUARD_DIRS:
        scoped_dir = tests_dir / directory_name
        files.extend(
            [
                file
                for file in scoped_dir.rglob("*.py")
                if file.name not in _EXCLUDED_FILE_NAMES
            ]
        )
    return sorted(files)


def _unit_api_test_files() -> list[Path]:
    tests_dir = Path(__file__).resolve().parents[2]
    scoped_dir = tests_dir / _UNIT_API_GUARD_DIR
    return sorted(
        [
            file
            for file in scoped_dir.rglob("*.py")
            if file.name not in _EXCLUDED_FILE_NAMES
        ]
    )


def test_integration_and_e2e_tests_do_not_reintroduce_weak_patterns() -> None:
    """Prevent weak assertion patterns from slipping back into integration/E2E tests."""
    violations: list[str] = []

    for file_path in _quality_guard_test_files():
        content = file_path.read_text(encoding="utf-8")
        relative_path = file_path.relative_to(Path(__file__).resolve().parents[3])

        for rule_name, pattern in _FORBIDDEN_RULES:
            for match in re.finditer(pattern, content):
                line_number = content.count("\n", 0, match.start()) + 1
                violations.append(f"{relative_path}:{line_number} [{rule_name}]")

    assert not violations, (
        "Found weak integration-test patterns. Please replace with explicit "
        "contract assertions.\n"
        + "\n".join(violations[:30])
    )


def test_unit_api_tests_do_not_swallow_exceptions_with_pass() -> None:
    """Prevent `except Exception: pass` from creeping back into unit API tests."""
    violations: list[str] = []

    for file_path in _unit_api_test_files():
        content = file_path.read_text(encoding="utf-8")
        relative_path = file_path.relative_to(Path(__file__).resolve().parents[3])

        for rule_name, pattern in _UNIT_API_FORBIDDEN_RULES:
            for match in re.finditer(pattern, content):
                line_number = content.count("\n", 0, match.start()) + 1
                violations.append(f"{relative_path}:{line_number} [{rule_name}]")

    assert not violations, (
        "Found weak unit-api test patterns. Please replace broad exception swallow "
        "with explicit cleanup checks.\n"
        + "\n".join(violations[:30])
    )
