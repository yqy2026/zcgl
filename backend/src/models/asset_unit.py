"""Asset-operations v5 asset-unit source models."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


_JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class AssetUnitAcquisitionMode(str, enum.Enum):
    """How the operator acquired the right to manage an asset unit."""

    OWNED = "owned"
    LEASED = "leased"
    MANAGED = "managed"


class AssetUnitVacancyReason(str, enum.Enum):
    """Optional operating note for a currently vacant asset unit."""

    RENOVATION = "renovation"
    MARKETING = "marketing"
    REPOSSESSION = "repossession"
    PENDING_CONTRACT = "pending_contract"
    OTHER = "other"


class AssetUnitBoundaryChangeType(str, enum.Enum):
    """Supported physical-boundary changes."""

    SPLIT = "split"
    MERGE = "merge"


class AssetUnit(Base):
    """Smallest independently counted and leasable property boundary."""

    __tablename__ = "asset_units"
    __table_args__ = (
        UniqueConstraint("unit_code", name="uq_asset_units_unit_code"),
        CheckConstraint(
            "acquisition_mode IN ('owned', 'leased', 'managed')",
            name="ck_asset_units_acquisition_mode",
        ),
        CheckConstraint(
            "land_area >= 0",
            name="ck_asset_units_land_area_nonnegative",
        ),
        CheckConstraint(
            "building_area >= 0",
            name="ck_asset_units_building_area_nonnegative",
        ),
        CheckConstraint(
            "rentable_area >= 0 AND rentable_area <= building_area",
            name="ck_asset_units_rentable_area_valid",
        ),
        CheckConstraint(
            "managed_to IS NULL OR managed_to >= managed_from",
            name="ck_asset_units_managed_range",
        ),
        CheckConstraint(
            "vacancy_reason IS NULL OR vacancy_reason IN "
            "('renovation', 'marketing', 'repossession', "
            "'pending_contract', 'other')",
            name="ck_asset_units_vacancy_reason",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    unit_code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    owner_party_id: Mapped[str] = mapped_column(
        String, ForeignKey("parties.id"), nullable=False, index=True
    )
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    usage_type: Mapped[str] = mapped_column(String(100), nullable=False)
    acquisition_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    is_operating: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    land_area: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    building_area: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    rentable_area: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    managed_from: Mapped[date] = mapped_column(Date, nullable=False)
    managed_to: Mapped[date | None] = mapped_column(Date)
    vacancy_reason: Mapped[str | None] = mapped_column(String(30))
    expected_lease_start: Mapped[date | None] = mapped_column(Date)
    predecessor_unit_ids: Mapped[list[str]] = mapped_column(
        _JSON_TYPE, nullable=False, default=list
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow_naive
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=_utcnow_naive,
        onupdate=_utcnow_naive,
    )

    __mapper_args__ = {"version_id_col": version}


class AssetUnitBoundaryChange(Base):
    """Append-only split or merge event for asset-unit boundaries."""

    __tablename__ = "asset_unit_boundary_changes"
    __table_args__ = (
        UniqueConstraint(
            "created_by",
            "idempotency_key",
            name="uq_asset_unit_boundary_changes_actor_request",
        ),
        CheckConstraint(
            "change_type IN ('split', 'merge')",
            name="ck_asset_unit_boundary_changes_type",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source_unit_ids: Mapped[list[str]] = mapped_column(_JSON_TYPE, nullable=False)
    result_unit_ids: Mapped[list[str]] = mapped_column(_JSON_TYPE, nullable=False)
    area_check: Mapped[dict[str, object]] = mapped_column(_JSON_TYPE, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow_naive
    )
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    result_data: Mapped[dict[str, object]] = mapped_column(_JSON_TYPE, nullable=False)


class AssetUnitBoundarySource(Base):
    """Normalized source link preventing one unit from being consumed twice."""

    __tablename__ = "asset_unit_boundary_sources"
    __table_args__ = (
        UniqueConstraint(
            "asset_unit_id",
            name="uq_asset_unit_boundary_sources_unit",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    asset_unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("asset_units.id"), nullable=False
    )
    boundary_change_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("asset_unit_boundary_changes.id"), nullable=False
    )


class PropertyCertificateAssetUnit(Base):
    """Temporal property-certificate link to an asset unit."""

    __tablename__ = "property_certificate_asset_units"
    __table_args__ = (
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_property_certificate_asset_units_effective_range",
        ),
    )

    certificate_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("property_certificates.id", ondelete="CASCADE"),
        primary_key=True,
    )
    asset_unit_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("asset_units.id", ondelete="CASCADE"),
        primary_key=True,
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)


__all__ = [
    "AssetUnit",
    "AssetUnitAcquisitionMode",
    "AssetUnitBoundaryChange",
    "AssetUnitBoundaryChangeType",
    "AssetUnitBoundarySource",
    "AssetUnitVacancyReason",
    "PropertyCertificateAssetUnit",
]
