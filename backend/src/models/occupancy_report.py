"""Monthly occupancy-report models for asset-operations v5 reporting."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


_JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class MonthlyOccupancyReport(Base):
    """One operator's monthly reporting chain entry; draft rows hold the note.

    Draft rows carry only identity, status and the change note; totals and
    the locked scope version are snapshot fields written at submission time.
    """

    __tablename__ = "monthly_occupancy_reports"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'submitted', 'withdrawn')",
            name="ck_monthly_occupancy_reports_status",
        ),
        CheckConstraint(
            "period ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'",
            name="ck_monthly_occupancy_reports_period_format",
        ),
        CheckConstraint(
            "unit_count IS NULL OR unit_count >= 0",
            name="ck_monthly_occupancy_reports_unit_count",
        ),
        CheckConstraint(
            "rented_unit_count IS NULL OR rented_unit_count >= 0",
            name="ck_monthly_occupancy_reports_rented_unit_count",
        ),
        CheckConstraint(
            "land_area IS NULL OR land_area >= 0",
            name="ck_monthly_occupancy_reports_land_area",
        ),
        CheckConstraint(
            "building_area IS NULL OR building_area >= 0",
            name="ck_monthly_occupancy_reports_building_area",
        ),
        CheckConstraint(
            "rentable_area IS NULL OR rentable_area >= 0",
            name="ck_monthly_occupancy_reports_rentable_area",
        ),
        CheckConstraint(
            "rented_area IS NULL OR rented_area >= 0",
            name="ck_monthly_occupancy_reports_rented_area",
        ),
        Index(
            "uq_monthly_occupancy_reports_active_chain",
            "operator_party_id",
            "period",
            unique=True,
            postgresql_where=text("status <> 'withdrawn'"),
        ),
        Index(
            "ix_monthly_occupancy_reports_operator_period",
            "operator_party_id",
            "period",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    operator_party_id: Mapped[str] = mapped_column(
        String, ForeignKey("parties.id"), nullable=False
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    scope_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assessment_scope_versions.id")
    )
    change_note: Mapped[str | None] = mapped_column(Text)
    project_count: Mapped[int | None] = mapped_column(Integer)
    operating_project_count: Mapped[int | None] = mapped_column(Integer)
    non_operating_project_count: Mapped[int | None] = mapped_column(Integer)
    unit_count: Mapped[int | None] = mapped_column(Integer)
    rented_unit_count: Mapped[int | None] = mapped_column(Integer)
    occupancy_rate: Mapped[Decimal | None] = mapped_column(Numeric(19, 10))
    land_area: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    building_area: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    rentable_area: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    rented_area: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    submitted_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    withdrawn_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime)
    withdraw_reason: Mapped[str | None] = mapped_column(Text)
    predecessor_report_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("monthly_occupancy_reports.id")
    )
    created_by: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow_naive
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version}


class MonthlyOccupancyReportLine(Base):
    """Immutable per-unit snapshot row locked at submission time."""

    __tablename__ = "monthly_occupancy_report_lines"
    __table_args__ = (
        CheckConstraint(
            "rental_status IN ('rented', 'vacant', 'non_rentable')",
            name="ck_monthly_occupancy_report_lines_rental_status",
        ),
        CheckConstraint(
            "unit_count = 1",
            name="ck_monthly_occupancy_report_lines_unit_count",
        ),
        CheckConstraint(
            "rented_unit_count IN (0, 1)",
            name="ck_monthly_occupancy_report_lines_rented_unit_count",
        ),
        CheckConstraint(
            "land_area >= 0 AND building_area >= 0 AND rentable_area >= 0 "
            "AND rented_area >= 0",
            name="ck_monthly_occupancy_report_lines_areas_nonnegative",
        ),
        UniqueConstraint(
            "report_id",
            "asset_unit_id",
            name="uq_monthly_occupancy_report_lines_report_unit",
        ),
        Index(
            "ix_monthly_occupancy_report_lines_report",
            "report_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    report_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("monthly_occupancy_reports.id"),
        nullable=False,
    )
    asset_unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("asset_units.id"), nullable=False
    )
    owner_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    usage_type_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    project_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    address_snapshot: Mapped[str] = mapped_column(String(500), nullable=False)
    land_area: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    building_area: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    rentable_area: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    rented_area: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    unit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    rented_unit_count: Mapped[int] = mapped_column(Integer, nullable=False)
    rental_status: Mapped[str] = mapped_column(String(20), nullable=False)
    terminal_contract_ids: Mapped[list[str]] = mapped_column(
        _JSON_TYPE, nullable=False
    )


__all__ = ["MonthlyOccupancyReport", "MonthlyOccupancyReportLine"]
