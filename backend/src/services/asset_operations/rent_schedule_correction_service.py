"""Previewed rent schedule replacement preserves every historical source row."""

from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from ...crud.asset_contract import asset_contract_repository
from ...crud.rent_commands import rent_command_repository
from ...models.asset_contract import (
    ContractRentSchedule,
    TerminalContract,
    UpstreamContract,
)
from ...schemas.asset_operations import ContractRentScheduleInput
from ...schemas.rent_commands import (
    RentScheduleCorrectionCommit,
    RentScheduleCorrectionPreview,
    RentScheduleCorrectionProposal,
    RentScheduleCorrectionResponse,
)
from ..party_scope_resolver import EffectivePartyScope
from .boundary_command_service import (
    AssetUnitBoundaryPreviewStore,
    AssetUnitBoundaryPreviewStoreProtocol,
)
from .contract_command_service import AssetContractCommandService
from .errors import (
    AssetOperationsPreviewStaleError,
    AssetOperationsVersionConflictError,
    ContractFieldNotApplicableError,
    TerminalContractAlreadyTerminatedError,
    UpstreamContractAlreadyExitedError,
)
from .rent_command_support import (
    audit,
    check_version,
    fingerprint,
    receipt,
    replay_receipt,
    require_scope,
    scoped_contract,
)
from .rent_errors import rent_error
from .rent_obligation_service import rent_obligation_service


def validate_history(
    old: Sequence[ContractRentScheduleInput],
    proposed: Sequence[ContractRentScheduleInput],
    first_month: date,
) -> tuple[tuple[date, date], ...]:
    """Compare piecewise historical contents, allowing additions only inside gaps."""
    boundaries = {first_month}
    for stage in [*old, *proposed]:
        if stage.stage_start < first_month:
            boundaries.add(stage.stage_start)
            boundaries.add(
                stage.stage_end + timedelta(days=1)
                if stage.stage_end < first_month
                else first_month
            )
    points = sorted(boundaries)
    gaps: list[tuple[date, date]] = []
    for start, stop in zip(points, points[1:]):
        previous = next(
            (stage for stage in old if stage.stage_start <= start <= stage.stage_end),
            None,
        )
        replacement = next(
            (
                stage
                for stage in proposed
                if stage.stage_start <= start <= stage.stage_end
            ),
            None,
        )
        if previous is not None and (
            replacement is None
            or previous.model_dump(exclude={"stage_start", "stage_end"})
            != replacement.model_dump(exclude={"stage_start", "stage_end"})
        ):
            raise rent_error(
                "RENT_SCHEDULE_HISTORY_IMMUTABLE", "往月已有租金阶段不可修改"
            )
        if previous is None and replacement is not None:
            end = stop - timedelta(days=1)
            if gaps and gaps[-1][1] + timedelta(days=1) == start:
                gaps[-1] = (gaps[-1][0], end)
            else:
                gaps.append((start, end))
    return tuple(gaps)


def split_at_current_month(
    stages: Sequence[ContractRentScheduleInput], first_month: date
) -> list[ContractRentScheduleInput]:
    """Keep a separate immutable history segment without changing cycle contents."""
    result = []
    for stage in stages:
        if stage.stage_start < first_month <= stage.stage_end:
            result.append(
                stage.model_copy(update={"stage_end": first_month - timedelta(days=1)})
            )
            result.append(stage.model_copy(update={"stage_start": first_month}))
        else:
            result.append(stage)
    return result


class RentSchedulePreviewStore(AssetUnitBoundaryPreviewStore):
    NAMESPACE = "rent_schedule_correction_preview"


