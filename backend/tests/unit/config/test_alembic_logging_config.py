"""Alembic logging configuration regression guards."""

import ast
from pathlib import Path


def test_alembic_preserves_existing_application_loggers() -> None:
    """In-process migrations must not disable loggers created during test collection."""
    env_path = Path(__file__).resolve().parents[3] / "alembic" / "env.py"
    module = ast.parse(env_path.read_text(encoding="utf-8"))
    file_config_calls = [
        node
        for node in ast.walk(module)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "fileConfig"
    ]

    assert len(file_config_calls) == 1
    disable_keyword = next(
        (
            keyword
            for keyword in file_config_calls[0].keywords
            if keyword.arg == "disable_existing_loggers"
        ),
        None,
    )
    assert disable_keyword is not None
    assert isinstance(disable_keyword.value, ast.Constant)
    assert disable_keyword.value.value is False
