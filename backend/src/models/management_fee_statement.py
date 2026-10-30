"""Management fee statement identities and immutable confirmation snapshots.

Draft status and totals are projections: NULL means unconfirmed, never a
persisted collecting/pending_stamp value. Confirmation fills the snapshot.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
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


class ManagementFeeStatement(Base):
    __tablename__ = "management_fee_statements"
    __table_args__ = (
        CheckConstraint(
            "status IS NULL OR status IN ('confirmed','superseded')",
            name="ck_management_fee_statements_status",
        ),
        CheckConstraint(
            "(status IS NULL AND base_amount IS NULL AND fee_amount IS NULL "
            "AND upstream_contract_ids IS NULL AND confirmed_at IS NULL AND confirmed_by IS NULL) "
            "OR (status IS NOT NULL AND base_amount IS NOT NULL AND fee_amount IS NOT NULL "
            "AND upstream_contract_ids IS NOT NULL AND stamped_document_id IS NOT NULL "
            "AND confirmed_at IS NOT NULL AND confirmed_by IS NOT NULL)",
            name="ck_management_fee_statements_snapshot",
        ),
        CheckConstraint(
            "base_amount >= 0 AND fee_amount >= 0",
            name="ck_management_fee_statements_amounts",
        ),
        CheckConstraint("version >= 1", name="ck_management_fee_statements_version"),
        CheckConstraint(
            "id <> predecessor_statement_id AND id <> successor_statement_id",
            name="ck_management_fee_statements_no_self_link",
        ),
        CheckConstraint(
            "length(period) = 7 AND substr(period, 5, 1) = '-' "
            "AND substr(period, 6, 2) IN ('01','02','03','04','05','06','07','08','09','10','11','12') "
            "AND substr(period, 1, 4) > '0000' "
            "AND substr(period, 1, 1) BETWEEN '0' AND '9' "
            "AND substr(period, 2, 1) BETWEEN '0' AND '9' "
            "AND substr(period, 3, 1) BETWEEN '0' AND '9' "
            "AND substr(period, 4, 1) BETWEEN '0' AND '9'",
            name="ck_management_fee_statements_period",
        ),
        Index(
            "uq_management_fee_statements_owner_period",
            "owner_party_id",
            "period",
            unique=True,
            postgresql_where=text("status IS NULL OR status <> 'superseded'"),
            sqlite_where=text("status IS NULL OR status <> 'superseded'"),
        ),
    )
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    owner_party_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parties.id"), nullable=False
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    statement_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    upstream_contract_ids: Mapped[list[str] | None] = mapped_column(
        JSON(none_as_null=True).with_variant(JSONB(none_as_null=True), "postgresql")
    )
    base_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    fee_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    status: Mapped[str | None] = mapped_column(String(20))
    stamped_document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("attachments.id")
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"))
    predecessor_statement_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("management_fee_statements.id"), unique=True
    )
    successor_statement_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("management_fee_statements.id"), unique=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}


class ManagementFeeStatementLine(Base):
    __tablename__ = "management_fee_statement_lines"
    __table_args__ = (
        UniqueConstraint(
            "statement_id",
            "rent_ledger_entry_id",
            name="uq_management_fee_lines_statement_entry",
        ),
        CheckConstraint(
            "line_kind IN ('current','carried')", name="ck_management_fee_lines_kind"
        ),
        CheckConstraint(
            "scheduled_rent >= 0 AND owner_received_amount >= 0 AND fee_amount >= 0 AND deferred_amount >= 0",
            name="ck_management_fee_lines_amounts",
        ),
        CheckConstraint(
            "fee_rate >= 0 AND fee_rate <= 1", name="ck_management_fee_lines_rate"
        ),
        CheckConstraint(
            "deferred_amount = 0 OR (deferral_reason IS NOT NULL AND length(trim(deferral_reason)) > 0)",
            name="ck_management_fee_lines_deferral_reason",
        ),
        CheckConstraint(
            "line_kind = 'carried' OR carried_from_statement_id IS NULL",
            name="ck_management_fee_lines_carried_source",
        ),
        CheckConstraint(
            "length(rent_period) = 7 AND substr(rent_period, 5, 1) = '-' "
            "AND substr(rent_period, 6, 2) IN ('01','02','03','04','05','06','07','08','09','10','11','12') "
            "AND substr(rent_period, 1, 4) > '0000' "
            "AND substr(rent_period, 1, 1) BETWEEN '0' AND '9' "
            "AND substr(rent_period, 2, 1) BETWEEN '0' AND '9' "
            "AND substr(rent_period, 3, 1) BETWEEN '0' AND '9' "
            "AND substr(rent_period, 4, 1) BETWEEN '0' AND '9'",
            name="ck_management_fee_lines_period",
        ),
    )
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    statement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("management_fee_statements.id"), nullable=False
    )
    line_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    upstream_contract_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("upstream_contracts.id"), nullable=False
    )
    terminal_contract_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("terminal_contracts.id"), nullable=False
    )
    rent_ledger_entry_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rent_ledger_entries.id"), nullable=False
    )
    asset_unit_ids: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    tenant_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    rent_period: Mapped[str] = mapped_column(String(7), nullable=False)
    scheduled_rent: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    owner_received_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    counted_record_ids: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    received_on: Mapped[date | None] = mapped_column(Date)
    fee_rate: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    deferred_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    deferral_reason: Mapped[str | None] = mapped_column(Text)
    carried_from_statement_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("management_fee_statements.id")
    )
