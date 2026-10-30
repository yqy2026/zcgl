"""Explicit deferral decisions, separate from projected and confirmed lines."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ManagementFeeDeferral(Base):
    __tablename__ = "management_fee_deferrals"
    __table_args__ = (
        UniqueConstraint(
            "statement_id",
            "rent_ledger_entry_id",
            name="uq_management_fee_deferrals_statement_entry",
        ),
        CheckConstraint(
            "length(trim(reason)) > 0", name="ck_management_fee_deferrals_reason"
        ),
    )
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    statement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("management_fee_statements.id"), nullable=False
    )
    rent_ledger_entry_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rent_ledger_entries.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
