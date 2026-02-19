"""create_party_tables

Revision ID: 20260219_create_party_tables
Revises: 20260219_enable_btree_gist_extension
Create Date: 2026-02-19 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260219_create_party_tables"
down_revision: str | None = "20260219_enable_btree_gist_extension"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create party domain tables and constraints."""
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "parties",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("party_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("external_ref", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("party_type", "code", name="uq_parties_party_type_code"),
    )
    op.create_index("ix_parties_party_type", "parties", ["party_type"], unique=False)
    op.create_index("ix_parties_code", "parties", ["code"], unique=False)

    op.create_table(
        "party_hierarchy",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("parent_party_id", sa.String(), nullable=False),
        sa.Column("child_party_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "parent_party_id <> child_party_id", name="ck_party_hierarchy_no_self_ref"
        ),
        sa.ForeignKeyConstraint(["child_party_id"], ["parties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_party_id"], ["parties.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "parent_party_id",
            "child_party_id",
            name="uq_party_hierarchy_parent_child",
        ),
    )
    op.create_index(
        "ix_party_hierarchy_parent_party_id",
        "party_hierarchy",
        ["parent_party_id"],
        unique=False,
    )
    op.create_index(
        "ix_party_hierarchy_child_party_id",
        "party_hierarchy",
        ["child_party_id"],
        unique=False,
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_party_hierarchy_prevent_cycle()
        RETURNS trigger AS $$
        DECLARE
            has_cycle boolean;
        BEGIN
            IF NEW.parent_party_id = NEW.child_party_id THEN
                RAISE EXCEPTION 'party_hierarchy self-cycle is not allowed';
            END IF;

            WITH RECURSIVE ascend AS (
                SELECT ph.parent_party_id, ph.child_party_id
                FROM party_hierarchy ph
                WHERE ph.child_party_id = NEW.parent_party_id
                  AND (TG_OP = 'INSERT' OR ph.id <> NEW.id)

                UNION ALL

                SELECT ph2.parent_party_id, ph2.child_party_id
                FROM party_hierarchy ph2
                JOIN ascend a ON ph2.child_party_id = a.parent_party_id
                WHERE (TG_OP = 'INSERT' OR ph2.id <> NEW.id)
            )
            SELECT EXISTS (
                SELECT 1 FROM ascend WHERE parent_party_id = NEW.child_party_id
            ) INTO has_cycle;

            IF has_cycle THEN
                RAISE EXCEPTION 'party_hierarchy cycle detected';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_party_hierarchy_prevent_cycle
        BEFORE INSERT OR UPDATE ON party_hierarchy
        FOR EACH ROW
        EXECUTE FUNCTION fn_party_hierarchy_prevent_cycle();
        """
    )

    op.create_table(
        "party_contacts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("party_id", sa.String(), nullable=False),
        sa.Column("contact_name", sa.String(length=100), nullable=False),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("position", sa.String(length=100), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["party_id"], ["parties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_party_contacts_party_id", "party_contacts", ["party_id"], unique=False)
    op.execute(
        """
        CREATE UNIQUE INDEX uq_party_contacts_primary_per_party
        ON party_contacts (party_id)
        WHERE is_primary = true;
        """
    )

    op.create_table(
        "party_role_defs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("role_code", sa.String(length=100), nullable=False),
        sa.Column("scope_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_code", "scope_type", name="uq_party_role_defs_code_scope"),
    )
    op.execute(
        """
        INSERT INTO party_role_defs (id, role_code, scope_type, description)
        VALUES
            (gen_random_uuid()::text, 'OWNER', 'global', '主体所有者角色'),
            (gen_random_uuid()::text, 'MANAGER', 'global', '主体管理者角色'),
            (gen_random_uuid()::text, 'HEADQUARTERS', 'global', '总部视角角色')
        ON CONFLICT (role_code, scope_type) DO NOTHING;
        """
    )

    op.create_table(
        "party_role_bindings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("party_id", sa.String(), nullable=False),
        sa.Column("role_def_id", sa.String(), nullable=False),
        sa.Column("scope_type", sa.String(length=50), nullable=False),
        sa.Column("scope_id", sa.String(), nullable=True),
        sa.Column(
            "valid_from",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("valid_to", sa.DateTime(), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_party_role_bindings_valid_range",
        ),
        sa.CheckConstraint(
            "(scope_type = 'global' AND scope_id IS NULL) OR "
            "(scope_type <> 'global' AND scope_id IS NOT NULL)",
            name="ck_party_role_bindings_scope_id",
        ),
        sa.ForeignKeyConstraint(["party_id"], ["parties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["role_def_id"], ["party_role_defs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_party_role_bindings_party_id", "party_role_bindings", ["party_id"], unique=False
    )
    op.create_index(
        "ix_party_role_bindings_role_def_id",
        "party_role_bindings",
        ["role_def_id"],
        unique=False,
    )

    op.execute(
        """
        ALTER TABLE party_role_bindings
        ADD CONSTRAINT ex_party_role_bindings_no_overlap
        EXCLUDE USING gist (
            party_id WITH =,
            role_def_id WITH =,
            scope_type WITH =,
            COALESCE(scope_id, '') WITH =,
            tsrange(valid_from, COALESCE(valid_to, 'infinity'::timestamp), '[]') WITH &&
        );
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_party_role_binding_scope_guard()
        RETURNS trigger AS $$
        DECLARE
            role_scope text;
        BEGIN
            SELECT prd.scope_type INTO role_scope
            FROM party_role_defs prd
            WHERE prd.id = NEW.role_def_id;

            IF role_scope IS NULL THEN
                RAISE EXCEPTION 'party_role_defs not found for role_def_id=%', NEW.role_def_id;
            END IF;

            IF NEW.scope_type <> role_scope THEN
                RAISE EXCEPTION 'scope_type mismatch: binding=% role_def=%', NEW.scope_type, role_scope;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_party_role_binding_scope_guard
        BEFORE INSERT OR UPDATE ON party_role_bindings
        FOR EACH ROW
        EXECUTE FUNCTION fn_party_role_binding_scope_guard();
        """
    )

    op.create_table(
        "user_party_bindings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("party_id", sa.String(), nullable=False),
        sa.Column("relation_type", sa.String(length=50), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "valid_from",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("valid_to", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_user_party_bindings_valid_range",
        ),
        sa.ForeignKeyConstraint(["party_id"], ["parties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_party_bindings_user_id", "user_party_bindings", ["user_id"], unique=False
    )
    op.create_index(
        "ix_user_party_bindings_party_id", "user_party_bindings", ["party_id"], unique=False
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_user_party_bindings_primary_per_relation
        ON user_party_bindings (user_id, relation_type)
        WHERE is_primary = true;
        """
    )
    op.execute(
        """
        ALTER TABLE user_party_bindings
        ADD CONSTRAINT ex_user_party_bindings_no_overlap
        EXCLUDE USING gist (
            user_id WITH =,
            party_id WITH =,
            relation_type WITH =,
            tsrange(valid_from, COALESCE(valid_to, 'infinity'::timestamp), '[]') WITH &&
        );
        """
    )


def downgrade() -> None:
    """Drop party domain tables and helper triggers."""
    op.execute(
        "DROP TRIGGER IF EXISTS trg_party_role_binding_scope_guard ON party_role_bindings"
    )
    op.execute("DROP FUNCTION IF EXISTS fn_party_role_binding_scope_guard()")

    op.drop_table("user_party_bindings")
    op.drop_table("party_role_bindings")
    op.drop_table("party_role_defs")

    op.drop_table("party_contacts")

    op.execute("DROP TRIGGER IF EXISTS trg_party_hierarchy_prevent_cycle ON party_hierarchy")
    op.execute("DROP FUNCTION IF EXISTS fn_party_hierarchy_prevent_cycle()")

    op.drop_table("party_hierarchy")

    op.drop_table("parties")
