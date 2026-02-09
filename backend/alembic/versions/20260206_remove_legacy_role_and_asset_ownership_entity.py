"""remove legacy users.role and assets.ownership_entity

Revision ID: 20260206_remove_legacy_role_and_asset_ownership_entity
Revises: 20260206_add_asset_search_index
Create Date: 2026-02-06 00:00:00.000000

"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260206_remove_legacy_role_and_asset_ownership_entity"
down_revision: str | None = "20260206_add_asset_search_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(conn: sa.Connection, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(conn)
    return any(
        col["name"] == column_name for col in inspector.get_columns(table_name)
    )


def upgrade() -> None:
    conn = op.get_bind()

    # Backfill assets.ownership_id from legacy assets.ownership_entity (name-based)
    if _column_exists(conn, "assets", "ownership_entity"):
        conn.execute(
            sa.text(
                """
                UPDATE assets AS a
                SET ownership_id = o.id
                FROM ownerships AS o
                WHERE a.ownership_id IS NULL
                  AND a.ownership_entity IS NOT NULL
                  AND a.ownership_entity != ''
                  AND o.name = a.ownership_entity
                """
            )
        )

    # Backfill RBAC assignments from users.role legacy column
    if _column_exists(conn, "users", "role"):
        roles = conn.execute(sa.text("SELECT id, name FROM roles")).fetchall()
        role_by_name = {row[1].lower(): row[0] for row in roles}
        admin_role_id = role_by_name.get("super_admin") or role_by_name.get("admin")
        user_role_id = (
            role_by_name.get("asset_viewer")
            or role_by_name.get("user")
            or role_by_name.get("viewer")
        )

        if admin_role_id or user_role_id:
            users = conn.execute(
                sa.text(
                    "SELECT id, role FROM users WHERE role IS NOT NULL AND role != ''"
                )
            ).fetchall()
            for user_id, legacy_role in users:
                if legacy_role is None:
                    continue
                role_value = str(legacy_role).strip().lower()
                target_role_id = None
                if role_value in {"admin", "super_admin", "superadmin"}:
                    target_role_id = admin_role_id
                elif role_value in {"user", "viewer", "asset_viewer"}:
                    target_role_id = user_role_id

                if not target_role_id:
                    continue

                exists = conn.execute(
                    sa.text(
                        """
                        SELECT 1 FROM user_role_assignments
                        WHERE user_id = :user_id AND role_id = :role_id
                        """
                    ),
                    {"user_id": user_id, "role_id": target_role_id},
                ).first()
                if exists:
                    continue

                conn.execute(
                    sa.text(
                        """
                        INSERT INTO user_role_assignments (
                            id,
                            user_id,
                            role_id,
                            assigned_by,
                            assigned_at,
                            is_active,
                            created_at,
                            updated_at
                        ) VALUES (
                            :id,
                            :user_id,
                            :role_id,
                            :assigned_by,
                            :assigned_at,
                            :is_active,
                            :created_at,
                            :updated_at
                        )
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "role_id": target_role_id,
                        "assigned_by": "migration",
                        "assigned_at": datetime.now(UTC).replace(tzinfo=None),
                        "is_active": True,
                        "created_at": datetime.now(UTC).replace(tzinfo=None),
                        "updated_at": datetime.now(UTC).replace(tzinfo=None),
                    },
                )

    # Clean up legacy search index entries
    conn.execute(
        sa.text(
            "DELETE FROM asset_search_index WHERE field_name = 'ownership_entity'"
        )
    )

    # Drop legacy indexes (if they exist)
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_assets_ownership_entity_trgm"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_assets_ownership_entity"))
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_assets_ownership_entity"))

    # Drop legacy columns
    if _column_exists(conn, "assets", "ownership_entity"):
        with op.batch_alter_table("assets") as batch_op:
            batch_op.drop_column("ownership_entity")

    if _column_exists(conn, "users", "role"):
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("role")


def downgrade() -> None:
    conn = op.get_bind()

    # Recreate users.role column
    if not _column_exists(conn, "users", "role"):
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "role",
                    sa.String(length=20),
                    nullable=False,
                    server_default="user",
                    comment="用户角色",
                )
            )

    # Recreate assets.ownership_entity column
    if not _column_exists(conn, "assets", "ownership_entity"):
        with op.batch_alter_table("assets") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "ownership_entity",
                    sa.String(length=200),
                    nullable=True,
                    comment="权属方",
                )
            )

    # Backfill ownership_entity using ownership_id when possible
    conn.execute(
        sa.text(
            """
            UPDATE assets AS a
            SET ownership_entity = o.name
            FROM ownerships AS o
            WHERE a.ownership_id = o.id
            """
        )
    )

    # Recreate legacy index for assets.ownership_entity (if desired)
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_assets_ownership_entity ON assets (ownership_entity)"
        )
    )
