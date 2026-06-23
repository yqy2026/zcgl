"""Cross-aggregate many-to-many association tables."""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Table

from ..database import Base

contract_group_assets = Table(
    "contract_group_assets",
    Base.metadata,
    Column(
        "contract_group_id",
        String,
        ForeignKey("contract_groups.contract_group_id"),
        primary_key=True,
    ),
    Column("asset_id", String, ForeignKey("assets.id"), primary_key=True),
    Column(
        "created_at",
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="Association created at.",
    ),
    comment="Contract group to asset many-to-many association.",
)

contract_assets = Table(
    "contract_assets",
    Base.metadata,
    Column(
        "contract_id",
        String,
        ForeignKey("contracts.contract_id"),
        primary_key=True,
    ),
    Column("asset_id", String, ForeignKey("assets.id"), primary_key=True),
    Column(
        "created_at",
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="Association created at.",
    ),
    comment="Contract to asset many-to-many association.",
)

contract_scan_document_links = Table(
    "contract_scan_document_links",
    Base.metadata,
    Column(
        "contract_id",
        String,
        ForeignKey("contracts.contract_id"),
        primary_key=True,
    ),
    Column(
        "document_id",
        String,
        ForeignKey("contract_scan_documents.document_id"),
        primary_key=True,
    ),
    Column(
        "created_at",
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="Shared scan link created at.",
    ),
    comment="Contract to shared stamped scan document links.",
)

property_cert_assets = Table(
    "property_cert_assets",
    Base.metadata,
    Column(
        "certificate_id",
        String,
        ForeignKey("property_certificates.id"),
        primary_key=True,
    ),
    Column("asset_id", String, ForeignKey("assets.id"), primary_key=True),
    Column(
        "link_type", String(50), comment="Relation type: primary/secondary/partial."
    ),
    Column("notes", String(500), comment="Relation notes."),
    comment="Property certificate to asset association.",
)


__all__ = [
    "contract_group_assets",
    "contract_assets",
    "contract_scan_document_links",
    "property_cert_assets",
]
