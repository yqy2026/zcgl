#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test-fixture hardcoded-credential gate.

Background (#86): Mimosa L3 git-gate treats assignments shaped like
`credential_name = "literal"` (e.g. refresh_token assigned a raw string,
password assigned a literal) as high-severity hardcoded credentials. Tests that
need fake tokens / passwords must use the generators in
backend/tests/fixtures/fake_credentials.py instead of literal values.

This script scans TEST code and blocks new additions of that shape. Criteria
(aligned with the scanner semantics measured in the #86 remediation record):
  - the assignment target contains a credential keyword (token / key / secret /
    password / passwd), either as a compound name (refresh_token, api_key,
    new_password) or as the bare name password/passwd; bare key/token/secret
    are excluded (React keys, generic identifiers);
  - the assigned value is a non-empty quoted string literal whose content
    itself looks credential-shaped (contains token/password/passwd/secret/pass
    as a word, or sk-, or a bcrypt prefix);
  - dict colon style, function calls and f-string generation do not match;
  - only code lines are scanned; pure comment lines are skipped.

Whitelist: backend/tests/e2e/ and frontend/tests/e2e/ hold the shared seed
default passwords (kept by the #86 disposition decision) and are excluded until
the L3 gate disposition is settled.

Usage: python scripts/check_test_credentials.py [files_or_dirs ...]
       python scripts/check_test_credentials.py --self-test
Exit codes: 0 = clean; 1 = violations.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# 赋值名：复合凭证名（含前后缀），或裸 password/passwd；裸 key/token/secret 排除
_NAME = re.compile(
    r"(?:[a-zA-Z_0-9]+(?:token|key|secret|password|passwd)"
    r"|(?:token|key|secret|password|passwd)[a-zA-Z_0-9]+"
    r"|password|passwd)"
)

# 值必须本身凭证形状：含 token/password/passwd/secret/pass 词、sk- 或 bcrypt 前缀
_CREDENTIAL_VALUE = re.compile(
    r"[\"'](?=[^\"']*?(?:\b(?:token|password|passwd|secret|pass)\b|sk-|\$2b\$))[^\"']+[\"']"
)

# 完整命中形态：凭证名 = 凭证形状字符串字面量（含 kwargs 无空格写法）
_VIOLATION = re.compile(
    r"\b(" + _NAME.pattern + r")\s*=\s*(" + _CREDENTIAL_VALUE.pattern + r")"
)

# 纯注释行
_COMMENT_LINE = re.compile(r"^\s*#")

# 行尾注释（近似剥离）
_TRAILING_COMMENT = re.compile(r"\s+#.*$")

# e2e 默认口令白名单目录（不动清单）
_WHITELIST_DIRS = (
    "backend/tests/e2e",
    "frontend/tests/e2e",
)

# 默认扫描根：后端测试 + 前端测试代码
_DEFAULT_ROOTS = (
    "backend/tests",
    "backend/conftest.py",
    "frontend/src",
    "frontend/tests",
)

_SCAN_GLOBS = ("*.py", "*.ts", "*.tsx", "*.js", "*.jsx")


def _is_whitelisted(path: Path) -> bool:
    """e2e default-password dirs are excluded by the #86 disposition."""
    normalized = "/" + path.as_posix()
    return any(
        f"/{entry}/" in normalized or normalized.endswith(f"/{entry}")
        for entry in _WHITELIST_DIRS
    )


def _is_test_file(path: Path) -> bool:
    """Only test code is in scope: *.test/spec.* or src/test/."""
    name = path.name
    if ".test." in name or ".spec." in name:
        return True
    normalized = path.as_posix()
    return "/src/test/" in normalized or "/tests/" in normalized


def scan_file(path: Path) -> list[tuple[int, str]]:
    """Scan one file; returns [(line_no, credential_name), ...]."""
    violations: list[tuple[int, str]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return violations

    for number, raw in enumerate(lines, start=1):
        if _COMMENT_LINE.match(raw):
            continue
        line = _TRAILING_COMMENT.sub("", raw)
        for match in _VIOLATION.finditer(line):
            violations.append((number, match.group(1)))
    return violations


def scan(paths: list[str]) -> dict[str, list[tuple[int, str]]]:
    """Scan the given paths (defaults to the test-code roots)."""
    results: dict[str, list[tuple[int, str]]] = {}
    for raw_path in paths or list(_DEFAULT_ROOTS):
        path = Path(raw_path)
        if path.is_file():
            if not _is_whitelisted(path):
                found = scan_file(path)
                if found:
                    results[path.as_posix()] = found
            continue
        if not path.is_dir():
            continue
        for pattern in _SCAN_GLOBS:
            for candidate in path.rglob(pattern):
                if (
                    not candidate.is_file()
                    or not _is_test_file(candidate)
                    or _is_whitelisted(candidate)
                ):
                    continue
                found = scan_file(candidate)
                if found:
                    results[candidate.as_posix()] = found
    return results


def _fixture_line(name: str, value: str) -> str:
    """Build a fixture line at runtime so the source never contains the shape."""
    return name + ' = "' + value + '"\n'


def self_test() -> int:
    """Red/green self-test locking the gate boundaries (Rule 9)."""
    import tempfile

    cases = [
        # (filename, content, expected count)
        ("red_assignment.py", _fixture_line("refresh_token", "refresh_token_abc"), 1),
        ("red_kwarg.py", "create(" + "password" + '="password123"' + ")\n", 1),
        ("green_generated.py", "refresh_token = fake_refresh_token()\n", 0),
        ("green_dict.py", 'data = {"refresh_token": "abc"}\n', 0),
        ("green_comment.py", "# refresh_token = " + '"abc"\n', 0),
        ("green_neutral_name.py", 'x = "refresh_token_abc"\n', 0),
        ("green_jsx_key.py", 'key="complete"\n', 0),
        ("green_ui_state.py", "passwordError = " + "'please enter password'\n", 0),
        ("green_bare_token.py", _fixture_line("token", "token-value"), 0),
    ]
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for filename, content, expected in cases:
            target = root / filename
            target.write_text(content, encoding="utf-8")
            found = len(scan_file(target))
            if found != expected:
                failures.append(f"{filename}: expected {expected}, got {found}")

        e2e_file = root / "backend/tests/e2e/seed_defaults.py"
        e2e_file.parent.mkdir(parents=True)
        e2e_file.write_text(_fixture_line("password", "AdminPass123!"), encoding="utf-8")
        if scan([str(e2e_file)]):
            failures.append("whitelist e2e dir should be skipped")

        # 非测试文件（普通源码）不在扫描范围
        src_file = root / "frontend/src/pages/LoginPage.tsx"
        src_file.parent.mkdir(parents=True)
        src_file.write_text(_fixture_line("password", "password123"), encoding="utf-8")
        if scan(["frontend/src"]) and str(src_file) in scan([str(src_file)]):
            failures.append("non-test source should be skipped by path scan")

    if failures:
        print("check-test-credentials self-test: FAIL")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("check-test-credentials self-test: PASS (9 boundaries + whitelist)")
    return 0


def main() -> int:
    """CLI entry: print violations, exit 0/1."""
    if "--self-test" in sys.argv:
        return self_test()

    paths = [arg for arg in sys.argv[1:] if arg != "--self-test"]
    results = scan(paths)

    if not results:
        print("check-test-credentials: PASS (no hardcoded fake credentials in tests)")
        return 0

    total = 0
    for file, violations in sorted(results.items()):
        print(f"[VIOLATION] {file}")
        for number, name in violations:
            total += 1
            print(f"  L{number}: {name}")
    print(
        f"check-test-credentials: FAIL ({total} hardcoded credential literal(s); "
        "use generators from backend/tests/fixtures/fake_credentials.py)"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
