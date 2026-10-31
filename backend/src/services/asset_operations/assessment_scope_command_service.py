"""Assessment-scope draft, preview and version-commit commands."""

from __future__ import annotations

import calendar
import hashlib
import json
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.cache_manager import cache_manager
from ...core.exception_handler import (
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from ...crud.assessment_scope import (
    AssessmentScopeRepository,
    assessment_scope_repository,
)
from ...crud.asset_contract import asset_contract_repository
from ...crud.business_change_event import business_change_repository
from ...crud.rent_commands import rent_command_repository
from ...models.assessment_scope import (
    AssessmentScopeItem,
    AssessmentScopeVersion,
    build_unit_snapshot,
)
from ...models.asset_contract import AssetContractWriteReceipt
from ...models.asset_unit import AssetUnit
from ...models.business_change_event import BusinessChangeEvent
from ...schemas.asset_operations import (
    AssessmentScopeCommitRequest,
    AssessmentScopeCommitResponse,
    AssessmentScopeDraftResponse,
    AssessmentScopeItemResponse,
    AssessmentScopeOverviewResponse,
    AssessmentScopePendingItem,
    AssessmentScopePreviewResponse,
    AssessmentScopeVersionSummary,
    CreateAssessmentScopeDraftRequest,
    OccupancySnapshot,
    UpdateAssessmentScopeDraftRequest,
)
from ..party_scope_resolver import EffectivePartyScope
from .assessment_scope_rules import (
    PriorScopeDecision,
    ScopeUnitFact,
    affected_periods,
    derive_scope_defaults,
)
from .errors import (
    AssessmentScopeDraftExistsError,
    AssessmentScopeDraftStateError,
    AssessmentScopeOperatorForbiddenError,
    AssessmentScopePeriodInvalidError,
    AssetOperationsIdempotencyConflictError,
    AssetOperationsPreviewStaleError,
    AssetOperationsVersionConflictError,
)
from .occupancy_report_rules import OccupancyUnitFact, project_occupancy
from .rent_command_support import require_scope

_BUSINESS_TIMEZONE = ZoneInfo("Asia/Shanghai")
_PREVIEW_NAMESPACE = "assessment_scope_preview"
_PREVIEW_TTL = timedelta(minutes=10)


class AssessmentScopePreviewStoreProtocol(Protocol):
    def issue(self, payload: dict[str, object]) -> tuple[str, datetime]: ...

    def peek(self, raw_token: str) -> dict[str, object] | None: ...

    def delete(self, raw_token: str) -> bool: ...


class AssessmentScopePreviewStore:
    """Short-lived opaque tokens deleted only after a successful commit."""

    NAMESPACE = _PREVIEW_NAMESPACE
    TTL = _PREVIEW_TTL

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
                "无法保存考核范围预览",
                service_name=_PREVIEW_NAMESPACE,
            )
        return token, expires_at

    def peek(self, raw_token: str) -> dict[str, object] | None:
        token = str(raw_token).strip()
        if token == "":  # nosec B105 - empty-token guard
            return None
        payload = cache_manager.get(
            self._token_hash(token), namespace=self.NAMESPACE
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
            self._token_hash(token), namespace=self.NAMESPACE
        )

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _DraftItemValues:
    included: bool
    exclusion_reason: str | None


@dataclass(frozen=True)
class _ScopeView:
    """Active version row plus its items and freshly derived pending units."""

    version: AssessmentScopeVersion | None
    items: tuple[AssessmentScopeItem, ...]
    candidates: tuple[AssetUnit, ...]
    pending: tuple[tuple[str, str], ...]


