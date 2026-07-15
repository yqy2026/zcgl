"""Generic attachment metadata shared by business objects."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Attachment(Base):
    """Stored file metadata with an explicit owning business object."""

    __tablename__ = "attachments"
    __table_args__ = (
        CheckConstraint(
            "owner_type IN ('asset', 'contract', 'property_certificate', 'payment_flow')",
            name="ck_attachment_owner_type",
        ),
        CheckConstraint(
            "file_type IN ('pdf', 'jpg', 'jpeg', 'png')",
            name="ck_attachment_file_type",
        ),
        CheckConstraint(
            "file_size >= 0 AND file_size <= 20971520",
            name="ck_attachment_file_size",
        ),
        Index("ix_attachments_owner", "owner_type", "owner_id"),
    )

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    owner_type: Mapped[str] = mapped_column(String(40), nullable=False)
    owner_id: Mapped[str] = mapped_column(String, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
    )
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
