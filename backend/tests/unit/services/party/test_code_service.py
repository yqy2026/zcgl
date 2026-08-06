"""Concurrency-safe Party system code tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.party.code_service import PartyCodeService


def _result(value: str | None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_generate_locks_type_before_reading_latest_code() -> None:
    db = AsyncMock()
    db.execute.side_effect = [_result(None), _result("LE-000041")]

    code = await PartyCodeService().generate(db, party_type="legal_entity")

    assert code == "LE-000042"
    assert db.execute.await_count == 2
    lock_statement = str(db.execute.await_args_list[0].args[0])
    lookup_statement = str(db.execute.await_args_list[1].args[0])
    assert "pg_advisory_xact_lock" in lock_statement
    assert "parties.code" in lookup_statement


@pytest.mark.asyncio
async def test_generate_starts_each_party_type_in_its_own_namespace() -> None:
    db = AsyncMock()
    db.execute.side_effect = [_result(None), _result(None)]

    code = await PartyCodeService().generate(db, party_type="individual")

    assert code == "NP-000001"


@pytest.mark.asyncio
async def test_generate_fails_loud_for_polluted_or_exhausted_sequence() -> None:
    service = PartyCodeService()
    polluted_db = AsyncMock()
    polluted_db.execute.side_effect = [_result(None), _result("LE-BROKEN")]

    with pytest.raises(RuntimeError, match="invalid existing Party code"):
        await service.generate(polluted_db, party_type="legal_entity")

    exhausted_db = AsyncMock()
    exhausted_db.execute.side_effect = [_result(None), _result("NP-999999")]
    with pytest.raises(RuntimeError, match="exhausted"):
        await service.generate(exhausted_db, party_type="individual")


@pytest.mark.asyncio
async def test_generate_rejects_retired_party_type() -> None:
    with pytest.raises(ValueError, match="unsupported Party type"):
        await PartyCodeService().generate(AsyncMock(), party_type="organization")
