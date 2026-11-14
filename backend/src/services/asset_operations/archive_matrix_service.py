"""Pure archive requirements projected from authorized business facts."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import BaseBusinessError
from ...crud.archive_matrix import (
    ArchiveMatrixFacts,
    ArchiveMatrixRepository,
    archive_matrix_repository,
)
from ...models.asset_contract import TerminalContract, UpstreamContract
from ...schemas.archive_matrix import (
    ArchiveCategory,
    ArchiveCompletion,
    ArchiveMatrix,
    ArchiveMatrixRow,
    ArchiveMissingItem,
)
from ..party_scope_resolver import EffectivePartyScope
from .contract_projections import (
    derive_terminal_contract_status,
    derive_upstream_contract_status,
)
from .rent_command_support import require_scope
from .rent_ledger_query_service import business_today

LABELS = {
    "property_certificate": "产权证",
    "upstream_contract": "上游合同",
    "terminal_contract": "终端合同",
    "supplement": "补充协议",
    "handover": "交接书",
    "management_fee_statement": "对账单",
}


@dataclass(frozen=True)
class Requirement:
    document_type: str
    target_type: str
    target_id: str
    label: str
    unit_ids: frozenset[str]
    existing: bool
    href: str


_SHANGHAI = ZoneInfo("Asia/Shanghai")


def _as_of_end(as_of: date) -> datetime:
    """Exclusive upper bound (next-day midnight) of the as-of business day, naive UTC."""
    return (
        datetime.combine(as_of + timedelta(days=1), time(), _SHANGHAI)
        .astimezone(UTC)
        .replace(tzinfo=None)
    )


def _bound_by(value: datetime | None, end: datetime) -> bool:
    """True when a timestamp falls strictly before the as-of day's end."""
    if value is None:
        return False
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value < end


