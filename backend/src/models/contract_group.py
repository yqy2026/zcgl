"""
Contract relationship and contract hierarchy models.

ContractGroup is the technical aggregate root for a user-visible contract
relationship. Contract stores shared fields, with specialized details in
LeaseContractDetail and AgencyAgreementDetail.
"""

import enum
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .asset import Asset
    from .party import Party
    from .project import Project

from sqlalchemy import (
    DECIMAL,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    case,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .associations import (
    contract_assets,
    contract_group_assets,
    contract_scan_document_links,
)


def _decimal_or_zero(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def derive_ledger_payment_status(
    *,
    amount_due: Any,
    paid_amount: Any,
    stored_status: Any = None,
) -> str:
    """Derive unpaid/partial/paid from money facts; preserve system voided."""
    if stored_status == "voided":
        return "voided"
    paid = _decimal_or_zero(paid_amount)
    due = _decimal_or_zero(amount_due)
    if paid <= 0:
        return "unpaid"
    if paid < due:
        return "partial"
    return "paid"


def _ledger_payment_status_expression(cls: type[Any]) -> Any:
    return case(
        (cls._payment_status == "voided", "voided"),
        (cls.paid_amount <= 0, "unpaid"),
        (cls.paid_amount < cls.amount_due, "partial"),
        else_="paid",
    )


class RevenueMode(str, enum.Enum):
    """Revenue mode for a contract group."""

    LEASE = "lease"
    AGENCY = "agency"


class ContractDirection(str, enum.Enum):
    """Contract direction from the operator perspective."""

    LESSOR = "出租"
    LESSEE = "承租"


class GroupRelationType(str, enum.Enum):
    """Role of a contract inside a contract group."""

    UPSTREAM = "上游"
    DOWNSTREAM = "下游"
    ENTRUSTED = "委托"
    DIRECT_LEASE = "直租"


class ContractLifecycleStatus(str, enum.Enum):
    """Contract lifecycle status."""

    DRAFT = "草稿"
    ACTIVE = "生效"
    TERMINATED = "已终止"


class ContractGroup(Base):
    """Technical aggregate for one contract relationship."""

    __tablename__ = "contract_groups"

    contract_group_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    project_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("projects.id"),
        nullable=True,
        index=True,
        comment="Project ID, nullable before phase 1a backfill.",
    )
    group_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Unique contract group code.",
    )
    revenue_mode: Mapped[RevenueMode] = mapped_column(
        Enum(RevenueMode, values_callable=lambda e: [m.name for m in e]),
        nullable=False,
        comment="Revenue mode. DB stores enum names.",
    )
    operator_party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id"),
        nullable=False,
        index=True,
        comment="Operator party ID.",
    )
    owner_party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id"),
        nullable=False,
        index=True,
        comment="Owner party ID.",
    )
    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Effective start date.",
    )
    effective_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Effective end date.",
    )
    settlement_rule: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Optional settlement rule snapshot.",
    )
    revenue_attribution_rule: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Revenue attribution rule.",
    )
    revenue_share_rule: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Revenue share rule reserved for MVP.",
    )
    risk_tags: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Risk tag list.",
    )
    data_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="正常",
        comment="Data status.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    operator_party: Mapped["Party"] = relationship(
        "Party",
        foreign_keys=[operator_party_id],
    )
    owner_party: Mapped["Party"] = relationship(
        "Party",
        foreign_keys=[owner_party_id],
    )
    project: Mapped["Project | None"] = relationship(
        "Project",
        back_populates="contract_groups",
    )
    contracts: Mapped[list["Contract"]] = relationship(
        "Contract",
        back_populates="contract_group",
        cascade="all, delete-orphan",
    )
    service_fee_ledgers: Mapped[list["ServiceFeeLedger"]] = relationship(
        "ServiceFeeLedger",
        back_populates="contract_group",
        cascade="all, delete-orphan",
    )
    assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        secondary=contract_group_assets,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ContractGroup(group_code={self.group_code}, mode={self.revenue_mode})>"
        )


