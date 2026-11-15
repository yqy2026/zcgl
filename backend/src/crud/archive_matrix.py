"""Batch fact reads for the scoped current-property archive projection."""

from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.archive_document import ArchiveDocument
from ..models.asset_contract import (
    ContractLifecycleEvent,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from ..models.asset_unit import AssetUnit, PropertyCertificateAssetUnit
from ..models.attachment import Attachment
from ..models.business_change_event import BusinessChangeEvent
from ..models.contract_supplement import ContractSupplement
from ..models.management_fee_statement import ManagementFeeStatement
from ..models.property_certificate import PropertyCertificate
from ..services.party_scope_resolver import EffectivePartyScope
from .asset_contract import asset_contract_repository
from .asset_unit import asset_unit_repository
from .business_change_event import fee_statement_ids_for_scope


@dataclass
class ArchiveMatrixFacts:
    units: tuple[AssetUnit, ...]
    upstream: tuple[UpstreamContract, ...]
    terminal: tuple[TerminalContract, ...]
    upstream_links: tuple[UpstreamContractAssetUnit, ...]
    terminal_links: tuple[TerminalContractAssetUnit, ...]
    certificates: tuple[PropertyCertificate, ...]
    certificate_links: tuple[PropertyCertificateAssetUnit, ...]
    events: tuple[ContractLifecycleEvent, ...]
    statements: tuple[ManagementFeeStatement, ...]
    attachments: tuple[Attachment, ...]
    documents: tuple[ArchiveDocument, ...]
    successors: dict[tuple[str, str], date]
    supplements: tuple[ContractSupplement, ...] = ()
    superseded_at: dict[str, datetime] = field(default_factory=dict)


class ArchiveMatrixRepository:
    async def load(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        as_of: date,
        project_id: str | None = None,
        query: str | None = None,
    ) -> ArchiveMatrixFacts:
        stmt = asset_unit_repository._apply_scope(select(AssetUnit), scope=scope).where(
            AssetUnit.managed_from <= as_of,
            or_(AssetUnit.managed_to.is_(None), AssetUnit.managed_to >= as_of),
        )
        if project_id is not None:
            stmt = stmt.where(AssetUnit.project_id == project_id)
        if query is not None and query.strip() != "":
            pattern = "%" + query.strip() + "%"
            stmt = stmt.where(
                or_(
                    AssetUnit.name.ilike(pattern),
                    AssetUnit.unit_code.ilike(pattern),
                    AssetUnit.address.ilike(pattern),
                )
            )
        units = tuple(
            (await db.execute(stmt.order_by(AssetUnit.unit_code, AssetUnit.id)))
            .scalars()
            .all()
        )
        ids = [u.id for u in units]
        uplinks = tuple(
            (
                await db.execute(
                    select(UpstreamContractAssetUnit).where(
                        UpstreamContractAssetUnit.asset_unit_id.in_(ids)
                    )
                )
            )
            .scalars()
            .all()
        )
        telinks = tuple(
            (
                await db.execute(
                    select(TerminalContractAssetUnit).where(
                        TerminalContractAssetUnit.asset_unit_id.in_(ids)
                    )
                )
            )
            .scalars()
            .all()
        )
        ups = tuple(
            (
                await db.execute(
                    asset_contract_repository._apply_upstream_scope(
                        select(UpstreamContract), scope=scope
                    ).where(
                        UpstreamContract.id.in_(
                            [r.upstream_contract_id for r in uplinks]
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        tes = tuple(
            (
                await db.execute(
                    asset_contract_repository._apply_terminal_scope(
                        select(TerminalContract), scope=scope
                    ).where(
                        TerminalContract.id.in_(
                            [r.terminal_contract_id for r in telinks]
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        upids, teids = [r.id for r in ups], [r.id for r in tes]
        events = tuple(
            (
                await db.execute(
                    select(ContractLifecycleEvent).where(
                        or_(
                            (ContractLifecycleEvent.contract_kind == "upstream")
                            & ContractLifecycleEvent.contract_id.in_(upids),
                            (ContractLifecycleEvent.contract_kind == "terminal")
                            & ContractLifecycleEvent.contract_id.in_(teids),
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        certlinks = tuple(
            (
                await db.execute(
                    select(PropertyCertificateAssetUnit).where(
                        PropertyCertificateAssetUnit.asset_unit_id.in_(ids),
                        PropertyCertificateAssetUnit.effective_from <= as_of,
                        or_(
                            PropertyCertificateAssetUnit.effective_to.is_(None),
                            PropertyCertificateAssetUnit.effective_to >= as_of,
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )
        certids = [r.certificate_id for r in certlinks]
        certs = tuple(
            (
                await db.execute(
                    select(PropertyCertificate).where(
                        PropertyCertificate.id.in_(certids)
                    )
                )
            )
            .scalars()
            .all()
        )
        fees = tuple(
            (
                await db.execute(
                    select(ManagementFeeStatement).where(
                        ManagementFeeStatement.id.in_(
                            fee_statement_ids_for_scope(scope)
                        ),
                        # Superseded statements still count historically until
                        # their correction moment passes the as-of day; the
                        # projection decides with the supersede events below.
                        ManagementFeeStatement.status.in_(("confirmed", "superseded")),
                    )
                )
            )
            .scalars()
            .all()
        )
        superseded_at = {
            row.target_id: row.occurred_at
            for row in (
                await db.execute(
                    select(BusinessChangeEvent)
                    .where(
                        BusinessChangeEvent.target_type == "management_fee_statement",
                        BusinessChangeEvent.action
                        == "supersede_management_fee_statement",
                        BusinessChangeEvent.target_id.in_([f.id for f in fees]),
                    )
                    .order_by(BusinessChangeEvent.occurred_at)
                )
            )
            .scalars()
            .all()
        }
        supplements = tuple(
            (
                await db.execute(
                    select(ContractSupplement).where(
                        or_(
                            (ContractSupplement.contract_kind == "upstream")
                            & ContractSupplement.contract_id.in_(upids),
                            (ContractSupplement.contract_kind == "terminal")
                            & ContractSupplement.contract_id.in_(teids),
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )
        target_ids = (
            certids
            + upids
            + teids
            + [r.id for r in events]
            + [r.id for r in supplements]
        )
        docs = tuple(
            (
                await db.execute(
                    select(ArchiveDocument).where(
                        ArchiveDocument.target_id.in_(target_ids)
                    )
                )
            )
            .scalars()
            .all()
        )
        fileids = (
            [r.attachment_id for r in docs]
            + [r.scan_document_id for r in ups if r.scan_document_id is not None]
            + [r.scan_document_id for r in tes if r.scan_document_id is not None]
            + [r.stamped_document_id for r in fees if r.stamped_document_id is not None]
        )
        files = tuple(
            (await db.execute(select(Attachment).where(Attachment.id.in_(fileids))))
            .scalars()
            .all()
        )
        successors: dict[tuple[str, str], date] = {}
        for parent, start in (
            await db.execute(
                select(
                    UpstreamContract.renewed_from_id, UpstreamContract.start_date
                ).where(UpstreamContract.renewed_from_id.in_(upids))
            )
        ).all():
            key = ("upstream", parent)
            successors[key] = min(successors.get(key, start), start)
        for parent, start in (
            await db.execute(
                select(
                    TerminalContract.renewed_from_id, TerminalContract.start_date
                ).where(TerminalContract.renewed_from_id.in_(teids))
            )
        ).all():
            key = ("terminal", parent)
            successors[key] = min(successors.get(key, start), start)
        return ArchiveMatrixFacts(
            units,
            ups,
            tes,
            uplinks,
            telinks,
            certs,
            certlinks,
            events,
            fees,
            files,
            docs,
            successors,
            supplements,
            superseded_at,
        )


archive_matrix_repository = ArchiveMatrixRepository()
