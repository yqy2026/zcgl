from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ContractSupplement(Base):
    __tablename__ = "contract_supplements"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_contract_supplements_version"),
        UniqueConstraint(
            "contract_kind",
            "contract_id",
            "agreement_number",
            name="uq_contract_supplements_number",
        ),
        CheckConstraint(
            "contract_kind IN ('upstream','terminal')",
            name="ck_contract_supplements_kind",
        ),
        CheckConstraint(
            "length(trim(agreement_number)) > 0 AND length(trim(title)) > 0",
            name="ck_contract_supplements_text",
        ),
        CheckConstraint(
            "(withdrawn_at IS NULL AND withdrawn_by IS NULL AND withdrawal_reason IS NULL) OR (withdrawn_at IS NOT NULL AND withdrawn_by IS NOT NULL AND withdrawal_reason IS NOT NULL AND length(trim(withdrawal_reason)) > 0)",
            name="ck_contract_supplements_withdrawal",
        ),
    )
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    contract_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    contract_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    agreement_number: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    signed_on: Mapped[date | None] = mapped_column(Date)
    created_by: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    withdrawn_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawal_reason: Mapped[str | None] = mapped_column(String(1000))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}
