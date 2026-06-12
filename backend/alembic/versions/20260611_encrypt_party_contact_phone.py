"""encrypt existing PartyContact contact_phone values

Revision ID: 20260611_encrypt_party_contact_phone
Revises: 20260611_drop_property_certificate_is_verified
Create Date: 2026-06-11 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from src.crud.asset_support import SensitiveDataHandler

# revision identifiers, used by Alembic.
revision: str = "20260611_encrypt_party_contact_phone"
down_revision: str | None = "20260611_drop_property_certificate_is_verified"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    column_name: str,
) -> bool:
    if not inspector.has_table(table_name):
        return False
    return any(
        column["name"] == column_name for column in inspector.get_columns(table_name)
    )


def upgrade() -> None:
    """Backfill plaintext PartyContact phone values into deterministic ciphertext."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not (
        _column_exists(inspector, "party_contacts", "contact_phone")
        and _column_exists(inspector, "parties", "metadata")
    ):
        return

    handler = SensitiveDataHandler(searchable_fields={"contact_phone"})
    if not handler.encryption_enabled:
        raise RuntimeError(
            "DATA_ENCRYPTION_KEY is required to encrypt party_contacts.contact_phone"
        )

    bind.execute(
        sa.text(
            """
            INSERT INTO party_contacts (
                id,
                party_id,
                contact_name,
                contact_phone,
                is_primary,
                created_at,
                updated_at
            )
            SELECT
                gen_random_uuid()::text,
                p.id,
                COALESCE(NULLIF(BTRIM(p.metadata ->> 'contact_name'), ''), '主联系人'),
                NULLIF(BTRIM(p.metadata ->> 'contact_phone'), ''),
                true,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            FROM parties p
            WHERE p.metadata IS NOT NULL
              AND (
                  p.metadata ? 'contact_name'
                  OR p.metadata ? 'contact_phone'
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM party_contacts pc
                  WHERE pc.party_id = p.id
              )
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE parties
            SET metadata = metadata - 'contact_name' - 'contact_phone'
            WHERE metadata IS NOT NULL
              AND (
                  metadata ? 'contact_name'
                  OR metadata ? 'contact_phone'
              )
            """
        )
    )

    party_contacts = sa.table(
        "party_contacts",
        sa.column("id", sa.String),
        sa.column("contact_phone", sa.String),
    )
    rows = bind.execute(
        sa.select(party_contacts.c.id, party_contacts.c.contact_phone).where(
            party_contacts.c.contact_phone.is_not(None),
            party_contacts.c.contact_phone.not_like("enc:v%"),
        )
    ).mappings()

    for row in rows:
        encrypted_phone = handler.encrypt_field("contact_phone", row["contact_phone"])
        bind.execute(
            party_contacts.update()
            .where(party_contacts.c.id == row["id"])
            .values(contact_phone=encrypted_phone)
        )


def downgrade() -> None:
    """Encrypted contact phones are intentionally not downgraded to plaintext."""
    raise RuntimeError(
        "Downgrading 20260611_encrypt_party_contact_phone would expose PII plaintext"
    )
