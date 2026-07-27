"""drop retired document, Prompt, and certificate attachment schema

Revision ID: 20260722_drop_legacy_document_and_prompt_schema
Revises: 20260714_asset_manager_party_nullable
Create Date: 2026-07-22

This migration is destructive. Stop all old application processes before upgrade.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260722_drop_legacy_document_and_prompt_schema"
down_revision: str | Sequence[str] | None = "20260714_asset_manager_party_nullable"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove schema owned only by retired document extraction paths."""
    op.execute(
        sa.text(
            "DELETE FROM permission_grants WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE resource = 'llm_prompt')"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM resource_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE resource = 'llm_prompt')"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE resource = 'llm_prompt')"
        )
    )
    op.execute(
        sa.text("DELETE FROM abac_policy_rules WHERE resource_type = 'llm_prompt'")
    )
    op.execute(sa.text("DELETE FROM permissions WHERE resource = 'llm_prompt'"))

    op.drop_table("property_certificate_attachments")
    op.drop_table("pdf_import_session_logs")
    op.drop_table("pdf_import_configurations")
    op.drop_table("pdf_import_sessions")
    op.drop_table("extraction_feedback")
    op.drop_table("prompt_metrics")
    op.drop_constraint(
        "fk_prompt_templates_current_version",
        "prompt_templates",
        type_="foreignkey",
    )
    op.drop_table("prompt_versions")
    op.drop_table("prompt_templates")
    op.drop_column("property_certificates", "extraction_confidence")
    op.drop_column("property_certificates", "extraction_source")


def downgrade() -> None:
    raise RuntimeError("legacy document schema removal is irreversible")