class RentScheduleCorrectionService:
    def __init__(
        self,
        *,
        preview_store: AssetUnitBoundaryPreviewStoreProtocol | None = None,
        business_today: Callable[[], date] | None = None,
    ) -> None:
        self.preview_store = preview_store or RentSchedulePreviewStore()
        self.business_today = business_today or (
            lambda: datetime.now(ZoneInfo("Asia/Shanghai")).date()
        )

    @staticmethod
    def _scope(scope: EffectivePartyScope) -> dict[str, object]:
        return {
            "mode": scope.scope_mode,
            "owners": sorted(scope.owner_party_ids),
            "managers": sorted(scope.manager_party_ids),
        }

    async def _prepare(
        self,
        db: AsyncSession,
        *,
        kind: str,
        contract_id: str,
        request: RentScheduleCorrectionProposal,
        actor_id: str,
        scope: EffectivePartyScope,
        lock: bool,
    ) -> tuple[
        UpstreamContract | TerminalContract,
        tuple[ContractRentSchedule, ...],
        list[ContractRentSchedule],
        date,
        tuple[tuple[date, date], ...],
    ]:
        require_scope(scope, actor_id)
        contract = await scoped_contract(
            db, kind=kind, contract_id=contract_id, scope=scope, lock=lock
        )
        if (
            isinstance(contract, UpstreamContract)
            and contract.contract_type == "management_agreement"
        ):
            raise ContractFieldNotApplicableError(
                contract_type="management_agreement", field_names=["rent_schedules"]
            )
        if request.reason.strip() == "":
            raise rent_error(
                "CORRECTION_REASON_REQUIRED", "租金阶段更正原因必填", status=422
            )
        events = await asset_contract_repository.list_lifecycle_events(
            db, contract_kind=kind, contract_id=contract_id
        )
        reversed_ids = {
            event.reversed_event_id
            for event in events
            if event.event_type == "reversed"
        }
        for event in events:
            if event.id not in reversed_ids:
                if event.event_type == "terminated":
                    raise TerminalContractAlreadyTerminatedError(event_id=event.id)
                if event.event_type == "exited":
                    raise UpstreamContractAlreadyExitedError(event_id=event.id)
        AssetContractCommandService._validate_schedules(
            request.rent_schedules,
            contract_start=contract.start_date,
            contract_end=contract.end_date,
        )
        old = await asset_contract_repository.list_rent_schedules(
            db, contract_kind=kind, contract_ids=(contract_id,)
        )
        old_inputs = [
            ContractRentScheduleInput.model_validate(
                {
                    field: getattr(row, field)
                    for field in ContractRentScheduleInput.model_fields
                }
            )
            for row in old
        ]
        first = self.business_today().replace(day=1)
        gaps = validate_history(old_inputs, request.rent_schedules, first)
        new = [
            ContractRentSchedule(  # type: ignore[call-arg]
                id=str(uuid4()),
                contract_kind=kind,
                contract_id=contract_id,
                **stage.model_dump(),
            )
            for stage in split_at_current_month(request.rent_schedules, first)
        ]
        return contract, old, new, first, gaps

    async def preview(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contract_id: str,
        request: RentScheduleCorrectionProposal,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> RentScheduleCorrectionPreview:
        contract, _, new, first, gaps = await self._prepare(
            db,
            kind=contract_kind,
            contract_id=contract_id,
            request=request,
            actor_id=actor_id,
            scope=scope,
            lock=False,
        )
        plan = await rent_obligation_service.preview(
            db,
            contract_kind=contract_kind,
            contract_id=contract_id,
            schedules=tuple(new),
            replan_from=first,
            supplemental_ranges=gaps,
        )
        state = await rent_obligation_service.fingerprint(
            db, contract_kind=contract_kind, contract_id=contract_id
        )
        token, expires_at = self.preview_store.issue(
            {
                "contract_kind": contract_kind,
                "contract_id": contract_id,
                "actor_id": actor_id,
                "scope": self._scope(scope),
                "state": state,
                "contract_version": contract.version,
                "first_month": first.isoformat(),
                "proposal": request.model_dump(mode="json"),
            }
        )
        return RentScheduleCorrectionPreview(
            contract_id=contract_id,
            contract_version=contract.version,
            rent_schedules=[
                ContractRentScheduleInput.model_validate(stage, from_attributes=True)
                for stage in new
            ],
            impact=plan.summary(),
            preview_token=token,
            expires_at=expires_at,
        )

    async def commit(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contract_id: str,
        request: RentScheduleCorrectionCommit,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> RentScheduleCorrectionResponse:
        require_scope(scope, actor_id)
        action = "correct_rent_schedule"
        request_fingerprint = fingerprint(
            action, f"{contract_kind}:{contract_id}", request
        )
        try:
            locked_contract = await scoped_contract(
                db, kind=contract_kind, contract_id=contract_id, scope=scope, lock=True
            )
            existing = await asset_contract_repository.get_write_receipt(
                db, actor_id=actor_id, idempotency_key=idempotency_key
            )
            if existing is not None:
                return RentScheduleCorrectionResponse.model_validate(
                    replay_receipt(existing, request_fingerprint)
                )
            token = self.preview_store.peek(request.preview_token)
            if token is None or any(
                token.get(key) != value
                for key, value in {
                    "contract_kind": contract_kind,
                    "contract_id": contract_id,
                    "actor_id": actor_id,
                    "scope": self._scope(scope),
                    "first_month": self.business_today().replace(day=1).isoformat(),
                }.items()
            ):
                raise AssetOperationsPreviewStaleError(
                    "target_actor_scope_or_month_changed"
                )
            state = await rent_obligation_service.fingerprint(
                db, contract_kind=contract_kind, contract_id=contract_id
            )
            if (
                token.get("state") != state
                or token.get("contract_version") != locked_contract.version
            ):
                raise AssetOperationsPreviewStaleError("rent_facts_changed")
            proposal = RentScheduleCorrectionProposal.model_validate(
                token.get("proposal")
            )
            contract, old, new, first, gaps = await self._prepare(
                db,
                kind=contract_kind,
                contract_id=contract_id,
                request=proposal,
                actor_id=actor_id,
                scope=scope,
                lock=False,
            )
            check_version(contract_id, contract.version, request.expected_version)
            correlation_id = str(uuid4())
            before = {
                "schedule_ids": [row.id for row in old],
                "contract_version": contract.version,
            }
            await rent_command_repository.replace_schedules(
                db,
                old=old,
                new=new,
                occurred_at=datetime.now(UTC),
                correlation_id=correlation_id,
            )
            contract.version += 1
            await db.flush()
            plan = await rent_obligation_service.replan(
                db,
                contract_kind=contract_kind,
                contract_id=contract_id,
                actor_id=actor_id,
                correlation_id=correlation_id,
                schedules=tuple(new),
                replan_from=first,
                supplemental_ranges=gaps,
            )
            await audit(
                db,
                kind=contract_kind,
                contract_id=contract_id,
                action="rent_schedule_corrected",
                actor_id=actor_id,
                correlation_id=correlation_id,
                before=before,
                after={
                    "schedule_ids": [row.id for row in new],
                    "contract_version": contract.version,
                },
                reason=proposal.reason,
            )
            result = RentScheduleCorrectionResponse(
                contract_id=contract_id, version=contract.version, impact=plan.summary()
            )
            await receipt(
                db,
                actor_id=actor_id,
                key=idempotency_key,
                action=action,
                request_fingerprint=request_fingerprint,
                result=result,
            )
            await db.commit()
            self.preview_store.delete(request.preview_token)
            return result
        except IntegrityError:
            await db.rollback()
            await scoped_contract(
                db, kind=contract_kind, contract_id=contract_id, scope=scope
            )
            existing = await asset_contract_repository.get_write_receipt(
                db, actor_id=actor_id, idempotency_key=idempotency_key
            )
            if existing is None:
                raise
            return RentScheduleCorrectionResponse.model_validate(
                replay_receipt(existing, request_fingerprint)
            )
        except StaleDataError as error:
            await db.rollback()
            raise AssetOperationsVersionConflictError(
                unit_id=contract_id,
                expected_version=request.expected_version,
                actual_version=None,
            ) from error
        except Exception:
            await db.rollback()
            raise


rent_schedule_correction_service = RentScheduleCorrectionService()
