"""simplify organization schema and remove employee-position tables

Revision ID: 20260208_simplify_organization_schema
Revises: 20260207_add_asset_cached_occupancy_rate
Create Date: 2026-02-08 18:40:00.000000
"""

import uuid
from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260208_simplify_organization_schema"
down_revision: str | None = "20260207_add_asset_cached_occupancy_rate"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ORGANIZATION_REMOVED_COLUMNS = [
    "phone",
    "email",
    "address",
    "leader_name",
    "leader_phone",
    "leader_email",
    "functions",
]

ORGANIZATION_ENUMS: dict[str, dict[str, object]] = {
    "organization_type": {
        "name": "组织类型",
        "category": "系统管理",
        "description": "组织架构类型分类",
        "values": [
            {"value": "company", "label": "公司", "sort_order": 1},
            {"value": "group", "label": "集团", "sort_order": 2},
            {"value": "division", "label": "事业部", "sort_order": 3},
            {"value": "department", "label": "部门", "sort_order": 4},
            {"value": "team", "label": "团队", "sort_order": 5},
            {"value": "branch", "label": "分公司", "sort_order": 6},
            {"value": "office", "label": "办事处", "sort_order": 7},
        ],
    },
    "organization_status": {
        "name": "组织状态",
        "category": "系统管理",
        "description": "组织架构状态分类",
        "values": [
            {"value": "active", "label": "活跃", "sort_order": 1},
            {"value": "inactive", "label": "停用", "sort_order": 2},
            {"value": "suspended", "label": "暂停", "sort_order": 3},
        ],
    },
}


def _table_exists(conn: sa.Connection, table_name: str) -> bool:
    return sa.inspect(conn).has_table(table_name)