class Contract(Base):
    """Shared base table for all contract types."""

    __tablename__ = "contracts"
    __table_args__ = (
        CheckConstraint(
            "data_status <> '正常' OR project_id IS NOT NULL",
            name="ck_contracts_active_project_id_required",
        ),
        UniqueConstraint(
            "contract_number",
            "project_id",
            name="uq_contract_number_project",
        ),
    )
    contract_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    contract_group_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("contract_groups.contract_group_id"),
        nullable=False,
        index=True,
        comment="Owning contract group.",
    )
    project_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("projects.id"),
        nullable=True,
        index=True,
        comment="Frozen project ID for per-project contract number uniqueness.",
    )
    contract_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Contract number.",
    )
    contract_direction: Mapped[ContractDirection] = mapped_column(
        Enum(ContractDirection, values_callable=lambda e: [m.name for m in e]),
        nullable=False,
        comment="Contract direction. DB stores enum names.",
    )
    group_relation_type: Mapped[GroupRelationType] = mapped_column(
        Enum(GroupRelationType, values_callable=lambda e: [m.name for m in e]),
        nullable=False,
        comment="Contract role in group. DB stores enum names.",
    )
    lessor_party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id"),
        nullable=False,
        index=True,
        comment="Lessor or entrusted party ID.",
    )
    lessee_party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id"),
        nullable=False,
        index=True,
        comment="Lessee or operator party ID.",
    )
    lessor_name_snapshot: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Lessor/entrusting party name snapshot captured at finalization.",
    )
    lessee_name_snapshot: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Lessee/entrusted party name snapshot captured at finalization.",
    )
    correction_source_contract_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("contracts.contract_id"),
        nullable=True,
        index=True,
        comment="Source contract for correction drafts.",
    )
    sign_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Sign date.",
    )
    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Effective start date.",
    )
    effective_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Effective end date.",
    )
    currency_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="CNY",
        comment="Currency code.",
    )
    tax_rate: Mapped[Decimal | None] = mapped_column(
        DECIMAL(5, 4),
        nullable=True,
        comment="Tax rate in [0, 1].",
    )
    is_tax_included: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether amount includes tax.",
    )
    status: Mapped[ContractLifecycleStatus] = mapped_column(
        Enum(ContractLifecycleStatus, values_callable=lambda e: [m.name for m in e]),
        nullable=False,
        default=ContractLifecycleStatus.DRAFT,
        comment="Contract lifecycle status. DB stores enum names.",
    )

    data_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="正常",
        comment="Data status.",
    )
    contract_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Contract notes.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_session_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="PDF import session ID.",
    )

    contract_group: Mapped["ContractGroup"] = relationship(
        "ContractGroup",
        back_populates="contracts",
    )
    lessor_party: Mapped["Party"] = relationship(
        "Party",
        foreign_keys=[lessor_party_id],
    )
    lessee_party: Mapped["Party"] = relationship(
        "Party",
        foreign_keys=[lessee_party_id],
    )
    correction_source_contract: Mapped["Contract | None"] = relationship(
        "Contract",
        remote_side=[contract_id],
        foreign_keys=[correction_source_contract_id],
    )
    assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        secondary=contract_assets,
    )
    lease_detail: Mapped["LeaseContractDetail | None"] = relationship(
        "LeaseContractDetail",
        back_populates="contract",
        uselist=False,
        cascade="all, delete-orphan",
    )
    agency_detail: Mapped["AgencyAgreementDetail | None"] = relationship(
        "AgencyAgreementDetail",
        back_populates="contract",
        uselist=False,
        cascade="all, delete-orphan",
    )
    scan_documents: Mapped[list["ContractScanDocument"]] = relationship(
        "ContractScanDocument",
        secondary=contract_scan_document_links,
        back_populates="contracts",
    )
    audit_logs: Mapped[list["ContractAuditLog"]] = relationship(
        "ContractAuditLog",
        back_populates="contract",
        cascade="all, delete-orphan",
    )
    rent_terms: Mapped[list["ContractRentTerm"]] = relationship(
        "ContractRentTerm",
        back_populates="contract",
        cascade="all, delete-orphan",
    )
    ledger_entries: Mapped[list["ContractLedgerEntry"]] = relationship(
        "ContractLedgerEntry",
        back_populates="contract",
        cascade="all, delete-orphan",
    )
    service_fee_ledgers: Mapped[list["ServiceFeeLedger"]] = relationship(
        "ServiceFeeLedger",
        back_populates="agency_contract",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Contract(contract_id={self.contract_id}, "
            f"type={self.group_relation_type}, status={self.status})>"
        )


class LeaseContractDetail(Base):
    """Lease-specific detail table."""

    __tablename__ = "lease_contract_details"

    lease_detail_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    contract_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("contracts.contract_id"),
        nullable=False,
        unique=True,
        index=True,
        comment="One-to-one contract FK.",
    )
    total_deposit: Mapped[Decimal | None] = mapped_column(
        DECIMAL(18, 2),
        nullable=True,
        default=Decimal("0"),
        comment="Total deposit amount.",
    )
    rent_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 2),
        nullable=False,
        comment="Contract-level total rent amount.",
    )
    monthly_rent_base: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2),
        nullable=True,
        comment="Base monthly rent.",
    )
    payment_cycle: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="月付",
        comment="Payment cycle.",
    )
    payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Denormalized tenant display name.",
    )
    tenant_contact: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tenant_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tenant_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tenant_usage: Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Denormalized owner display name.",
    )
    owner_contact: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    contract: Mapped["Contract"] = relationship(
        "Contract",
        back_populates="lease_detail",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<LeaseContractDetail(contract_id={self.contract_id}, "
            f"rent_amount={self.rent_amount})>"
        )


class AgencyAgreementDetail(Base):
    """Agency-agreement-specific detail table."""

    __tablename__ = "agency_agreement_details"

    agency_detail_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    contract_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("contracts.contract_id"),
        nullable=False,
        unique=True,
        index=True,
        comment="One-to-one contract FK.",
    )
    service_fee_ratio: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 4),
        nullable=False,
        comment="Service fee ratio, e.g. 0.0500 = 5%.",
    )
    fee_calculation_base: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="actual_received",
        comment="Fee base: actual_received or due_amount.",
    )
    agency_scope: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Agency scope free text.",
    )

    contract: Mapped["Contract"] = relationship(
        "Contract",
        back_populates="agency_detail",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<AgencyAgreementDetail(contract_id={self.contract_id}, "
            f"ratio={self.service_fee_ratio})>"
        )


class ContractScanDocument(Base):
    """Shared stamped scan document referenced by one or more contracts."""

    __tablename__ = "contract_scan_documents"

    document_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    storage_key: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        unique=True,
        index=True,
        comment="Stable storage key or file path for the stamped scan.",
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Optional content checksum for duplicate hints.",
    )
    data_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="正常",
        comment="Data status.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    contracts: Mapped[list["Contract"]] = relationship(
        "Contract",
        secondary=contract_scan_document_links,
        back_populates="scan_documents",
    )


