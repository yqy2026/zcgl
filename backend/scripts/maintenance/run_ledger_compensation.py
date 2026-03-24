"""Manual runner for ledger compensation."""

from __future__ import annotations

import asyncio
import json

from src.database import async_session_scope
from src.services.contract.ledger_compensation_service import (
    ledger_compensation_service,
)


async def run_ledger_compensation() -> dict[str, object]:
    async with async_session_scope() as db:
        return await ledger_compensation_service.run(db)


if __name__ == "__main__":
    result = asyncio.run(run_ledger_compensation())
    print(json.dumps(result, ensure_ascii=False))
