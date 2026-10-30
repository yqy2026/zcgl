"""Test bootstrap must never inspect or relocate a developer's secret files."""

import ast
import os
from pathlib import Path

import pytest
from pydantic_settings.sources import DotEnvSettingsSource

from src.core.config import Settings

SECRET = "aB3xK7mN9pQ2rS5tU8vW1xY4zZ6bC8dE0fG2hI4jK6!@#$%^&*"


@pytest.mark.parametrize("relative", ["tests/conftest.py", "tests/unit/conftest.py"])
def test_connection_resolver_only_uses_explicit_environment(relative, monkeypatch):
    backend = Path(__file__).resolve().parents[3]
    source = backend / relative
    tree = ast.parse(source.read_text(encoding="utf-8"))
    resolver = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_resolve_test_database_url"
    )
    namespace = {"os": os, "Path": Path, "__file__": str(source)}
    exec(
        compile(ast.Module(body=[resolver], type_ignores=[]), str(source), "exec"),
        namespace,
    )
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("E2E_TEST_DATABASE_URL", raising=False)
    with monkeypatch.context() as isolated:
        isolated.setattr(
            Path, "exists", lambda self: pytest.fail("bootstrap inspected a local file")
        )
        assert namespace["_resolve_test_database_url"]() is None
    monkeypatch.setenv("E2E_TEST_DATABASE_URL", "postgresql://explicit/e2e_test")
    assert namespace["_resolve_test_database_url"]() == "postgresql://explicit/e2e_test"
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://explicit/test")
    assert namespace["_resolve_test_database_url"]() == "postgresql://explicit/test"


def test_root_bootstrap_does_not_move_secret_files():
    source = Path(__file__).resolve().parents[3] / "tests/conftest.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    forbidden = {
        ("shutil", "move"),
        ("os", "rename"),
        ("os", "replace"),
        ("os", "unlink"),
    }
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and (node.func.value.id, node.func.attr) in forbidden
        for node in ast.walk(tree)
    )


def test_ignore_dotenv_does_not_even_read_the_source(tmp_path, monkeypatch):
    fake = tmp_path / ".env"
    fake.write_text("APP_NAME=from-file\n", encoding="utf-8")
    monkeypatch.setenv("SECRET_KEY", SECRET)
    monkeypatch.setenv("PYDANTIC_SETTINGS_IGNORE_DOT_ENV", "1")
    monkeypatch.setattr(
        DotEnvSettingsSource,
        "_read_env_file",
        lambda *args, **kwargs: pytest.fail("dotenv source was read"),
    )
    assert Settings(_env_file=fake).APP_NAME != "from-file"


def test_normal_settings_keep_explicit_dotenv_loading(tmp_path, monkeypatch):
    fake = tmp_path / ".env"
    fake.write_text("APP_NAME=from-file\n", encoding="utf-8")
    monkeypatch.setenv("SECRET_KEY", SECRET)
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("PYDANTIC_SETTINGS_IGNORE_DOT_ENV", raising=False)
    assert Settings(_env_file=fake).APP_NAME == "from-file"
