import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from scripts.check_requirements_authority import check_issue_index_coverage


def test_issue_index_coverage_reports_missing_and_stale_entries(tmp_path: Path) -> None:
    issues_dir = tmp_path / "issues"
    issues_dir.mkdir()
    index_path = issues_dir / "README.md"
    index_path.write_text(
        "[indexed](./indexed.md)\n[stale](./stale.md)\n",
        encoding="utf-8",
    )
    (issues_dir / "indexed.md").write_text("# Indexed\n", encoding="utf-8")
    (issues_dir / "missing.md").write_text("# Missing\n", encoding="utf-8")

    issues = check_issue_index_coverage(issues_dir, index_path)

    assert any("missing.md" in issue and "not indexed" in issue for issue in issues)
    assert any("stale.md" in issue and "missing file" in issue for issue in issues)


def test_issue_index_coverage_accepts_complete_index(tmp_path: Path) -> None:
    issues_dir = tmp_path / "issues"
    issues_dir.mkdir()
    index_path = issues_dir / "README.md"
    index_path.write_text("[indexed](./indexed.md)\n", encoding="utf-8")
    (issues_dir / "indexed.md").write_text("# Indexed\n", encoding="utf-8")

    assert check_issue_index_coverage(issues_dir, index_path) == []


def test_issue_index_coverage_reports_duplicate_index_entries(tmp_path: Path) -> None:
    issues_dir = tmp_path / "issues"
    issues_dir.mkdir()
    index_path = issues_dir / "README.md"
    index_path.write_text(
        "[indexed](./indexed.md)\n[indexed-again](./indexed.md)\n",
        encoding="utf-8",
    )
    (issues_dir / "indexed.md").write_text("# Indexed\n", encoding="utf-8")

    issues = check_issue_index_coverage(issues_dir, index_path)

    assert any("indexed.md" in issue and "duplicates file" in issue for issue in issues)
