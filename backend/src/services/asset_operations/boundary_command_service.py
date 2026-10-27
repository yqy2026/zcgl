"""Preview and commit asset-unit boundary changes behind one command interface."""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from ...core.cache_manager import cache_manager
from ...core.exception_handler import (
    PartyScopeForbiddenError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from ...crud.asset_unit_boundary import (
    AssetUnitMergeContext,
    AssetUnitSplitContext,
    asset_unit_boundary_repository,
)
from ...models.asset_unit import AssetUnit, AssetUnitBoundaryChange
from ...schemas.asset_operations import (
    AssetUnitBoundaryCommitResponse,
    AssetUnitBoundaryImpact,
    AssetUnitBoundaryPreviewResponse,
    AssetUnitMergeCommitRequest,
    AssetUnitMergeProposal,
    AssetUnitMergeResultInput,
    AssetUnitSplitCommitRequest,
    AssetUnitSplitPartInput,
    AssetUnitSplitProposal,
)
from ..party_scope_resolver import EffectivePartyScope
from .boundary_rules import (
    active_upstream_contract_ids,
    terminal_contract_conflict_ids,
    validate_merge,
    validate_split,
)
from .errors import (
    AssetOperationsIdempotencyConflictError,
    AssetOperationsPreviewStaleError,
    AssetOperationsVersionConflictError,
    AssetUnitBoundaryInvalidError,
    AssetUnitPeriodOverlapError,
)

_BUSINESS_TIMEZONE = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class _SplitAnalysis:
    context: AssetUnitSplitContext
    source: AssetUnit
    proposed_source: AssetUnit
    proposed_results: tuple[AssetUnit, ...]
    normalized_proposal: dict[str, object]
    state_fingerprint: str
    area_check: dict[str, dict[str, str]]
    active_upstream_contract_ids: tuple[str, ...]
    terminal_contract_conflict_ids: tuple[str, ...]


@dataclass(frozen=True)
class _MergeAnalysis:
    context: AssetUnitMergeContext
    sources: tuple[AssetUnit, ...]
    proposed_sources: tuple[AssetUnit, ...]
    proposed_result: AssetUnit
    normalized_proposal: dict[str, object]
    state_fingerprint: str
    area_check: dict[str, dict[str, str]]
    active_upstream_contract_ids: tuple[str, ...]
    terminal_contract_conflict_ids: tuple[str, ...]


class AssetUnitBoundaryRepositoryProtocol(Protocol):
    async def load_split_context(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        scope: EffectivePartyScope,
        effective_date: date,
        result_unit_codes: tuple[str, ...],
        for_update: bool,
    ) -> AssetUnitSplitContext: ...

    async def load_merge_context(
        self,
        db: AsyncSession,
        *,
        unit_ids: tuple[str, ...],
        scope: EffectivePartyScope,
        effective_date: date,
        result_unit_code: str,
        for_update: bool,
    ) -> AssetUnitMergeContext: ...

    async def get_boundary_change_by_idempotency(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        idempotency_key: str,
    ) -> AssetUnitBoundaryChange | None: ...

    async def get_asset_unit_version(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
    ) -> int | None: ...

    async def persist_split(
        self,
        db: AsyncSession,
        *,
        source: AssetUnit,
        results: list[AssetUnit],
        boundary_change: AssetUnitBoundaryChange,
        active_upstream_contract_ids: tuple[str, ...],
        effective_date: date,
    ) -> AssetUnitBoundaryChange: ...

    async def persist_merge(
        self,
        db: AsyncSession,
        *,
        sources: tuple[AssetUnit, ...],
        result: AssetUnit,
        boundary_change: AssetUnitBoundaryChange,
        active_upstream_contract_ids: tuple[str, ...],
        effective_date: date,
    ) -> AssetUnitBoundaryChange: ...


class AssetUnitBoundaryPreviewStoreProtocol(Protocol):
    def issue(self, payload: dict[str, object]) -> tuple[str, datetime]: ...

    def peek(self, raw_token: str) -> dict[str, object] | None: ...

    def delete(self, raw_token: str) -> bool: ...


class AssetUnitBoundaryPreviewStore:
    """Short-lived opaque tokens deleted only after a successful commit."""

    NAMESPACE = "asset_unit_boundary_preview"
    TTL = timedelta(minutes=10)

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC).replace(tzinfo=None))

    def issue(self, payload: dict[str, object]) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(32)
        expires_at = self._clock() + self.TTL
        if not cache_manager.set(
            self._token_hash(token),
            {**payload, "expires_at": expires_at.isoformat()},
            ttl=int(self.TTL.total_seconds()),
            namespace=self.NAMESPACE,
        ):
            raise ServiceUnavailableError(
                "无法保存资产单元调整预览",
                service_name="asset_unit_boundary_preview",
            )
        return token, expires_at

    def peek(self, raw_token: str) -> dict[str, object] | None:
        token = str(raw_token).strip()
        if token == "":  # nosec B105 - empty-token guard
            return None
        payload = cache_manager.get(
            self._token_hash(token),
            namespace=self.NAMESPACE,
        )
        if not isinstance(payload, dict):
            return None
        expires_at_raw = payload.get("expires_at")
        if not isinstance(expires_at_raw, str):
            return None
        try:
            expires_at = datetime.fromisoformat(expires_at_raw)
        except ValueError:
            return None
        if expires_at <= self._clock():
            return None
        return payload

    def delete(self, raw_token: str) -> bool:
        token = str(raw_token).strip()
        if token == "":  # nosec B105 - empty-token guard
            return False
        return cache_manager.delete(
            self._token_hash(token),
            namespace=self.NAMESPACE,
        )

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AssetUnitBoundaryCommandService:
    """Hide scope, normalization, rule evaluation and token binding from callers."""

    def __init__(
        self,
        *,
        repository: AssetUnitBoundaryRepositoryProtocol | None = None,
        preview_store: AssetUnitBoundaryPreviewStoreProtocol | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository or asset_unit_boundary_repository
        self._clock = clock or (lambda: datetime.now(UTC).replace(tzinfo=None))
        self.preview_store = preview_store or AssetUnitBoundaryPreviewStore(
            clock=self._clock
        )

    async def preview(
        self,
        db: AsyncSession,
        *,
        proposal: AssetUnitSplitProposal,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> AssetUnitBoundaryPreviewResponse:
        self._require_actor_scope(actor_id=actor_id, scope=scope)
        self._require_effective_scope(scope)
        analysis = await self._analyze_split(
            db,
            proposal=proposal,
            scope=scope,
            for_update=False,
        )
        versions = {analysis.source.id: analysis.source.version}
        token, expires_at = self.preview_store.issue(
            {
                "actor_id": actor_id,
                "action": "split",
                "source_unit_ids": [analysis.source.id],
                "proposal": analysis.normalized_proposal,
                "scope_signature": self._scope_signature(scope),
                "versions": versions,
                "state_fingerprint": analysis.state_fingerprint,
            }
        )
        return AssetUnitBoundaryPreviewResponse(
            change_type="split",
            source_unit_ids=[analysis.source.id],
            results=proposal.parts,
            area_check=analysis.area_check,
            impact=AssetUnitBoundaryImpact(
                source_units_stop_on=proposal.effective_date - timedelta(days=1),
                result_units_start_on=proposal.effective_date,
                unit_count_delta=len(proposal.parts) - 1,
            ),
            warnings=[],
            versions=versions,
            preview_token=token,
            expires_at=self._api_datetime(expires_at),
        )

    async def preview_merge(
        self,
        db: AsyncSession,
        *,
        proposal: AssetUnitMergeProposal,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> AssetUnitBoundaryPreviewResponse:
        """Validate a multi-source merge and issue a bound preview token."""
        self._require_actor_scope(actor_id=actor_id, scope=scope)
        self._require_effective_scope(scope)
        analysis = await self._analyze_merge(
            db,
            proposal=proposal,
            scope=scope,
            for_update=False,
        )
        versions = {source.id: source.version for source in analysis.sources}
        source_unit_ids = [source.id for source in analysis.sources]
        token, expires_at = self.preview_store.issue(
            {
                "actor_id": actor_id,
                "action": "merge",
                "source_unit_ids": source_unit_ids,
                "proposal": analysis.normalized_proposal,
                "scope_signature": self._scope_signature(scope),
                "versions": versions,
                "state_fingerprint": analysis.state_fingerprint,
            }
        )
        return AssetUnitBoundaryPreviewResponse(
            change_type="merge",
            source_unit_ids=source_unit_ids,
            results=[self._part_from_result(analysis.proposed_result)],
            area_check=analysis.area_check,
            impact=AssetUnitBoundaryImpact(
                source_units_stop_on=proposal.effective_date - timedelta(days=1),
                result_units_start_on=proposal.effective_date,
                unit_count_delta=1 - len(source_unit_ids),
            ),
            warnings=[],
            versions=versions,
            preview_token=token,
            expires_at=self._api_datetime(expires_at),
        )

    async def commit(
        self,
        db: AsyncSession,
        *,
        source_unit_id: str,
        request: AssetUnitSplitCommitRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> AssetUnitBoundaryCommitResponse:
        """Commit one split atomically and replay its first response on retry."""
        self._require_actor_scope(actor_id=actor_id, scope=scope)
        self._require_effective_scope(scope)
        request_fingerprint = self._request_fingerprint(
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            source_unit_id=source_unit_id,
            request=request,
        )
        existing = await self.repository.get_boundary_change_by_idempotency(
            db,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return self._response_from_existing(
                existing,
                request_fingerprint=request_fingerprint,
            )

        preview_payload = self.preview_store.peek(request.preview_token)
        if preview_payload is None:
            raise AssetOperationsPreviewStaleError("missing_or_expired")
        proposal = self._proposal_from_preview_payload(
            preview_payload,
            actor_id=actor_id,
            scope=scope,
        )
        if proposal.source_unit_id != source_unit_id:
            raise AssetOperationsPreviewStaleError("target_mismatch")
        token_versions = preview_payload.get("versions")
        if not isinstance(token_versions, dict):
            raise AssetOperationsPreviewStaleError("versions_missing")
        token_version = token_versions.get(proposal.source_unit_id)
        if token_version != request.expected_version:
            raise AssetOperationsVersionConflictError(
                unit_id=proposal.source_unit_id,
                expected_version=request.expected_version,
                actual_version=int(token_version)
                if isinstance(token_version, int)
                else -1,
            )

        analysis = await self._analyze_split(
            db,
            proposal=proposal,
            scope=scope,
            for_update=True,
        )
        if analysis.source.version != request.expected_version:
            raise AssetOperationsVersionConflictError(
                unit_id=analysis.source.id,
                expected_version=request.expected_version,
                actual_version=analysis.source.version,
            )
        if preview_payload.get("state_fingerprint") != analysis.state_fingerprint:
            raise AssetOperationsPreviewStaleError("state_changed")

        existing = await self.repository.get_boundary_change_by_idempotency(
            db,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return self._response_from_existing(
                existing,
                request_fingerprint=request_fingerprint,
            )

        occurred_at = self._clock()
        committed_at = self._api_datetime(occurred_at)
        persisted_created_at = self._database_datetime(occurred_at)
        source_id = analysis.source.id
        observed_version = analysis.source.version
        result_units = [
            self._persistable_result(result) for result in analysis.proposed_results
        ]
        analysis.source.managed_to = proposal.effective_date - timedelta(days=1)
        analysis.source.version = observed_version + 1
        boundary_change_id = str(uuid.uuid4())
        response = AssetUnitBoundaryCommitResponse(
            boundary_change_id=boundary_change_id,
            change_type="split",
            source_unit_ids=[analysis.source.id],
            result_unit_ids=[unit.id for unit in result_units],
            effective_date=proposal.effective_date,
            committed_at=committed_at,
            idempotent=False,
        )
        boundary_change = AssetUnitBoundaryChange(  # type: ignore[call-arg]
            id=boundary_change_id,
            change_type="split",
            effective_date=proposal.effective_date,
            source_unit_ids=[analysis.source.id],
            result_unit_ids=response.result_unit_ids,
            area_check=analysis.area_check,
            reason=request.reason,
            created_by=actor_id,
            created_at=persisted_created_at,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            result_data=response.model_dump(mode="json"),
        )
        try:
            await self.repository.persist_split(
                db,
                source=analysis.source,
                results=result_units,
                boundary_change=boundary_change,
                active_upstream_contract_ids=analysis.active_upstream_contract_ids,
                effective_date=proposal.effective_date,
            )
            await db.commit()
        except StaleDataError as exc:
            await db.rollback()
            actual_version = await self.repository.get_asset_unit_version(
                db,
                unit_id=source_id,
            )
            raise AssetOperationsVersionConflictError(
                unit_id=source_id,
                expected_version=request.expected_version,
                actual_version=actual_version,
            ) from exc
        except IntegrityError as exc:
            await db.rollback()
            concurrent = await self.repository.get_boundary_change_by_idempotency(
                db,
                actor_id=actor_id,
                idempotency_key=idempotency_key,
            )
            if concurrent is None:
                if self._integrity_constraint_name(exc) == "uq_asset_units_unit_code":
                    raise AssetUnitBoundaryInvalidError(
                        reason="result_unit_code_conflict",
                        unit_ids=[source_id],
                    ) from exc
                if (
                    self._integrity_constraint_name(exc)
                    == "uq_asset_unit_boundary_sources_unit"
                ):
                    raise AssetUnitBoundaryInvalidError(
                        reason="source_boundary_already_changed",
                        unit_ids=[source_id],
                    ) from exc
                raise
            replay = self._response_from_existing(
                concurrent,
                request_fingerprint=request_fingerprint,
            )
            self.preview_store.delete(request.preview_token)
            return replay
        self.preview_store.delete(request.preview_token)
        return response

    async def commit_merge(
        self,
        db: AsyncSession,
        *,
        request: AssetUnitMergeCommitRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> AssetUnitBoundaryCommitResponse:
        """Commit one merge atomically and replay its first response on retry."""
        self._require_actor_scope(actor_id=actor_id, scope=scope)
        self._require_effective_scope(scope)
        request_fingerprint = self._merge_request_fingerprint(
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            request=request,
        )
        existing = await self.repository.get_boundary_change_by_idempotency(
            db,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return self._response_from_existing(
                existing,
                request_fingerprint=request_fingerprint,
            )

        preview_payload = self.preview_store.peek(request.preview_token)
        if preview_payload is None:
            raise AssetOperationsPreviewStaleError("missing_or_expired")
        proposal = self._merge_proposal_from_preview_payload(
            preview_payload,
            actor_id=actor_id,
            scope=scope,
        )
        token_versions = preview_payload.get("versions")
        if not isinstance(token_versions, dict):
            raise AssetOperationsPreviewStaleError("versions_missing")
        source_unit_ids = tuple(proposal.source_unit_ids)
        if set(token_versions) != set(source_unit_ids) or set(
            request.expected_versions
        ) != set(source_unit_ids):
            raise AssetOperationsPreviewStaleError("version_set_mismatch")
        for unit_id in source_unit_ids:
            token_version = token_versions.get(unit_id)
            expected_version = request.expected_versions[unit_id]
            if token_version != expected_version:
                raise AssetOperationsVersionConflictError(
                    unit_id=unit_id,
                    expected_version=expected_version,
                    actual_version=(
                        int(token_version) if isinstance(token_version, int) else None
                    ),
                )

        analysis = await self._analyze_merge(
            db,
            proposal=proposal,
            scope=scope,
            for_update=True,
        )
        for source in analysis.sources:
            expected_version = request.expected_versions[source.id]
            if source.version != expected_version:
                raise AssetOperationsVersionConflictError(
                    unit_id=source.id,
                    expected_version=expected_version,
                    actual_version=source.version,
                )
        if preview_payload.get("state_fingerprint") != analysis.state_fingerprint:
            raise AssetOperationsPreviewStaleError("state_changed")

        existing = await self.repository.get_boundary_change_by_idempotency(
            db,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return self._response_from_existing(
                existing,
                request_fingerprint=request_fingerprint,
            )

        occurred_at = self._clock()
        committed_at = self._api_datetime(occurred_at)
        persisted_created_at = self._database_datetime(occurred_at)
        result = self._persistable_result(analysis.proposed_result)
        for source in analysis.sources:
            source.managed_to = proposal.effective_date - timedelta(days=1)
            source.version += 1
        boundary_change_id = str(uuid.uuid4())
        response = AssetUnitBoundaryCommitResponse(
            boundary_change_id=boundary_change_id,
            change_type="merge",
            source_unit_ids=[source.id for source in analysis.sources],
            result_unit_ids=[result.id],
            effective_date=proposal.effective_date,
            committed_at=committed_at,
            idempotent=False,
        )
        boundary_change = AssetUnitBoundaryChange(  # type: ignore[call-arg]
            id=boundary_change_id,
            change_type="merge",
            effective_date=proposal.effective_date,
            source_unit_ids=response.source_unit_ids,
            result_unit_ids=response.result_unit_ids,
            area_check=analysis.area_check,
            reason=request.reason,
            created_by=actor_id,
            created_at=persisted_created_at,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            result_data=response.model_dump(mode="json"),
        )
        try:
            await self.repository.persist_merge(
                db,
                sources=analysis.sources,
                result=result,
                boundary_change=boundary_change,
                active_upstream_contract_ids=analysis.active_upstream_contract_ids,
                effective_date=proposal.effective_date,
            )
            await db.commit()
        except StaleDataError as exc:
            await db.rollback()
            for unit_id in source_unit_ids:
                actual_version = await self.repository.get_asset_unit_version(
                    db,
                    unit_id=unit_id,
                )
                expected_version = request.expected_versions[unit_id]
                if actual_version != expected_version:
                    raise AssetOperationsVersionConflictError(
                        unit_id=unit_id,
                        expected_version=expected_version,
                        actual_version=actual_version,
                    ) from exc
            first_unit_id = source_unit_ids[0]
            raise AssetOperationsVersionConflictError(
                unit_id=first_unit_id,
                expected_version=request.expected_versions[first_unit_id],
                actual_version=None,
            ) from exc
        except IntegrityError as exc:
            await db.rollback()
            concurrent = await self.repository.get_boundary_change_by_idempotency(
                db,
                actor_id=actor_id,
                idempotency_key=idempotency_key,
            )
            if concurrent is None:
                constraint_name = self._integrity_constraint_name(exc)
                if constraint_name == "uq_asset_units_unit_code":
                    raise AssetUnitBoundaryInvalidError(
                        reason="result_unit_code_conflict",
                        unit_ids=list(source_unit_ids),
                    ) from exc
                if constraint_name == "uq_asset_unit_boundary_sources_unit":
                    raise AssetUnitBoundaryInvalidError(
                        reason="source_boundary_already_changed",
                        unit_ids=list(source_unit_ids),
                    ) from exc
                raise
            replay = self._response_from_existing(
                concurrent,
                request_fingerprint=request_fingerprint,
            )
            self.preview_store.delete(request.preview_token)
            return replay
        self.preview_store.delete(request.preview_token)
        return response

    async def _analyze_split(
        self,
        db: AsyncSession,
        *,
        proposal: AssetUnitSplitProposal,
        scope: EffectivePartyScope,
        for_update: bool,
    ) -> _SplitAnalysis:
        if proposal.effective_date <= self._business_today():
            raise AssetUnitBoundaryInvalidError(
                reason="effective_date_not_future",
                unit_ids=[proposal.source_unit_id],
            )
        context = await self.repository.load_split_context(
            db,
            unit_id=proposal.source_unit_id,
            scope=scope,
            effective_date=proposal.effective_date,
            result_unit_codes=tuple(part.unit_code for part in proposal.parts),
            for_update=for_update,
        )
        source = context.source
        if source is None:
            raise ResourceNotFoundError("AssetUnit", proposal.source_unit_id)
        if context.existing_boundary_change_id is not None:
            raise AssetUnitBoundaryInvalidError(
                reason="source_boundary_already_changed",
                unit_ids=[source.id],
            )
        boundary_day = proposal.effective_date - timedelta(days=1)
        if source.managed_from > boundary_day or (
            source.managed_to is not None and source.managed_to < boundary_day
        ):
            raise AssetUnitBoundaryInvalidError(
                reason="source_not_effective_on_boundary",
                unit_ids=[source.id],
            )
        if len(context.existing_result_unit_codes) > 0:
            raise AssetUnitBoundaryInvalidError(
                reason="result_unit_code_conflict",
                unit_ids=[source.id],
            )
        future_upstream_unit_ids = sorted(
            {
                coverage.asset_unit_id
                for coverage in context.upstream_coverages
                if coverage.effective_from > proposal.effective_date
            }
        )
        if len(future_upstream_unit_ids) > 0:
            raise AssetUnitBoundaryInvalidError(
                reason="source_has_future_upstream_coverage",
                unit_ids=future_upstream_unit_ids,
            )
        covered_upstream_ids = {
            coverage.upstream_contract_id
            for coverage in context.upstream_coverages
            if coverage.asset_unit_id == source.id
            and coverage.effective_from <= proposal.effective_date
            and (
                coverage.effective_to is None
                or coverage.effective_to >= proposal.effective_date
            )
        }
        active_upstream_ids = tuple(
            sorted(
                active_upstream_contract_ids(
                    contracts=context.upstream_contracts,
                    lifecycle_events=context.lifecycle_events,
                    effective_date=proposal.effective_date,
                )
                & covered_upstream_ids
            )
        )
        upstream_coverage_state = tuple(
            sorted(
                (
                    coverage.upstream_contract_id,
                    coverage.effective_from.isoformat(),
                    (
                        coverage.effective_to.isoformat()
                        if coverage.effective_to is not None
                        else None
                    ),
                )
                for coverage in context.upstream_coverages
                if coverage.asset_unit_id == source.id
                and coverage.upstream_contract_id in active_upstream_ids
            )
        )
        terminal_conflict_ids = terminal_contract_conflict_ids(
            asset_unit_ids={source.id},
            contracts=context.terminal_contracts,
            coverages=context.terminal_coverages,
            lifecycle_events=context.lifecycle_events,
            effective_date=proposal.effective_date,
        )
        if len(terminal_conflict_ids) > 0:
            raise AssetUnitPeriodOverlapError(
                asset_unit_ids=[source.id],
                terminal_contract_ids=list(terminal_conflict_ids),
            )
        proposed_source = self._source_ending_before(source, proposal.effective_date)
        proposed_results = tuple(
            self._result_from_part(
                source=source,
                part=part,
                effective_date=proposal.effective_date,
            )
            for part in proposal.parts
        )
        area_totals = validate_split(
            source=proposed_source,
            children=proposed_results,
            effective_date=proposal.effective_date,
        )
        normalized_proposal = proposal.model_dump(mode="json")
        return _SplitAnalysis(
            context=context,
            source=source,
            proposed_source=proposed_source,
            proposed_results=proposed_results,
            normalized_proposal=normalized_proposal,
            state_fingerprint=self._state_fingerprint(
                source=source,
                normalized_proposal=normalized_proposal,
                scope=scope,
                active_upstream_contract_ids=active_upstream_ids,
                upstream_coverage_state=upstream_coverage_state,
                terminal_contract_conflict_ids=terminal_conflict_ids,
            ),
            area_check={
                "source": area_totals.source.as_dict(),
                "result": area_totals.result.as_dict(),
            },
            active_upstream_contract_ids=active_upstream_ids,
            terminal_contract_conflict_ids=terminal_conflict_ids,
        )

    async def _analyze_merge(
        self,
        db: AsyncSession,
        *,
        proposal: AssetUnitMergeProposal,
        scope: EffectivePartyScope,
        for_update: bool,
    ) -> _MergeAnalysis:
        source_unit_ids = tuple(proposal.source_unit_ids)
        if proposal.effective_date <= self._business_today():
            raise AssetUnitBoundaryInvalidError(
                reason="effective_date_not_future",
                unit_ids=list(source_unit_ids),
            )
        context = await self.repository.load_merge_context(
            db,
            unit_ids=source_unit_ids,
            scope=scope,
            effective_date=proposal.effective_date,
            result_unit_code=proposal.result.unit_code,
            for_update=for_update,
        )
        sources_by_id = {source.id: source for source in context.sources}
        missing_source_ids = [
            unit_id for unit_id in source_unit_ids if unit_id not in sources_by_id
        ]
        if len(missing_source_ids) > 0:
            raise ResourceNotFoundError("AssetUnit", missing_source_ids[0])
        sources = tuple(sources_by_id[unit_id] for unit_id in source_unit_ids)
        if len(context.existing_boundary_source_unit_ids) > 0:
            raise AssetUnitBoundaryInvalidError(
                reason="source_boundary_already_changed",
                unit_ids=list(context.existing_boundary_source_unit_ids),
            )
        if context.result_unit_code_exists:
            raise AssetUnitBoundaryInvalidError(
                reason="result_unit_code_conflict",
                unit_ids=list(source_unit_ids),
            )
        boundary_day = proposal.effective_date - timedelta(days=1)
        ineffective_source_ids = [
            source.id
            for source in sources
            if source.managed_from > boundary_day
            or (source.managed_to is not None and source.managed_to < boundary_day)
        ]
        if len(ineffective_source_ids) > 0:
            raise AssetUnitBoundaryInvalidError(
                reason="source_not_effective_on_boundary",
                unit_ids=ineffective_source_ids,
            )
        self._require_merge_metadata_match(sources)
        future_upstream_unit_ids = sorted(
            {
                coverage.asset_unit_id
                for coverage in context.upstream_coverages
                if coverage.asset_unit_id in source_unit_ids
                and coverage.effective_from > proposal.effective_date
            }
        )
        if len(future_upstream_unit_ids) > 0:
            raise AssetUnitBoundaryInvalidError(
                reason="source_has_future_upstream_coverage",
                unit_ids=future_upstream_unit_ids,
            )

        terminal_conflict_ids = terminal_contract_conflict_ids(
            asset_unit_ids=set(source_unit_ids),
            contracts=context.terminal_contracts,
            coverages=context.terminal_coverages,
            lifecycle_events=context.lifecycle_events,
            effective_date=proposal.effective_date,
        )
        if len(terminal_conflict_ids) > 0:
            raise AssetUnitPeriodOverlapError(
                asset_unit_ids=list(source_unit_ids),
                terminal_contract_ids=list(terminal_conflict_ids),
            )

        proposed_sources = tuple(
            self._source_ending_before(source, proposal.effective_date)
            for source in sources
        )
        proposed_result = self._merge_result_from_sources(
            sources=sources,
            result=proposal.result,
            effective_date=proposal.effective_date,
        )
        area_totals = validate_merge(
            sources=proposed_sources,
            result=proposed_result,
            coverages=context.upstream_coverages,
            upstream_contracts=context.upstream_contracts,
            lifecycle_events=context.lifecycle_events,
            effective_date=proposal.effective_date,
        )
        globally_active_upstream_ids = active_upstream_contract_ids(
            contracts=context.upstream_contracts,
            lifecycle_events=context.lifecycle_events,
            effective_date=proposal.effective_date,
        )
        first_source_id = source_unit_ids[0]
        active_upstream_ids = tuple(
            sorted(
                coverage.upstream_contract_id
                for coverage in context.upstream_coverages
                if coverage.asset_unit_id == first_source_id
                and coverage.upstream_contract_id in globally_active_upstream_ids
                and coverage.effective_from <= proposal.effective_date
                and (
                    coverage.effective_to is None
                    or coverage.effective_to >= proposal.effective_date
                )
            )
        )
        upstream_coverage_state = tuple(
            sorted(
                (
                    coverage.asset_unit_id,
                    coverage.upstream_contract_id,
                    coverage.effective_from.isoformat(),
                    (
                        coverage.effective_to.isoformat()
                        if coverage.effective_to is not None
                        else None
                    ),
                )
                for coverage in context.upstream_coverages
                if coverage.asset_unit_id in source_unit_ids
                and coverage.upstream_contract_id in active_upstream_ids
            )
        )
        for contract_id in active_upstream_ids:
            future_ends = {
                coverage.effective_to
                for coverage in context.upstream_coverages
                if coverage.asset_unit_id in source_unit_ids
                and coverage.upstream_contract_id == contract_id
                and coverage.effective_from <= proposal.effective_date
                and (
                    coverage.effective_to is None
                    or coverage.effective_to >= proposal.effective_date
                )
            }
            if len(future_ends) != 1:
                raise AssetUnitBoundaryInvalidError(
                    reason="merge_upstream_coverage_boundary_mismatch",
                    unit_ids=list(source_unit_ids),
                )

        normalized_proposal = proposal.model_dump(mode="json")
        return _MergeAnalysis(
            context=context,
            sources=sources,
            proposed_sources=proposed_sources,
            proposed_result=proposed_result,
            normalized_proposal=normalized_proposal,
            state_fingerprint=self._merge_state_fingerprint(
                sources=sources,
                normalized_proposal=normalized_proposal,
                scope=scope,
                active_upstream_contract_ids=active_upstream_ids,
                upstream_coverage_state=upstream_coverage_state,
                terminal_contract_conflict_ids=terminal_conflict_ids,
            ),
            area_check={
                "source": area_totals.source.as_dict(),
                "result": area_totals.result.as_dict(),
            },
            active_upstream_contract_ids=active_upstream_ids,
            terminal_contract_conflict_ids=terminal_conflict_ids,
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
    def _source_ending_before(source: AssetUnit, effective_date: date) -> AssetUnit:
        return AssetUnit(  # type: ignore[call-arg]
            id=source.id,
            unit_code=source.unit_code,
            name=source.name,
            project_id=source.project_id,
            owner_party_id=source.owner_party_id,
            address=source.address,
            usage_type=source.usage_type,
            acquisition_mode=source.acquisition_mode,
            is_operating=source.is_operating,
            land_area=source.land_area,
            building_area=source.building_area,
            rentable_area=source.rentable_area,
            managed_from=source.managed_from,
            managed_to=effective_date - timedelta(days=1),
            vacancy_reason=source.vacancy_reason,
            expected_lease_start=source.expected_lease_start,
            predecessor_unit_ids=list(source.predecessor_unit_ids),
            version=source.version,
        )

    @staticmethod
    def _result_from_part(
        *,
        source: AssetUnit,
        part: AssetUnitSplitPartInput,
        effective_date: date,
    ) -> AssetUnit:
        return AssetUnit(  # type: ignore[call-arg]
            id=f"preview:{part.unit_code}",
            unit_code=part.unit_code,
            name=part.name,
            project_id=source.project_id,
            owner_party_id=source.owner_party_id,
            address=source.address,
            usage_type=source.usage_type,
            acquisition_mode=source.acquisition_mode,
            is_operating=source.is_operating,
            land_area=part.land_area,
            building_area=part.building_area,
            rentable_area=part.rentable_area,
            managed_from=effective_date,
            managed_to=None,
            vacancy_reason=source.vacancy_reason,
            expected_lease_start=source.expected_lease_start,
            predecessor_unit_ids=[source.id],
        )

    @staticmethod
    def _require_merge_metadata_match(sources: tuple[AssetUnit, ...]) -> None:
        metadata_signatures = {
            (
                source.project_id,
                source.owner_party_id,
                source.address,
                source.usage_type,
                source.acquisition_mode,
                source.is_operating,
            )
            for source in sources
        }
        if len(metadata_signatures) != 1:
            raise AssetUnitBoundaryInvalidError(
                reason="merge_source_metadata_mismatch",
                unit_ids=[source.id for source in sources],
            )

    @staticmethod
    def _merge_result_from_sources(
        *,
        sources: tuple[AssetUnit, ...],
        result: AssetUnitMergeResultInput,
        effective_date: date,
    ) -> AssetUnit:
        first_source = sources[0]
        vacancy_reasons = {source.vacancy_reason for source in sources}
        expected_lease_starts = {source.expected_lease_start for source in sources}
        return AssetUnit(  # type: ignore[call-arg]
            id=f"preview:{result.unit_code}",
            unit_code=result.unit_code,
            name=result.name,
            project_id=first_source.project_id,
            owner_party_id=first_source.owner_party_id,
            address=first_source.address,
            usage_type=first_source.usage_type,
            acquisition_mode=first_source.acquisition_mode,
            is_operating=first_source.is_operating,
            land_area=sum(
                (source.land_area for source in sources),
                start=Decimal("0"),
            ),
            building_area=sum(
                (source.building_area for source in sources),
                start=Decimal("0"),
            ),
            rentable_area=sum(
                (source.rentable_area for source in sources),
                start=Decimal("0"),
            ),
            managed_from=effective_date,
            managed_to=None,
            vacancy_reason=(
                next(iter(vacancy_reasons)) if len(vacancy_reasons) == 1 else None
            ),
            expected_lease_start=(
                next(iter(expected_lease_starts))
                if len(expected_lease_starts) == 1
                else None
            ),
            predecessor_unit_ids=[source.id for source in sources],
        )

    @staticmethod
    def _part_from_result(result: AssetUnit) -> AssetUnitSplitPartInput:
        return AssetUnitSplitPartInput(
            unit_code=result.unit_code,
            name=result.name,
            land_area=result.land_area,
            building_area=result.building_area,
            rentable_area=result.rentable_area,
        )

    @staticmethod
    def _persistable_result(result: AssetUnit) -> AssetUnit:
        return AssetUnit(  # type: ignore[call-arg]
            id=str(uuid.uuid4()),
            unit_code=result.unit_code,
            name=result.name,
            project_id=result.project_id,
            owner_party_id=result.owner_party_id,
            address=result.address,
            usage_type=result.usage_type,
            acquisition_mode=result.acquisition_mode,
            is_operating=result.is_operating,
            land_area=result.land_area,
            building_area=result.building_area,
            rentable_area=result.rentable_area,
            managed_from=result.managed_from,
            managed_to=result.managed_to,
            vacancy_reason=result.vacancy_reason,
            expected_lease_start=result.expected_lease_start,
            predecessor_unit_ids=list(result.predecessor_unit_ids),
        )

    @classmethod
    def _proposal_from_preview_payload(
        cls,
        payload: dict[str, object],
        *,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> AssetUnitSplitProposal:
        if payload.get("actor_id") != actor_id:
            raise AssetOperationsPreviewStaleError("actor_mismatch")
        if payload.get("action") != "split":
            raise AssetOperationsPreviewStaleError("action_mismatch")
        if payload.get("scope_signature") != cls._scope_signature(scope):
            raise AssetOperationsPreviewStaleError("scope_changed")
        raw_proposal = payload.get("proposal")
        if not isinstance(raw_proposal, dict):
            raise AssetOperationsPreviewStaleError("proposal_missing")
        try:
            proposal = AssetUnitSplitProposal.model_validate(raw_proposal)
        except ValueError as exc:
            raise AssetOperationsPreviewStaleError("proposal_invalid") from exc
        if payload.get("source_unit_ids") != [proposal.source_unit_id]:
            raise AssetOperationsPreviewStaleError("target_mismatch")
        return proposal

    @classmethod
    def _merge_proposal_from_preview_payload(
        cls,
        payload: dict[str, object],
        *,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> AssetUnitMergeProposal:
        if payload.get("actor_id") != actor_id:
            raise AssetOperationsPreviewStaleError("actor_mismatch")
        if payload.get("action") != "merge":
            raise AssetOperationsPreviewStaleError("action_mismatch")
        if payload.get("scope_signature") != cls._scope_signature(scope):
            raise AssetOperationsPreviewStaleError("scope_changed")
        raw_proposal = payload.get("proposal")
        if not isinstance(raw_proposal, dict):
            raise AssetOperationsPreviewStaleError("proposal_missing")
        try:
            proposal = AssetUnitMergeProposal.model_validate(raw_proposal)
        except ValueError as exc:
            raise AssetOperationsPreviewStaleError("proposal_invalid") from exc
        if payload.get("source_unit_ids") != proposal.source_unit_ids:
            raise AssetOperationsPreviewStaleError("target_mismatch")
        return proposal

    @staticmethod
    def _request_fingerprint(
        *,
        actor_id: str,
        idempotency_key: str,
        source_unit_id: str,
        request: AssetUnitSplitCommitRequest,
    ) -> str:
        payload = {
            "actor_id": actor_id,
            "action": "split",
            "idempotency_key": idempotency_key,
            "source_unit_id": source_unit_id,
            "preview_token_hash": hashlib.sha256(
                request.preview_token.encode("utf-8")
            ).hexdigest(),
            "reason": request.reason,
            "expected_version": request.expected_version,
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _merge_request_fingerprint(
        *,
        actor_id: str,
        idempotency_key: str,
        request: AssetUnitMergeCommitRequest,
    ) -> str:
        payload = {
            "actor_id": actor_id,
            "action": "merge",
            "idempotency_key": idempotency_key,
            "preview_token_hash": hashlib.sha256(
                request.preview_token.encode("utf-8")
            ).hexdigest(),
            "reason": request.reason,
            "expected_versions": request.expected_versions,
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _integrity_constraint_name(error: IntegrityError) -> str | None:
        diagnostics = getattr(error.orig, "diag", None)
        constraint_name = getattr(diagnostics, "constraint_name", None)
        return constraint_name if isinstance(constraint_name, str) else None

    def _business_today(self) -> date:
        current = self._clock()
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        return current.astimezone(_BUSINESS_TIMEZONE).date()

    @staticmethod
    def _api_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _database_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    @staticmethod
    def _response_from_existing(
        boundary_change: AssetUnitBoundaryChange,
        *,
        request_fingerprint: str,
    ) -> AssetUnitBoundaryCommitResponse:
        if boundary_change.request_fingerprint != request_fingerprint:
            raise AssetOperationsIdempotencyConflictError()
        return AssetUnitBoundaryCommitResponse.model_validate(
            {**boundary_change.result_data, "idempotent": True}
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

    @classmethod
    def _state_fingerprint(
        cls,
        *,
        source: AssetUnit,
        normalized_proposal: dict[str, object],
        scope: EffectivePartyScope,
        active_upstream_contract_ids: tuple[str, ...],
        upstream_coverage_state: tuple[tuple[str, str, str | None], ...],
        terminal_contract_conflict_ids: tuple[str, ...],
    ) -> str:
        payload = {
            "source": {
                "id": source.id,
                "version": source.version,
                "managed_from": source.managed_from.isoformat(),
                "managed_to": (
                    source.managed_to.isoformat()
                    if source.managed_to is not None
                    else None
                ),
                "land_area": str(source.land_area),
                "building_area": str(source.building_area),
                "rentable_area": str(source.rentable_area),
            },
            "proposal": normalized_proposal,
            "scope": cls._scope_signature(scope),
            "active_upstream_contract_ids": list(active_upstream_contract_ids),
            "upstream_coverage_state": list(upstream_coverage_state),
            "terminal_contract_conflict_ids": list(terminal_contract_conflict_ids),
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def _merge_state_fingerprint(
        cls,
        *,
        sources: tuple[AssetUnit, ...],
        normalized_proposal: dict[str, object],
        scope: EffectivePartyScope,
        active_upstream_contract_ids: tuple[str, ...],
        upstream_coverage_state: tuple[tuple[str, str, str, str | None], ...],
        terminal_contract_conflict_ids: tuple[str, ...],
    ) -> str:
        payload = {
            "sources": [
                {
                    "id": source.id,
                    "version": source.version,
                    "managed_from": source.managed_from.isoformat(),
                    "managed_to": (
                        source.managed_to.isoformat()
                        if source.managed_to is not None
                        else None
                    ),
                    "project_id": source.project_id,
                    "owner_party_id": source.owner_party_id,
                    "address": source.address,
                    "usage_type": source.usage_type,
                    "acquisition_mode": source.acquisition_mode,
                    "is_operating": source.is_operating,
                    "land_area": str(source.land_area),
                    "building_area": str(source.building_area),
                    "rentable_area": str(source.rentable_area),
                }
                for source in sources
            ],
            "proposal": normalized_proposal,
            "scope": cls._scope_signature(scope),
            "active_upstream_contract_ids": list(active_upstream_contract_ids),
            "upstream_coverage_state": list(upstream_coverage_state),
            "terminal_contract_conflict_ids": list(terminal_contract_conflict_ids),
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


asset_unit_boundary_command_service = AssetUnitBoundaryCommandService()


__all__ = [
    "AssetUnitBoundaryCommandService",
    "AssetUnitBoundaryPreviewStore",
    "AssetUnitBoundaryPreviewStoreProtocol",
    "AssetUnitBoundaryRepositoryProtocol",
    "AssetUnitMergeContext",
    "AssetUnitSplitContext",
    "asset_unit_boundary_command_service",
]
