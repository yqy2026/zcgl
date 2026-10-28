"""Shared transaction and authorization contracts for rent writers."""

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import PartyScopeForbiddenError, ResourceNotFoundError
from ...crud.asset_contract import asset_contract_repository
from ...crud.asset_unit import asset_unit_repository
from ...crud.business_change_event import business_change_repository
from ...crud.rent_commands import rent_command_repository
from ...models.asset_contract import (
    AssetContractWriteReceipt,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from ...models.business_change_event import BusinessChangeEvent
from ..party_scope_resolver import EffectivePartyScope
from .errors import (
    AssetOperationsIdempotencyConflictError,
    AssetOperationsVersionConflictError,
)


def require_scope(scope: EffectivePartyScope, actor_id: str) -> None:
    has_axis = (
        scope.scope_mode == "owner"
        and len(scope.owner_party_ids) > 0
        or scope.scope_mode == "manager"
        and len(scope.manager_party_ids) > 0
        or scope.scope_mode == "all"
        and len(scope.effective_party_ids) > 0
    )
    if actor_id != scope.user_id or (
        scope.scope_mode != "unrestricted"
        and (scope.error_code is not None or not has_axis)
    ):
        raise PartyScopeForbiddenError(code=scope.error_code or "PARTY_SCOPE_MISSING")


async def scoped_contract(
    db: AsyncSession,
    *,
    kind: str,
    contract_id: str,
    scope: EffectivePartyScope,
    lock: bool = False,
) -> UpstreamContract | TerminalContract:
    row: UpstreamContract | TerminalContract | None
    coverages: (
        tuple[UpstreamContractAssetUnit, ...] | tuple[TerminalContractAssetUnit, ...]
    )
    if kind == "upstream":
        row = await asset_contract_repository.get_upstream(
            db, contract_id=contract_id, scope=scope
        )
        coverages = (
            await asset_contract_repository.list_upstream_coverages(
                db, contract_id=contract_id
            )
            if lock and row is not None
            else ()
        )
    else:
        row = await asset_contract_repository.get_terminal(
            db, contract_id=contract_id, scope=scope
        )
        coverages = (
            await asset_contract_repository.list_terminal_coverages(
                db, contract_id=contract_id
            )
            if lock and row is not None
            else ()
        )
    if row is None:
        raise ResourceNotFoundError("Contract", contract_id)
    if lock:
        unit_ids = sorted({coverage.asset_unit_id for coverage in coverages})
        units = await asset_unit_repository.lock_for_write(
            db, unit_ids=unit_ids, scope=scope
        )
        if sorted(unit.id for unit in units) != unit_ids:
            raise ResourceNotFoundError("Contract", contract_id)
        if kind == "upstream":
            row = await asset_contract_repository.get_upstream(
                db, contract_id=contract_id, scope=scope, for_update=True
            )
        else:
            row = await asset_contract_repository.get_terminal(
                db, contract_id=contract_id, scope=scope, for_update=True
            )
        if row is None:
            raise ResourceNotFoundError("Contract", contract_id)
    return row


def check_version(target_id: str, actual: int, expected: int) -> None:
    if actual != expected:
        raise AssetOperationsVersionConflictError(
            unit_id=target_id, expected_version=expected, actual_version=actual
        )


def fingerprint(action: str, target: str, request: BaseModel) -> str:
    data = json.dumps(
        {
            "action": action,
            "target": target,
            "request": request.model_dump(mode="json"),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(data.encode()).hexdigest()


async def audit(
    db: AsyncSession,
    *,
    kind: str,
    contract_id: str,
    action: str,
    actor_id: str,
    correlation_id: str,
    before: dict[str, object],
    after: dict[str, object],
    reason: str | None = None,
) -> None:
    await business_change_repository.add(
        db,
        event=BusinessChangeEvent(  # type: ignore[call-arg]
            id=str(uuid4()),
            target_type=f"{kind}_contract",
            target_id=contract_id,
            action=action,
            actor_id=actor_id,
            before=before,
            after=after,
            reason=reason,
            correlation_id=correlation_id,
            occurred_at=datetime.now(UTC),
        ),
    )


async def receipt(
    db: AsyncSession,
    *,
    actor_id: str,
    key: str,
    action: str,
    request_fingerprint: str,
    result: BaseModel,
) -> None:
    await rent_command_repository.add_receipt(
        db,
        receipt=AssetContractWriteReceipt(  # type: ignore[call-arg]
            id=str(uuid4()),
            actor_id=actor_id,
            command_kind=action,
            idempotency_key=key,
            request_fingerprint=request_fingerprint,
            result_data=result.model_dump(mode="json"),
            created_at=datetime.now(UTC).replace(tzinfo=None),
        ),
    )


def replay_receipt(
    value: AssetContractWriteReceipt, expected_fingerprint: str
) -> dict[str, object]:
    if value.request_fingerprint != expected_fingerprint:
        raise AssetOperationsIdempotencyConflictError()
    return {**value.result_data, "idempotent": True}
