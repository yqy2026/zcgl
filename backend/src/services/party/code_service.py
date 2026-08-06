"""Concurrency-safe Party system-code allocation."""

from __future__ import annotations

import re

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.party import Party

_PREFIXES = {"legal_entity": "LE", "individual": "NP"}


class PartyCodeService:
    """Allocate one immutable code inside the current database transaction."""

    async def generate(self, db: AsyncSession, *, party_type: str) -> str:
        prefix = _PREFIXES.get(party_type)
        if prefix is None:
            raise ValueError(f"unsupported Party type: {party_type}")

        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"party-code:{prefix}"},
        )
        result = await db.execute(
            select(Party.code)
            .where(Party.code.like(f"{prefix}-%"))
            .order_by(Party.code.desc())
            .limit(1)
        )
        latest_code = result.scalar_one_or_none()
        if latest_code is None:
            return f"{prefix}-000001"
        if re.fullmatch(rf"{prefix}-\d{{6}}", str(latest_code)) is None:
            raise RuntimeError(f"invalid existing Party code: {latest_code}")

        next_sequence = int(str(latest_code)[-6:]) + 1
        if next_sequence > 999999:
            raise RuntimeError(f"Party code namespace {prefix} is exhausted")
        return f"{prefix}-{next_sequence:06d}"


__all__ = ["PartyCodeService"]
