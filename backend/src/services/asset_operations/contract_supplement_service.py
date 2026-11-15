from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import BaseBusinessError, ResourceNotFoundError
from ...crud.asset_contract import asset_contract_repository
from ...crud.business_change_event import business_change_repository
from ...crud.contract_supplement import contract_supplement_repository
from ...models.asset_contract import TerminalContract, UpstreamContract
from ...models.business_change_event import BusinessChangeEvent
from ...models.contract_supplement import ContractSupplement
from ...schemas.contract_supplement import (
    SupplementCreate,
    SupplementItem,
    SupplementList,
    SupplementWithdrawal,
)
from ..party_scope_resolver import EffectivePartyScope
from .rent_command_support import require_scope


class ContractSupplementService:
    async def _parent(
        self,
        db: AsyncSession,
        kind: str,
        identity: str,
        scope: EffectivePartyScope,
        *,
        lock: bool = False,
    ) -> None:
        require_scope(scope, scope.user_id)
        parent: UpstreamContract | TerminalContract | None
        if kind == "upstream":
            parent = await asset_contract_repository.get_upstream(
                db, contract_id=identity, scope=scope, for_update=lock
            )
        else:
            parent = await asset_contract_repository.get_terminal(
                db, contract_id=identity, scope=scope, for_update=lock
            )
        if parent is None:
            raise ResourceNotFoundError("Contract", identity)

    async def list(
        self,
        db: AsyncSession,
        *,
        kind: str,
        contract_id: str,
        scope: EffectivePartyScope,
    ) -> SupplementList:
        await self._parent(db, kind, contract_id, scope)
        return SupplementList(
            items=[
                SupplementItem.model_validate(row)
                for row in await contract_supplement_repository.list(
                    db, kind=kind, contract_id=contract_id
                )
            ]
        )

    async def create(
        self,
        db: AsyncSession,
        *,
        request: SupplementCreate,
        scope: EffectivePartyScope,
        actor_id: str,
    ) -> SupplementItem:
        require_scope(scope, actor_id)
        await self._parent(
            db, request.contract_kind, request.contract_id, scope, lock=True
        )
        rows = await contract_supplement_repository.list(
            db, kind=request.contract_kind, contract_id=request.contract_id
        )
        if any(row.agreement_number == request.agreement_number for row in rows):
            raise BaseBusinessError(
                "该合同已登记此协议编号",
                code="SUPPLEMENT_NUMBER_EXISTS",
                status_code=409,
            )
        row = ContractSupplement(**{**request.model_dump(), "created_by": actor_id})
        await contract_supplement_repository.add(db, row)
        await self._audit(db, row, actor_id, "supplement_registered", None)
        result = SupplementItem.model_validate(row)
        await db.commit()
        return result

    async def withdraw(
        self,
        db: AsyncSession,
        *,
        identity: str,
        request: SupplementWithdrawal,
        scope: EffectivePartyScope,
        actor_id: str,
    ) -> SupplementItem:
        require_scope(scope, actor_id)
        row = await contract_supplement_repository.get(db, identity)
        if row is None:
            raise ResourceNotFoundError("ContractSupplement", identity)
        await self._parent(db, row.contract_kind, row.contract_id, scope, lock=True)
        row = await contract_supplement_repository.get(db, identity, lock=True)
        if row is None:
            raise ResourceNotFoundError("ContractSupplement", identity)
        if row.version != request.expected_version or row.withdrawn_at is not None:
            raise BaseBusinessError(
                "登记已变化，请刷新", code="SUPPLEMENT_VERSION_STALE", status_code=409
            )
        await contract_supplement_repository.withdraw(
            db, row, actor_id=actor_id, reason=request.reason
        )
        await self._audit(db, row, actor_id, "supplement_withdrawn", request.reason)
        result = SupplementItem.model_validate(row)
        await db.commit()
        return result

    async def _audit(
        self,
        db: AsyncSession,
        row: ContractSupplement,
        actor: str,
        action: str,
        reason: str | None,
    ) -> None:
        await business_change_repository.add(
            db,
            event=BusinessChangeEvent(
                **{
                    "target_type": row.contract_kind + "_contract",
                    "target_id": row.contract_id,
                    "action": action,
                    "before": {},
                    "after": {
                        "supplement_id": row.id,
                        "agreement_number": row.agreement_number,
                        "title": row.title,
                    },
                    "reason": reason,
                    "actor_id": actor,
                    "occurred_at": datetime.now(UTC),
                    "correlation_id": str(uuid4()),
                }
            ),
        )


contract_supplement_service = ContractSupplementService()
