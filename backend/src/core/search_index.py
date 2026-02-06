from __future__ import annotations

import hashlib
import hmac
from typing import Any

from sqlalchemy import Select, func, or_, select

from .encryption import EncryptionKeyManager
from ..models.asset_search_index import AssetSearchIndex

DEFAULT_NGRAM_MIN = 2
DEFAULT_NGRAM_MAX = 3

# Fields that use blind index for substring search
SEARCH_INDEX_FIELDS = {"address"}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    return " ".join(text.split()).lower()


def build_ngrams(
    text: str, min_len: int = DEFAULT_NGRAM_MIN, max_len: int = DEFAULT_NGRAM_MAX
) -> set[str]:
    normalized = normalize_text(text)
    if not normalized:
        return set()
    length = len(normalized)
    if length < min_len:
        return set()
    max_len = min(max_len, length)
    tokens: set[str] = set()
    for size in range(min_len, max_len + 1):
        for idx in range(0, length - size + 1):
            tokens.add(normalized[idx : idx + size])
    return tokens


def _derive_search_key(key_bytes: bytes) -> bytes:
    return hmac.new(key_bytes, b"search-index", hashlib.sha256).digest()


def _hash_token(token: str, key_bytes: bytes) -> str:
    return hmac.new(key_bytes, token.encode("utf-8"), hashlib.sha256).hexdigest()


def build_search_index_entries(
    *,
    asset_id: str,
    field_name: str,
    value: Any,
    key_manager: EncryptionKeyManager,
    min_len: int = DEFAULT_NGRAM_MIN,
    max_len: int = DEFAULT_NGRAM_MAX,
) -> list[AssetSearchIndex]:
    if not key_manager.is_available():
        return []

    tokens = build_ngrams(
        str(value) if value is not None else "",
        min_len=min_len,
        max_len=max_len,
    )
    if not tokens:
        return []

    key_bytes = key_manager.get_key()
    if not key_bytes:
        return []
    version = key_manager.get_version()
    search_key = _derive_search_key(key_bytes)

    return [
        AssetSearchIndex(
            asset_id=asset_id,
            field_name=field_name,
            token_hash=_hash_token(token, search_key),
            key_version=version,
        )
        for token in sorted(tokens)
    ]


def build_asset_id_subquery(
    *,
    field_name: str,
    search_text: str,
    key_manager: EncryptionKeyManager,
    min_len: int = DEFAULT_NGRAM_MIN,
    max_len: int = DEFAULT_NGRAM_MAX,
) -> Select[Any] | None:
    if not key_manager.is_available():
        return None

    tokens = build_ngrams(search_text, min_len=min_len, max_len=max_len)
    if not tokens:
        return None

    token_count = len(tokens)
    version_filters = []
    for version in key_manager.get_versions():
        key_bytes = key_manager.get_key(version)
        if not key_bytes:
            continue
        search_key = _derive_search_key(key_bytes)
        token_hashes = [_hash_token(token, search_key) for token in tokens]
        version_filters.append(
            (AssetSearchIndex.key_version == version)
            & (AssetSearchIndex.token_hash.in_(token_hashes))
        )

    if not version_filters:
        return None

    return (
        select(AssetSearchIndex.asset_id)
        .where(
            AssetSearchIndex.field_name == field_name,
            or_(*version_filters),
        )
        .group_by(AssetSearchIndex.asset_id)
        .having(func.count(func.distinct(AssetSearchIndex.token_hash)) >= token_count)
    )
