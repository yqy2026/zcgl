from __future__ import annotations

from src.database_url import get_database_url


def test_get_database_url_loads_cwd_dotenv_when_process_environment_is_missing(
    monkeypatch, tmp_path
) -> None:
    dotenv_database_url = "postgresql+psycopg://dotenv:pass@localhost:5432/dotenv_db"
    (tmp_path / ".env").write_text(
        f"DATABASE_URL={dotenv_database_url}\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("PYDANTIC_SETTINGS_IGNORE_DOT_ENV", raising=False)

    assert get_database_url() == dotenv_database_url


def test_get_database_url_keeps_explicit_process_environment_over_dotenv(
    monkeypatch, tmp_path
) -> None:
    dotenv_database_url = "postgresql+psycopg://dotenv:pass@localhost:5432/dotenv_db"
    environment_database_url = (
        "postgresql+psycopg://environment:pass@localhost:5432/env_db"
    )
    (tmp_path / ".env").write_text(
        f"DATABASE_URL={dotenv_database_url}\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PYDANTIC_SETTINGS_IGNORE_DOT_ENV", raising=False)
    monkeypatch.setenv("DATABASE_URL", environment_database_url)

    assert get_database_url() == environment_database_url
