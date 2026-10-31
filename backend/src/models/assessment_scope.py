"""Assessment-scope version models for asset-operations v5 reporting."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .asset_unit import AssetUnit


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


_JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class AssessmentScopeVersion(Base):
    """One operator's yearly assessment-scope version chain entry."""

    __tablename__ = "assessment_scope_versions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'superseded')",
            name="ck_assessment_scope_versions_status",
        ),
        CheckConstraint(
            "(status = 'draft' AND version_number IS NULL) "
            "OR (status <> 'draft' AND version_number >= 1)",
            name="ck_assessment_scope_versions_number",
        ),
        UniqueConstraint(
            "operator_party_id",
            "year",
            "version_number",
            name="uq_assessment_scope_versions_number",
        ),
        Index(
            "ix_assessment_scope_versions_operator",
            "operator_party_id",
            "year",
        ),
        Index(
            "uq_assessment_scope_versions_active",
            "operator_party_id",
            "year",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index(
            "uq_assessment_scope_versions_draft",
            "operator_party_id",
            "year",
            unique=True,
            postgresql_where=text("status = 'draft'"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    operator_party_id: Mapped[str] = mapped_column(
        String, ForeignKey("parties.id"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    version_number: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    effective_from_period: Mapped[str] = mapped_column(String(7), nullable=False)
    based_on_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assessment_scope_versions.id")
    )
    created_by: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow_naive
    )
    activated_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version}


class AssessmentScopeItem(Base):
    """One explicit include/exclude decision inside a scope version."""

    __tablename__ = "assessment_scope_items"
    __table_args__ = (
        CheckConstraint(
            "included = TRUE OR (exclusion_reason IS NOT NULL "
            "AND btrim(exclusion_reason) <> '')",
            name="ck_assessment_scope_items_exclusion_reason",
        ),
    )

    scope_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assessment_scope_versions.id"),
        primary_key=True,
    )
    asset_unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("asset_units.id"), primary_key=True
    )
    included: Mapped[bool] = mapped_column(Boolean, nullable=False)
    exclusion_reason: Mapped[str | None] = mapped_column(Text)
    unit_snapshot: Mapped[dict[str, object]] = mapped_column(_JSON_TYPE, nullable=False)


def build_unit_snapshot(unit: AssetUnit) -> dict[str, object]:
    """Capture the unit facts a saved scope version must reproduce."""
    return {
        "unit_code": unit.unit_code,
        "name": unit.name,
        "project_id": unit.project_id,
        "usage_type": unit.usage_type,
        "is_operating": unit.is_operating,
        "land_area": str(unit.land_area),
        "building_area": str(unit.building_area),
        "rentable_area": str(unit.rentable_area),
        "managed_from": (
            unit.managed_from.isoformat()
            if isinstance(unit.managed_from, date)
            else str(unit.managed_from)
        ),
        "predecessor_unit_ids": list(unit.predecessor_unit_ids),
    }


__all__ = [
    "AssessmentScopeItem",
    "AssessmentScopeVersion",
    "build_unit_snapshot",
]
