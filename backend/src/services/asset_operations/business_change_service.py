"""Build redacted audit facts and expose Party-scoped read projections."""

import re
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi.encoders import jsonable_encoder
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import class_mapper

from ...core.exception_handler import BaseBusinessError, PartyScopeForbiddenError
from ...crud.business_change_event import business_change_repository
from ...models.asset_contract import TerminalContract, UpstreamContract
from ...models.business_change_event import BusinessChangeEvent
from ...schemas.business_change_event import BusinessChangeEventResponse
from ..party_scope_resolver import EffectivePartyScope

_PRIVATE_FIELDS = {
    "phone",
    "mobile",
    "id_card",
    "id_card_number",
    "identity_card",
    "password",
    "password_hash",
    "bank_account",
    "bank_account_number",
    "contact_phone",
    "email",
}
_ACTION_LABELS = {
    "rent_obligations_replanned": "重排租金义务",
    "rent_payment_registered": "登记租金",
    "rent_payment_reversed": "撤销租金登记",
    "manual_rent_created": "登记手工租金义务",
    "manual_rent_voided": "作废手工租金义务",
    "rent_schedule_corrected": "更正租金阶段",
    "confirmed": "确认合同",
    "updated": "修改合同",
    "renewed": "续签合同",
    "terminated": "终止合同",
    "exited": "退出合同",
    "reversed": "撤销合同变更",
}


def redact_snapshot(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: "***" if key.lower() in _PRIVATE_FIELDS else redact_snapshot(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_snapshot(item) for item in value]
    return value


def contract_snapshot(contract: object) -> dict[str, object]:
    return cast(
        dict[str, object],
        jsonable_encoder(
            {
                column.key: getattr(contract, column.key)
                for column in class_mapper(type(contract)).columns
            }
        ),
    )


async def record_contract_change(
    db: AsyncSession,
    *,
    contract: UpstreamContract | TerminalContract,
    contract_kind: str,
    action: str,
    actor_id: str,
    before: dict[str, object] | None = None,
    after: dict[str, object] | None = None,
    reason: str | None = None,
    correlation_id: str | None = None,
    occurred_at: datetime | None = None,
    target_id: str | None = None,
) -> None:
    if action in {"terminated", "exited", "reversed"} and (
        reason is None or not reason.strip()
    ):
        raise ValueError("Business change reason is required")
    await business_change_repository.add(
        db,
        event=BusinessChangeEvent(  # type: ignore[call-arg]
            id=str(uuid4()),
            target_type=f"{contract_kind}_contract",
            target_id=target_id if target_id is not None else contract.id,
            action=action,
            actor_id=actor_id,
            before=redact_snapshot(before or {}),
            after=redact_snapshot(
                after if after is not None else contract_snapshot(contract)
            ),
            reason=reason,
            correlation_id=correlation_id or str(uuid4()),
            occurred_at=occurred_at or datetime.now(UTC),
        ),
    )


class BusinessChangeService:
    async def list_events(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        target_type: str | None = None,
        target_id: str | None = None,
        period: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[BusinessChangeEventResponse], int]:
        has_axis = (
            (scope.scope_mode == "owner" and len(scope.owner_party_ids) > 0)
            or (scope.scope_mode == "manager" and len(scope.manager_party_ids) > 0)
            or (scope.scope_mode == "all" and len(scope.effective_party_ids) > 0)
        )
        if scope.scope_mode != "unrestricted" and (
            scope.error_code is not None or not has_axis
        ):
            raise PartyScopeForbiddenError(
                code=scope.error_code or "PARTY_SCOPE_MISSING"
            )
        since = until = None
        if period is not None:
            if re.fullmatch(r"[1-9][0-9]{3}-(0[1-9]|1[0-2])", period) is None:
                raise BaseBusinessError(
                    message="月份格式无效，请使用 YYYY-MM",
                    code="INVALID_PERIOD",
                    status_code=400,
                )
            year, month = map(int, period.split("-"))
            since = datetime(year, month, 1, tzinfo=ZoneInfo("Asia/Shanghai"))
            if year != 9999 or month != 12:
                until = datetime(
                    year + (month == 12),
                    month % 12 + 1,
                    1,
                    tzinfo=ZoneInfo("Asia/Shanghai"),
                )
        events, total = await business_change_repository.list_events(
            db,
            scope=scope,
            target_type=target_type,
            target_id=target_id,
            since=since,
            until=until,
            offset=offset,
            limit=limit,
        )
        return [
            BusinessChangeEventResponse.model_validate(
                {
                    **{
                        column.key: getattr(event, column.key)
                        for column in inspect(BusinessChangeEvent).columns
                    },
                    "summary": _ACTION_LABELS.get(event.action, event.action),
                    "related_objects": [
                        {"target_type": event.target_type, "target_id": event.target_id}
                    ],
                }
            )
            for event in events
        ], total


business_change_service = BusinessChangeService()
