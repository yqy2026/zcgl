"""Data access for asset-operations v5 assessment-scope versions."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import and_, exists, func, not_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.assessment_scope import (
    AssessmentScopeItem,
    AssessmentScopeVersion,
)
from ..models.asset_contract import UpstreamContract, UpstreamContractAssetUnit
from ..models.asset_unit import AssetUnit
from ..models.party import Party
from ..models.project import Project


class AssessmentScopeRepository:
    """Read and persist scope versions scoped by operator party, never by user."""

    async def party_exists(self, db: AsyncSession, *, party_id: str) -> bool:
        statement = select(func.count()).select_from(Party).where(Party.id == party_id)
        return int((await db.execute(statement)).scalar_one()) > 0

    async def get_active_version(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        year: int,
    ) -> AssessmentScopeVersion | None:
        statement = (
            select(AssessmentScopeVersion)
            .where(
                AssessmentScopeVersion.operator_party_id == operator_party_id,
                AssessmentScopeVersion.year == year,
                AssessmentScopeVersion.status == "active",
            )
            .limit(1)
        )
        return (await db.execute(statement)).scalars().one_or_none()

    async def get_draft_version(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        year: int,
    ) -> AssessmentScopeVersion | None:
        statement = (
            select(AssessmentScopeVersion)
            .where(
                AssessmentScopeVersion.operator_party_id == operator_party_id,
                AssessmentScopeVersion.year == year,
                AssessmentScopeVersion.status == "draft",
            )
            .limit(1)
        )
        return (await db.execute(statement)).scalars().one_or_none()

    async def get_version(
        self,
        db: AsyncSession,
        *,
        version_id: str,
        for_update: bool = False,
    ) -> AssessmentScopeVersion | None:
        statement = (
            select(AssessmentScopeVersion)
            .where(AssessmentScopeVersion.id == version_id)
            .limit(1)
        )
        if for_update:
            # populate_existing discards a stale identity-map row so a caller
            # that queued on the serialization lock re-reads committed state
            # instead of its own pre-lock snapshot.
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return (await db.execute(statement)).scalars().one_or_none()

    async def next_version_number(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        year: int,
    ) -> int:
        statement = select(func.max(AssessmentScopeVersion.version_number)).where(
            AssessmentScopeVersion.operator_party_id == operator_party_id,
            AssessmentScopeVersion.year == year,
        )
        current = (await db.execute(statement)).scalar_one()
        return int(current) + 1 if current is not None else 1

    async def list_items(
        self,
        db: AsyncSession,
        *,
        version_id: str,
    ) -> list[AssessmentScopeItem]:
        statement = (
            select(AssessmentScopeItem)
            .where(AssessmentScopeItem.scope_version_id == version_id)
            .order_by(AssessmentScopeItem.asset_unit_id)
        )
        return list((await db.execute(statement)).scalars().all())

    async def replace_items(
        self,
        db: AsyncSession,
        *,
        version_id: str,
        items: Sequence[AssessmentScopeItem],
    ) -> None:
        await db.execute(
            AssessmentScopeItem.__table__.delete().where(
                AssessmentScopeItem.scope_version_id == version_id
            )
        )
        for item in items:
            db.add(item)
        await db.flush()

    async def list_managed_units(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        as_of: date,
        year: int,
    ) -> list[AssetUnit]:
        """Units this operator currently manages, whole-company, not user-scoped.

        Ownership follows an effective upstream coverage first; only units
        without any effective coverage fall back to the project operator.
        """
        active_coverage = and_(
            UpstreamContractAssetUnit.effective_from <= as_of,
            (UpstreamContractAssetUnit.effective_to.is_(None))
            | (UpstreamContractAssetUnit.effective_to >= as_of),
        )
        operator_coverage = exists(
            select(1)
            .select_from(UpstreamContractAssetUnit)
            .join(
                UpstreamContract,
                UpstreamContract.id
                == UpstreamContractAssetUnit.upstream_contract_id,
            )
            .where(
                UpstreamContractAssetUnit.asset_unit_id == AssetUnit.id,
                active_coverage,
                UpstreamContract.operator_party_id == operator_party_id,
            )
        )
        any_coverage = exists(
            select(1)
            .select_from(UpstreamContractAssetUnit).where(
                UpstreamContractAssetUnit.asset_unit_id == AssetUnit.id,
                active_coverage,
            )
        )
        project_operator = exists(
            select(1)
            .select_from(Project)
            .where(
                Project.id == AssetUnit.project_id,
                Project.manager_party_id == operator_party_id,
            )
        )
        statement = (
            select(AssetUnit)
            .where(
                AssetUnit.is_operating.is_(True),
                AssetUnit.managed_from <= date(year, 12, 31),
                (AssetUnit.managed_to.is_(None))
                | (AssetUnit.managed_to >= date(year, 1, 1)),
                operator_coverage | (not_(any_coverage) & project_operator),
            )
            .order_by(AssetUnit.unit_code)
        )
        return list((await db.execute(statement)).scalars().all())

    async def lock_serialization(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        year: int,
    ) -> None:
        """Serialize draft creation and version activation per operator-year."""
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"assessment_scope:{operator_party_id}:{year}"},
        )


assessment_scope_repository = AssessmentScopeRepository()


__all__ = ["AssessmentScopeRepository", "assessment_scope_repository"]
