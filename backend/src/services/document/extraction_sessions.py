"""Redis-only temporary storage for document extraction sessions."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Protocol

SESSION_TTL_SECONDS = 3600
_KEY_PREFIX = "document-extraction:"
_CAS_SCRIPT = """
local current = cjson.decode(redis.call('GET', KEYS[1]))
if current.status ~= ARGV[1] then return 0 end
redis.call('SET', KEYS[1], ARGV[2], 'EX', ARGV[3])
return 1
"""


class RedisSessionClient(Protocol):
    def set(self, key: str, value: str, *, ex: int, nx: bool = False) -> bool: ...

    def get(self, key: str) -> str | None: ...

    def delete(self, key: str) -> int: ...

    def eval(
        self,
        script: str,
        numkeys: int,
        key: str,
        expected: str,
        replacement: str,
        ttl: str,
    ) -> int: ...


class ExtractionSessionStateError(RuntimeError):
    """A requested extraction-session state change is no longer valid."""


class ExtractionSessionRepository:
    """Persist session state in Redis without any process-memory fallback."""

    def __init__(self, redis_client: RedisSessionClient) -> None:
        self._redis = redis_client

    def create(
        self,
        *,
        session_id: str,
        target_type: str,
        staged_file_key: str,
        candidates: Mapping[str, Any],
        context: Mapping[str, str] | None = None,
        errors: list[str] | None = None,
    ) -> dict[str, Any]:
        session = {
            "session_id": session_id,
            "target_type": target_type,
            "status": "ready_for_review",
            "staged_file_key": staged_file_key,
            "candidates": dict(candidates),
            "context": dict(context or {}),
            "errors": list(errors or []),
        }
        created = self._redis.set(
            self._key(session_id),
            json.dumps(session, ensure_ascii=False, default=str),
            ex=SESSION_TTL_SECONDS,
            nx=True,
        )
        if not created:
            raise ExtractionSessionStateError("session_already_exists")
        return session

    def get(self, session_id: str) -> dict[str, Any] | None:
        value = self._redis.get(self._key(session_id))
        if value is None:
            return None
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ExtractionSessionStateError("session_payload_invalid")
        return parsed

    def transition(
        self, session_id: str, expected_status: str, next_status: str
    ) -> dict[str, Any]:
        session = self.get(session_id)
        if session is None:
            raise ExtractionSessionStateError("session_not_found")
        session["status"] = next_status
        changed = self._redis.eval(
            _CAS_SCRIPT,
            1,
            self._key(session_id),
            expected_status,
            json.dumps(session, ensure_ascii=False, default=str),
            str(SESSION_TTL_SECONDS),
        )
        if changed != 1:
            raise ExtractionSessionStateError("session_state_conflict")
        return session

    def delete_terminal(self, session_id: str, terminal_status: str) -> str:
        session = self.transition(session_id, "ready_for_review", terminal_status)
        return self._delete_session(session)

    def delete_after_status(self, session_id: str, expected_status: str) -> str:
        session = self.get(session_id)
        if session is None:
            raise ExtractionSessionStateError("session_not_found")
        if session.get("status") != expected_status:
            raise ExtractionSessionStateError("session_state_conflict")
        return self._delete_session(session)

    def _delete_session(self, session: Mapping[str, Any]) -> str:
        staged_file_key = session.get("staged_file_key")
        session_id = session.get("session_id")
        if not isinstance(staged_file_key, str) or staged_file_key.strip() == "":
            raise ExtractionSessionStateError("session_staged_file_missing")
        if not isinstance(session_id, str) or session_id.strip() == "":
            raise ExtractionSessionStateError("session_payload_invalid")
        self._redis.delete(self._key(session_id))
        return staged_file_key

    @staticmethod
    def _key(session_id: str) -> str:
        return f"{_KEY_PREFIX}{session_id}"
