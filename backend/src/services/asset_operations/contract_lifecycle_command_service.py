"""Scoped, append-only lifecycle commands for signed contracts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta
from typing import Protocol
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import PartyScopeForbiddenError, ResourceNotFoundError
from ...crud.asset_contract import (
    asset_contract_repository as default_contract_repository,
)
from ...models.asset_contract import (
    AssetContractWriteReceipt,
    ContractLifecycleEvent,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from ...schemas.asset_operations import (
    ContractLifecycleEventResponse,
    TerminalContractCreate,
    TerminalContractRenewalRequest,
    TerminalContractResponse,
    TerminalContractTerminationCommitRequest,
    TerminalContractTerminationCoverageImpact,
    TerminalContractTerminationPreviewResponse,
    TerminalContractTerminationProposal,
    TerminalContractTerminationReversalProposal,
    UpstreamContractCreate,
    UpstreamContractExitCommitRequest,
    UpstreamContractExitCoverageImpact,
    UpstreamContractExitPreviewResponse,
    UpstreamContractExitProposal,
    UpstreamContractExitReversalProposal,
    UpstreamContractRenewalRequest,
    UpstreamContractResponse,
)
from ..party_scope_resolver import EffectivePartyScope
from .boundary_command_service import (
    AssetUnitBoundaryPreviewStore,
    AssetUnitBoundaryPreviewStoreProtocol,
)
from .business_change_service import contract_snapshot, record_contract_change
from .contract_command_service import (
    asset_contract_command_service as _default_contract_command,
)
from .errors import (
    AssetContractCoverageInvalidError,
    AssetOperationsIdempotencyConflictError,
    AssetOperationsPreviewStaleError,
    AssetOperationsVersionConflictError,
    ContractAlreadyRenewedError,
    TerminalContractAlreadyTerminatedError,
    TerminationReversalBlockedError,
    TerminationReversalTargetInvalidError,
    UpstreamContractAlreadyExitedError,
    UpstreamExitReversalBlockedError,
    UpstreamExitReversalTargetInvalidError,
)
from .lifecycle_rules import validate_upstream_exit


class ContractLifecycleWriter(Protocol):
    async def get_lifecycle_event_by_idempotency_key(
        self,
        db: AsyncSession,
        *,
        idempotency_key: str,
    ) -> ContractLifecycleEvent | None: ...

    async def get_write_receipt(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        idempotency_key: str,
    ) -> AssetContractWriteReceipt | None: ...

    async def get_terminal(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        scope: EffectivePartyScope,
        for_update: bool = False,
    ) -> TerminalContract | None: ...

    async def get_upstream(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        scope: EffectivePartyScope,
        for_update: bool = False,
    ) -> UpstreamContract | None: ...

    async def list_upstream_coverages(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> tuple[UpstreamContractAssetUnit, ...]: ...

    async def truncate_upstream_coverages(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        effective_date: date,
    ) -> int: ...

    async def restore_upstream_coverages(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        cutoff: date,
        until: date,
    ) -> int: ...

    async def find_upstream_overlaps(
        self,
        db: AsyncSession,
        *,
        unit_ids: tuple[str, ...],
        start_date: date,
        end_date: date,
    ) -> tuple[str, ...]: ...

    async def list_terminal_by_upstream(
        self,
        db: AsyncSession,
        *,
        upstream_contract_id: str,
    ) -> tuple[TerminalContract, ...]: ...

    async def list_terminal_lifecycle_events(
        self,
        db: AsyncSession,
        *,
        contract_ids: tuple[str, ...],
    ) -> tuple[ContractLifecycleEvent, ...]: ...

    async def list_lifecycle_events(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contract_id: str,
    ) -> tuple[ContractLifecycleEvent, ...]: ...

    async def list_terminal_coverages(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> tuple[TerminalContractAssetUnit, ...]: ...

    async def find_terminal_overlaps(
        self,
        db: AsyncSession,
        *,
        unit_ids: tuple[str, ...],
        start_date: date,
        end_date: date,
    ) -> tuple[str, ...]: ...

    async def get_lifecycle_event_by_id(
        self,
        db: AsyncSession,
        *,
        event_id: str,
    ) -> ContractLifecycleEvent | None: ...

    async def restore_terminal_coverages(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        cutoff: date,
        until: date,
    ) -> int: ...

    async def truncate_terminal_coverages(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        effective_date: date,
    ) -> int: ...

    async def add_lifecycle_event(
        self,
        db: AsyncSession,
        *,
        event: ContractLifecycleEvent,
    ) -> None: ...


class ContractLifecyclePreviewStore(AssetUnitBoundaryPreviewStore):
    """Termination preview tokens isolated from boundary preview tokens."""

    NAMESPACE = "contract_lifecycle_preview"


class ContractCreator(Protocol):
    """The create commands a renewal chains its successor through."""

    async def create_upstream(
        self,
        db: AsyncSession,
        *,
        request: UpstreamContractCreate,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
        attachment_owner_id: str,
        lifecycle_event: ContractLifecycleEvent | None = None,
    ) -> UpstreamContractResponse: ...

    async def create_terminal(
        self,
        db: AsyncSession,
        *,
        request: TerminalContractCreate,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
        attachment_owner_id: str,
        lifecycle_event: ContractLifecycleEvent | None = None,
    ) -> TerminalContractResponse: ...


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _coverage_end_after(current: date | None, cutoff: date) -> date:
    if current is None or current > cutoff:
        return cutoff
    return current


class ContractLifecycleCommandService:
    """Hide target locking, scope checks and idempotent event persistence."""

    def __init__(
        self,
        *,
        repository: ContractLifecycleWriter | None = None,
        preview_store: AssetUnitBoundaryPreviewStoreProtocol | None = None,
        contract_command: ContractCreator | None = None,
        clock: Callable[[], datetime] = _utcnow,
        id_factory: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self.repository = repository or default_contract_repository
        self.preview_store = preview_store or ContractLifecyclePreviewStore()
        self.contract_command = contract_command or _default_contract_command
        self.clock = clock
        self.id_factory = id_factory

    async def terminate_terminal(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        proposal: TerminalContractTerminationProposal,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> ContractLifecycleEventResponse:
        self._require_actor_scope(actor_id=actor_id, scope=scope)
        self._require_effective_scope(scope)
        existing = await self.repository.get_lifecycle_event_by_idempotency_key(
            db,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            await self._require_terminal(db, contract_id=contract_id, scope=scope)
            return self._replay_termination(
                existing,
                contract_id=contract_id,
                proposal=proposal,
                actor_id=actor_id,
            )

        contract = await self._require_terminal(
            db,
            contract_id=contract_id,
            scope=scope,
        )
        existing = await self.repository.get_lifecycle_event_by_idempotency_key(
            db,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return self._replay_termination(
                existing,
                contract_id=contract_id,
                proposal=proposal,
                actor_id=actor_id,
            )

        events = await self.repository.list_lifecycle_events(
            db,
            contract_kind="terminal",
            contract_id=contract_id,
        )
        active_termination = self._active_termination(events)
        if active_termination is not None:
            raise TerminalContractAlreadyTerminatedError(event_id=active_termination.id)
        coverages = await self.repository.list_terminal_coverages(
            db,
            contract_id=contract_id,
        )
        self._validate_termination_window(
            contract=contract,
            proposal=proposal,
            coverages=coverages,
        )

        audit_before: dict[str, object] = {
            "contract": contract_snapshot(contract),
            "coverages": [contract_snapshot(row) for row in coverages],
        }
        created_at = self._naive_utc(self.clock())
        event = ContractLifecycleEvent(  # type: ignore[call-arg]
            id=self.id_factory(),
            contract_kind="terminal",
            contract_id=contract_id,
            event_type="terminated",
            effective_date=proposal.effective_date,
            termination_type=proposal.termination_type,
            handover_status=proposal.handover_status,
            deposit_settlement_status=proposal.deposit_settlement_status,
            reason=proposal.reason,
            created_by=actor_id,
            created_at=created_at,
            idempotency_key=idempotency_key,
        )
        try:
            await self.repository.truncate_terminal_coverages(
                db,
                contract_id=contract_id,
                effective_date=proposal.effective_date,
            )
            await self.repository.add_lifecycle_event(db, event=event)
            await record_contract_change(
                db,
                contract=contract,
                contract_kind=event.contract_kind,
                action=event.event_type,
                actor_id=actor_id,
                before=audit_before,
                after={
                    "contract": contract_snapshot(contract),
                    "coverages": [contract_snapshot(row) for row in coverages],
                    "lifecycle_event": contract_snapshot(event),
                },
                reason=event.reason,
                correlation_id=event.id,
                occurred_at=self.clock(),
            )
            await db.commit()
            return self._response(event, idempotent=False)
        except IntegrityError:
            await db.rollback()
            existing = await self.repository.get_lifecycle_event_by_idempotency_key(
                db,
                idempotency_key=idempotency_key,
            )
            if existing is None:
                raise
            return self._replay_termination(
                existing,
                contract_id=contract_id,
                proposal=proposal,
                actor_id=actor_id,
            )
        except Exception:
            await db.rollback()
            raise

    async def reverse_terminal_termination(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        proposal: TerminalContractTerminationReversalProposal,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> ContractLifecycleEventResponse:
        """Void one termination: reopen its truncated coverage, append a fact.

        A reversal asserts the terminated event was wrong from the start, so
        the rows it closed reopen to the contract's signed end date. Successor
        facts fail closed: the period is no longer the contract's to reclaim.
        """
        self._require_actor_scope(actor_id=actor_id, scope=scope)
        self._require_effective_scope(scope)
        existing = await self.repository.get_lifecycle_event_by_idempotency_key(
            db,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            await self._require_terminal(db, contract_id=contract_id, scope=scope)
            return self._replay_reversal(
                existing,
                contract_id=contract_id,
                proposal=proposal,
                actor_id=actor_id,
            )

        contract = await self._require_terminal(
            db,
            contract_id=contract_id,
            scope=scope,
        )
        existing = await self.repository.get_lifecycle_event_by_idempotency_key(
            db,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return self._replay_reversal(
                existing,
                contract_id=contract_id,
                proposal=proposal,
                actor_id=actor_id,
            )

        target = await self.repository.get_lifecycle_event_by_id(
            db,
            event_id=proposal.target_event_id,
        )
        if (
            target is None
            or target.contract_kind != "terminal"
            or target.contract_id != contract_id
            or target.event_type != "terminated"
        ):
            raise TerminationReversalTargetInvalidError(reason="target_not_terminated")
        events = await self.repository.list_lifecycle_events(
            db,
            contract_kind="terminal",
            contract_id=contract_id,
        )
        reversed_event_ids = {
            event.reversed_event_id
            for event in events
            if event.event_type == "reversed" and event.reversed_event_id is not None
        }
        if target.id in reversed_event_ids:
            raise TerminationReversalTargetInvalidError(
                reason="target_already_reversed"
            )
        renewed_event_ids = sorted(
            event.id for event in events if event.event_type == "renewed"
        )
        coverages = await self.repository.list_terminal_coverages(
            db,
            contract_id=contract_id,
        )
        blocking_contract_ids = sorted(
            await self.repository.find_terminal_overlaps(
                db,
                unit_ids=tuple(sorted({c.asset_unit_id for c in coverages})),
                start_date=target.effective_date,
                end_date=contract.end_date,
            )
        )
        if renewed_event_ids or blocking_contract_ids:
            raise TerminationReversalBlockedError(
                renewed_event_ids=renewed_event_ids,
                blocking_contract_ids=blocking_contract_ids,
            )

        audit_before: dict[str, object] = {
            "contract": contract_snapshot(contract),
            "coverages": [contract_snapshot(row) for row in coverages],
        }
        created_at = self._naive_utc(self.clock())
        event = ContractLifecycleEvent(  # type: ignore[call-arg]
            id=self.id_factory(),
            contract_kind="terminal",
            contract_id=contract_id,
            event_type="reversed",
            effective_date=proposal.effective_date,
            reversed_event_id=target.id,
            reason=proposal.reason,
            created_by=actor_id,
            created_at=created_at,
            idempotency_key=idempotency_key,
        )
        try:
            await self.repository.restore_terminal_coverages(
                db,
                contract_id=contract_id,
                cutoff=target.effective_date - timedelta(days=1),
                until=contract.end_date,
            )
            await self.repository.add_lifecycle_event(db, event=event)
            await record_contract_change(
                db,
                contract=contract,
                contract_kind=event.contract_kind,
                action=event.event_type,
                actor_id=actor_id,
                before=audit_before,
                after={
                    "contract": contract_snapshot(contract),
                    "coverages": [contract_snapshot(row) for row in coverages],
                    "lifecycle_event": contract_snapshot(event),
                },
                reason=event.reason,
                correlation_id=event.id,
                occurred_at=self.clock(),
            )
            await db.commit()
            return self._response(event, idempotent=False)
        except IntegrityError:
            await db.rollback()
            existing = await self.repository.get_lifecycle_event_by_idempotency_key(
                db,
                idempotency_key=idempotency_key,
            )
            if existing is None:
                raise
            return self._replay_reversal(
                existing,
                contract_id=contract_id,
                proposal=proposal,
                actor_id=actor_id,
            )
        except Exception:
            await db.rollback()
            raise

    async def preview_terminal_termination(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        proposal: TerminalContractTerminationProposal,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> TerminalContractTerminationPreviewResponse:
        """Report the termination impact and bind it to a short-lived token."""
        self._require_actor_scope(actor_id=actor_id, scope=scope)
        self._require_effective_scope(scope)
        contract = await self.repository.get_terminal(
            db,
            contract_id=contract_id,
            scope=scope,
            for_update=False,
        )
        if contract is None:
            raise ResourceNotFoundError("TerminalContract", contract_id)
        events = await self.repository.list_lifecycle_events(
            db,
            contract_kind="terminal",
            contract_id=contract_id,
        )
        active_termination = self._active_termination(events)
        if active_termination is not None:
            raise TerminalContractAlreadyTerminatedError(event_id=active_termination.id)
        coverages = await self.repository.list_terminal_coverages(
            db,
            contract_id=contract_id,
        )
        self._validate_termination_window(
            contract=contract,
            proposal=proposal,
            coverages=coverages,
        )
        cutoff = proposal.effective_date - timedelta(days=1)
        impact = [
            TerminalContractTerminationCoverageImpact(
                asset_unit_id=coverage.asset_unit_id,
                effective_from=coverage.effective_from,
                current_effective_to=coverage.effective_to,
                new_effective_to=_coverage_end_after(coverage.effective_to, cutoff),
            )
            for coverage in coverages
        ]
        warnings: list[str] = []
        if (
            proposal.deposit_settlement_status == "pending"
            and contract.deposit_amount > 0
        ):
            warnings.append("deposit_unsettled")
        token, expires_at = self.preview_store.issue(
            {
                "actor_id": actor_id,
                "action": "terminal_termination",
                "contract_id": contract_id,
                "proposal": proposal.model_dump(mode="json"),
                "scope_signature": self._scope_signature(scope),
                "versions": {contract_id: contract.version},
                "state_fingerprint": self._lifecycle_state_fingerprint(
                    contract_id=contract.id,
                    contract_version=contract.version,
                    coverage_rows=self._coverage_fingerprint_rows(coverages),
                    events=events,
                ),
            }
        )
        return TerminalContractTerminationPreviewResponse(
            contract_id=contract_id,
            contract_number=contract.contract_number,
            contract_version=contract.version,
            effective_date=proposal.effective_date,
            last_valid_day=cutoff,
            coverage_impact=impact,
            warnings=warnings,
            proposal=proposal,
            preview_token=token,
            expires_at=expires_at,
        )

    async def commit_terminal_termination(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        request: TerminalContractTerminationCommitRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> ContractLifecycleEventResponse:
        """Re-validate one preview under lock, then append the event."""
        self._require_actor_scope(actor_id=actor_id, scope=scope)
        self._require_effective_scope(scope)
        existing = await self.repository.get_lifecycle_event_by_idempotency_key(
            db,
            idempotency_key=idempotency_key,
        )
        preview_payload = self.preview_store.peek(request.preview_token)
        if existing is not None:
            if preview_payload is not None:
                # The token is still live: prove it carries the very
                # proposal this key committed before replaying it.
                proposal = self._termination_proposal_from_preview_payload(
                    preview_payload,
                    actor_id=actor_id,
                    scope=scope,
                    contract_id=contract_id,
                )
                self._replay_termination(
                    existing,
                    contract_id=contract_id,
                    proposal=proposal,
                    actor_id=actor_id,
                )
                self.preview_store.delete(request.preview_token)
            return self._replay_committed_termination(
                existing,
                contract_id=contract_id,
                actor_id=actor_id,
            )

        if preview_payload is None:
            raise AssetOperationsPreviewStaleError("missing_or_expired")
        proposal = self._termination_proposal_from_preview_payload(
            preview_payload,
            actor_id=actor_id,
            scope=scope,
            contract_id=contract_id,
        )
        token_versions = preview_payload.get("versions")
        if not isinstance(token_versions, dict):
            raise AssetOperationsPreviewStaleError("versions_missing")
        token_version = token_versions.get(contract_id)
        if token_version != request.expected_version:
            raise AssetOperationsVersionConflictError(
                unit_id=contract_id,
                expected_version=request.expected_version,
                actual_version=token_version if isinstance(token_version, int) else -1,
            )

        contract = await self._require_terminal(
            db,
            contract_id=contract_id,
            scope=scope,
        )
        if contract.version != request.expected_version:
            raise AssetOperationsVersionConflictError(
                unit_id=contract_id,
                expected_version=request.expected_version,
                actual_version=contract.version,
            )
        coverages = await self.repository.list_terminal_coverages(
            db,
            contract_id=contract_id,
        )
        events = await self.repository.list_lifecycle_events(
            db,
            contract_kind="terminal",
            contract_id=contract_id,
        )
        if preview_payload.get(
            "state_fingerprint"
        ) != self._lifecycle_state_fingerprint(
            contract_id=contract.id,
            contract_version=contract.version,
            coverage_rows=self._coverage_fingerprint_rows(coverages),
            events=events,
        ):
            raise AssetOperationsPreviewStaleError("state_changed")

        existing = await self.repository.get_lifecycle_event_by_idempotency_key(
            db,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            self._replay_termination(
                existing,
                contract_id=contract_id,
                proposal=proposal,
                actor_id=actor_id,
            )
            response = self._response(existing, idempotent=True)
            self.preview_store.delete(request.preview_token)
            return response

        response = await self.terminate_terminal(
            db,
            contract_id=contract_id,
            proposal=proposal,
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key,
        )
        self.preview_store.delete(request.preview_token)
        return response

    async def exit_upstream(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        proposal: UpstreamContractExitProposal,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> ContractLifecycleEventResponse:
        """Exit one upstream contract after its terminal leases are handled."""
        self._require_actor_scope(actor_id=actor_id, scope=scope)
        self._require_effective_scope(scope)
        existing = await self.repository.get_lifecycle_event_by_idempotency_key(
            db,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            await self._require_upstream(db, contract_id=contract_id, scope=scope)
            return self._replay_exit(
                existing,
                contract_id=contract_id,
                proposal=proposal,
                actor_id=actor_id,
            )

        contract = await self._require_upstream(
            db,
            contract_id=contract_id,
            scope=scope,
        )
        existing = await self.repository.get_lifecycle_event_by_idempotency_key(
            db,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return self._replay_exit(
                existing,
                contract_id=contract_id,
                proposal=proposal,
                actor_id=actor_id,
            )

        events = await self.repository.list_lifecycle_events(
            db,
            contract_kind="upstream",
            contract_id=contract_id,
        )
        active_exit = self._active_exit(events)
        if active_exit is not None:
            raise UpstreamContractAlreadyExitedError(event_id=active_exit.id)
        coverages = await self.repository.list_upstream_coverages(
            db,
            contract_id=contract_id,
        )
        self._validate_exit_window(
            contract=contract,
            proposal=proposal,
            coverages=coverages,
        )
        await self._assert_no_active_terminals(
            db,
            contract_id=contract_id,
            effective_date=proposal.effective_date,
        )

        audit_before: dict[str, object] = {
            "contract": contract_snapshot(contract),
            "coverages": [contract_snapshot(row) for row in coverages],
        }
        created_at = self._naive_utc(self.clock())
        event = ContractLifecycleEvent(  # type: ignore[call-arg]
            id=self.id_factory(),
            contract_kind="upstream",
            contract_id=contract_id,
            event_type="exited",
            effective_date=proposal.effective_date,
            reason=proposal.reason,
            created_by=actor_id,
            created_at=created_at,
            idempotency_key=idempotency_key,
        )
        try:
            await self.repository.truncate_upstream_coverages(
                db,
                contract_id=contract_id,
                effective_date=proposal.effective_date,
            )
            await self.repository.add_lifecycle_event(db, event=event)
            await record_contract_change(
                db,
                contract=contract,
                contract_kind=event.contract_kind,
                action=event.event_type,
                actor_id=actor_id,
                before=audit_before,
                after={
                    "contract": contract_snapshot(contract),
                    "coverages": [contract_snapshot(row) for row in coverages],
                    "lifecycle_event": contract_snapshot(event),
                },
                reason=event.reason,
                correlation_id=event.id,
                occurred_at=self.clock(),
            )
            await db.commit()
            return self._response(event, idempotent=False)
        except IntegrityError:
            await db.rollback()
            existing = await self.repository.get_lifecycle_event_by_idempotency_key(
                db,
                idempotency_key=idempotency_key,
            )
            if existing is None:
                raise
            return self._replay_exit(
                existing,
                contract_id=contract_id,
                proposal=proposal,
                actor_id=actor_id,
            )
        except Exception:
            await db.rollback()
            raise

    async def preview_upstream_exit(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        proposal: UpstreamContractExitProposal,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> UpstreamContractExitPreviewResponse:
        """Report the exit impact and bind it to a short-lived token."""
        self._require_actor_scope(actor_id=actor_id, scope=scope)
        self._require_effective_scope(scope)
        contract = await self.repository.get_upstream(
            db,
            contract_id=contract_id,
            scope=scope,
            for_update=False,
        )
        if contract is None:
            raise ResourceNotFoundError("UpstreamContract", contract_id)
        events = await self.repository.list_lifecycle_events(
            db,
            contract_kind="upstream",
            contract_id=contract_id,
        )
        active_exit = self._active_exit(events)
        if active_exit is not None:
            raise UpstreamContractAlreadyExitedError(event_id=active_exit.id)
        coverages = await self.repository.list_upstream_coverages(
            db,
            contract_id=contract_id,
        )
        self._validate_exit_window(
            contract=contract,
            proposal=proposal,
            coverages=coverages,
        )
        await self._assert_no_active_terminals(
            db,
            contract_id=contract_id,
            effective_date=proposal.effective_date,
        )
        cutoff = proposal.effective_date - timedelta(days=1)
        impact = [
            UpstreamContractExitCoverageImpact(
                asset_unit_id=coverage.asset_unit_id,
                effective_from=coverage.effective_from,
                current_effective_to=coverage.effective_to,
                new_effective_to=_coverage_end_after(coverage.effective_to, cutoff),
            )
            for coverage in coverages
        ]
        token, expires_at = self.preview_store.issue(
            {
                "actor_id": actor_id,
                "action": "upstream_exit",
                "contract_id": contract_id,
                "proposal": proposal.model_dump(mode="json"),
                "scope_signature": self._scope_signature(scope),
                "versions": {contract_id: contract.version},
                "state_fingerprint": self._lifecycle_state_fingerprint(
                    contract_id=contract.id,
                    contract_version=contract.version,
                    coverage_rows=self._coverage_fingerprint_rows(coverages),
                    events=events,
                ),
            }
        )
        return UpstreamContractExitPreviewResponse(
            contract_id=contract_id,
            contract_number=contract.contract_number,
            contract_version=contract.version,
            deposit_amount=contract.deposit_amount,
            effective_date=proposal.effective_date,
            last_valid_day=cutoff,
            coverage_impact=impact,
            proposal=proposal,
            preview_token=token,
            expires_at=expires_at,
        )

    async def commit_upstream_exit(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        request: UpstreamContractExitCommitRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> ContractLifecycleEventResponse:
        """Re-validate one exit preview under lock, then append the event."""
        self._require_actor_scope(actor_id=actor_id, scope=scope)
        self._require_effective_scope(scope)
        existing = await self.repository.get_lifecycle_event_by_idempotency_key(
            db,
            idempotency_key=idempotency_key,
        )
        preview_payload = self.preview_store.peek(request.preview_token)
        if existing is not None:
            if preview_payload is not None:
                proposal = self._exit_proposal_from_preview_payload(
                    preview_payload,
                    actor_id=actor_id,
                    scope=scope,
                    contract_id=contract_id,
                )
                self._replay_exit(
                    existing,
                    contract_id=contract_id,
                    proposal=proposal,
                    actor_id=actor_id,
                )
                self.preview_store.delete(request.preview_token)
            return self._replay_committed_exit(
                existing,
                contract_id=contract_id,
                actor_id=actor_id,
            )

        if preview_payload is None:
            raise AssetOperationsPreviewStaleError("missing_or_expired")
        proposal = self._exit_proposal_from_preview_payload(
            preview_payload,
            actor_id=actor_id,
            scope=scope,
            contract_id=contract_id,
        )
        token_versions = preview_payload.get("versions")
        if not isinstance(token_versions, dict):
            raise AssetOperationsPreviewStaleError("versions_missing")
        token_version = token_versions.get(contract_id)
        if token_version != request.expected_version:
            raise AssetOperationsVersionConflictError(
                unit_id=contract_id,
                expected_version=request.expected_version,
                actual_version=token_version if isinstance(token_version, int) else -1,
            )

        contract = await self._require_upstream(
            db,
            contract_id=contract_id,
            scope=scope,
        )
        if contract.version != request.expected_version:
            raise AssetOperationsVersionConflictError(
                unit_id=contract_id,
                expected_version=request.expected_version,
                actual_version=contract.version,
            )
        coverages = await self.repository.list_upstream_coverages(
            db,
            contract_id=contract_id,
        )
        events = await self.repository.list_lifecycle_events(
            db,
            contract_kind="upstream",
            contract_id=contract_id,
        )
        if preview_payload.get(
            "state_fingerprint"
        ) != self._lifecycle_state_fingerprint(
            contract_id=contract.id,
            contract_version=contract.version,
            coverage_rows=self._coverage_fingerprint_rows(coverages),
            events=events,
        ):
            raise AssetOperationsPreviewStaleError("state_changed")

        existing = await self.repository.get_lifecycle_event_by_idempotency_key(
            db,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            self._replay_exit(
                existing,
                contract_id=contract_id,
                proposal=proposal,
                actor_id=actor_id,
            )
            response = self._response(existing, idempotent=True)
            self.preview_store.delete(request.preview_token)
            return response

        response = await self.exit_upstream(
            db,
            contract_id=contract_id,
            proposal=proposal,
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key,
        )
        self.preview_store.delete(request.preview_token)
        return response

    async def reverse_upstream_exit(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        proposal: UpstreamContractExitReversalProposal,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> ContractLifecycleEventResponse:
        """Void one exit: reopen its truncated coverage, append a fact."""
        self._require_actor_scope(actor_id=actor_id, scope=scope)
        self._require_effective_scope(scope)
        existing = await self.repository.get_lifecycle_event_by_idempotency_key(
            db,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            await self._require_upstream(db, contract_id=contract_id, scope=scope)
            return self._replay_exit_reversal(
                existing,
                contract_id=contract_id,
                proposal=proposal,
                actor_id=actor_id,
            )

        contract = await self._require_upstream(
            db,
            contract_id=contract_id,
            scope=scope,
        )
        existing = await self.repository.get_lifecycle_event_by_idempotency_key(
            db,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return self._replay_exit_reversal(
                existing,
                contract_id=contract_id,
                proposal=proposal,
                actor_id=actor_id,
            )

        target = await self.repository.get_lifecycle_event_by_id(
            db,
            event_id=proposal.target_event_id,
        )
        if (
            target is None
            or target.contract_kind != "upstream"
            or target.contract_id != contract_id
            or target.event_type != "exited"
        ):
            raise UpstreamExitReversalTargetInvalidError(reason="target_not_exited")
        events = await self.repository.list_lifecycle_events(
            db,
            contract_kind="upstream",
            contract_id=contract_id,
        )
        reversed_event_ids = {
            event.reversed_event_id
            for event in events
            if event.event_type == "reversed" and event.reversed_event_id is not None
        }
        if target.id in reversed_event_ids:
            raise UpstreamExitReversalTargetInvalidError(
                reason="target_already_reversed"
            )
        renewed_event_ids = sorted(
            event.id for event in events if event.event_type == "renewed"
        )
        coverages = await self.repository.list_upstream_coverages(
            db,
            contract_id=contract_id,
        )
        blocking_contract_ids = sorted(
            await self.repository.find_upstream_overlaps(
                db,
                unit_ids=tuple(sorted({c.asset_unit_id for c in coverages})),
                start_date=target.effective_date,
                end_date=contract.end_date,
            )
        )
        if renewed_event_ids or blocking_contract_ids:
            raise UpstreamExitReversalBlockedError(
                renewed_event_ids=renewed_event_ids,
                blocking_contract_ids=blocking_contract_ids,
            )

        audit_before: dict[str, object] = {
            "contract": contract_snapshot(contract),
            "coverages": [contract_snapshot(row) for row in coverages],
        }
        created_at = self._naive_utc(self.clock())
        event = ContractLifecycleEvent(  # type: ignore[call-arg]
            id=self.id_factory(),
            contract_kind="upstream",
            contract_id=contract_id,
            event_type="reversed",
            effective_date=proposal.effective_date,
            reversed_event_id=target.id,
            reason=proposal.reason,
            created_by=actor_id,
            created_at=created_at,
            idempotency_key=idempotency_key,
        )
        try:
            await self.repository.restore_upstream_coverages(
                db,
                contract_id=contract_id,
                cutoff=target.effective_date - timedelta(days=1),
                until=contract.end_date,
            )
            await self.repository.add_lifecycle_event(db, event=event)
            await record_contract_change(
                db,
                contract=contract,
                contract_kind=event.contract_kind,
                action=event.event_type,
                actor_id=actor_id,
                before=audit_before,
                after={
                    "contract": contract_snapshot(contract),
                    "coverages": [contract_snapshot(row) for row in coverages],
                    "lifecycle_event": contract_snapshot(event),
                },
                reason=event.reason,
                correlation_id=event.id,
                occurred_at=self.clock(),
            )
            await db.commit()
            return self._response(event, idempotent=False)
        except IntegrityError:
            await db.rollback()
            existing = await self.repository.get_lifecycle_event_by_idempotency_key(
                db,
                idempotency_key=idempotency_key,
            )
            if existing is None:
                raise
            return self._replay_exit_reversal(
                existing,
                contract_id=contract_id,
                proposal=proposal,
                actor_id=actor_id,
            )
        except Exception:
            await db.rollback()
            raise

    async def renew_upstream(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        request: UpstreamContractRenewalRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> UpstreamContractResponse:
        """Create the signed successor and chain it to this contract.

        Parties, contract type and covered units are carried from the
        predecessor; only the successor's signed terms arrive in the request.
        The successor and the ``renewed`` event land in one transaction.
        """
        self._require_actor_scope(actor_id=actor_id, scope=scope)
        self._require_effective_scope(scope)
        predecessor = await self._require_upstream(
            db,
            contract_id=contract_id,
            scope=scope,
        )
        coverages = await self.repository.list_upstream_coverages(
            db,
            contract_id=contract_id,
        )
        self._require_successor_after_coverage(
            request=request,
            coverages=coverages,
        )
        create_request = UpstreamContractCreate.model_validate(
            {
                "contract_number": request.contract_number,
                "contract_type": predecessor.contract_type,
                "name": request.name,
                "owner_party_id": predecessor.owner_party_id,
                "operator_party_id": predecessor.operator_party_id,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "payment_cycle": request.payment_cycle,
                "payment_day": request.payment_day,
                "management_fee_rate": request.management_fee_rate,
                "deposit_amount": request.deposit_amount,
                "oa_reference": request.oa_reference,
                "renewed_from_id": predecessor.id,
                "scan_document_id": request.scan_document_id,
                "asset_unit_ids": sorted(
                    {coverage.asset_unit_id for coverage in coverages}
                ),
                "rent_schedules": [
                    schedule.model_dump(mode="json")
                    for schedule in request.rent_schedules
                ],
            }
        )
        receipt = await self.repository.get_write_receipt(
            db,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
        )
        if receipt is not None:
            return await self.contract_command.create_upstream(
                db,
                request=create_request,
                actor_id=actor_id,
                scope=scope,
                idempotency_key=idempotency_key,
                attachment_owner_id=request.scan_owner_id,
            )

        events = await self.repository.list_lifecycle_events(
            db,
            contract_kind="upstream",
            contract_id=contract_id,
        )
        active_renewal = self._active_renewal(events)
        if active_renewal is not None:
            raise ContractAlreadyRenewedError(event_id=active_renewal.id)
        event = ContractLifecycleEvent(  # type: ignore[call-arg]
            id=self.id_factory(),
            contract_kind="upstream",
            contract_id=contract_id,
            event_type="renewed",
            effective_date=request.start_date,
            created_by=actor_id,
            created_at=self._naive_utc(self.clock()),
            idempotency_key=idempotency_key,
        )
        return await self.contract_command.create_upstream(
            db,
            request=create_request,
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key,
            attachment_owner_id=request.scan_owner_id,
            lifecycle_event=event,
        )

    async def renew_terminal(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        request: TerminalContractRenewalRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> TerminalContractResponse:
        """Create the signed terminal successor and chain it to this one.

        Tenant, lessor, mode, rent collector and covered units are carried
        from the predecessor; the successor upstream may be named when the
        upstream was renewed first.
        """
        self._require_actor_scope(actor_id=actor_id, scope=scope)
        self._require_effective_scope(scope)
        predecessor = await self._require_terminal(
            db,
            contract_id=contract_id,
            scope=scope,
        )
        coverages = await self.repository.list_terminal_coverages(
            db,
            contract_id=contract_id,
        )
        self._require_successor_after_coverage(
            request=request,
            coverages=coverages,
        )
        create_request = TerminalContractCreate.model_validate(
            {
                "contract_number": request.contract_number,
                "contract_mode": predecessor.contract_mode,
                "tenant_party_id": predecessor.tenant_party_id,
                "lessor_party_id": predecessor.lessor_party_id,
                "upstream_contract_id": request.upstream_contract_id
                if request.upstream_contract_id is not None
                else predecessor.upstream_contract_id,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "deposit_months": request.deposit_months,
                "deposit_amount": request.deposit_amount,
                "rent_collector": predecessor.rent_collector,
                "renewed_from_id": predecessor.id,
                "scan_document_id": request.scan_document_id,
                "asset_unit_ids": sorted(
                    {coverage.asset_unit_id for coverage in coverages}
                ),
                "rent_schedules": [
                    schedule.model_dump(mode="json")
                    for schedule in request.rent_schedules
                ],
            }
        )
        receipt = await self.repository.get_write_receipt(
            db,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
        )
        if receipt is not None:
            return await self.contract_command.create_terminal(
                db,
                request=create_request,
                actor_id=actor_id,
                scope=scope,
                idempotency_key=idempotency_key,
                attachment_owner_id=request.scan_owner_id,
            )

        events = await self.repository.list_lifecycle_events(
            db,
            contract_kind="terminal",
            contract_id=contract_id,
        )
        active_renewal = self._active_renewal(events)
        if active_renewal is not None:
            raise ContractAlreadyRenewedError(event_id=active_renewal.id)
        event = ContractLifecycleEvent(  # type: ignore[call-arg]
            id=self.id_factory(),
            contract_kind="terminal",
            contract_id=contract_id,
            event_type="renewed",
            effective_date=request.start_date,
            created_by=actor_id,
            created_at=self._naive_utc(self.clock()),
            idempotency_key=idempotency_key,
        )
        return await self.contract_command.create_terminal(
            db,
            request=create_request,
            actor_id=actor_id,
            scope=scope,
            idempotency_key=idempotency_key,
            attachment_owner_id=request.scan_owner_id,
            lifecycle_event=event,
        )

    @staticmethod
    def _active_renewal(
        events: Iterable[ContractLifecycleEvent],
    ) -> ContractLifecycleEvent | None:
        reversed_event_ids = {
            event.reversed_event_id
            for event in events
            if event.event_type == "reversed" and event.reversed_event_id is not None
        }
        for event in events:
            if event.event_type == "renewed" and event.id not in reversed_event_ids:
                return event
        return None

    @staticmethod
    def _require_successor_after_coverage(
        *,
        request: UpstreamContractRenewalRequest | TerminalContractRenewalRequest,
        coverages: tuple[TerminalContractAssetUnit, ...]
        | tuple[UpstreamContractAssetUnit, ...],
    ) -> None:
        unit_ids = sorted({coverage.asset_unit_id for coverage in coverages})
        if len(unit_ids) == 0:
            raise AssetContractCoverageInvalidError(
                reason="renewal_without_coverage",
                asset_unit_ids=[],
            )
        ends = [
            coverage.effective_to
            for coverage in coverages
            if coverage.effective_to is not None
        ]
        if len(ends) != len(coverages) or request.start_date <= max(ends):
            raise AssetContractCoverageInvalidError(
                reason="renewal_overlaps_predecessor",
                asset_unit_ids=unit_ids,
            )

    async def _assert_no_active_terminals(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        effective_date: date,
    ) -> None:
        terminal_contracts = await self.repository.list_terminal_by_upstream(
            db,
            upstream_contract_id=contract_id,
        )
        terminal_events = await self.repository.list_terminal_lifecycle_events(
            db,
            contract_ids=tuple(sorted(terminal.id for terminal in terminal_contracts)),
        )
        validate_upstream_exit(
            upstream_contract_id=contract_id,
            effective_date=effective_date,
            terminal_contracts=terminal_contracts,
            lifecycle_events=terminal_events,
        )

    async def _require_terminal(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        scope: EffectivePartyScope,
    ) -> TerminalContract:
        contract = await self.repository.get_terminal(
            db,
            contract_id=contract_id,
            scope=scope,
            for_update=True,
        )
        if contract is None:
            raise ResourceNotFoundError("TerminalContract", contract_id)
        return contract

    async def _require_upstream(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        scope: EffectivePartyScope,
    ) -> UpstreamContract:
        contract = await self.repository.get_upstream(
            db,
            contract_id=contract_id,
            scope=scope,
            for_update=True,
        )
        if contract is None:
            raise ResourceNotFoundError("UpstreamContract", contract_id)
        return contract

    def _replay_exit(
        self,
        event: ContractLifecycleEvent,
        *,
        contract_id: str,
        proposal: UpstreamContractExitProposal,
        actor_id: str,
    ) -> ContractLifecycleEventResponse:
        expected = (
            "upstream",
            contract_id,
            "exited",
            proposal.effective_date,
            proposal.reason,
            actor_id,
        )
        actual = (
            event.contract_kind,
            event.contract_id,
            event.event_type,
            event.effective_date,
            event.reason,
            event.created_by,
        )
        if actual != expected:
            raise AssetOperationsIdempotencyConflictError()
        return self._response(event, idempotent=True)

    def _replay_committed_exit(
        self,
        event: ContractLifecycleEvent,
        *,
        contract_id: str,
        actor_id: str,
    ) -> ContractLifecycleEventResponse:
        if (
            event.contract_kind != "upstream"
            or event.contract_id != contract_id
            or event.event_type != "exited"
            or event.created_by != actor_id
        ):
            raise AssetOperationsIdempotencyConflictError()
        return self._response(event, idempotent=True)

    def _replay_exit_reversal(
        self,
        event: ContractLifecycleEvent,
        *,
        contract_id: str,
        proposal: UpstreamContractExitReversalProposal,
        actor_id: str,
    ) -> ContractLifecycleEventResponse:
        expected = (
            "upstream",
            contract_id,
            "reversed",
            proposal.effective_date,
            proposal.target_event_id,
            proposal.reason,
            actor_id,
        )
        actual = (
            event.contract_kind,
            event.contract_id,
            event.event_type,
            event.effective_date,
            event.reversed_event_id,
            event.reason,
            event.created_by,
        )
        if actual != expected:
            raise AssetOperationsIdempotencyConflictError()
        return self._response(event, idempotent=True)

    def _exit_proposal_from_preview_payload(
        self,
        payload: dict[str, object],
        *,
        actor_id: str,
        scope: EffectivePartyScope,
        contract_id: str,
    ) -> UpstreamContractExitProposal:
        if payload.get("actor_id") != actor_id:
            raise AssetOperationsPreviewStaleError("actor_mismatch")
        if payload.get("action") != "upstream_exit":
            raise AssetOperationsPreviewStaleError("action_mismatch")
        if payload.get("scope_signature") != self._scope_signature(scope):
            raise AssetOperationsPreviewStaleError("scope_changed")
        if payload.get("contract_id") != contract_id:
            raise AssetOperationsPreviewStaleError("target_mismatch")
        raw_proposal = payload.get("proposal")
        if not isinstance(raw_proposal, dict):
            raise AssetOperationsPreviewStaleError("proposal_missing")
        try:
            return UpstreamContractExitProposal.model_validate(raw_proposal)
        except ValueError as exc:
            raise AssetOperationsPreviewStaleError("proposal_invalid") from exc

    def _replay_termination(
        self,
        event: ContractLifecycleEvent,
        *,
        contract_id: str,
        proposal: TerminalContractTerminationProposal,
        actor_id: str,
    ) -> ContractLifecycleEventResponse:
        expected = (
            "terminal",
            contract_id,
            "terminated",
            proposal.effective_date,
            proposal.termination_type,
            proposal.handover_status,
            proposal.deposit_settlement_status,
            proposal.reason,
            actor_id,
        )
        actual = (
            event.contract_kind,
            event.contract_id,
            event.event_type,
            event.effective_date,
            event.termination_type,
            event.handover_status,
            event.deposit_settlement_status,
            event.reason,
            event.created_by,
        )
        if actual != expected:
            raise AssetOperationsIdempotencyConflictError()
        return self._response(event, idempotent=True)

    def _replay_reversal(
        self,
        event: ContractLifecycleEvent,
        *,
        contract_id: str,
        proposal: TerminalContractTerminationReversalProposal,
        actor_id: str,
    ) -> ContractLifecycleEventResponse:
        expected = (
            "terminal",
            contract_id,
            "reversed",
            proposal.effective_date,
            proposal.target_event_id,
            proposal.reason,
            actor_id,
        )
        actual = (
            event.contract_kind,
            event.contract_id,
            event.event_type,
            event.effective_date,
            event.reversed_event_id,
            event.reason,
            event.created_by,
        )
        if actual != expected:
            raise AssetOperationsIdempotencyConflictError()
        return self._response(event, idempotent=True)

    def _replay_committed_termination(
        self,
        event: ContractLifecycleEvent,
        *,
        contract_id: str,
        actor_id: str,
    ) -> ContractLifecycleEventResponse:
        if (
            event.contract_kind != "terminal"
            or event.contract_id != contract_id
            or event.event_type != "terminated"
            or event.created_by != actor_id
        ):
            raise AssetOperationsIdempotencyConflictError()
        return self._response(event, idempotent=True)

    def _termination_proposal_from_preview_payload(
        self,
        payload: dict[str, object],
        *,
        actor_id: str,
        scope: EffectivePartyScope,
        contract_id: str,
    ) -> TerminalContractTerminationProposal:
        if payload.get("actor_id") != actor_id:
            raise AssetOperationsPreviewStaleError("actor_mismatch")
        if payload.get("action") != "terminal_termination":
            raise AssetOperationsPreviewStaleError("action_mismatch")
        if payload.get("scope_signature") != self._scope_signature(scope):
            raise AssetOperationsPreviewStaleError("scope_changed")
        if payload.get("contract_id") != contract_id:
            raise AssetOperationsPreviewStaleError("target_mismatch")
        raw_proposal = payload.get("proposal")
        if not isinstance(raw_proposal, dict):
            raise AssetOperationsPreviewStaleError("proposal_missing")
        try:
            return TerminalContractTerminationProposal.model_validate(raw_proposal)
        except ValueError as exc:
            raise AssetOperationsPreviewStaleError("proposal_invalid") from exc

    @staticmethod
    def _validate_termination_window(
        *,
        contract: TerminalContract,
        proposal: TerminalContractTerminationProposal,
        coverages: tuple[TerminalContractAssetUnit, ...],
    ) -> None:
        if proposal.effective_date <= contract.start_date:
            raise AssetContractCoverageInvalidError(
                reason="termination_covers_no_valid_period",
                asset_unit_ids=sorted(
                    {coverage.asset_unit_id for coverage in coverages}
                ),
            )

    @staticmethod
    def _active_termination(
        events: Iterable[ContractLifecycleEvent],
    ) -> ContractLifecycleEvent | None:
        reversed_event_ids = {
            event.reversed_event_id
            for event in events
            if event.event_type == "reversed" and event.reversed_event_id is not None
        }
        for event in events:
            if event.event_type == "terminated" and event.id not in reversed_event_ids:
                return event
        return None

    @staticmethod
    def _validate_exit_window(
        *,
        contract: UpstreamContract,
        proposal: UpstreamContractExitProposal,
        coverages: tuple[UpstreamContractAssetUnit, ...],
    ) -> None:
        if proposal.effective_date <= contract.start_date:
            raise AssetContractCoverageInvalidError(
                reason="exit_covers_no_valid_period",
                asset_unit_ids=sorted(
                    {coverage.asset_unit_id for coverage in coverages}
                ),
            )

    @staticmethod
    def _active_exit(
        events: Iterable[ContractLifecycleEvent],
    ) -> ContractLifecycleEvent | None:
        reversed_event_ids = {
            event.reversed_event_id
            for event in events
            if event.event_type == "reversed" and event.reversed_event_id is not None
        }
        for event in events:
            if event.event_type == "exited" and event.id not in reversed_event_ids:
                return event
        return None

    @staticmethod
    def _lifecycle_state_fingerprint(
        *,
        contract_id: str,
        contract_version: int,
        coverage_rows: Iterable[tuple[str, str, str]],
        events: tuple[ContractLifecycleEvent, ...],
    ) -> str:
        payload = {
            "contract_id": contract_id,
            "contract_version": contract_version,
            "coverages": sorted(coverage_rows),
            "lifecycle_events": sorted(
                (event.event_type, event.id) for event in events
            ),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _coverage_fingerprint_rows(
        coverages: Iterable[TerminalContractAssetUnit | UpstreamContractAssetUnit],
    ) -> Iterable[tuple[str, str, str]]:
        return (
            (
                coverage.asset_unit_id,
                coverage.effective_from.isoformat(),
                coverage.effective_to.isoformat()
                if coverage.effective_to is not None
                else "",
            )
            for coverage in coverages
        )

    @staticmethod
    def _require_actor_scope(
        *,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> None:
        if scope.user_id != actor_id:
            raise PartyScopeForbiddenError(
                code="PARTY_SCOPE_INVALID_BINDING",
                details={"reason": "scope_actor_mismatch"},
            )

    @staticmethod
    def _scope_signature(scope: EffectivePartyScope) -> dict[str, object]:
        return {
            "source": scope.source,
            "scope_mode": scope.scope_mode,
            "owner_party_ids": sorted(scope.owner_party_ids),
            "manager_party_ids": sorted(scope.manager_party_ids),
            "source_organization_id": scope.source_organization_id,
        }

    @staticmethod
    def _response(
        event: ContractLifecycleEvent,
        *,
        idempotent: bool,
    ) -> ContractLifecycleEventResponse:
        return ContractLifecycleEventResponse.model_validate(
            {
                "id": event.id,
                "contract_kind": event.contract_kind,
                "contract_id": event.contract_id,
                "event_type": event.event_type,
                "effective_date": event.effective_date,
                "termination_type": event.termination_type,
                "handover_status": event.handover_status,
                "deposit_settlement_status": event.deposit_settlement_status,
                "successor_contract_id": event.successor_contract_id,
                "reversed_event_id": event.reversed_event_id,
                "reason": event.reason,
                "created_by": event.created_by,
                "created_at": event.created_at,
                "idempotency_key": event.idempotency_key,
                "idempotent": idempotent,
            }
        )

    @staticmethod
    def _require_effective_scope(scope: EffectivePartyScope) -> None:
        if scope.scope_mode == "unrestricted":
            return
        has_required_axis = (
            scope.scope_mode == "owner"
            and len(scope.owner_party_ids) > 0
            or scope.scope_mode == "manager"
            and len(scope.manager_party_ids) > 0
            or scope.scope_mode == "all"
            and len(scope.effective_party_ids) > 0
        )
        if scope.error_code is not None or not has_required_axis:
            raise PartyScopeForbiddenError(
                code=scope.error_code or "PARTY_SCOPE_MISSING"
            )

    @staticmethod
    def _naive_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)


contract_lifecycle_command_service = ContractLifecycleCommandService()


__all__ = [
    "ContractCreator",
    "ContractLifecycleCommandService",
    "ContractLifecyclePreviewStore",
    "contract_lifecycle_command_service",
]