def project_requirements(
    facts: ArchiveMatrixFacts, as_of: date
) -> tuple[Requirement, ...]:
    end = _as_of_end(as_of)
    # Only files and versions bound by the as-of day count; later replacements
    # do not hide what was current at that moment.
    files = {
        r.id: r
        for r in facts.attachments
        if _bound_by(getattr(r, "created_at", None), end)
    }
    documents = tuple(
        d for d in facts.documents if _bound_by(getattr(d, "uploaded_at", None), end)
    )
    replaced = {
        r.replaces_document_id for r in documents if r.replaces_document_id is not None
    }

    def archived(
        kind: str, target: str, identity: str, owner: str, owner_id: str
    ) -> bool:
        return any(
            r.document_type == kind
            and r.target_type == target
            and r.target_id == identity
            and r.id not in replaced
            and (file := files.get(r.attachment_id)) is not None
            and file.owner_type == owner
            and file.owner_id == owner_id
            for r in documents
        )

    def linked_file(identity: str | None, owner: str, owner_id: str) -> bool:
        file = files.get(identity) if identity is not None else None
        return (
            file is not None and file.owner_type == owner and file.owner_id == owner_id
        )

    def covered(identity: str, kind: str, current: bool) -> frozenset[str]:
        if kind == "upstream":
            pairs = (
                (
                    r.upstream_contract_id,
                    r.asset_unit_id,
                    r.effective_from,
                    r.effective_to,
                )
                for r in facts.upstream_links
            )
        else:
            pairs = (
                (
                    r.terminal_contract_id,
                    r.asset_unit_id,
                    r.effective_from,
                    r.effective_to,
                )
                for r in facts.terminal_links
            )
        return frozenset(
            unit
            for cid, unit, start, valid_to in pairs
            if cid == identity
            and (
                not current
                or start <= as_of
                and (valid_to is None or valid_to >= as_of)
            )
        )

    result = []
    active_upstream_ids: set[str] = set()
    for cert in facts.certificates:
        ids = frozenset(
            r.asset_unit_id
            for r in facts.certificate_links
            if r.certificate_id == cert.id
        )
        if ids:
            result.append(
                Requirement(
                    "property_certificate",
                    "property_certificate",
                    cert.id,
                    cert.certificate_number,
                    ids,
                    archived(
                        "property_certificate",
                        "property_certificate",
                        cert.id,
                        "property_certificate",
                        cert.id,
                    ),
                    "/asset-operations/units?unit_id=" + sorted(ids)[0],
                )
            )
    contracts: dict[tuple[str, str], UpstreamContract | TerminalContract] = {
        ("upstream", r.id): r for r in facts.upstream
    }
    contracts.update({("terminal", r.id): r for r in facts.terminal})
    status: str
    for (kind, _), contract in contracts.items():
        ids = covered(contract.id, kind, True)
        if isinstance(contract, UpstreamContract):
            status = derive_upstream_contract_status(
                contract,
                as_of=as_of,
                lifecycle_events=facts.events,
                successor_effective_from=facts.successors.get((kind, contract.id)),
            )
        else:
            status = derive_terminal_contract_status(
                contract,
                as_of=as_of,
                lifecycle_events=facts.events,
                successor_effective_from=facts.successors.get((kind, contract.id)),
            )
        if ids and status in {"active", "expiring"}:
            if (
                isinstance(contract, UpstreamContract)
                and contract.contract_type == "management_agreement"
            ):
                active_upstream_ids.add(contract.id)
            result.append(
                Requirement(
                    kind + "_contract",
                    kind + "_contract",
                    contract.id,
                    contract.contract_number,
                    ids,
                    linked_file(contract.scan_document_id, "contract", contract.id)
                    or archived(
                        kind + "_contract",
                        kind + "_contract",
                        contract.id,
                        "contract",
                        contract.id,
                    ),
                    "/asset-operations/contracts/"
                    + kind
                    + "?contract_id="
                    + contract.id,
                )
            )
    reversed_ids = {
        r.reversed_event_id
        for r in facts.events
        if r.event_type == "reversed" and r.effective_date <= as_of
    }
    for event in facts.events:
        if (
            event.id in reversed_ids
            or event.effective_date > as_of
            or event.event_type not in {"terminated", "exited"}
            or event.handover_status not in {"pending", "completed"}
        ):
            continue
        parent = contracts.get((event.contract_kind, event.contract_id))
        ids = covered(event.contract_id, event.contract_kind, False)
        if parent is not None and ids:
            result.append(
                Requirement(
                    "handover",
                    "contract_lifecycle_event",
                    event.id,
                    parent.contract_number + " 交接",
                    ids,
                    archived(
                        "handover",
                        "contract_lifecycle_event",
                        event.id,
                        "contract",
                        parent.id,
                    ),
                    "/asset-operations/contracts/"
                    + event.contract_kind
                    + "?contract_id="
                    + parent.id,
                )
            )
    for fee in facts.statements:
        confirmed_at = getattr(fee, "confirmed_at", None)
        if not _bound_by(confirmed_at, end):
            continue
        superseded_at = facts.superseded_at.get(fee.id)
        if superseded_at is not None and _bound_by(superseded_at, end):
            continue
        ids = frozenset(
            unit
            for cid in (fee.upstream_contract_ids or [])
            if cid in active_upstream_ids
            for unit in covered(cid, "upstream", True)
        )
        if ids:
            result.append(
                Requirement(
                    "management_fee_statement",
                    "management_fee_statement",
                    fee.id,
                    fee.statement_number,
                    ids,
                    linked_file(
                        fee.stamped_document_id, "management_fee_statement", fee.id
                    )
                    or archived(
                        "management_fee_statement",
                        "management_fee_statement",
                        fee.id,
                        "management_fee_statement",
                        fee.id,
                    ),
                    "/asset-operations/management-fees/" + fee.id,
                )
            )
    active_contracts = {
        (r.target_type, r.target_id): r
        for r in result
        if r.document_type in {"upstream_contract", "terminal_contract"}
    }
    for supplement in facts.supplements:
        requirement_parent = active_contracts.get(
            (supplement.contract_kind + "_contract", supplement.contract_id)
        )
        created_at = getattr(supplement, "created_at", None)
        withdrawn_at = supplement.withdrawn_at
        if (
            _bound_by(created_at, end)
            and (withdrawn_at is None or not _bound_by(withdrawn_at, end))
            and requirement_parent is not None
        ):
            result.append(
                Requirement(
                    "supplement",
                    "contract_supplement",
                    supplement.id,
                    supplement.agreement_number + " " + supplement.title,
                    requirement_parent.unit_ids,
                    archived(
                        "supplement",
                        "contract_supplement",
                        supplement.id,
                        "contract",
                        supplement.contract_id,
                    ),
                    requirement_parent.href,
                )
            )
    return tuple(result)


