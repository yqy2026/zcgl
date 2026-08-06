"""Cut over the Organization, Party, and explicit scope storage model.

Revision ID: 20260804_organization_party_scope_model_cutover
Revises: 20260722_drop_legacy_document_and_prompt_schema
Create Date: 2026-08-04

This migration is destructive and intentionally irreversible. Stop every old
application process and pass the Organization/Party preflight before upgrade.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260804_organization_party_scope_model_cutover"
down_revision: str | Sequence[str] | None = (
    "20260722_drop_legacy_document_and_prompt_schema"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_PRECONDITIONS: tuple[tuple[str, str, str], ...] = (
    (
        "legacy_organization_parties",
        "organization Party rows must be manually reclassified or removed",
        """
        SELECT COUNT(*) /* gate:legacy_organization_parties */
        FROM parties
        WHERE party_type = 'organization'
        """,
    ),
    (
        "party_hierarchy_rows",
        "PartyHierarchy must be empty before its model is removed",
        """
        SELECT COUNT(*) /* gate:party_hierarchy_rows */
        FROM party_hierarchy
        """,
    ),
    (
        "headquarters_bindings",
        "headquarters bindings must be manually replaced or removed",
        """
        SELECT COUNT(*) /* gate:headquarters_bindings */
        FROM user_party_bindings
        WHERE relation_type = 'headquarters'
        """,
    ),
    (
        "invalid_binding_relations",
        "binding relations must contain only owner or manager",
        """
        SELECT COUNT(*) /* gate:invalid_binding_relations */
        FROM user_party_bindings
        WHERE relation_type NOT IN ('owner', 'manager')
        """,
    ),
    (
        "users_without_organization",
        "every existing account must be explicitly classified as a human account "
        "by assigning an organization before cutover",
        """
        SELECT COUNT(*) /* gate:users_without_organization */
        FROM users
        WHERE default_organization_id IS NULL
        """,
    ),
    (
        "invalid_user_organization_chain",
        "every user organization chain must be active, undeleted, and acyclic",
        """
        WITH RECURSIVE organization_chain AS (
            SELECT
                u.id AS user_id,
                o.id AS organization_id,
                o.parent_id,
                o.status,
                o.is_deleted,
                ARRAY[o.id]::text[] AS visited,
                false AS cycle
            FROM users AS u
            JOIN organizations AS o ON o.id = u.default_organization_id

            UNION ALL

            SELECT
                chain.user_id,
                parent.id,
                parent.parent_id,
                parent.status,
                parent.is_deleted,
                chain.visited || parent.id,
                parent.id = ANY(chain.visited)
            FROM organization_chain AS chain
            JOIN organizations AS parent ON parent.id = chain.parent_id
            WHERE NOT chain.cycle
        )
        SELECT COUNT(DISTINCT user_id) /* gate:invalid_user_organization_chain */
        FROM organization_chain
        WHERE status <> 'active' OR is_deleted OR cycle
        """,
    ),
    (
        "invalid_party_codes",
        "every Party code must be globally unique and match its target LE/NP format",
        """
        SELECT COUNT(*) /* gate:invalid_party_codes */
        FROM parties AS party
        WHERE party.party_type NOT IN ('legal_entity', 'individual')
           OR (party.party_type = 'legal_entity'
               AND party.code !~ '^LE-[0-9]{6}$')
           OR (party.party_type = 'individual'
               AND party.code !~ '^NP-[0-9]{6}$')
           OR EXISTS (
               SELECT 1
               FROM parties AS duplicate
               WHERE duplicate.code = party.code
                 AND duplicate.id <> party.id
           )
        """,
    ),
    (
        "duplicate_organization_codes",
        "Organization code values must be unique before cutover",
        """
        SELECT COUNT(*) /* gate:duplicate_organization_codes */
        FROM (
            SELECT code
            FROM organizations
            GROUP BY code
            HAVING COUNT(*) > 1
        ) AS duplicate_codes
        """,
    ),
    (
        "invalid_party_statuses",
        "Party status must contain only active or inactive",
        """
        SELECT COUNT(*) /* gate:invalid_party_statuses */
        FROM parties
        WHERE status NOT IN ('active', 'inactive')
        """,
    ),
    (
        "invalid_metadata_shape",
        "Party metadata must be a JSON object or null before cutover",
        """
        SELECT COUNT(*) /* gate:invalid_metadata_shape */
        FROM parties
        WHERE metadata IS NOT NULL
          AND jsonb_typeof(metadata) <> 'object'
        """,
    ),
    (
        "invalid_metadata_identifiers",
        "metadata identifier values must be complete, supported legal identifiers, "
        "and unique after normalization",
        """
        WITH source AS (
            SELECT
                id,
                party_type,
                metadata ? 'identifier_type' AS has_type,
                metadata ? 'identifier_value' AS has_value,
                metadata ->> 'identifier_type' AS identifier_type,
                upper(
                    regexp_replace(
                        btrim(metadata ->> 'identifier_value'),
                        '[[:space:]-]+',
                        '',
                        'g'
                    )
                ) AS normalized_value
            FROM parties
        ),
        invalid AS (
            SELECT id
            FROM source
            WHERE has_type <> has_value
               OR (
                    has_type
                    AND (
                        party_type <> 'legal_entity'
                        OR identifier_type IS NULL
                        OR identifier_type NOT IN (
                            'unified_social_credit_code',
                            'legal_registration_number',
                            'foreign_registration_number'
                        )
                        OR normalized_value IS NULL
                        OR normalized_value = ''
                    )
               )

            UNION

            SELECT source.id
            FROM source
            JOIN source AS duplicate
              ON duplicate.id <> source.id
             AND duplicate.has_type
             AND source.has_type
             AND duplicate.identifier_type = source.identifier_type
             AND duplicate.normalized_value = source.normalized_value
        )
        SELECT COUNT(*) /* gate:invalid_metadata_identifiers */
        FROM invalid
        """,
    ),
)


def _assert_preconditions(bind: sa.engine.Connection) -> None:
    for _gate_name, failure_message, query in _PRECONDITIONS:
        violation_count = int(bind.execute(sa.text(query)).scalar_one())
        if violation_count != 0:
            raise RuntimeError(
                f"ADR-0022 model cutover blocked: {failure_message}; "
                f"violations={violation_count}"
            )


def _add_party_contract(bind: sa.engine.Connection) -> None:
    op.add_column(
        "parties", sa.Column("identifier_type", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "parties", sa.Column("identifier_value", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "parties",
        sa.Column("identifier_fingerprint", sa.String(length=64), nullable=True),
    )
    bind.execute(
        sa.text(
            """
            UPDATE parties
            SET identifier_type = metadata ->> 'identifier_type',
                identifier_value = upper(
                    regexp_replace(
                        btrim(metadata ->> 'identifier_value'),
                        '[[:space:]-]+',
                        '',
                        'g'
                    )
                ),
                metadata = NULLIF(
                    metadata - 'identifier_type' - 'identifier_value'
                        - 'unified_identifier',
                    '{}'::jsonb
                )
            WHERE metadata ? 'identifier_type'
              AND metadata ? 'identifier_value'
            """
        )
    )

    op.drop_constraint("uq_parties_party_type_code", "parties", type_="unique")
    op.drop_index("ix_parties_code", table_name="parties")
    op.create_unique_constraint("uq_parties_code", "parties", ["code"])
    op.create_check_constraint(
        "ck_parties_party_type",
        "parties",
        "party_type IN ('legal_entity', 'individual')",
    )
    op.create_check_constraint(
        "ck_parties_status",
        "parties",
        "status IN ('active', 'inactive')",
    )
    op.create_check_constraint(
        "ck_parties_metadata_object",
        "parties",
        "metadata IS NULL OR jsonb_typeof(metadata) = 'object'",
    )
    op.create_check_constraint(
        "ck_parties_code_format",
        "parties",
        "(party_type = 'legal_entity' AND code ~ '^LE-[0-9]{6}$') OR "
        "(party_type = 'individual' AND code ~ '^NP-[0-9]{6}$')",
    )
    op.create_check_constraint(
        "ck_parties_identifier_pair",
        "parties",
        "(identifier_type IS NULL AND identifier_value IS NULL) OR "
        "(identifier_type IS NOT NULL AND identifier_value IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_parties_identifier_type",
        "parties",
        "identifier_type IS NULL OR "
        "(party_type = 'legal_entity' AND identifier_type IN "
        "('unified_social_credit_code', 'legal_registration_number', "
        "'foreign_registration_number')) OR "
        "(party_type = 'individual' AND identifier_type IN "
        "('national_id', 'passport'))",
    )
    op.create_check_constraint(
        "ck_parties_identifier_fingerprint",
        "parties",
        "(identifier_type IS NULL AND identifier_fingerprint IS NULL) OR "
        "(identifier_type IS NOT NULL AND party_type = 'legal_entity' AND "
        "identifier_fingerprint IS NULL) OR "
        "(identifier_type IS NOT NULL AND party_type = 'individual' AND "
        "identifier_fingerprint IS NOT NULL)",
    )
    op.create_index(
        "uq_parties_legal_identifier",
        "parties",
        ["identifier_type", "identifier_value"],
        unique=True,
        postgresql_where=sa.text(
            "party_type = 'legal_entity' AND identifier_type IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_parties_individual_identifier_fingerprint",
        "parties",
        ["identifier_type", "identifier_fingerprint"],
        unique=True,
        postgresql_where=sa.text(
            "party_type = 'individual' AND identifier_type IS NOT NULL"
        ),
    )


def _remove_party_hierarchy(bind: sa.engine.Connection) -> None:
    bind.execute(
        sa.text(
            "DROP TRIGGER IF EXISTS trg_party_hierarchy_prevent_cycle "
            "ON party_hierarchy"
        )
    )
    bind.execute(sa.text("DROP FUNCTION IF EXISTS fn_party_hierarchy_prevent_cycle()"))
    op.drop_table("party_hierarchy")


def _add_organization_party_contract() -> None:
    op.create_unique_constraint(
        "uq_organizations_code", "organizations", ["code"]
    )
    op.add_column(
        "organizations",
        sa.Column("represented_party_id", sa.String(), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("represented_party_perspective", sa.String(length=20), nullable=True),
    )
    op.create_foreign_key(
        "fk_organizations_represented_party_id_parties",
        "organizations",
        "parties",
        ["represented_party_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_organizations_represented_party_id",
        "organizations",
        ["represented_party_id"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_organizations_represented_party_pair",
        "organizations",
        "(represented_party_id IS NULL AND "
        "represented_party_perspective IS NULL) OR "
        "(represented_party_id IS NOT NULL AND "
        "represented_party_perspective IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_organizations_represented_party_perspective",
        "organizations",
        "represented_party_perspective IS NULL OR "
        "represented_party_perspective IN ('owner', 'manager')",
    )


def _cut_over_user_accounts(bind: sa.engine.Connection) -> None:
    op.alter_column(
        "users",
        "default_organization_id",
        new_column_name="organization_id",
        existing_type=sa.String(),
        existing_nullable=True,
    )
    op.add_column(
        "users", sa.Column("account_type", sa.String(length=20), nullable=True)
    )
    bind.execute(sa.text("UPDATE users SET account_type = 'human'"))
    op.alter_column(
        "users",
        "account_type",
        existing_type=sa.String(length=20),
        nullable=False,
    )
    op.create_check_constraint(
        "ck_users_account_type",
        "users",
        "account_type IN ('human', 'service', 'system')",
    )
    op.create_check_constraint(
        "ck_users_account_organization",
        "users",
        "(account_type = 'human' AND "
        "(is_active = false OR organization_id IS NOT NULL)) OR "
        "(account_type IN ('service', 'system') AND organization_id IS NULL)",
    )


def _cut_over_user_party_bindings() -> None:
    op.drop_index(
        "uq_user_party_bindings_primary_per_relation",
        table_name="user_party_bindings",
    )
    op.drop_column("user_party_bindings", "is_primary")
    op.create_check_constraint(
        "ck_user_party_bindings_relation_type",
        "user_party_bindings",
        "relation_type IN ('owner', 'manager')",
    )


def upgrade() -> None:
    """Apply the cutover only after every source-data ambiguity is resolved."""

    bind = op.get_bind()
    _assert_preconditions(bind)
    _add_party_contract(bind)
    _remove_party_hierarchy(bind)
    _add_organization_party_contract()
    _cut_over_user_accounts(bind)
    _cut_over_user_party_bindings()


def downgrade() -> None:
    raise RuntimeError("ADR-0022 Organization/Party model cutover is irreversible")