class ContractAuditLog(Base):
    """Contract lifecycle audit log."""

    __tablename__ = "contract_audit_logs"

    log_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    contract_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("contracts.contract_id"),
        nullable=False,
        index=True,
        comment="Contract ID.",
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Action: terminate, void, start_correction, finalize_correction",
    )
    old_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    operator_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    operator_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    related_entry_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Related document or ledger entry ID.",
    )
    context: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Structured audit context.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    contract: Mapped["Contract"] = relationship(
        "Contract",
        back_populates="audit_logs",
    )


class ContractRentTerm(Base):
    """Segmented rent terms."""

    __tablename__ = "contract_rent_terms"
    __table_args__ = (
        UniqueConstraint(
            "contract_id",
            "sort_order",
            name="uq_contract_rent_term_order",
        ),
    )

    rent_term_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    contract_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("contracts.contract_id"),
        nullable=False,
        index=True,
        comment="Contract ID.",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Term order, starting from 1.",
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    monthly_rent: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    management_fee: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        nullable=False,
        default=Decimal("0"),
    )
    other_fees: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        nullable=False,
        default=Decimal("0"),
    )
    total_monthly_amount: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2),
        nullable=True,
        comment="Derived monthly_rent + management_fee + other_fees.",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    contract: Mapped["Contract"] = relationship(
        "Contract",
        back_populates="rent_terms",
    )


