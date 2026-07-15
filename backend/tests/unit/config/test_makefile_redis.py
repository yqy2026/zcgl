"""Makefile contracts for the local Docker Redis workflow."""

from __future__ import annotations

from pathlib import Path


def _makefile_text() -> str:
    repo_root = Path(__file__).resolve().parents[4]
    return (repo_root / "Makefile").read_text(encoding="utf-8")


def test_makefile_exposes_local_redis_lifecycle_targets() -> None:
    makefile_text = _makefile_text()

    assert "redis-up:" in makefile_text
    assert "\tdocker compose up -d redis" in makefile_text
    assert "redis-down:" in makefile_text
    assert "\tdocker compose stop redis" in makefile_text


def test_redis_health_target_uses_non_interactive_container_check() -> None:
    makefile_text = _makefile_text()

    assert "redis-health:" in makefile_text
    assert "\tdocker compose exec -T redis redis-cli ping" in makefile_text
