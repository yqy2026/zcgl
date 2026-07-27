"""Tests for Redis-only temporary extraction sessions."""

import json

import pytest

from src.services.document.extraction_sessions import (
    ExtractionSessionRepository,
    ExtractionSessionStateError,
)


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    def set(self, key, value, *, ex, nx=False):
        if nx and key in self.values:
            return False
        self.values[key] = value
        self.ttls[key] = ex
        return True

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        return int(self.values.pop(key, None) is not None)

    def eval(self, script, count, key, expected, replacement, ttl):
        payload = self.values.get(key)
        if payload is None:
            return 0
        current = json.loads(payload)
        if current["status"] != expected:
            return 0
        self.values[key] = replacement
        self.ttls[key] = int(ttl)
        return 1


def test_session_is_created_in_redis_with_default_ttl_and_no_document_text():
    redis = FakeRedis()
    repository = ExtractionSessionRepository(redis)

    session = repository.create(
        session_id="session-1",
        target_type="contract",
        staged_file_key="staged/file.pdf",
        candidates={"contract_number": []},
    )

    assert session["status"] == "ready_for_review"
    assert redis.ttls["document-extraction:session-1"] == 3600
    assert "page_text" not in redis.values["document-extraction:session-1"]


def test_transition_is_compare_and_set_and_loser_cannot_confirm_or_cancel_again():
    repository = ExtractionSessionRepository(FakeRedis())
    repository.create(
        session_id="session-1",
        target_type="contract",
        staged_file_key="staged/file.pdf",
        candidates={},
    )

    confirmed = repository.transition("session-1", "ready_for_review", "confirming")

    assert confirmed["status"] == "confirming"
    with pytest.raises(ExtractionSessionStateError, match="session_state_conflict"):
        repository.transition("session-1", "ready_for_review", "cancelled")


def test_terminal_cleanup_deletes_session_and_returns_staged_file_key():
    repository = ExtractionSessionRepository(FakeRedis())
    repository.create(
        session_id="session-1",
        target_type="contract",
        staged_file_key="staged/file.pdf",
        candidates={},
    )

    staged_file_key = repository.delete_terminal("session-1", "cancelled")

    assert staged_file_key == "staged/file.pdf"
    assert repository.get("session-1") is None


def test_redis_error_is_not_silently_replaced_by_in_memory_storage():
    class BrokenRedis:
        def set(self, *args, **kwargs):
            raise ConnectionError("redis unavailable")

    with pytest.raises(ConnectionError, match="redis unavailable"):
        ExtractionSessionRepository(BrokenRedis()).create(
            session_id="session-1",
            target_type="contract",
            staged_file_key="staged/file.pdf",
            candidates={},
        )