class ContractLedgerEntry(Base):
    """Monthly contract ledger entry."""

    __tablename__ = "contract_ledger_entries"
    __table_args__ = (
        UniqueConstraint(
            "contract_id",
            "year_month",
            name="uq_contract_ledger_entry_month",
        ),
    )

    entry_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    contract_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("contracts.contract_id"),
        nullable=False,
        index=True,
        comment="Contract ID.",
    )
    year_month: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        comment="Ledger period in YYYY-MM format.",
    )
    due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Due date.",
    )
    amount_due: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        nullable=False,
        comment="Amount due.",
    )
    currency_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="CNY",
    )
    is_tax_included: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    tax_rate: Mapped[Decimal | None] = mapped_column(
        DECIMAL(5, 4),
        nullable=True,
    )
    _payment_status: Mapped[str] = mapped_column(
        "payment_status",
        String(20),
        nullable=False,
        default="unpaid",
    )
    paid_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        nullable=False,
        default=Decimal("0"),
    )
    attributed_project_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("projects.id"),
        nullable=True,
        index=True,
        comment="Frozen project attribution captured when the ledger entry is generated.",
    )
    attributed_owner_party_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("parties.id"),
        nullable=True,
        index=True,
        comment="Frozen owner party attribution captured when the ledger entry is generated.",
    )
    attributed_operator_party_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("parties.id"),
        nullable=True,
        index=True,
        comment="Frozen operator party attribution captured when the ledger entry is generated.",
    )
    attributed_asset_ids: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Frozen asset IDs captured when the ledger entry is generated.",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    contract: Mapped["Contract"] = relationship(
        "Contract",
        back_populates="ledger_entries",
    )

    @hybrid_property
    def payment_status(self) -> str:
        return derive_ledger_payment_status(
            amount_due=self.amount_due,
            paid_amount=self.paid_amount,
            stored_status=self._payment_status,
        )

    @payment_status.inplace.setter
    def _set_payment_status(self, value: str) -> None:
        self._payment_status = value

    @payment_status.inplace.expression
    @classmethod
    def _payment_status_expr(cls) -> Any:
        return _ledger_payment_status_expression(cls)


class ServiceFeeLedger(Base):
    """Agency-mode service fee ledger."""

    __tablename__ = "service_fee_ledgers"
    __table_args__ = (
        UniqueConstraint(
            "source_ledger_id",
            name="uq_service_fee_ledger_source",
        ),
    )

    service_fee_entry_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    contract_group_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("contract_groups.contract_group_id"),
        nullable=False,
        index=True,
    )
    agency_contract_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("contracts.contract_id"),
        nullable=False,
        index=True,
    )
    source_ledger_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("contract_ledger_entries.entry_id"),
        nullable=False,
        unique=True,
        index=True,
    )
    year_month: Mapped[str] = mapped_column(String(7), nullable=False)
    amount_due: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        nullable=False,
        default=Decimal("0"),
    )
    _payment_status: Mapped[str] = mapped_column(
        "payment_status",
        String(20),
        nullable=False,
        default="unpaid",
    )
    currency_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="CNY",
    )
    service_fee_ratio: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 4),
        nullable=False,
    )
    attributed_project_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("projects.id"),
        nullable=True,
        index=True,
        comment="Frozen project attribution inherited from the source rent ledger.",
    )
    attributed_owner_party_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("parties.id"),
        nullable=True,
        index=True,
        comment="Frozen owner party attribution inherited from the source rent ledger.",
    )
    attributed_operator_party_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("parties.id"),
        nullable=True,
        index=True,
        comment="Frozen operator party attribution inherited from the source rent ledger.",
    )
    attributed_asset_ids: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Frozen asset IDs inherited from the source rent ledger.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    contract_group: Mapped["ContractGroup"] = relationship(
        "ContractGroup",
        back_populates="service_fee_ledgers",
    )
    agency_contract: Mapped["Contract"] = relationship(
        "Contract",
        back_populates="service_fee_ledgers",
    )
    source_ledger: Mapped["ContractLedgerEntry"] = relationship(
        "ContractLedgerEntry",
    )

    @hybrid_property
    def payment_status(self) -> str:
        return derive_ledger_payment_status(
            amount_due=self.amount_due,
            paid_amount=self.paid_amount,
            stored_status=self._payment_status,
        )

    @payment_status.inplace.setter
    def _set_payment_status(self, value: str) -> None:
        self._payment_status = value

    @payment_status.inplace.expression
    @classmethod
    def _payment_status_expr(cls) -> Any:
        return _ledger_payment_status_expression(cls)
