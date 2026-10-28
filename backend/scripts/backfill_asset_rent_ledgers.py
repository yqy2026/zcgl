"""Idempotent v5 rent backfill; old-domain ledger tables are never read.

Run from backend with uv run --frozen --extra dev python
scripts/backfill_asset_rent_ledgers.py [--apply --actor-id USER_ID].
The default only reports the target obligations and missing rent schedules.
"""

import argparse
import asyncio
import json
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.crud.auth import UserCRUD
from src.crud.rent_backfill import rent_backfill_repository
from src.database import get_async_database_url
from src.services.asset_operations.rent_obligation_service import (
    rent_obligation_service,
)


async def run(*, apply: bool, actor_id: str | None) -> None:
    engine = create_async_engine(get_async_database_url())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            if apply and (
                actor_id is None
                or await UserCRUD().get_async(session, actor_id) is None
            ):
                raise ValueError(
                    "--apply requires an existing --actor-id for the audit trail"
                )
            contracts = await rent_backfill_repository.list_contracts(session)
            report: dict[str, object] = {
                "mode": "apply" if apply else "dry-run",
                "contract_count": len(contracts),
                "target_obligation_count": 0,
                "target_amount": Decimal("0"),
                "contracts": [],
            }
            details = []
            for kind, contract in contracts:
                if apply:
                    await rent_backfill_repository.lock_contract(session, contract)
                plan = await rent_obligation_service.preview(
                    session, contract_kind=kind, contract_id=contract.id
                )
                details.append(
                    {
                        "contract_kind": kind,
                        "contract_id": contract.id,
                        "contract_number": contract.contract_number,
                        "impact": plan.summary(),
                        "missing_ranges": [
                            (a.isoformat(), b.isoformat()) for a, b in plan.gaps
                        ],
                    }
                )
                report["target_obligation_count"] += len(plan.targets)
                report["target_amount"] += sum(
                    (row.due_amount for row in plan.targets.values()), Decimal("0")
                )
                if apply:
                    await rent_obligation_service.replan(
                        session,
                        contract_kind=kind,
                        contract_id=contract.id,
                        actor_id=actor_id,
                        correlation_id=str(uuid4()),
                    )
            report["contracts"] = details
            if apply:
                await session.commit()
            else:
                await session.rollback()
            print(json.dumps(report, ensure_ascii=False, default=str, indent=2))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--actor-id")
    args = parser.parse_args()
    asyncio.run(run(apply=args.apply, actor_id=args.actor_id))
