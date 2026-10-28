"""Asset-operations v5 signed-contract source models.

This module stores signed terms, temporal asset-unit coverage, rent schedules,
and append-only lifecycle events. Contract status and warning flags are
deliberately derived by the service layer rather than persisted here.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

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
    func,
    literal_column,
)
from sqlalchemy.dialects.postgresql import JSONB, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base

_JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class UpstreamContractType(str, enum.Enum):
    LEASE = "lease"
    MANAGEMENT_AGREEMENT = "management_agreement"


class TerminalContractMode(str, enum.Enum):
    SUBLEASE = "sublease"
    DIRECT_LEASE = "direct_lease"


class ContractKind(str, enum.Enum):
    UPSTREAM = "upstream"
    TERMINAL = "terminal"


class PaymentCycle(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class RentCollector(str, enum.Enum):
    OPERATOR = "operator"
    OWNER = "owner"


class ContractLifecycleEventType(str, enum.Enum):
    RENEWED = "renewed"
    TERMINATED = "terminated"
    EXITED = "exited"
    REVERSED = "reversed"


class ContractTerminationType(str, enum.Enum):
    EXPIRY = "expiry"
    EARLY = "early"
    MUTUAL = "mutual"


class HandoverStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    NOT_APPLICABLE = "not_applicable"


class DepositSettlementStatus(str, enum.Enum):
    PENDING = "pending"
    SETTLED = "settled"
    NOT_APPLICABLE = "not_applicable"


class AssetContractWriteReceipt(Base):
    """Durable response snapshot for idempotent signed-contract creation."""

    __tablename__ = "asset_contract_write_receipts"
    __table_args__ = (
        UniqueConstraint(
            "actor_id",
            "idempotency_key",
            name="uq_asset_contract_write_receipts_actor_request",
        ),
        CheckConstraint(
            "command_kind IN ('create_upstream', 'create_terminal', 'correct_rent_schedule', 'create_manual_rent_entry', 'void_manual_rent_entry')",
            name="ck_asset_contract_write_receipts_command_kind",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    actor_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
    command_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    result_data: Mapped[dict[str, object]] = mapped_column(_JSON_TYPE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow_naive
    )


class UpstreamContract(Base):
    """Signed lease or management agreement that grants operating authority."""

    __tablename__ = "upstream_contracts"
    __table_args__ = (
        CheckConstraint(
            "contract_type = 'lease' OR deposit_amount = 0",
            name="ck_upstream_contracts_management_deposit_zero",
        ),
        UniqueConstraint(
            "contract_number",
            name="uq_upstream_contracts_contract_number",
        ),
        CheckConstraint(
            "contract_type IN ('lease', 'management_agreement')",
            name="ck_upstream_contracts_type",
        ),
        CheckConstraint(
            "end_date >= start_date",
            name="ck_upstream_contracts_date_range",
        ),
        CheckConstraint(
            "(contract_type = 'lease' "
            "AND payment_cycle IN ('monthly', 'quarterly', 'yearly', 'custom') "
            "AND management_fee_rate IS NULL) OR "
            "(contract_type = 'management_agreement' "
            "AND payment_cycle IS NULL AND payment_day IS NULL "
            "AND management_fee_rate IS NOT NULL)",
            name="ck_upstream_contracts_payment_terms",
        ),
        CheckConstraint(
            "payment_day IS NULL OR payment_day BETWEEN 1 AND 31",
            name="ck_upstream_contracts_payment_day",
        ),
        CheckConstraint(
            "management_fee_rate IS NULL OR "
            "(management_fee_rate >= 0 AND management_fee_rate <= 1)",
            name="ck_upstream_contracts_management_fee_rate",
        ),
        CheckConstraint(
            "deposit_amount >= 0",
            name="ck_upstream_contracts_deposit_nonnegative",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    contract_number: Mapped[str] = mapped_column(String(100), nullable=False)
    contract_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_party_id: Mapped[str] = mapped_column(
        String, ForeignKey("parties.id"), nullable=False, index=True
    )
    operator_party_id: Mapped[str] = mapped_column(
        String, ForeignKey("parties.id"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payment_cycle: Mapped[str | None] = mapped_column(String(20))
    payment_day: Mapped[int | None] = mapped_column(Integer)
    management_fee_rate: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    deposit_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    oa_reference: Mapped[str | None] = mapped_column(String(100))
    renewed_from_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("upstream_contracts.id"), index=True
    )
    scan_document_id: Mapped[str] = mapped_column(
        String, ForeignKey("attachments.id"), nullable=False, index=True
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


class TerminalContract(Base):
    """Signed sublease or owner-direct lease covering one or more asset units."""

    __tablename__ = "terminal_contracts"
    __table_args__ = (
        UniqueConstraint(
            "contract_number",
            name="uq_terminal_contracts_contract_number",
        ),
        CheckConstraint(
            "contract_mode IN ('sublease', 'direct_lease')",
            name="ck_terminal_contracts_mode",
        ),
        CheckConstraint(
            "end_date >= start_date",
            name="ck_terminal_contracts_date_range",
        ),
        CheckConstraint(
            "(contract_mode = 'sublease' AND rent_collector = 'operator') OR "
            "(contract_mode = 'direct_lease' AND rent_collector = 'owner')",
            name="ck_terminal_contracts_rent_collector",
        ),
        CheckConstraint(
            "deposit_months IS NULL OR deposit_months >= 0",
            name="ck_terminal_contracts_deposit_months_nonnegative",
        ),
        CheckConstraint(
            "deposit_amount >= 0",
            name="ck_terminal_contracts_deposit_nonnegative",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    contract_number: Mapped[str] = mapped_column(String(100), nullable=False)
    contract_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    tenant_party_id: Mapped[str] = mapped_column(
        String, ForeignKey("parties.id"), nullable=False, index=True
    )
    lessor_party_id: Mapped[str] = mapped_column(
        String, ForeignKey("parties.id"), nullable=False, index=True
    )
    upstream_contract_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("upstream_contracts.id"), index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    deposit_months: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    deposit_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    rent_collector: Mapped[str] = mapped_column(String(20), nullable=False)
    renewed_from_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("terminal_contracts.id"), index=True
    )
    scan_document_id: Mapped[str] = mapped_column(
        String, ForeignKey("attachments.id"), nullable=False, index=True
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


class UpstreamContractAssetUnit(Base):
    """Temporal coverage of an asset unit by an upstream contract."""

    __tablename__ = "upstream_contract_asset_units"
    __table_args__ = (
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_upstream_contract_asset_units_effective_range",
        ),
    )

    upstream_contract_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("upstream_contracts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    asset_unit_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("asset_units.id", ondelete="CASCADE"),
        primary_key=True,
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)


class TerminalContractAssetUnit(Base):
    """Temporal terminal-contract coverage with no unit-period overlap."""

    __tablename__ = "terminal_contract_asset_units"

    terminal_contract_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("terminal_contracts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    asset_unit_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("asset_units.id", ondelete="CASCADE"),
        primary_key=True,
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)

    __table_args__ = (
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_terminal_contract_asset_units_effective_range",
        ),
        ExcludeConstraint(  # type: ignore[no-untyped-call]
            (asset_unit_id, "="),
            (
                func.daterange(
                    effective_from,
                    func.coalesce(
                        effective_to,
                        literal_column("'infinity'::date"),
                    ),
                    literal_column("'[]'"),
                ),
                "&&",
            ),
            using="gist",
            name="ex_terminal_contract_asset_units_unit_period",
        ),
    )


class ContractRentSchedule(Base):
    """One confirmed rent stage for an upstream or terminal contract."""

    __tablename__ = "contract_rent_schedules"
    __table_args__ = (
        Index(
            "uq_contract_rent_schedules_active_stage",
            "contract_kind",
            "contract_id",
            "stage_start",
            unique=True,
            postgresql_where=literal_column("superseded_at IS NULL"),
            sqlite_where=literal_column("superseded_at IS NULL"),
        ),
        CheckConstraint(
            "contract_kind IN ('upstream', 'terminal')",
            name="ck_contract_rent_schedules_kind",
        ),
        CheckConstraint(
            "stage_end >= stage_start",
            name="ck_contract_rent_schedules_stage_range",
        ),
        CheckConstraint(
            "base_monthly_rent >= 0 AND increase_rate >= 0 "
            "AND free_rent_months >= 0 AND discount_amount >= 0 "
            "AND actual_monthly_rent >= 0",
            name="ck_contract_rent_schedules_amounts_nonnegative",
        ),
        CheckConstraint(
            "payment_cycle IN ('monthly', 'quarterly', 'yearly', 'custom')",
            name="ck_contract_rent_schedules_payment_cycle",
        ),
        CheckConstraint(
            "due_day BETWEEN 1 AND 31",
            name="ck_contract_rent_schedules_due_day",
        ),
        Index(
            "ix_contract_rent_schedules_target",
            "contract_kind",
            "contract_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    contract_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    contract_id: Mapped[str] = mapped_column(String(36), nullable=False)
    stage_start: Mapped[date] = mapped_column(Date, nullable=False)
    stage_end: Mapped[date] = mapped_column(Date, nullable=False)
    base_monthly_rent: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    increase_rate: Mapped[Decimal] = mapped_column(
        Numeric(9, 6), nullable=False, default=Decimal("0")
    )
    free_rent_months: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), nullable=False, default=Decimal("0")
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    actual_monthly_rent: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    payment_cycle: Mapped[str] = mapped_column(String(20), nullable=False)
    due_day: Mapped[int] = mapped_column(Integer, nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_correlation_id: Mapped[str | None] = mapped_column(String(100))


class ContractLifecycleEvent(Base):
    """Append-only renewal, termination, exit, or reversal fact."""

    __tablename__ = "contract_lifecycle_events"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_contract_lifecycle_events_idempotency_key",
        ),
        CheckConstraint(
            "contract_kind IN ('upstream', 'terminal')",
            name="ck_contract_lifecycle_events_kind",
        ),
        CheckConstraint(
            "event_type IN ('renewed', 'terminated', 'exited', 'reversed')",
            name="ck_contract_lifecycle_events_type",
        ),
        CheckConstraint(
            "(event_type = 'terminated' AND contract_kind = 'terminal') OR "
            "(event_type = 'exited' AND contract_kind = 'upstream') OR "
            "event_type IN ('renewed', 'reversed')",
            name="ck_contract_lifecycle_events_target_compatibility",
        ),
        CheckConstraint(
            "(event_type = 'renewed' AND successor_contract_id IS NOT NULL "
            "AND successor_contract_id <> contract_id) OR "
            "(event_type <> 'renewed' AND successor_contract_id IS NULL)",
            name="ck_contract_lifecycle_events_successor",
        ),
        CheckConstraint(
            "(event_type = 'reversed' AND reversed_event_id IS NOT NULL) OR "
            "(event_type <> 'reversed' AND reversed_event_id IS NULL)",
            name="ck_contract_lifecycle_events_reversal",
        ),
        CheckConstraint(
            "event_type = 'renewed' OR "
            "(reason IS NOT NULL AND length(trim(reason)) > 0)",
            name="ck_contract_lifecycle_events_reason",
        ),
        CheckConstraint(
            "termination_type IS NULL OR "
            "termination_type IN ('expiry', 'early', 'mutual')",
            name="ck_contract_lifecycle_events_termination_type",
        ),
        CheckConstraint(
            "handover_status IS NULL OR "
            "handover_status IN ('pending', 'completed', 'not_applicable')",
            name="ck_contract_lifecycle_events_handover_status",
        ),
        CheckConstraint(
            "deposit_settlement_status IS NULL OR deposit_settlement_status IN "
            "('pending', 'settled', 'not_applicable')",
            name="ck_contract_lifecycle_events_deposit_status",
        ),
        Index(
            "ix_contract_lifecycle_events_target",
            "contract_kind",
            "contract_id",
            "effective_date",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    contract_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    contract_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    termination_type: Mapped[str | None] = mapped_column(String(20))
    handover_status: Mapped[str | None] = mapped_column(String(20))
    deposit_settlement_status: Mapped[str | None] = mapped_column(String(20))
    successor_contract_id: Mapped[str | None] = mapped_column(String(36))
    reversed_event_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contract_lifecycle_events.id")
    )
    reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow_naive
    )
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)


__all__ = [
    "AssetContractWriteReceipt",
    "ContractKind",
    "ContractLifecycleEvent",
    "ContractLifecycleEventType",
    "ContractRentSchedule",
    "ContractTerminationType",
    "DepositSettlementStatus",
    "HandoverStatus",
    "PaymentCycle",
    "RentCollector",
    "TerminalContract",
    "TerminalContractAssetUnit",
    "TerminalContractMode",
    "UpstreamContract",
    "UpstreamContractAssetUnit",
    "UpstreamContractType",
]
