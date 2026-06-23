"""contract number per project and shared scan documents

Revision ID: 20260620_contract_number_project_scan_documents
Revises: 20260619_drop_contract_review_workflow
Create Date: 2026-06-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260620_contract_number_project_scan_documents"
down_revision: str | Sequence[str] | None = "20260619_drop_contract_review_workflow"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_has_column(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    column_name: str,
) -> bool:
    if not inspector.has_table(table_name):
        return False
    return any(
        column["name"] == column_name for column in inspector.get_columns(table_name)
    )


def _index_exists(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    index_name: str,
) -> bool:
    if not inspector.has_table(table_name):
        return False
    return any(
        index["name"] == index_name for index in inspector.get_indexes(table_name)
    )


def _unique_constraint_exists(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    constraint_name: str,
) -> bool:
    if not inspector.has_table(table_name):
        return False
    return any(
        constraint["name"] == constraint_name
        for constraint in inspector.get_unique_constraints(table_name)
    )


def _check_constraint_exists(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    constraint_name: str,
) -> bool:
    if not inspector.has_table(table_name):
        return False
    return any(
        constraint["name"] == constraint_name
        for constraint in inspector.get_check_constraints(table_name)
    )


def _drop_unique_contract_number_index_if_present(
    inspector: sa.engine.reflection.Inspector,
) -> None:
    if _index_exists(inspector, "contracts", "ix_contracts_contract_number"):
        op.drop_index("ix_contracts_contract_number", table_name="contracts")


def _assert_no_project_contract_number_conflicts() -> None:
    bind = op.get_bind()
    conflict = bind.execute(
        sa.text(
            """
            SELECT contract_number, project_id, COUNT(*) AS duplicate_count
            FROM contracts
            WHERE project_id IS NOT NULL
            GROUP BY contract_number, project_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if conflict is None:
        return
    contract_number, project_id, duplicate_count = conflict
    raise RuntimeError(
        "Duplicate contract_number within project blocks migration: "
        f"contract_number={contract_number}, project_id={project_id}, "
        f"count={duplicate_count}"
    )


def _assert_no_active_contract_missing_project_id() -> None:
    bind = op.get_bind()
    missing_contract = bind.execute(
        sa.text(
            """
            SELECT contract_id, contract_number
            FROM contracts
            WHERE data_status = '正常'
              AND project_id IS NULL
            LIMIT 1
            """
        )
    ).first()
    if missing_contract is None:
        return
    contract_id, contract_number = missing_contract
    raise RuntimeError(
        "Active contract without project_id blocks migration: "
        f"contract_id={contract_id}, contract_number={contract_number}"
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_has_column(inspector, "contracts", "project_id"):
        op.add_column(
            "contracts",
            sa.Column(
                "project_id",
                sa.String(),
                sa.ForeignKey("projects.id"),
                nullable=True,
                comment="Frozen project ID for per-project contract number uniqueness.",
            ),
        )
        op.create_index("ix_contracts_project_id", "contracts", ["project_id"])

    bind.execute(
        sa.text(
            """
            UPDATE contracts AS c
            SET project_id = cg.project_id
            FROM contract_groups AS cg
            WHERE c.contract_group_id = cg.contract_group_id
              AND c.project_id IS NULL
            """
        )
    )

    _assert_no_active_contract_missing_project_id()
    _assert_no_project_contract_number_conflicts()
    inspector = sa.inspect(bind)
    _drop_unique_contract_number_index_if_present(inspector)

    if not _unique_constraint_exists(
        inspector,
        "contracts",
        "uq_contract_number_project",
    ):
        op.create_unique_constraint(
            "uq_contract_number_project",
            "contracts",
            ["contract_number", "project_id"],
        )

    if not _check_constraint_exists(
        inspector,
        "contracts",
        "ck_contracts_active_project_id_required",
    ):
        op.create_check_constraint(
            "ck_contracts_active_project_id_required",
            "contracts",
            "data_status <> '正常' OR project_id IS NOT NULL",
        )

    if not inspector.has_table("contract_scan_documents"):
        op.create_table(
            "contract_scan_documents",
            sa.Column("document_id", sa.String(), primary_key=True),
            sa.Column(
                "storage_key",
                sa.String(length=300),
                nullable=False,
                comment="Stable storage key or file path for the stamped scan.",
            ),
            sa.Column("original_filename", sa.String(length=255), nullable=False),
            sa.Column("content_type", sa.String(length=100), nullable=True),
            sa.Column("file_size", sa.Integer(), nullable=True),
            sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
            sa.Column(
                "data_status",
                sa.String(length=20),
                nullable=False,
                server_default="正常",
                comment="Data status.",
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.String(length=100), nullable=True),
            sa.Column("updated_by", sa.String(length=100), nullable=True),
            sa.UniqueConstraint("storage_key", name="uq_contract_scan_storage_key"),
        )
        op.create_index(
            "ix_contract_scan_documents_storage_key",
            "contract_scan_documents",
            ["storage_key"],
        )
        op.create_index(
            "ix_contract_scan_documents_checksum_sha256",
            "contract_scan_documents",
            ["checksum_sha256"],
        )

    if not inspector.has_table("contract_scan_document_links"):
        op.create_table(
            "contract_scan_document_links",
            sa.Column(
                "contract_id",
                sa.String(),
                sa.ForeignKey("contracts.contract_id"),
                primary_key=True,
            ),
            sa.Column(
                "document_id",
                sa.String(),
                sa.ForeignKey("contract_scan_documents.document_id"),
                primary_key=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=True,
                comment="Shared scan link created at.",
            ),
        )


def downgrade() -> None:
    raise RuntimeError(
        "contract number project uniqueness and shared scan documents are not downgraded"
    )