def _column_exists(conn: sa.Connection, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(conn)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _drop_fk_constraints_for_column(
    conn: sa.Connection, table_name: str, column_name: str
) -> None:
    inspector = sa.inspect(conn)
    for fk in inspector.get_foreign_keys(table_name):
        constrained_columns = fk.get("constrained_columns") or []
        fk_name = fk.get("name")
        if column_name in constrained_columns and fk_name:
            op.drop_constraint(fk_name, table_name, type_="foreignkey")


def _upsert_enum_type(
    conn: sa.Connection,
    *,
    code: str,
    name: str,
    category: str,
    description: str,
) -> str:
    now = datetime.utcnow()
    existing = conn.execute(
        sa.text("SELECT id FROM enum_field_types WHERE code = :code"),
        {"code": code},
    ).first()

    if existing:
        enum_type_id = str(existing[0])
        conn.execute(
            sa.text(
                """
                UPDATE enum_field_types
                SET name = :name,
                    category = :category,
                    description = :description,
                    is_system = :is_system,
                    is_multiple = :is_multiple,
                    is_hierarchical = :is_hierarchical,
                    status = :status,
                    is_deleted = :is_deleted,
                    updated_at = :updated_at,
                    updated_by = :updated_by
                WHERE id = :id
                """
            ),
            {
                "id": enum_type_id,
                "name": name,
                "category": category,
                "description": description,
                "is_system": True,
                "is_multiple": False,
                "is_hierarchical": False,
                "status": "active",
                "is_deleted": False,
                "updated_at": now,
                "updated_by": "migration",
            },
        )
        return enum_type_id

    enum_type_id = str(uuid.uuid4())
    conn.execute(
        sa.text(
            """
            INSERT INTO enum_field_types (
                id, name, code, category, description,
                is_system, is_multiple, is_hierarchical,
                default_value, validation_rules, display_config,
                status, is_deleted, created_at, updated_at, created_by, updated_by
            ) VALUES (
                :id, :name, :code, :category, :description,
                :is_system, :is_multiple, :is_hierarchical,
                :default_value, :validation_rules, :display_config,
                :status, :is_deleted, :created_at, :updated_at, :created_by, :updated_by
            )
            """
        ),
        {
            "id": enum_type_id,
            "name": name,
            "code": code,
            "category": category,
            "description": description,
            "is_system": True,
            "is_multiple": False,
            "is_hierarchical": False,
            "default_value": None,
            "validation_rules": None,
            "display_config": None,
            "status": "active",
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
            "created_by": "migration",
            "updated_by": "migration",
        },
    )
    return enum_type_id


def _upsert_enum_value(
    conn: sa.Connection,
    *,
    enum_type_id: str,
    value: str,
    label: str,
    sort_order: int,
) -> None:
    now = datetime.utcnow()
    existing = conn.execute(
        sa.text(
            """
            SELECT id
            FROM enum_field_values
            WHERE enum_type_id = :enum_type_id AND value = :value
            """
        ),
        {"enum_type_id": enum_type_id, "value": value},
    ).first()

    if existing:
        conn.execute(
            sa.text(
                """
                UPDATE enum_field_values
                SET label = :label,
                    code = :code,
                    sort_order = :sort_order,
                    is_active = :is_active,
                    is_deleted = :is_deleted,
                    updated_at = :updated_at,
                    updated_by = :updated_by
                WHERE id = :id
                """
            ),
            {
                "id": str(existing[0]),
                "label": label,
                "code": value,
                "sort_order": sort_order,
                "is_active": True,
                "is_deleted": False,
                "updated_at": now,
                "updated_by": "migration",
            },
        )
        return

    conn.execute(
        sa.text(
            """
            INSERT INTO enum_field_values (
                id, enum_type_id, label, value, code, description,
                parent_id, level, path, sort_order, color, icon, extra_properties,
                is_active, is_default, is_deleted,
                created_at, updated_at, created_by, updated_by
            ) VALUES (
                :id, :enum_type_id, :label, :value, :code, :description,
                :parent_id, :level, :path, :sort_order, :color, :icon, :extra_properties,
                :is_active, :is_default, :is_deleted,
                :created_at, :updated_at, :created_by, :updated_by
            )
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "enum_type_id": enum_type_id,
            "label": label,
            "value": value,
            "code": value,
            "description": None,
            "parent_id": None,
            "level": 1,
            "path": None,
            "sort_order": sort_order,
            "color": None,
            "icon": None,
            "extra_properties": None,
            "is_active": True,
            "is_default": False,
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
            "created_by": "migration",
            "updated_by": "migration",
        },
    )


def _seed_organization_enums(conn: sa.Connection) -> None:
    if not _table_exists(conn, "enum_field_types") or not _table_exists(
        conn, "enum_field_values"
    ):
        return

    for enum_code, enum_config in ORGANIZATION_ENUMS.items():
        enum_type_id = _upsert_enum_type(
            conn,
            code=enum_code,
            name=str(enum_config["name"]),
            category=str(enum_config["category"]),
            description=str(enum_config["description"]),
        )
        values = enum_config.get("values", [])
        if not isinstance(values, list):
            continue
        for value_item in values:
            if not isinstance(value_item, dict):
                continue
            _upsert_enum_value(
                conn,
                enum_type_id=enum_type_id,
                value=str(value_item["value"]),
                label=str(value_item["label"]),
                sort_order=int(value_item["sort_order"]),
            )


def upgrade() -> None:
    conn = op.get_bind()

    if _table_exists(conn, "users") and _column_exists(conn, "users", "employee_id"):
        _drop_fk_constraints_for_column(conn, "users", "employee_id")
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("employee_id")

    if _table_exists(conn, "employees"):
        op.drop_table("employees")

    if _table_exists(conn, "positions"):
        op.drop_table("positions")

    if _table_exists(conn, "organizations"):
        columns_to_drop = [
            column
            for column in ORGANIZATION_REMOVED_COLUMNS
            if _column_exists(conn, "organizations", column)
        ]
        if columns_to_drop:
            with op.batch_alter_table("organizations") as batch_op:
                for column in columns_to_drop:
                    batch_op.drop_column(column)

    _seed_organization_enums(conn)


def downgrade() -> None:
    conn = op.get_bind()

    if _table_exists(conn, "organizations"):
        with op.batch_alter_table("organizations") as batch_op:
            if not _column_exists(conn, "organizations", "phone"):
                batch_op.add_column(sa.Column("phone", sa.String(20), nullable=True))
            if not _column_exists(conn, "organizations", "email"):
                batch_op.add_column(sa.Column("email", sa.String(100), nullable=True))
            if not _column_exists(conn, "organizations", "address"):
                batch_op.add_column(sa.Column("address", sa.String(200), nullable=True))
            if not _column_exists(conn, "organizations", "leader_name"):
                batch_op.add_column(
                    sa.Column("leader_name", sa.String(50), nullable=True)
                )
            if not _column_exists(conn, "organizations", "leader_phone"):
                batch_op.add_column(
                    sa.Column("leader_phone", sa.String(20), nullable=True)
                )
            if not _column_exists(conn, "organizations", "leader_email"):
                batch_op.add_column(
                    sa.Column("leader_email", sa.String(100), nullable=True)
                )
            if not _column_exists(conn, "organizations", "functions"):
                batch_op.add_column(sa.Column("functions", sa.Text(), nullable=True))

    if not _table_exists(conn, "positions"):
        op.create_table(
            "positions",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("level", sa.Integer(), nullable=False),
            sa.Column("category", sa.String(50), nullable=True),
            sa.Column(
                "organization_id",
                sa.String(),
                sa.ForeignKey("organizations.id"),
                nullable=False,
            ),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("responsibilities", sa.Text(), nullable=True),
            sa.Column("requirements", sa.Text(), nullable=True),
            sa.Column("salary_min", sa.Integer(), nullable=True),
            sa.Column("salary_max", sa.Integer(), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.String(100), nullable=True),
            sa.Column("updated_by", sa.String(100), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists(conn, "employees"):
        op.create_table(
            "employees",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("employee_no", sa.String(50), nullable=False, unique=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("gender", sa.String(10), nullable=True),
            sa.Column("birth_date", sa.DateTime(), nullable=True),
            sa.Column("id_card", sa.String(20), nullable=True),
            sa.Column("emergency_contact", sa.String(100), nullable=True),
            sa.Column("emergency_phone", sa.String(20), nullable=True),
            sa.Column(
                "organization_id",
                sa.String(),
                sa.ForeignKey("organizations.id"),
                nullable=False,
            ),
            sa.Column(
                "position_id",
                sa.String(),
                sa.ForeignKey("positions.id"),
                nullable=True,
            ),
            sa.Column(
                "direct_supervisor_id",
                sa.String(),
                sa.ForeignKey("employees.id"),
                nullable=True,
            ),
            sa.Column("hire_date", sa.DateTime(), nullable=True),
            sa.Column("probation_end_date", sa.DateTime(), nullable=True),
            sa.Column("employment_type", sa.String(20), nullable=True),
            sa.Column("work_location", sa.String(200), nullable=True),
            sa.Column("base_salary", sa.Integer(), nullable=True),
            sa.Column("performance_salary", sa.Integer(), nullable=True),
            sa.Column("total_salary", sa.Integer(), nullable=True),
            sa.Column("resignation_date", sa.DateTime(), nullable=True),
            sa.Column("resignation_reason", sa.Text(), nullable=True),
            sa.Column("education", sa.String(50), nullable=True),
            sa.Column("major", sa.String(100), nullable=True),
            sa.Column("skills", sa.Text(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.String(100), nullable=True),
            sa.Column("updated_by", sa.String(100), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if _table_exists(conn, "users") and not _column_exists(conn, "users", "employee_id"):
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "employee_id",
                    sa.String(),
                    sa.ForeignKey("employees.id"),
                    nullable=True,
                )
            )