def categories(requirements: tuple[Requirement, ...]) -> list[ArchiveCategory]:
    result = []
    for kind, label in LABELS.items():
        rows = {r.target_id: r for r in requirements if r.document_type == kind}
        required, existing = len(rows), sum(r.existing for r in rows.values())
        result.append(
            ArchiveCategory(
                document_type=kind,
                label=label,
                required=required,
                existing=existing,
                missing=required - existing,
                completion_rate=existing / required if required else None,
            )
        )
    return result


class ArchiveMatrixService:
    def __init__(
        self,
        *,
        repository: ArchiveMatrixRepository = archive_matrix_repository,
        clock: Callable[[], date] = business_today,
    ):
        self.repository, self.clock = repository, clock

    def _effective_as_of(self, as_of: date | None) -> date:
        today = self.clock()
        if as_of is not None and as_of > today:
            raise BaseBusinessError(
                "统计日期不可晚于今天", code="ARCHIVE_AS_OF_INVALID", status_code=422
            )
        return as_of if as_of is not None else today

    async def completion(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        project_id: str | None = None,
        query: str | None = None,
        as_of: date | None = None,
    ) -> ArchiveCompletion:
        require_scope(scope, scope.user_id)
        effective = self._effective_as_of(as_of)
        facts = await self.repository.load(
            db, scope=scope, as_of=effective, project_id=project_id, query=query
        )
        requirements = project_requirements(facts, effective)
        linked = {
            uid
            for r in requirements
            if r.document_type == "property_certificate"
            for uid in r.unit_ids
        }
        return ArchiveCompletion(
            as_of=effective,
            categories=categories(requirements),
            unlinked_unit_count=sum(u.id not in linked for u in facts.units),
        )

    async def matrix(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        project_id: str | None = None,
        query: str | None = None,
        offset: int = 0,
        limit: int = 20,
        as_of: date | None = None,
    ) -> ArchiveMatrix:
        require_scope(scope, scope.user_id)
        effective = self._effective_as_of(as_of)
        facts = await self.repository.load(
            db, scope=scope, as_of=effective, project_id=project_id, query=query
        )
        requirements = project_requirements(facts, effective)
        items = []
        for unit in facts.units[offset : offset + limit]:
            rows = tuple(r for r in requirements if unit.id in r.unit_ids)
            items.append(
                ArchiveMatrixRow(
                    unit_id=unit.id,
                    unit_code=unit.unit_code,
                    unit_name=unit.name,
                    categories=categories(rows),
                    missing_items=[
                        ArchiveMissingItem(
                            document_type=r.document_type,
                            target_type=r.target_type,
                            target_id=r.target_id,
                            label=r.label,
                            href=(
                                "/asset-operations/units?unit_id=" + unit.id
                                if r.document_type == "property_certificate"
                                else r.href
                            ),
                        )
                        for r in rows
                        if not r.existing
                    ],
                )
            )
        return ArchiveMatrix(as_of=effective, items=items, total=len(facts.units))


archive_matrix_service = ArchiveMatrixService()
