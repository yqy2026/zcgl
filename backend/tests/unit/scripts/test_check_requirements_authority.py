import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from scripts.check_requirements_authority import (
    check_document_filenames,
    check_issue_index_coverage,
    check_local_markdown_links,
    check_plans_residual,
)


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


def test_plans_residual_accepts_indexed_active_plan(tmp_path: Path) -> None:
    plans_dir = tmp_path / "plans"
    plans_dir.mkdir()
    (plans_dir / "README.md").write_text(
        "[active](./2026-07-28-active-plan.md)\n",
        encoding="utf-8",
    )
    (plans_dir / "2026-07-28-active-plan.md").write_text(
        "# Active\n\n🔄 进行中\n",
        encoding="utf-8",
    )

    assert check_plans_residual(plans_dir) == []


def test_plans_residual_reports_unindexed_nested_completed_plan(tmp_path: Path) -> None:
    plans_dir = tmp_path / "plans"
    hidden_dir = plans_dir / "execution"
    hidden_dir.mkdir(parents=True)
    (plans_dir / "README.md").write_text("# Plans\n", encoding="utf-8")
    (hidden_dir / "snapshot.md").write_text(
        "# Snapshot\n\n✅ 已完成\n",
        encoding="utf-8",
    )

    issues = check_plans_residual(plans_dir)

    assert any("snapshot.md" in issue and "completed" in issue for issue in issues)
    assert any("snapshot.md" in issue and "not indexed" in issue for issue in issues)


def test_local_markdown_links_accept_valid_maintained_links(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    archive_dir = docs_dir / "archive"
    archive_dir.mkdir(parents=True)
    (docs_dir / "guide.md").write_text("# Guide\n", encoding="utf-8")
    (docs_dir / "README.md").write_text("[guide](./guide.md)\n", encoding="utf-8")
    (archive_dir / "README.md").write_text(
        "[guide](../guide.md)\n",
        encoding="utf-8",
    )

    assert check_local_markdown_links(docs_dir) == []


def test_local_markdown_links_report_active_broken_link_but_skip_archive_body(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    archive_dir = docs_dir / "archive"
    archive_dir.mkdir(parents=True)
    (docs_dir / "README.md").write_text("[missing](./missing.md)\n", encoding="utf-8")
    (archive_dir / "history.md").write_text(
        "[historical](./removed.md)\n",
        encoding="utf-8",
    )
    (archive_dir / "README.md").write_text("# Archive\n", encoding="utf-8")

    issues = check_local_markdown_links(docs_dir)

    assert len(issues) == 1
    assert "missing.md" in issues[0]


def test_local_markdown_links_validate_repository_root_relative_links(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "README.md").write_text(
        "[valid](/docs/guide.md)\n[missing](/docs/missing.md)\n",
        encoding="utf-8",
    )
    (docs_dir / "guide.md").write_text("# Guide\n", encoding="utf-8")

    issues = check_local_markdown_links(docs_dir, repo_root=tmp_path)

    assert len(issues) == 1
    assert "/docs/missing.md" in issues[0]


def test_document_filenames_allow_readme_and_adr_but_reject_other_names(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "README.md").write_text("# Docs\n", encoding="utf-8")
    (docs_dir / "ADR-0001-valid-decision.md").write_text("# ADR\n", encoding="utf-8")
    (docs_dir / "valid-file.md").write_text("# Valid\n", encoding="utf-8")
    (docs_dir / "Bad File.md").write_text("# Invalid\n", encoding="utf-8")
    (docs_dir / "extra.dot.md").write_text("# Invalid\n", encoding="utf-8")

    issues = check_document_filenames(docs_dir)

    assert len(issues) == 2
    assert any("Bad File.md" in issue for issue in issues)
    assert any("extra.dot.md" in issue for issue in issues)
