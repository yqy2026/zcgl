"""Makefile guards for backend import smoke checks."""

from __future__ import annotations

from pathlib import Path


def _extract_make_target(makefile_text: str, target_name: str) -> str:
    lines = makefile_text.splitlines()
    start_index = next(
        index for index, line in enumerate(lines) if line.startswith(f"{target_name}:")
    )

    collected: list[str] = []
    for line in lines[start_index:]:
        if collected and line and not line.startswith(("\t", " ")):
            break
        collected.append(line)

    return "\n".join(collected)


def test_backend_import_target_should_resolve_secret_key_without_external_injection() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    makefile_text = (repo_root / "Makefile").read_text(encoding="utf-8")
    backend_import_block = _extract_make_target(makefile_text, "backend-import")

    assert 'RESOLVED_SECRET_KEY="$${SECRET_KEY:-}"' in backend_import_block
    assert "SECRET_KEY=\"$$RESOLVED_SECRET_KEY\"" in backend_import_block
    assert "BACKEND_IMPORT_FALLBACK_SECRET_KEY" in backend_import_block