class AssessmentScopeCommandService:
    """Own operator authorization, derivation, locking and idempotent commits."""

    def __init__(
        self,
        *,
        repository: AssessmentScopeRepository | None = None,
        preview_store: AssessmentScopePreviewStoreProtocol | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository or assessment_scope_repository
        self._clock = clock or (lambda: datetime.now(UTC).replace(tzinfo=None))
        self.preview_store = preview_store or AssessmentScopePreviewStore(
            clock=self._clock
        )

    async def get_overview(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        year: int,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> AssessmentScopeOverviewResponse:
        require_scope(scope, actor_id)
        self._require_operator_access(scope, operator_party_id=operator_party_id)
        await self._require_party(db, operator_party_id)
        view = await self._load_view(
            db,
            operator_party_id=operator_party_id,
            year=year,
        )
        occupancy = await self._occupancy_snapshot(
            db,
            period=self._current_period(),
            items=view.items,
            units=view.candidates,
        )
        return AssessmentScopeOverviewResponse(
            operator_party_id=operator_party_id,
            year=year,
            scope=self._summary(view.version),
            items=self._item_responses(view.items),
            pending=self._pending_responses(view),
            occupancy=occupancy,
        )

    async def get_draft(
        self,
        db: AsyncSession,
        *,
        draft_id: str,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> AssessmentScopeDraftResponse:
        require_scope(scope, actor_id)
        draft = await self._require_draft(db, draft_id=draft_id)
        self._require_operator_access(
            scope, operator_party_id=draft.operator_party_id
        )
        if draft.status != "draft":
            raise AssessmentScopeDraftStateError(draft_status=draft.status)
        draft_items = tuple(
            await self.repository.list_items(db, version_id=draft.id)
        )
        candidates = await self.repository.list_managed_units(
            db,
            operator_party_id=draft.operator_party_id,
            as_of=self._business_today(),
            year=draft.year,
        )
        view = self._view_for(draft, draft_items, candidates)
        return self._draft_response(draft, view)

    async def create_draft(
        self,
        db: AsyncSession,
        *,
        year: int,
        request: CreateAssessmentScopeDraftRequest,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> AssessmentScopeDraftResponse:
        """Derive one editable draft from explicit facts and a prior version."""
        require_scope(scope, actor_id)
        operator_party_id = request.operator_party_id
        self._require_operator_access(scope, operator_party_id=operator_party_id)
        await self._require_party(db, operator_party_id)

        await self.repository.lock_serialization(
            db, operator_party_id=operator_party_id, year=year
        )
        existing = await self.repository.get_draft_version(
            db, operator_party_id=operator_party_id, year=year
        )
        if existing is not None:
            raise AssessmentScopeDraftExistsError(draft_id=existing.id)

        source = await self._copy_source(
            db,
            operator_party_id=operator_party_id,
            year=year,
            source=request.source,
        )
        candidates = await self.repository.list_managed_units(
            db,
            operator_party_id=operator_party_id,
            as_of=self._business_today(),
            year=year,
        )
        prior_items: tuple[AssessmentScopeItem, ...] = ()
        if source is not None:
            prior_items = tuple(
                await self.repository.list_items(db, version_id=source.id)
            )
        prior_decisions = tuple(
            PriorScopeDecision(
                unit_id=item.asset_unit_id,
                included=item.included,
                exclusion_reason=item.exclusion_reason,
            )
            for item in prior_items
        )
        derivation = derive_scope_defaults(
            year,
            self._scope_facts(candidates),
            prior_decisions,
        )
        snapshot_by_unit = {
            unit.id: build_unit_snapshot(unit) for unit in candidates
        }
        occurred_at = self._clock()
        draft = AssessmentScopeVersion(  # type: ignore[call-arg]
            id=str(uuid.uuid4()),
            operator_party_id=operator_party_id,
            year=year,
            version_number=None,
            status="draft",
            effective_from_period=self._current_period(),
            based_on_version_id=source.id if source is not None else None,
            created_by=actor_id,
            created_at=self._database_datetime(occurred_at),
        )
        db.add(draft)
        await db.flush()
        items = tuple(
            AssessmentScopeItem(  # type: ignore[call-arg]
                scope_version_id=draft.id,
                asset_unit_id=decision.unit_id,
                included=decision.included,
                exclusion_reason=decision.exclusion_reason,
                unit_snapshot=snapshot_by_unit[decision.unit_id],
            )
            for decision in derivation.decisions
        )
        await self.repository.replace_items(db, version_id=draft.id, items=items)
        await db.commit()

        view = _ScopeView(
            version=draft,
            items=items,
            candidates=tuple(candidates),
            pending=tuple(
                (pending.unit_id, pending.reason.value)
                for pending in derivation.pending
            ),
        )
        return self._draft_response(draft, view)

    async def update_draft(
        self,
        db: AsyncSession,
        *,
        draft_id: str,
        request: UpdateAssessmentScopeDraftRequest,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> AssessmentScopeDraftResponse:
        """Apply explicit include/exclude decisions to one editable draft."""
        require_scope(scope, actor_id)
        draft = await self._require_draft(db, draft_id=draft_id)
        self._require_operator_access(
            scope, operator_party_id=draft.operator_party_id
        )
        if draft.status != "draft":
            raise AssessmentScopeDraftStateError(draft_status=draft.status)
        # Serialize concurrent edits of the same draft: without the advisory
        # lock a racing writer surfaces as StaleDataError (500) instead of a
        # proper version conflict.
        await self.repository.lock_serialization(
            db,
            operator_party_id=draft.operator_party_id,
            year=draft.year,
        )
        locked_draft: AssessmentScopeVersion | None = (
            await self.repository.get_version(
                db, version_id=draft_id, for_update=True
            )
        )
        if locked_draft is None:
            raise ResourceNotFoundError("AssessmentScopeVersion", draft_id)
        draft = locked_draft
        if draft.status != "draft":
            raise AssessmentScopeDraftStateError(draft_status=draft.status)
        self._check_version(
            draft_id, actual=draft.version, expected=request.expected_version
        )

        draft_items = tuple(
            await self.repository.list_items(db, version_id=draft.id)
        )
        candidates = await self.repository.list_managed_units(
            db,
            operator_party_id=draft.operator_party_id,
            as_of=self._business_today(),
            year=draft.year,
        )
        current_view = self._view_for(draft, draft_items, candidates)
        known_units = {item.asset_unit_id for item in draft_items} | {
            unit_id for unit_id, _ in current_view.pending
        }
        requested_units = {
            decision.asset_unit_id for decision in request.decisions
        }
        unknown = sorted(requested_units - known_units)
        if unknown:
            raise ResourceNotFoundError("AssetUnit", unknown[0])

        snapshot_by_unit = {
            unit.id: build_unit_snapshot(unit) for unit in candidates
        }
        persisted_snapshot = {
            item.asset_unit_id: item.unit_snapshot for item in draft_items
        }
        merged: dict[str, _DraftItemValues] = {
            item.asset_unit_id: _DraftItemValues(
                included=item.included,
                exclusion_reason=item.exclusion_reason,
            )
            for item in draft_items
        }
        for decision in request.decisions:
            merged[decision.asset_unit_id] = _DraftItemValues(
                included=decision.included,
                exclusion_reason=(
                    decision.exclusion_reason.strip()
                    if decision.exclusion_reason is not None
                    else None
                ),
            )
        items = tuple(
            AssessmentScopeItem(  # type: ignore[call-arg]
                scope_version_id=draft.id,
                asset_unit_id=unit_id,
                included=values.included,
                exclusion_reason=values.exclusion_reason,
                unit_snapshot=snapshot_by_unit.get(
                    unit_id, persisted_snapshot.get(unit_id, {})
                ),
            )
            for unit_id, values in sorted(merged.items())
        )
        draft.version = draft.version + 1
        await self.repository.replace_items(db, version_id=draft.id, items=items)
        await db.commit()

        view = _ScopeView(
            version=draft,
            items=items,
            candidates=tuple(candidates),
            pending=tuple(
                (unit_id, reason)
                for unit_id, reason in current_view.pending
                if unit_id not in requested_units
            ),
        )
        return self._draft_response(draft, view)

    async def preview(
        self,
        db: AsyncSession,
        *,
        draft_id: str,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> AssessmentScopePreviewResponse:
        """Compare the draft with the active version and bind a commit token."""
        require_scope(scope, actor_id)
        draft = await self._require_draft(db, draft_id=draft_id)
        self._require_operator_access(
            scope, operator_party_id=draft.operator_party_id
        )
        if draft.status != "draft":
            raise AssessmentScopeDraftStateError(draft_status=draft.status)
        draft_items = tuple(
            await self.repository.list_items(db, version_id=draft.id)
        )
        candidates = await self.repository.list_managed_units(
            db,
            operator_party_id=draft.operator_party_id,
            as_of=self._business_today(),
            year=draft.year,
        )
        active = await self.repository.get_active_version(
            db,
            operator_party_id=draft.operator_party_id,
            year=draft.year,
        )
        current_items: tuple[AssessmentScopeItem, ...] = ()
        if active is not None:
            current_items = tuple(
                await self.repository.list_items(db, version_id=active.id)
            )
        period = self._current_period()
        occupancy_current = await self._occupancy_snapshot(
            db, period=period, items=current_items, units=candidates
        )
        occupancy_new = await self._occupancy_snapshot(
            db, period=period, items=draft_items, units=candidates
        )
        decided_ids = {item.asset_unit_id for item in draft_items}
        candidate_ids = {unit.id for unit in candidates}
        pending_count = len(candidate_ids - decided_ids)
        state_fingerprint = self._state_fingerprint(
            draft=draft,
            draft_items=draft_items,
            active=active,
            candidates=tuple(candidates),
        )
        token, expires_at = self.preview_store.issue(
            {
                "actor_id": actor_id,
                "action": "commit_assessment_scope",
                "draft_id": draft.id,
                "operator_party_id": draft.operator_party_id,
                "year": draft.year,
                "scope_signature": self._scope_signature(scope),
                "versions": {draft.id: draft.version},
                "state_fingerprint": state_fingerprint,
            }
        )
        return AssessmentScopePreviewResponse(
            preview_token=token,
            expires_at=self._api_datetime(expires_at),
            current_version_number=(
                active.version_number if active is not None else None
            ),
            current_included_count=sum(
                1 for item in current_items if item.included
            ),
            current_excluded_count=sum(
                1 for item in current_items if not item.included
            ),
            new_included_count=sum(1 for item in draft_items if item.included),
            new_excluded_count=sum(
                1 for item in draft_items if not item.included
            ),
            pending_count=pending_count,
            occupancy_period=period,
            occupancy_rate_current=(
                occupancy_current.occupancy_rate
                if occupancy_current is not None
                else None
            ),
            occupancy_rate_new=(
                occupancy_new.occupancy_rate if occupancy_new is not None else None
            ),
            affected_periods=list(
                affected_periods(draft.effective_from_period, draft.year)
            ),
        )

    async def commit(
        self,
        db: AsyncSession,
        *,
        draft_id: str,
        request: AssessmentScopeCommitRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> AssessmentScopeCommitResponse:
        """Activate one draft atomically and replay the first result on retry."""
        require_scope(scope, actor_id)
        request_fingerprint = self._request_fingerprint(
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            draft_id=draft_id,
            request=request,
        )
        existing = await asset_contract_repository.get_write_receipt(
            db, actor_id=actor_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            return self._replay(existing, request_fingerprint=request_fingerprint)

        draft = await self._require_draft(db, draft_id=draft_id)
        self._require_operator_access(
            scope, operator_party_id=draft.operator_party_id
        )

        preview_payload = self.preview_store.peek(request.preview_token)
        if preview_payload is None:
            raise AssetOperationsPreviewStaleError("missing_or_expired")
        if preview_payload.get("actor_id") != actor_id:
            raise AssetOperationsPreviewStaleError("actor_mismatch")
        if preview_payload.get("action") != "commit_assessment_scope":
            raise AssetOperationsPreviewStaleError("action_mismatch")
        if preview_payload.get("draft_id") != draft.id:
            raise AssetOperationsPreviewStaleError("target_mismatch")
        if (
            preview_payload.get("scope_signature") != self._scope_signature(scope)
        ):
            raise AssetOperationsPreviewStaleError("scope_changed")
        token_versions = preview_payload.get("versions")
        if not isinstance(token_versions, dict):
            raise AssetOperationsPreviewStaleError("versions_missing")
        if token_versions.get(draft.id) != request.expected_version:
            bound_version = token_versions.get(draft.id)
            raise AssetOperationsVersionConflictError(
                unit_id=draft.id,
                expected_version=request.expected_version,
                actual_version=(
                    bound_version if isinstance(bound_version, int) else -1
                ),
            )

        await self.repository.lock_serialization(
            db,
            operator_party_id=draft.operator_party_id,
            year=draft.year,
        )
        locked: AssessmentScopeVersion | None = await self.repository.get_version(
            db, version_id=draft_id, for_update=True
        )
        if locked is None:
            raise ResourceNotFoundError("AssessmentScopeVersion", draft_id)
        draft = locked
        self._require_operator_access(
            scope, operator_party_id=draft.operator_party_id
        )
        if draft.status != "draft":
            raise AssetOperationsPreviewStaleError("state_changed")
        if draft.version != request.expected_version:
            raise AssetOperationsVersionConflictError(
                unit_id=draft.id,
                expected_version=request.expected_version,
                actual_version=draft.version,
            )
        if (
            request.effective_from_period[:4] != str(draft.year)
            or not 1 <= int(request.effective_from_period[5:7]) <= 12
        ):
            raise AssessmentScopePeriodInvalidError(
                effective_from_period=request.effective_from_period,
                year=draft.year,
            )

        draft_items = tuple(
            await self.repository.list_items(db, version_id=draft.id)
        )
        active = await self.repository.get_active_version(
            db,
            operator_party_id=draft.operator_party_id,
            year=draft.year,
        )
        candidates = await self.repository.list_managed_units(
            db,
            operator_party_id=draft.operator_party_id,
            as_of=self._business_today(),
            year=draft.year,
        )
        if preview_payload.get("state_fingerprint") != self._state_fingerprint(
            draft=draft,
            draft_items=draft_items,
            active=active,
            candidates=tuple(candidates),
        ):
            raise AssetOperationsPreviewStaleError("state_changed")

        existing = await asset_contract_repository.get_write_receipt(
            db, actor_id=actor_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            return self._replay(existing, request_fingerprint=request_fingerprint)

        version_number = await self.repository.next_version_number(
            db, operator_party_id=draft.operator_party_id, year=draft.year
        )
        superseded_version_id = active.id if active is not None else None
        if active is not None:
            # Flush the demotion first: SQLAlchemy orders same-table updates
            # by primary key, so flipping this row after the draft would
            # briefly leave two active versions and violate the partial
            # unique index.
            active.status = "superseded"
            await db.flush()
        snapshot_by_unit = {
            unit.id: build_unit_snapshot(unit) for unit in candidates
        }
        for item in draft_items:
            refreshed = snapshot_by_unit.get(item.asset_unit_id)
            if refreshed is not None:
                item.unit_snapshot = refreshed
        occurred_at = self._clock()
        draft.status = "active"
        draft.version_number = version_number
        draft.effective_from_period = request.effective_from_period
        draft.activated_by = actor_id
        draft.activated_at = self._database_datetime(occurred_at)
        draft.version = draft.version + 1
        response = AssessmentScopeCommitResponse(
            version_id=draft.id,
            version_number=version_number,
            effective_from_period=request.effective_from_period,
            activated_at=self._api_datetime(occurred_at),
            idempotent=False,
        )
        await business_change_repository.add(
            db,
            event=BusinessChangeEvent(  # type: ignore[call-arg]
                id=str(uuid.uuid4()),
                target_type="assessment_scope_version",
                target_id=draft.id,
                action="activate",
                actor_id=actor_id,
                before={
                    "operator_party_id": draft.operator_party_id,
                    "year": draft.year,
                    "superseded_version_id": superseded_version_id,
                },
                after={
                    "version_number": version_number,
                    "effective_from_period": request.effective_from_period,
                    "included_count": sum(
                        1 for item in draft_items if item.included
                    ),
                    "excluded_count": sum(
                        1 for item in draft_items if not item.included
                    ),
                },
                reason=None,
                correlation_id=draft_id,
                occurred_at=occurred_at,
            ),
        )
        await rent_command_repository.add_receipt(
            db,
            receipt=AssetContractWriteReceipt(  # type: ignore[call-arg]
                id=str(uuid.uuid4()),
                actor_id=actor_id,
                command_kind="commit_assessment_scope",
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                result_data=response.model_dump(mode="json"),
                created_at=self._database_datetime(occurred_at),
            ),
        )
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            concurrent = await asset_contract_repository.get_write_receipt(
                db, actor_id=actor_id, idempotency_key=idempotency_key
            )
            if concurrent is not None:
                replay = self._replay(
                    concurrent, request_fingerprint=request_fingerprint
                )
                self.preview_store.delete(request.preview_token)
                return replay
            raise AssetOperationsPreviewStaleError(
                "concurrent_modification"
            ) from exc
        self.preview_store.delete(request.preview_token)
        return response

    async def _load_view(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        year: int,
    ) -> _ScopeView:
        active = await self.repository.get_active_version(
            db, operator_party_id=operator_party_id, year=year
        )
        items: tuple[AssessmentScopeItem, ...] = ()
        if active is not None:
            items = tuple(await self.repository.list_items(db, version_id=active.id))
        candidates = await self.repository.list_managed_units(
            db,
            operator_party_id=operator_party_id,
            as_of=self._business_today(),
            year=year,
        )
        return self._view_for(active, items, candidates)

    @staticmethod
    def _view_for(
        version: AssessmentScopeVersion | None,
        items: tuple[AssessmentScopeItem, ...],
        candidates: list[AssetUnit] | tuple[AssetUnit, ...],
    ) -> _ScopeView:
        """Pending units are current candidates without any persisted decision."""
        return view_for(version, items, candidates)

    async def _copy_source(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        year: int,
        source: str,
    ) -> AssessmentScopeVersion | None:
        if source == "current":
            return await self.repository.get_active_version(
                db, operator_party_id=operator_party_id, year=year
            )
        return await self.repository.get_active_version(
            db, operator_party_id=operator_party_id, year=year - 1
        )

    async def _require_draft(
        self, db: AsyncSession, *, draft_id: str
    ) -> AssessmentScopeVersion:
        version = await self.repository.get_version(db, version_id=draft_id)
        if version is None:
            raise ResourceNotFoundError("AssessmentScopeVersion", draft_id)
        return version

    async def _require_party(
        self, db: AsyncSession, operator_party_id: str
    ) -> None:
        if not await self.repository.party_exists(db, party_id=operator_party_id):
            raise ResourceNotFoundError("Party", operator_party_id)

    async def _occupancy_snapshot(
        self,
        db: AsyncSession,
        *,
        period: str,
        items: tuple[AssessmentScopeItem, ...],
        units: tuple[AssetUnit, ...] | list[AssetUnit],
    ) -> OccupancySnapshot | None:
        """Derive the period occupancy for included units from live rental facts.

        Both denominator and rented numerator follow the operator-party unit
        set; the caller's data scope must not shrink either side of the rate.
        """
        included_ids = {item.asset_unit_id for item in items if item.included}
        units_by_id = {unit.id: unit for unit in units}
        facts = [units_by_id[unit_id] for unit_id in included_ids if unit_id in units_by_id]
        if len(facts) == 0:
            return None
        rented_ids = await asset_contract_repository.list_rented_unit_ids_by_units(
            db,
            unit_ids={unit.id for unit in facts},
            as_of=self._period_end(period),
        )
        projection = project_occupancy(
            period,
            (
                OccupancyUnitFact(
                    unit_id=unit.id,
                    managed_from=unit.managed_from,
                    managed_to=unit.managed_to,
                    is_operating=unit.is_operating,
                    included=True,
                    rented=unit.id in rented_ids,
                    land_area=unit.land_area,
                    building_area=unit.building_area,
                    rentable_area=unit.rentable_area,
                )
                for unit in facts
            ),
        )
        return OccupancySnapshot(
            period=period,
            unit_count=projection.unit_count,
            rented_unit_count=projection.rented_unit_count,
            occupancy_rate=projection.occupancy_rate,
            rentable_area=projection.rentable_area,
            rented_area=projection.rented_area,
        )

    @staticmethod
    def _scope_facts(
        units: list[AssetUnit] | tuple[AssetUnit, ...]
    ) -> tuple[ScopeUnitFact, ...]:
        return tuple(
            ScopeUnitFact(
                unit_id=unit.id,
                managed_from=unit.managed_from,
                managed_to=unit.managed_to,
                is_operating=unit.is_operating,
                predecessor_unit_ids=tuple(unit.predecessor_unit_ids),
            )
            for unit in units
        )

    @staticmethod
    def _item_responses(
        items: tuple[AssessmentScopeItem, ...]
    ) -> list[AssessmentScopeItemResponse]:
        return [
            AssessmentScopeItemResponse(
                asset_unit_id=item.asset_unit_id,
                included=item.included,
                exclusion_reason=item.exclusion_reason,
                unit_snapshot=item.unit_snapshot,  # type: ignore[arg-type]
            )
            for item in sorted(items, key=lambda row: row.asset_unit_id)
        ]

    def _pending_responses(
        self, view: _ScopeView
    ) -> list[AssessmentScopePendingItem]:
        units_by_id = {unit.id: unit for unit in view.candidates}
        result: list[AssessmentScopePendingItem] = []
        for unit_id, reason in sorted(view.pending):
            unit = units_by_id.get(unit_id)
            if unit is None:
                continue
            result.append(
                AssessmentScopePendingItem(
                    asset_unit_id=unit_id,
                    reason=reason,  # type: ignore[arg-type]
                    unit_snapshot=build_unit_snapshot(unit),  # type: ignore[arg-type]
                )
            )
        return result

    def _draft_response(
        self, draft: AssessmentScopeVersion, view: _ScopeView
    ) -> AssessmentScopeDraftResponse:
        return AssessmentScopeDraftResponse(
            draft_id=draft.id,
            operator_party_id=draft.operator_party_id,
            year=draft.year,
            status="draft",
            effective_from_period=draft.effective_from_period,
            version=draft.version,
            items=self._item_responses(view.items),
            pending=self._pending_responses(view),
        )

    @staticmethod
    def _summary(
        version: AssessmentScopeVersion | None
    ) -> AssessmentScopeVersionSummary | None:
        return summarize_version(version)

    @staticmethod
    def _check_version(target_id: str, *, actual: int, expected: int) -> None:
        if actual != expected:
            raise AssetOperationsVersionConflictError(
                unit_id=target_id,
                expected_version=expected,
                actual_version=actual,
            )

    @staticmethod
    def _require_operator_access(
        scope: EffectivePartyScope, *, operator_party_id: str
    ) -> None:
        require_operator_access(scope, operator_party_id=operator_party_id)

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
    def _state_fingerprint(
        *,
        draft: AssessmentScopeVersion,
        draft_items: tuple[AssessmentScopeItem, ...],
        active: AssessmentScopeVersion | None,
        candidates: tuple[AssetUnit, ...],
    ) -> str:
        payload = {
            "draft": {
                "id": draft.id,
                "version": draft.version,
                "status": draft.status,
                "effective_from_period": draft.effective_from_period,
            },
            "draft_items": [
                {
                    "asset_unit_id": item.asset_unit_id,
                    "included": item.included,
                    "exclusion_reason": item.exclusion_reason,
                }
                for item in sorted(draft_items, key=lambda row: row.asset_unit_id)
            ],
            "active": (
                {
                    "id": active.id,
                    "version_number": active.version_number,
                    "version": active.version,
                }
                if active is not None
                else None
            ),
            "candidates": [
                {
                    "id": unit.id,
                    "version": unit.version,
                    "managed_to": (
                        unit.managed_to.isoformat()
                        if unit.managed_to is not None
                        else None
                    ),
                    "is_operating": unit.is_operating,
                }
                for unit in sorted(candidates, key=lambda row: row.id)
            ],
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _request_fingerprint(
        *,
        actor_id: str,
        idempotency_key: str,
        draft_id: str,
        request: AssessmentScopeCommitRequest,
    ) -> str:
        payload = {
            "actor_id": actor_id,
            "action": "commit_assessment_scope",
            "idempotency_key": idempotency_key,
            "draft_id": draft_id,
            "preview_token_hash": hashlib.sha256(
                request.preview_token.encode("utf-8")
            ).hexdigest(),
            "expected_version": request.expected_version,
            "effective_from_period": request.effective_from_period,
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _replay(
        receipt: AssetContractWriteReceipt, *, request_fingerprint: str
    ) -> AssessmentScopeCommitResponse:
        if receipt.request_fingerprint != request_fingerprint:
            raise AssetOperationsIdempotencyConflictError()
        return AssessmentScopeCommitResponse.model_validate(
            {**receipt.result_data, "idempotent": True}
        )

    def _business_today(self) -> date:
        current = self._clock()
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        return current.astimezone(_BUSINESS_TIMEZONE).date()

    def _current_period(self) -> str:
        today = self._business_today()
        return f"{today.year:04d}-{today.month:02d}"

    @staticmethod
    def _period_end(period: str) -> date:
        year, month = int(period[:4]), int(period[5:7])
        return date(year, month, calendar.monthrange(year, month)[1])

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


def require_operator_access(
    scope: EffectivePartyScope, *, operator_party_id: str
) -> None:
    """A reporting unit is a manager identity, never an owner-side filter."""
    if scope.scope_mode == "unrestricted":
        return
    if scope.scope_mode in {"manager", "all"} and (
        operator_party_id in scope.manager_party_ids
    ):
        return
    raise AssessmentScopeOperatorForbiddenError(
        operator_party_id=operator_party_id
    )


def summarize_version(
    version: AssessmentScopeVersion | None,
) -> AssessmentScopeVersionSummary | None:
    if version is None:
        return None
    return AssessmentScopeVersionSummary(
        version_id=version.id,
        version_number=version.version_number,
        status=version.status,  # type: ignore[arg-type]
        effective_from_period=version.effective_from_period,
        activated_at=(
            version.activated_at.replace(tzinfo=UTC)
            if version.activated_at is not None
            else None
        ),
        version=version.version,
    )


def view_for(
    version: AssessmentScopeVersion | None,
    items: tuple[AssessmentScopeItem, ...],
    candidates: list[AssetUnit] | tuple[AssetUnit, ...],
) -> _ScopeView:
    """Pending units are current candidates without any persisted decision."""
    decided = {item.asset_unit_id for item in items}
    return _ScopeView(
        version=version,
        items=items,
        candidates=tuple(candidates),
        pending=tuple(
            (
                unit.id,
                "boundary_uncertain"
                if unit.predecessor_unit_ids
                else "new_takeover",
            )
            for unit in sorted(candidates, key=lambda row: row.id)
            if unit.id not in decided
        ),
    )


assessment_scope_command_service = AssessmentScopeCommandService()


__all__ = [
    "AssessmentScopeCommandService",
    "AssessmentScopePreviewStore",
    "AssessmentScopePreviewStoreProtocol",
    "assessment_scope_command_service",
    "require_operator_access",
    "summarize_version",
    "view_for",
]
