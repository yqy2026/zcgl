"""
Search index helper unit tests.
"""

import base64

import pytest
from sqlalchemy import Select

from src.core import encryption as encryption_module
from src.core.encryption import EncryptionKeyManager
from src.core.search_index import (
    build_asset_id_subquery,
    build_ngrams,
    build_search_index_entries,
    normalize_text,
)


@pytest.fixture(autouse=True)
def reset_encryption_modules(monkeypatch):
    monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)

    import sys

    modules_to_clear = [
        "src.core.config",
        "src.core.encryption",
    ]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]

    yield

    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]


def _setup_valid_key(monkeypatch) -> str:
    key_bytes = b"k" * 32
    key_b64 = base64.b64encode(key_bytes).decode("ascii")
    test_key = f"{key_b64}:1"
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", test_key)

    from src.core import config

    monkeypatch.setattr(config.settings, "DATA_ENCRYPTION_KEY", test_key)
    monkeypatch.setattr(encryption_module.settings, "DATA_ENCRYPTION_KEY", test_key)
    return test_key


def test_normalize_and_ngrams():
    assert normalize_text("  Foo  Bar ") == "foo bar"
    tokens = build_ngrams("abcd", min_len=2, max_len=3)
    assert tokens == {"ab", "bc", "cd", "abc", "bcd"}


def test_build_search_index_entries(monkeypatch):
    _setup_valid_key(monkeypatch)
    manager = EncryptionKeyManager()
    entries = build_search_index_entries(
        asset_id="asset-1",
        field_name="address",
        value="Test Road 123",
        key_manager=manager,
    )
    assert entries
    assert all(entry.asset_id == "asset-1" for entry in entries)
    assert all(entry.key_version == 1 for entry in entries)


def test_build_asset_id_subquery(monkeypatch):
    _setup_valid_key(monkeypatch)
    manager = EncryptionKeyManager()
    query = build_asset_id_subquery(
        field_name="address",
        search_text="Test Road",
        key_manager=manager,
    )
    assert isinstance(query, Select)
