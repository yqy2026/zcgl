"""Initial schema creation

Revision ID: e4c9e4968dd7
Revises:
Create Date: 2026-01-17 11:05:39.118899

This migration creates ALL tables for the ZCGL asset management system.
Tables are created in dependency order to respect foreign key constraints.

Historical note:
This initial snapshot included legacy `tenant_id` columns for early
multi-tenant experiments. These columns were later removed by
`20260130_drop_tenant_id_columns` and are not part of current runtime
authorization semantics.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4c9e4968dd7"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all tables for the ZCGL system."""

    # ==================== TIER 1: Base Tables (No FK Dependencies) ====================

    # organizations - 组织架构表
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False, comment="组织名称"),
        sa.Column("code", sa.String(50), nullable=False, comment="组织编码"),
        sa.Column("level", sa.Integer(), nullable=False, default=1, comment="组织层级"),
        sa.Column("sort_order", sa.Integer(), default=0, comment="排序"),
        sa.Column("type", sa.String(20), nullable=False, comment="组织类型"),
        sa.Column(
            "status", sa.String(20), nullable=False, default="active", comment="状态"
        ),
        sa.Column("phone", sa.String(20), comment="联系电话"),
        sa.Column("email", sa.String(100), comment="邮箱"),
        sa.Column("address", sa.String(200), comment="地址"),
        sa.Column("leader_name", sa.String(50), comment="负责人姓名"),
        sa.Column("leader_phone", sa.String(20), comment="负责人电话"),
        sa.Column("leader_email", sa.String(100), comment="负责人邮箱"),
        sa.Column(
            "parent_id",
            sa.String(),
            sa.ForeignKey("organizations.id"),
            comment="上级组织ID",
        ),
        sa.Column("path", sa.String(1000), comment="组织路径"),
        sa.Column("description", sa.Text(), comment="组织描述"),
        sa.Column("functions", sa.Text(), comment="主要职能"),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否删除",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("created_by", sa.String(100), comment="创建人"),
        sa.Column("updated_by", sa.String(100), comment="更新人"),
        sa.PrimaryKeyConstraint("id"),
    )

    # positions - 职位表
    op.create_table(
        "positions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, comment="职位名称"),
        sa.Column("level", sa.Integer(), nullable=False, default=1, comment="职位级别"),
        sa.Column("category", sa.String(50), comment="职位类别"),
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            comment="所属组织ID",
        ),
        sa.Column("description", sa.Text(), comment="职位描述"),
        sa.Column("responsibilities", sa.Text(), comment="岗位职责"),
        sa.Column("requirements", sa.Text(), comment="任职要求"),
        sa.Column("salary_min", sa.Integer(), comment="最低薪资"),
        sa.Column("salary_max", sa.Integer(), comment="最高薪资"),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否删除",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("created_by", sa.String(100), comment="创建人"),
        sa.Column("updated_by", sa.String(100), comment="更新人"),
        sa.PrimaryKeyConstraint("id"),
    )

    # employees - 员工表
    op.create_table(
        "employees",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "employee_no",
            sa.String(50),
            unique=True,
            nullable=False,
            comment="员工编号",
        ),
        sa.Column("name", sa.String(100), nullable=False, comment="姓名"),
        sa.Column("gender", sa.String(10), comment="性别"),
        sa.Column("birth_date", sa.DateTime(), comment="出生日期"),
        sa.Column("id_card", sa.String(20), comment="身份证号"),
        sa.Column("emergency_contact", sa.String(100), comment="紧急联系人"),
        sa.Column("emergency_phone", sa.String(20), comment="紧急联系电话"),
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            comment="所属组织ID",
        ),
        sa.Column(
            "position_id", sa.String(), sa.ForeignKey("positions.id"), comment="职位ID"
        ),
        sa.Column(
            "direct_supervisor_id",
            sa.String(),
            sa.ForeignKey("employees.id"),
            comment="直接上级ID",
        ),
        sa.Column("hire_date", sa.DateTime(), comment="入职日期"),
        sa.Column("probation_end_date", sa.DateTime(), comment="试用期结束日期"),
        sa.Column("employment_type", sa.String(20), comment="用工类型"),
        sa.Column("work_location", sa.String(200), comment="工作地点"),
        sa.Column("base_salary", sa.Integer(), comment="基本工资"),
        sa.Column("performance_salary", sa.Integer(), comment="绩效工资"),
        sa.Column("total_salary", sa.Integer(), comment="总薪资"),
        sa.Column("resignation_date", sa.DateTime(), comment="离职日期"),
        sa.Column("resignation_reason", sa.Text(), comment="离职原因"),
        sa.Column("education", sa.String(50), comment="学历"),
        sa.Column("major", sa.String(100), comment="专业"),
        sa.Column("skills", sa.Text(), comment="技能"),
        sa.Column("notes", sa.Text(), comment="备注"),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否删除",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("created_by", sa.String(100), comment="创建人"),
        sa.Column("updated_by", sa.String(100), comment="更新人"),
        sa.PrimaryKeyConstraint("id"),
    )

    # users - 用户表
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "username", sa.String(50), unique=True, nullable=False, comment="用户名"
        ),
        sa.Column("email", sa.String(100), unique=True, nullable=False, comment="邮箱"),
        sa.Column("full_name", sa.String(100), nullable=False, comment="全名"),
        sa.Column("password_hash", sa.String(255), nullable=False, comment="密码哈希"),
        sa.Column("password_history", sa.JSON(), comment="密码历史记录"),
        sa.Column(
            "role", sa.String(20), nullable=False, default="user", comment="用户角色"
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, default=True, comment="是否激活"
        ),
        sa.Column(
            "is_locked", sa.Boolean(), nullable=False, default=False, comment="是否锁定"
        ),
        sa.Column("last_login_at", sa.DateTime(), comment="最后登录时间"),
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="失败登录次数",
        ),
        sa.Column("locked_until", sa.DateTime(), comment="锁定到期时间"),
        sa.Column("password_last_changed", sa.DateTime(), comment="密码最后修改时间"),
        sa.Column(
            "employee_id",
            sa.String(),
            sa.ForeignKey("employees.id"),
            comment="关联员工ID",
        ),
        sa.Column(
            "default_organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id"),
            comment="默认组织ID",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("created_by", sa.String(100), comment="创建人"),
        sa.Column("updated_by", sa.String(100), comment="更新人"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])

    # permissions - 权限表
    op.create_table(
        "permissions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "name", sa.String(100), unique=True, nullable=False, comment="权限名称"
        ),
        sa.Column("display_name", sa.String(200), nullable=False, comment="显示名称"),
        sa.Column("description", sa.Text(), comment="权限描述"),
        sa.Column("resource", sa.String(50), nullable=False, comment="资源类型"),
        sa.Column("action", sa.String(50), nullable=False, comment="操作类型"),
        sa.Column(
            "is_system_permission",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否系统权限",
        ),
        sa.Column(
            "requires_approval", sa.Boolean(), default=False, comment="是否需要审批"
        ),
        sa.Column("max_level", sa.Integer(), comment="最大级别"),
        sa.Column("conditions", sa.JSON(), comment="权限条件"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("created_by", sa.String(100), comment="创建人"),
        sa.Column("updated_by", sa.String(100), comment="更新人"),
        sa.PrimaryKeyConstraint("id"),
    )

    # roles - 角色表
    op.create_table(
        "roles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "name", sa.String(100), unique=True, nullable=False, comment="角色名称"
        ),
        sa.Column("display_name", sa.String(200), nullable=False, comment="显示名称"),
        sa.Column("description", sa.Text(), comment="角色描述"),
        sa.Column("level", sa.Integer(), nullable=False, default=1, comment="角色级别"),
        sa.Column("category", sa.String(50), comment="角色类别"),
        sa.Column(
            "is_system_role",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否系统角色",
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, default=True, comment="是否激活"
        ),
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id"),
            comment="所属组织ID",
        ),
        sa.Column("scope", sa.String(50), default="global", comment="权限范围"),
        sa.Column("scope_id", sa.String(), comment="范围ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("created_by", sa.String(100), comment="创建人"),
        sa.Column("updated_by", sa.String(100), comment="更新人"),
        sa.PrimaryKeyConstraint("id"),
    )

    # role_permissions - 角色权限关联表
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.String(), sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column(
            "permission_id",
            sa.String(),
            sa.ForeignKey("permissions.id"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(), comment="创建时间"),
        sa.Column("created_by", sa.String(100), comment="创建人"),
    )

    # user_role_assignments - 用户角色分配表
    op.create_table(
        "user_role_assignments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role_id", sa.String(), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("assigned_by", sa.String(100), comment="分配人"),
        sa.Column("assigned_at", sa.DateTime(), nullable=False, comment="分配时间"),
        sa.Column("expires_at", sa.DateTime(), comment="过期时间"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, default=True, comment="是否激活"
        ),
        sa.Column("reason", sa.Text(), comment="分配原因"),
        sa.Column("notes", sa.Text(), comment="备注"),
        sa.Column("context", sa.JSON(), comment="上下文信息"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )

    # user_sessions - 用户会话表
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", sa.String(100), unique=True, comment="会话ID"),
        sa.Column(
            "refresh_token", sa.Text(), unique=True, nullable=False, comment="刷新令牌"
        ),
        sa.Column("device_info", sa.Text(), comment="设备信息"),
        sa.Column("device_id", sa.String(100), comment="设备ID"),
        sa.Column("platform", sa.String(50), comment="平台"),
        sa.Column("ip_address", sa.String(45), comment="IP地址"),
        sa.Column("user_agent", sa.Text(), comment="用户代理"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, default=True, comment="是否活跃"
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False, comment="过期时间"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column(
            "last_accessed_at", sa.DateTime(), nullable=False, comment="最后访问时间"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # audit_logs - 审计日志表
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("user_role", sa.String(20), comment="用户角色"),
        sa.Column("user_organization", sa.String(200), comment="用户所属组织"),
        sa.Column("action", sa.String(100), nullable=False, comment="操作动作"),
        sa.Column("resource_type", sa.String(50), comment="资源类型"),
        sa.Column("resource_id", sa.String(), comment="资源ID"),
        sa.Column("resource_name", sa.String(200), comment="资源名称"),
        sa.Column("api_endpoint", sa.String(200), comment="API端点"),
        sa.Column("http_method", sa.String(10), comment="HTTP方法"),
        sa.Column("request_params", sa.Text(), comment="请求参数"),
        sa.Column("request_body", sa.Text(), comment="请求体"),
        sa.Column("response_status", sa.Integer(), comment="响应状态码"),
        sa.Column("response_message", sa.String(500), comment="响应消息"),
        sa.Column("ip_address", sa.String(45), comment="IP地址"),
        sa.Column("user_agent", sa.Text(), comment="用户代理"),
        sa.Column("session_id", sa.String(100), comment="会话ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.PrimaryKeyConstraint("id"),
    )

    # organization_history - 组织变更历史表
    op.create_table(
        "organization_history",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            comment="组织ID",
        ),
        sa.Column("action", sa.String(20), nullable=False, comment="操作类型"),
        sa.Column("field_name", sa.String(100), comment="变更字段"),
        sa.Column("old_value", sa.Text(), comment="原值"),
        sa.Column("new_value", sa.Text(), comment="新值"),
        sa.Column("change_reason", sa.String(500), comment="变更原因"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="操作时间"),
        sa.Column("created_by", sa.String(100), comment="操作人"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ==================== TIER 2: Enum Tables ====================

    # enum_field_types - 枚举字段类型表
    op.create_table(
        "enum_field_types",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, comment="枚举类型名称"),
        sa.Column(
            "code", sa.String(50), unique=True, nullable=False, comment="枚举类型编码"
        ),
        sa.Column("category", sa.String(50), comment="枚举类别"),
        sa.Column("description", sa.Text(), comment="枚举类型描述"),
        sa.Column(
            "is_system",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否系统内置",
        ),
        sa.Column(
            "is_multiple",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否支持多选",
        ),
        sa.Column(
            "is_hierarchical",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否层级结构",
        ),
        sa.Column("default_value", sa.String(100), comment="默认值"),
        sa.Column("validation_rules", sa.JSON(), comment="验证规则"),
        sa.Column("display_config", sa.JSON(), comment="显示配置"),
        sa.Column(
            "status", sa.String(20), nullable=False, default="active", comment="状态"
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否删除",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("created_by", sa.String(100), comment="创建人"),
        sa.Column("updated_by", sa.String(100), comment="更新人"),
        sa.PrimaryKeyConstraint("id"),
    )

    # enum_field_values - 枚举字段值表
    op.create_table(
        "enum_field_values",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "enum_type_id",
            sa.String(),
            sa.ForeignKey("enum_field_types.id"),
            nullable=False,
            comment="枚举类型ID",
        ),
        sa.Column("label", sa.String(100), nullable=False, comment="显示标签"),
        sa.Column("value", sa.String(100), nullable=False, comment="枚举值"),
        sa.Column("code", sa.String(50), comment="枚举编码"),
        sa.Column("description", sa.Text(), comment="描述"),
        sa.Column(
            "parent_id",
            sa.String(),
            sa.ForeignKey("enum_field_values.id"),
            comment="父级枚举值ID",
        ),
        sa.Column("level", sa.Integer(), default=1, comment="层级级别"),
        sa.Column("path", sa.String(1000), comment="层级路径"),
        sa.Column("sort_order", sa.Integer(), default=0, comment="排序"),
        sa.Column("color", sa.String(20), comment="颜色标识"),
        sa.Column("icon", sa.String(50), comment="图标"),
        sa.Column("extra_properties", sa.JSON(), comment="扩展属性"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, default=True, comment="是否启用"
        ),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否默认值",
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否删除",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("created_by", sa.String(100), comment="创建人"),
        sa.Column("updated_by", sa.String(100), comment="更新人"),
        sa.PrimaryKeyConstraint("id"),
    )

    # enum_field_usage - 枚举字段使用记录表
    op.create_table(
        "enum_field_usage",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "enum_type_id",
            sa.String(),
            sa.ForeignKey("enum_field_types.id"),
            nullable=False,
            comment="枚举类型ID",
        ),
        sa.Column("table_name", sa.String(100), nullable=False, comment="使用表名"),
        sa.Column("field_name", sa.String(100), nullable=False, comment="使用字段名"),
        sa.Column("field_label", sa.String(100), comment="字段显示名称"),
        sa.Column("module_name", sa.String(100), comment="所属模块"),
        sa.Column(
            "is_required",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否必填",
        ),
        sa.Column("default_value", sa.String(100), comment="默认值"),
        sa.Column("validation_config", sa.JSON(), comment="验证配置"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, default=True, comment="是否启用"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("created_by", sa.String(100), comment="创建人"),
        sa.Column("updated_by", sa.String(100), comment="更新人"),
        sa.PrimaryKeyConstraint("id"),
    )

    # enum_field_history - 枚举字段变更历史表
    op.create_table(
        "enum_field_history",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "enum_type_id",
            sa.String(),
            sa.ForeignKey("enum_field_types.id"),
            comment="枚举类型ID",
        ),
        sa.Column(
            "enum_value_id",
            sa.String(),
            sa.ForeignKey("enum_field_values.id"),
            comment="枚举值ID",
        ),
        sa.Column("action", sa.String(20), nullable=False, comment="操作类型"),
        sa.Column("target_type", sa.String(20), nullable=False, comment="目标类型"),
        sa.Column("field_name", sa.String(100), comment="变更字段"),
        sa.Column("old_value", sa.Text(), comment="原值"),
        sa.Column("new_value", sa.Text(), comment="新值"),
        sa.Column("change_reason", sa.String(500), comment="变更原因"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="操作时间"),
        sa.Column("created_by", sa.String(100), comment="操作人"),
        sa.Column("ip_address", sa.String(45), comment="IP地址"),
        sa.Column("user_agent", sa.Text(), comment="用户代理"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ==================== TIER 3: Project & Ownership Tables ====================

    # projects - 项目表
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(200), nullable=False, comment="项目名称"),
        sa.Column("short_name", sa.String(100), comment="项目简称"),
        sa.Column(
            "code", sa.String(100), unique=True, nullable=False, comment="项目编码"
        ),
        sa.Column("project_type", sa.String(50), comment="项目类型"),
        sa.Column("project_scale", sa.String(50), comment="项目规模"),
        sa.Column(
            "project_status",
            sa.String(50),
            nullable=False,
            default="规划中",
            comment="项目状态",
        ),
        sa.Column("start_date", sa.Date(), comment="开始日期"),
        sa.Column("end_date", sa.Date(), comment="结束日期"),
        sa.Column("expected_completion_date", sa.Date(), comment="预计完成日期"),
        sa.Column("actual_completion_date", sa.Date(), comment="实际完成日期"),
        sa.Column("address", sa.String(500), comment="项目地址"),
        sa.Column("city", sa.String(100), comment="城市"),
        sa.Column("district", sa.String(100), comment="区域"),
        sa.Column("province", sa.String(100), comment="省份"),
        sa.Column("project_manager", sa.String(100), comment="项目经理"),
        sa.Column("project_phone", sa.String(50), comment="项目电话"),
        sa.Column("project_email", sa.String(100), comment="项目邮箱"),
        sa.Column("total_investment", sa.DECIMAL(15, 2), comment="总投资"),
        sa.Column("planned_investment", sa.DECIMAL(15, 2), comment="计划投资"),
        sa.Column("actual_investment", sa.DECIMAL(15, 2), comment="实际投资"),
        sa.Column("project_budget", sa.DECIMAL(15, 2), comment="项目预算"),
        sa.Column("project_description", sa.Text(), comment="项目描述"),
        sa.Column("project_objectives", sa.Text(), comment="项目目标"),
        sa.Column("project_scope", sa.Text(), comment="项目范围"),
        sa.Column("management_entity", sa.String(200), comment="管理单位"),
        sa.Column("ownership_entity", sa.String(200), comment="权属单位"),
        sa.Column("construction_company", sa.String(200), comment="施工单位"),
        sa.Column("design_company", sa.String(200), comment="设计单位"),
        sa.Column("supervision_company", sa.String(200), comment="监理单位"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, default=True, comment="是否启用"
        ),
        sa.Column(
            "data_status",
            sa.String(20),
            nullable=False,
            default="正常",
            comment="数据状态",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("created_by", sa.String(100), comment="创建人"),
        sa.Column("updated_by", sa.String(100), comment="更新人"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ownerships - 权属方表
    op.create_table(
        "ownerships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False, comment="权属方全称"),
        sa.Column("code", sa.String(100), nullable=False, comment="权属方编码"),
        sa.Column("short_name", sa.String(100), comment="权属方简称"),
        sa.Column("address", sa.String(500), comment="地址"),
        sa.Column("management_entity", sa.String(200), comment="管理单位"),
        sa.Column("notes", sa.Text(), comment="备注"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, default=True, comment="状态"
        ),
        sa.Column(
            "data_status",
            sa.String(20),
            nullable=False,
            default="正常",
            comment="数据状态",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("created_by", sa.String(100), comment="创建人"),
        sa.Column("updated_by", sa.String(100), comment="更新人"),
        sa.PrimaryKeyConstraint("id"),
    )

    # project_ownership_relations - 项目权属方关联表
    op.create_table(
        "project_ownership_relations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "project_id",
            sa.String(),
            sa.ForeignKey("projects.id"),
            nullable=False,
            comment="项目ID",
        ),
        sa.Column(
            "ownership_id",
            sa.String(),
            sa.ForeignKey("ownerships.id"),
            nullable=False,
            comment="权属方ID",
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, default=True, comment="是否有效"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("created_by", sa.String(100), comment="创建人"),
        sa.Column("updated_by", sa.String(100), comment="更新人"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_project_ownership_project_id", "project_ownership_relations", ["project_id"]
    )
    op.create_index(
        "ix_project_ownership_ownership_id",
        "project_ownership_relations",
        ["ownership_id"],
    )

    # ==================== TIER 4: Asset Tables ====================

    # assets - 资产表
    op.create_table(
        "assets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("ownership_entity", sa.String(200), nullable=False, comment="权属方"),
        sa.Column("ownership_category", sa.String(100), comment="权属类别"),
        sa.Column("project_name", sa.String(200), comment="项目名称"),
        sa.Column("property_name", sa.String(200), nullable=False, comment="物业名称"),
        sa.Column("address", sa.String(500), nullable=False, comment="物业地址"),
        sa.Column(
            "ownership_status", sa.String(50), nullable=False, comment="确权状态"
        ),
        sa.Column("property_nature", sa.String(50), nullable=False, comment="物业性质"),
        sa.Column("usage_status", sa.String(50), nullable=False, comment="使用状态"),
        sa.Column("management_entity", sa.String(200), comment="经营管理单位"),
        sa.Column("business_category", sa.String(100), comment="业态类别"),
        sa.Column(
            "is_litigated",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否涉诉",
        ),
        sa.Column("notes", sa.Text(), comment="备注"),
        sa.Column("land_area", sa.DECIMAL(12, 2), comment="土地面积"),
        sa.Column("actual_property_area", sa.DECIMAL(12, 2), comment="实际房产面积"),
        sa.Column("rentable_area", sa.DECIMAL(12, 2), comment="可出租面积"),
        sa.Column("rented_area", sa.DECIMAL(12, 2), comment="已出租面积"),
        sa.Column("non_commercial_area", sa.DECIMAL(12, 2), comment="非经营物业面积"),
        sa.Column(
            "include_in_occupancy_rate",
            sa.Boolean(),
            nullable=False,
            default=True,
            comment="是否计入出租率统计",
        ),
        sa.Column("certificated_usage", sa.String(100), comment="证载用途"),
        sa.Column("actual_usage", sa.String(100), comment="实际用途"),
        sa.Column("tenant_name", sa.String(200), comment="租户名称"),
        sa.Column("tenant_type", sa.String(20), comment="租户类型"),
        sa.Column("lease_contract_number", sa.String(100), comment="租赁合同编号"),
        sa.Column("contract_start_date", sa.Date(), comment="合同开始日期"),
        sa.Column("contract_end_date", sa.Date(), comment="合同结束日期"),
        sa.Column("monthly_rent", sa.DECIMAL(15, 2), comment="月租金"),
        sa.Column("deposit", sa.DECIMAL(15, 2), comment="押金"),
        sa.Column(
            "is_sublease",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否分租/转租",
        ),
        sa.Column("sublease_notes", sa.Text(), comment="分租/转租备注"),
        sa.Column("business_model", sa.String(50), comment="接收模式"),
        sa.Column("operation_status", sa.String(20), comment="经营状态"),
        sa.Column("manager_name", sa.String(100), comment="管理责任人"),
        sa.Column(
            "operation_agreement_start_date", sa.Date(), comment="接收协议开始日期"
        ),
        sa.Column(
            "operation_agreement_end_date", sa.Date(), comment="接收协议结束日期"
        ),
        sa.Column("operation_agreement_attachments", sa.Text(), comment="接收协议文件"),
        sa.Column("terminal_contract_files", sa.Text(), comment="终端合同文件"),
        sa.Column(
            "data_status",
            sa.String(20),
            nullable=False,
            default="正常",
            comment="数据状态",
        ),
        sa.Column("version", sa.Integer(), nullable=False, default=1, comment="版本号"),
        sa.Column("tags", sa.Text(), comment="标签"),
        sa.Column("created_by", sa.String(100), comment="创建人"),
        sa.Column("updated_by", sa.String(100), comment="更新人"),
        sa.Column("audit_notes", sa.Text(), comment="审核备注"),
        sa.Column("created_at", sa.DateTime(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), comment="更新时间"),
        sa.Column("tenant_id", sa.String(50), comment="租户ID"),
        sa.Column(
            "project_id", sa.String(), sa.ForeignKey("projects.id"), comment="项目ID"
        ),
        sa.Column(
            "ownership_id",
            sa.String(),
            sa.ForeignKey("ownerships.id"),
            comment="权属方ID",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assets_project_id", "assets", ["project_id"])
    op.create_index("ix_assets_ownership_id", "assets", ["ownership_id"])

    # asset_history - 资产变更历史表
    op.create_table(
        "asset_history",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "asset_id",
            sa.String(),
            sa.ForeignKey("assets.id"),
            nullable=False,
            comment="资产ID",
        ),
        sa.Column("operation_type", sa.String(50), nullable=False, comment="操作类型"),
        sa.Column("field_name", sa.String(100), comment="字段名称"),
        sa.Column("old_value", sa.Text(), comment="原值"),
        sa.Column("new_value", sa.Text(), comment="新值"),
        sa.Column("operator", sa.String(100), comment="操作人"),
        sa.Column("operation_time", sa.DateTime(), comment="操作时间"),
        sa.Column("description", sa.Text(), comment="操作描述"),
        sa.Column("change_reason", sa.String(200), comment="变更原因"),
        sa.Column("ip_address", sa.String(45), comment="IP地址"),
        sa.Column("user_agent", sa.Text(), comment="用户代理"),
        sa.Column("session_id", sa.String(100), comment="会话ID"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asset_history_asset_id", "asset_history", ["asset_id"])

    # asset_documents - 资产文档表
    op.create_table(
        "asset_documents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "asset_id",
            sa.String(),
            sa.ForeignKey("assets.id"),
            nullable=False,
            comment="资产ID",
        ),
        sa.Column("document_name", sa.String(200), nullable=False, comment="文档名称"),
        sa.Column("document_type", sa.String(50), nullable=False, comment="文档类型"),
        sa.Column("file_path", sa.String(500), comment="文件路径"),
        sa.Column("file_size", sa.Integer(), comment="文件大小"),
        sa.Column("mime_type", sa.String(100), comment="文件MIME类型"),
        sa.Column("upload_time", sa.DateTime(), comment="上传时间"),
        sa.Column("uploader", sa.String(100), comment="上传人"),
        sa.Column("description", sa.Text(), comment="文档描述"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asset_documents_asset_id", "asset_documents", ["asset_id"])

    # system_dictionaries - 系统数据字典表
    op.create_table(
        "system_dictionaries",
        sa.Column("id", sa.String(50), nullable=False),
        sa.Column("dict_type", sa.String(50), nullable=False, comment="字典类型"),
        sa.Column("dict_code", sa.String(50), nullable=False, comment="字典编码"),
        sa.Column("dict_label", sa.String(100), nullable=False, comment="字典标签"),
        sa.Column("dict_value", sa.String(100), nullable=False, comment="字典值"),
        sa.Column(
            "sort_order", sa.Integer(), nullable=False, default=0, comment="排序"
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, default=True, comment="是否启用"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_system_dictionaries_dict_type", "system_dictionaries", ["dict_type"]
    )
    op.create_index(
        "ix_system_dictionaries_dict_code", "system_dictionaries", ["dict_code"]
    )

    # asset_custom_fields - 资产自定义字段表
    op.create_table(
        "asset_custom_fields",
        sa.Column("id", sa.String(50), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=False, comment="字段名称"),
        sa.Column("display_name", sa.String(100), nullable=False, comment="显示名称"),
        sa.Column("field_type", sa.String(20), nullable=False, comment="字段类型"),
        sa.Column(
            "is_required",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否必填",
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, default=True, comment="是否启用"
        ),
        sa.Column(
            "sort_order", sa.Integer(), nullable=False, default=0, comment="排序"
        ),
        sa.Column("default_value", sa.Text(), comment="默认值"),
        sa.Column("field_options", sa.Text(), comment="字段选项"),
        sa.Column("validation_rules", sa.Text(), comment="验证规则"),
        sa.Column("help_text", sa.Text(), comment="帮助文本"),
        sa.Column("description", sa.Text(), comment="描述"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ==================== TIER 5: Rent Contract Tables ====================

    # rent_contracts - 租金合同表
    op.create_table(
        "rent_contracts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "contract_number",
            sa.String(100),
            unique=True,
            nullable=False,
            comment="合同编号",
        ),
        sa.Column(
            "ownership_id",
            sa.String(),
            sa.ForeignKey("ownerships.id"),
            nullable=False,
            comment="权属方ID",
        ),
        sa.Column(
            "contract_type",
            sa.String(50),
            nullable=False,
            default="lease_downstream",
            comment="合同类型",
        ),
        sa.Column(
            "upstream_contract_id",
            sa.String(),
            sa.ForeignKey("rent_contracts.id"),
            comment="上游合同ID",
        ),
        sa.Column("owner_name", sa.String(200), comment="甲方名称"),
        sa.Column("owner_contact", sa.String(100), comment="甲方联系人"),
        sa.Column("owner_phone", sa.String(20), comment="甲方联系电话"),
        sa.Column("service_fee_rate", sa.DECIMAL(5, 4), comment="服务费率"),
        sa.Column("tenant_name", sa.String(200), nullable=False, comment="承租方名称"),
        sa.Column("tenant_contact", sa.String(100), comment="承租方联系人"),
        sa.Column("tenant_phone", sa.String(20), comment="承租方联系电话"),
        sa.Column("tenant_address", sa.String(500), comment="承租方地址"),
        sa.Column("tenant_usage", sa.String(500), comment="用途说明"),
        sa.Column("sign_date", sa.Date(), nullable=False, comment="签订日期"),
        sa.Column("start_date", sa.Date(), nullable=False, comment="租期开始日期"),
        sa.Column("end_date", sa.Date(), nullable=False, comment="租期结束日期"),
        sa.Column("total_deposit", sa.DECIMAL(15, 2), default=0, comment="总押金金额"),
        sa.Column("monthly_rent_base", sa.DECIMAL(15, 2), comment="基础月租金"),
        sa.Column(
            "payment_cycle", sa.String(20), default="monthly", comment="付款周期"
        ),
        sa.Column(
            "contract_status", sa.String(20), default="ACTIVE", comment="合同状态"
        ),
        sa.Column("payment_terms", sa.Text(), comment="支付条款"),
        sa.Column("contract_notes", sa.Text(), comment="合同备注"),
        sa.Column("data_status", sa.String(20), default="正常", comment="数据状态"),
        sa.Column("version", sa.Integer(), default=1, comment="版本号"),
        sa.Column("created_at", sa.DateTime(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), comment="更新时间"),
        sa.Column("tenant_id", sa.String(50), comment="租户ID"),
        sa.Column("source_session_id", sa.String(100), comment="PDF导入会话ID"),
        sa.PrimaryKeyConstraint("id"),
    )

    # rent_contract_assets - 合同资产关联表
    op.create_table(
        "rent_contract_assets",
        sa.Column(
            "contract_id",
            sa.String(),
            sa.ForeignKey("rent_contracts.id"),
            primary_key=True,
        ),
        sa.Column(
            "asset_id", sa.String(), sa.ForeignKey("assets.id"), primary_key=True
        ),
        sa.Column("created_at", sa.DateTime(), comment="关联创建时间"),
    )

    # rent_terms - 租金条款表
    op.create_table(
        "rent_terms",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "contract_id",
            sa.String(),
            sa.ForeignKey("rent_contracts.id"),
            nullable=False,
            comment="关联合同ID",
        ),
        sa.Column("start_date", sa.Date(), nullable=False, comment="条款开始日期"),
        sa.Column("end_date", sa.Date(), nullable=False, comment="条款结束日期"),
        sa.Column(
            "monthly_rent", sa.DECIMAL(15, 2), nullable=False, comment="月租金金额"
        ),
        sa.Column("rent_description", sa.String(500), comment="租金描述"),
        sa.Column("management_fee", sa.DECIMAL(15, 2), default=0, comment="管理费"),
        sa.Column("other_fees", sa.DECIMAL(15, 2), default=0, comment="其他费用"),
        sa.Column("total_monthly_amount", sa.DECIMAL(15, 2), comment="月总金额"),
        sa.Column("created_at", sa.DateTime(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )

    # rent_ledger - 租金台账表
    op.create_table(
        "rent_ledger",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "contract_id",
            sa.String(),
            sa.ForeignKey("rent_contracts.id"),
            nullable=False,
            comment="关联合同ID",
        ),
        sa.Column(
            "asset_id", sa.String(), sa.ForeignKey("assets.id"), comment="关联资产ID"
        ),
        sa.Column(
            "ownership_id",
            sa.String(),
            sa.ForeignKey("ownerships.id"),
            nullable=False,
            comment="权属方ID",
        ),
        sa.Column("year_month", sa.String(7), nullable=False, comment="年月"),
        sa.Column("due_date", sa.Date(), nullable=False, comment="应缴日期"),
        sa.Column("due_amount", sa.DECIMAL(15, 2), nullable=False, comment="应收金额"),
        sa.Column("paid_amount", sa.DECIMAL(15, 2), default=0, comment="实收金额"),
        sa.Column("overdue_amount", sa.DECIMAL(15, 2), default=0, comment="逾期金额"),
        sa.Column(
            "payment_status", sa.String(20), default="未支付", comment="支付状态"
        ),
        sa.Column("payment_date", sa.Date(), comment="支付日期"),
        sa.Column("payment_method", sa.String(50), comment="支付方式"),
        sa.Column("payment_reference", sa.String(100), comment="支付参考号"),
        sa.Column("late_fee", sa.DECIMAL(15, 2), default=0, comment="滞纳金"),
        sa.Column("late_fee_days", sa.Integer(), default=0, comment="滞纳天数"),
        sa.Column("notes", sa.Text(), comment="备注"),
        sa.Column("data_status", sa.String(20), default="正常", comment="数据状态"),
        sa.Column("version", sa.Integer(), default=1, comment="版本号"),
        sa.Column("created_at", sa.DateTime(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )

    # rent_deposit_ledger - 押金台账表
    op.create_table(
        "rent_deposit_ledger",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "contract_id",
            sa.String(),
            sa.ForeignKey("rent_contracts.id"),
            nullable=False,
            comment="关联合同ID",
        ),
        sa.Column(
            "transaction_type", sa.String(20), nullable=False, comment="交易类型"
        ),
        sa.Column("amount", sa.DECIMAL(15, 2), nullable=False, comment="金额"),
        sa.Column("transaction_date", sa.Date(), nullable=False, comment="交易日期"),
        sa.Column(
            "related_contract_id",
            sa.String(),
            sa.ForeignKey("rent_contracts.id"),
            comment="关联合同ID",
        ),
        sa.Column("notes", sa.Text(), comment="备注"),
        sa.Column("operator", sa.String(100), comment="操作人"),
        sa.Column("operator_id", sa.String(50), comment="操作人ID"),
        sa.Column("created_at", sa.DateTime(), comment="创建时间"),
        sa.PrimaryKeyConstraint("id"),
    )

    # service_fee_ledger - 服务费台账表
    op.create_table(
        "service_fee_ledger",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "contract_id",
            sa.String(),
            sa.ForeignKey("rent_contracts.id"),
            nullable=False,
            comment="关联合同ID",
        ),
        sa.Column(
            "source_ledger_id",
            sa.String(),
            sa.ForeignKey("rent_ledger.id"),
            comment="关联租金台账ID",
        ),
        sa.Column("year_month", sa.String(7), nullable=False, comment="年月"),
        sa.Column(
            "paid_rent_amount", sa.DECIMAL(15, 2), nullable=False, comment="实收租金"
        ),
        sa.Column("fee_rate", sa.DECIMAL(5, 4), nullable=False, comment="服务费率"),
        sa.Column(
            "fee_amount", sa.DECIMAL(15, 2), nullable=False, comment="服务费金额"
        ),
        sa.Column(
            "settlement_status", sa.String(20), default="待结算", comment="结算状态"
        ),
        sa.Column("settlement_date", sa.Date(), comment="结算日期"),
        sa.Column("notes", sa.Text(), comment="备注"),
        sa.Column("operator", sa.String(100), comment="操作人"),
        sa.Column("operator_id", sa.String(50), comment="操作人ID"),
        sa.Column("created_at", sa.DateTime(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )

    # rent_contract_history - 合同历史记录表
    op.create_table(
        "rent_contract_history",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "contract_id",
            sa.String(),
            sa.ForeignKey("rent_contracts.id"),
            nullable=False,
            comment="关联合同ID",
        ),
        sa.Column("change_type", sa.String(50), nullable=False, comment="变更类型"),
        sa.Column("change_description", sa.Text(), comment="变更描述"),
        sa.Column("old_data", sa.JSON(), comment="变更前数据"),
        sa.Column("new_data", sa.JSON(), comment="变更后数据"),
        sa.Column("operator", sa.String(100), comment="操作人"),
        sa.Column("operator_id", sa.String(50), comment="操作人ID"),
        sa.Column("created_at", sa.DateTime(), comment="创建时间"),
        sa.PrimaryKeyConstraint("id"),
    )

    # rent_contract_attachments - 合同附件表
    op.create_table(
        "rent_contract_attachments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "contract_id",
            sa.String(),
            sa.ForeignKey("rent_contracts.id"),
            nullable=False,
            comment="关联合同ID",
        ),
        sa.Column("file_name", sa.String(255), nullable=False, comment="文件名"),
        sa.Column("file_path", sa.String(500), nullable=False, comment="文件存储路径"),
        sa.Column("file_size", sa.Integer(), comment="文件大小"),
        sa.Column("mime_type", sa.String(100), comment="文件MIME类型"),
        sa.Column("file_type", sa.String(50), default="other", comment="文件类型"),
        sa.Column("description", sa.Text(), comment="附件描述"),
        sa.Column("uploader", sa.String(100), comment="上传人"),
        sa.Column("uploader_id", sa.String(50), comment="上传人ID"),
        sa.Column("created_at", sa.DateTime(), comment="上传时间"),
        sa.PrimaryKeyConstraint("id"),
    )

    # collection_records - 催缴记录表
    op.create_table(
        "collection_records",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "ledger_id",
            sa.String(),
            sa.ForeignKey("rent_ledger.id"),
            nullable=False,
            comment="关联租金台账ID",
        ),
        sa.Column(
            "contract_id",
            sa.String(),
            sa.ForeignKey("rent_contracts.id"),
            nullable=False,
            comment="关联合同ID",
        ),
        sa.Column(
            "collection_method", sa.String(20), nullable=False, comment="催缴方式"
        ),
        sa.Column("collection_date", sa.Date(), nullable=False, comment="催缴日期"),
        sa.Column(
            "collection_status", sa.String(20), default="pending", comment="催缴状态"
        ),
        sa.Column("contacted_person", sa.String(100), comment="被联系人"),
        sa.Column("contact_phone", sa.String(20), comment="联系电话"),
        sa.Column("promised_amount", sa.DECIMAL(15, 2), comment="承诺付款金额"),
        sa.Column("promised_date", sa.Date(), comment="承诺付款日期"),
        sa.Column("actual_payment_amount", sa.DECIMAL(15, 2), comment="实际付款金额"),
        sa.Column("collection_notes", sa.Text(), comment="催缴备注"),
        sa.Column("next_follow_up_date", sa.Date(), comment="下次跟进日期"),
        sa.Column("operator", sa.String(100), comment="操作人"),
        sa.Column("operator_id", sa.String(50), comment="操作人ID"),
        sa.Column("created_at", sa.DateTime(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ==================== TIER 6: Contact & Notification Tables ====================

    # contacts - 联系人表
    op.create_table(
        "contacts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False, comment="关联实体类型"),
        sa.Column("entity_id", sa.String(), nullable=False, comment="关联实体ID"),
        sa.Column("name", sa.String(100), nullable=False, comment="联系人姓名"),
        sa.Column("title", sa.String(100), comment="职位/头衔"),
        sa.Column("department", sa.String(100), comment="部门"),
        sa.Column("phone", sa.String(20), comment="手机号码"),
        sa.Column("office_phone", sa.String(20), comment="办公电话"),
        sa.Column("email", sa.String(200), comment="电子邮箱"),
        sa.Column("wechat", sa.String(100), comment="微信号"),
        sa.Column("address", sa.String(500), comment="地址"),
        sa.Column(
            "contact_type",
            sa.String(20),
            nullable=False,
            default="general",
            comment="联系人类型",
        ),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            default=False,
            nullable=False,
            comment="是否主要联系人",
        ),
        sa.Column("notes", sa.Text(), comment="备注"),
        sa.Column("preferred_contact_time", sa.String(100), comment="偏好联系时间"),
        sa.Column("preferred_contact_method", sa.String(50), comment="偏好联系方式"),
        sa.Column(
            "is_active", sa.Boolean(), default=True, nullable=False, comment="是否启用"
        ),
        sa.Column("created_at", sa.DateTime(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), comment="更新时间"),
        sa.Column("created_by", sa.String(100), comment="创建人"),
        sa.Column("updated_by", sa.String(100), comment="更新人"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contacts_entity_type", "contacts", ["entity_type"])
    op.create_index("ix_contacts_entity_id", "contacts", ["entity_id"])

    # notifications - 通知表
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column(
            "recipient_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
            comment="接收用户ID",
        ),
        sa.Column("type", sa.String(50), nullable=False, comment="通知类型"),
        sa.Column("priority", sa.String(20), default="normal", comment="通知优先级"),
        sa.Column("title", sa.String(200), nullable=False, comment="通知标题"),
        sa.Column("content", sa.Text(), nullable=False, comment="通知内容"),
        sa.Column("related_entity_type", sa.String(50), comment="关联实体类型"),
        sa.Column("related_entity_id", sa.String(36), comment="关联实体ID"),
        sa.Column("is_read", sa.Boolean(), default=False, comment="是否已读"),
        sa.Column("read_at", sa.DateTime(), comment="已读时间"),
        sa.Column(
            "is_sent_wecom", sa.Boolean(), default=False, comment="是否已发送企业微信"
        ),
        sa.Column("wecom_sent_at", sa.DateTime(), comment="企业微信发送时间"),
        sa.Column("wecom_send_error", sa.Text(), comment="企业微信发送错误信息"),
        sa.Column("extra_data", sa.Text(), comment="额外数据"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_type", "notifications", ["type"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])

    # operation_logs - 操作日志表
    op.create_table(
        "operation_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False, comment="操作用户ID"),
        sa.Column("username", sa.String(100), comment="操作用户名"),
        sa.Column("action", sa.String(50), nullable=False, comment="操作类型"),
        sa.Column("action_name", sa.String(200), comment="操作名称"),
        sa.Column("module", sa.String(50), nullable=False, comment="操作模块"),
        sa.Column("module_name", sa.String(200), comment="模块名称"),
        sa.Column("resource_type", sa.String(50), comment="资源类型"),
        sa.Column("resource_id", sa.String(100), comment="资源ID"),
        sa.Column("resource_name", sa.String(200), comment="资源名称"),
        sa.Column("request_method", sa.String(10), comment="HTTP方法"),
        sa.Column("request_url", sa.Text(), comment="请求URL"),
        sa.Column("request_params", sa.Text(), comment="请求参数"),
        sa.Column("request_body", sa.Text(), comment="请求体"),
        sa.Column("response_status", sa.Integer(), comment="响应状态码"),
        sa.Column("response_time", sa.Integer(), comment="响应时间"),
        sa.Column("error_message", sa.Text(), comment="错误消息"),
        sa.Column("ip_address", sa.String(45), comment="客户端IP"),
        sa.Column("user_agent", sa.Text(), comment="用户代理"),
        sa.Column("details", sa.Text(), comment="详细信息"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ==================== TIER 7: Dynamic Permission Tables ====================

    # dynamic_permissions - 动态权限表
    op.create_table(
        "dynamic_permissions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "permission_id",
            sa.String(),
            sa.ForeignKey("permissions.id"),
            nullable=False,
        ),
        sa.Column("permission_type", sa.String(), nullable=False),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("scope_id", sa.String()),
        sa.Column("conditions", sa.JSON()),
        sa.Column("expires_at", sa.DateTime()),
        sa.Column(
            "assigned_by", sa.String(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_by", sa.String(), sa.ForeignKey("users.id")),
        sa.Column("revoked_at", sa.DateTime()),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dynamic_permissions_user_id", "dynamic_permissions", ["user_id"]
    )
    op.create_index(
        "ix_dynamic_permissions_permission_id", "dynamic_permissions", ["permission_id"]
    )
    op.create_index(
        "ix_dynamic_permissions_is_active", "dynamic_permissions", ["is_active"]
    )

    # temporary_permissions - 临时权限表
    op.create_table(
        "temporary_permissions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "permission_id",
            sa.String(),
            sa.ForeignKey("permissions.id"),
            nullable=False,
        ),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("scope_id", sa.String()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "assigned_by", sa.String(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_temporary_permissions_user_id", "temporary_permissions", ["user_id"]
    )
    op.create_index(
        "ix_temporary_permissions_expires_at", "temporary_permissions", ["expires_at"]
    )

    # conditional_permissions - 条件权限表
    op.create_table(
        "conditional_permissions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "permission_id",
            sa.String(),
            sa.ForeignKey("permissions.id"),
            nullable=False,
        ),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("scope_id", sa.String()),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column(
            "assigned_by", sa.String(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conditional_permissions_user_id", "conditional_permissions", ["user_id"]
    )

    # permission_templates - 权限模板表
    op.create_table(
        "permission_templates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("permission_ids", sa.JSON(), nullable=False),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("conditions", sa.JSON()),
        sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_permission_templates_name", "permission_templates", ["name"])

    # dynamic_permission_audit - 动态权限审计表
    op.create_table(
        "dynamic_permission_audit",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "permission_id",
            sa.String(),
            sa.ForeignKey("permissions.id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("permission_type", sa.String(), nullable=False),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("scope_id", sa.String()),
        sa.Column(
            "assigned_by", sa.String(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("reason", sa.Text()),
        sa.Column("conditions", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dynamic_permission_audit_user_id", "dynamic_permission_audit", ["user_id"]
    )
    op.create_index(
        "ix_dynamic_permission_audit_action", "dynamic_permission_audit", ["action"]
    )

    # permission_requests - 权限申请表
    op.create_table(
        "permission_requests",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("permission_ids", sa.JSON(), nullable=False),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("scope_id", sa.String()),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("requested_duration_hours", sa.String()),
        sa.Column("requested_conditions", sa.JSON()),
        sa.Column("status", sa.String(), default="pending", nullable=False),
        sa.Column("approved_by", sa.String(), sa.ForeignKey("users.id")),
        sa.Column("approved_at", sa.DateTime()),
        sa.Column("approval_comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_permission_requests_user_id", "permission_requests", ["user_id"]
    )
    op.create_index("ix_permission_requests_status", "permission_requests", ["status"])

    # permission_delegations - 权限委托表
    op.create_table(
        "permission_delegations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "delegator_id", sa.String(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "delegatee_id", sa.String(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("permission_ids", sa.JSON(), nullable=False),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("scope_id", sa.String()),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("conditions", sa.JSON()),
        sa.Column("reason", sa.Text()),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_permission_delegations_delegator_id",
        "permission_delegations",
        ["delegator_id"],
    )
    op.create_index(
        "ix_permission_delegations_delegatee_id",
        "permission_delegations",
        ["delegatee_id"],
    )

    # resource_permissions - 资源权限表
    op.create_table(
        "resource_permissions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False, comment="资源类型"),
        sa.Column("resource_id", sa.String(), nullable=False, comment="资源ID"),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), comment="用户ID"),
        sa.Column("role_id", sa.String(), sa.ForeignKey("roles.id"), comment="角色ID"),
        sa.Column(
            "permission_id",
            sa.String(),
            sa.ForeignKey("permissions.id"),
            comment="权限ID",
        ),
        sa.Column(
            "permission_level", sa.String(20), default="read", comment="权限级别"
        ),
        sa.Column("granted_at", sa.DateTime(), nullable=False, comment="授权时间"),
        sa.Column("expires_at", sa.DateTime(), comment="过期时间"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, default=True, comment="是否激活"
        ),
        sa.Column("granted_by", sa.String(100), comment="授权人"),
        sa.Column("reason", sa.Text(), comment="授权原因"),
        sa.Column("conditions", sa.JSON(), comment="权限条件"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )

    # permission_audit_logs - 权限审计日志表
    op.create_table(
        "permission_audit_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("action", sa.String(50), nullable=False, comment="操作类型"),
        sa.Column("resource_type", sa.String(50), comment="资源类型"),
        sa.Column("resource_id", sa.String(), comment="资源ID"),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), comment="用户ID"),
        sa.Column(
            "operator_id", sa.String(), sa.ForeignKey("users.id"), comment="操作人ID"
        ),
        sa.Column("old_permissions", sa.JSON(), comment="原权限"),
        sa.Column("new_permissions", sa.JSON(), comment="新权限"),
        sa.Column("reason", sa.Text(), comment="变更原因"),
        sa.Column("ip_address", sa.String(45), comment="IP地址"),
        sa.Column("user_agent", sa.Text(), comment="用户代理"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ==================== TIER 8: Property Certificate Tables ====================

    # property_owners - 权利人表
    op.create_table(
        "property_owners",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner_type", sa.String(20), nullable=False, comment="权利人类型"),
        sa.Column(
            "name", sa.String(200), nullable=False, comment="权利人姓名/单位名称"
        ),
        sa.Column("id_type", sa.String(50), comment="证件类型"),
        sa.Column("id_number", sa.String(100), comment="证件号码"),
        sa.Column("phone", sa.String(20), comment="联系电话"),
        sa.Column("address", sa.String(500), comment="地址"),
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id"),
            comment="关联组织ID",
        ),
        sa.Column("created_at", sa.DateTime(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_property_owners_owner_type", "property_owners", ["owner_type"])
    op.create_index("ix_property_owners_name", "property_owners", ["name"])

    # property_certificates - 产权证表
    op.create_table(
        "property_certificates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "certificate_number",
            sa.String(100),
            unique=True,
            nullable=False,
            comment="证书编号",
        ),
        sa.Column(
            "certificate_type", sa.String(20), nullable=False, comment="证书类型"
        ),
        sa.Column("extraction_confidence", sa.Float(), comment="LLM提取置信度"),
        sa.Column(
            "extraction_source", sa.String(20), default="manual", comment="数据来源"
        ),
        sa.Column("verified", sa.Boolean(), default=False, comment="是否人工审核"),
        sa.Column("registration_date", sa.Date(), comment="登记日期"),
        sa.Column("property_address", sa.String(500), comment="坐落地址"),
        sa.Column("property_type", sa.String(50), comment="用途"),
        sa.Column("building_area", sa.String(50), comment="建筑面积"),
        sa.Column("floor_info", sa.String(100), comment="楼层信息"),
        sa.Column("land_area", sa.String(50), comment="土地使用面积"),
        sa.Column("land_use_type", sa.String(50), comment="土地使用权类型"),
        sa.Column("land_use_term_start", sa.Date(), comment="土地使用期限起"),
        sa.Column("land_use_term_end", sa.Date(), comment="土地使用期限止"),
        sa.Column("co_ownership", sa.String(200), comment="共有情况"),
        sa.Column("restrictions", sa.Text(), comment="权利限制情况"),
        sa.Column("remarks", sa.Text(), comment="备注"),
        sa.Column("created_at", sa.DateTime(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), comment="更新时间"),
        sa.Column("created_by", sa.String(100), comment="创建人ID"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_property_certificates_certificate_number",
        "property_certificates",
        ["certificate_number"],
    )
    op.create_index(
        "ix_property_certificates_certificate_type",
        "property_certificates",
        ["certificate_type"],
    )

    # property_certificate_owners - 产权证权利人关联表
    op.create_table(
        "property_certificate_owners",
        sa.Column(
            "certificate_id",
            sa.String(),
            sa.ForeignKey("property_certificates.id"),
            primary_key=True,
        ),
        sa.Column(
            "owner_id",
            sa.String(),
            sa.ForeignKey("property_owners.id"),
            primary_key=True,
        ),
        sa.Column("ownership_share", sa.Numeric(5, 2), comment="拥有权比例"),
        sa.Column("owner_category", sa.String(50), comment="权利人类别"),
    )

    # property_cert_assets - 产权证资产关联表
    op.create_table(
        "property_cert_assets",
        sa.Column(
            "certificate_id",
            sa.String(),
            sa.ForeignKey("property_certificates.id"),
            primary_key=True,
        ),
        sa.Column(
            "asset_id", sa.String(), sa.ForeignKey("assets.id"), primary_key=True
        ),
        sa.Column("link_type", sa.String(50), comment="关联类型"),
        sa.Column("notes", sa.String(500), comment="关联备注"),
    )

    # ==================== TIER 9: LLM Prompt Tables ====================

    # prompt_templates - Prompt模板表
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "name", sa.String(100), unique=True, nullable=False, comment="Prompt名称"
        ),
        sa.Column("doc_type", sa.String(50), nullable=False, comment="文档类型"),
        sa.Column("provider", sa.String(50), nullable=False, comment="LLM提供商"),
        sa.Column("description", sa.String(500), comment="Prompt描述"),
        sa.Column("system_prompt", sa.Text(), nullable=False, comment="系统提示词"),
        sa.Column(
            "user_prompt_template", sa.Text(), nullable=False, comment="用户提示词模板"
        ),
        sa.Column("few_shot_examples", sa.JSON(), comment="Few-shot示例"),
        sa.Column("version", sa.String(20), nullable=False, comment="版本号"),
        sa.Column("status", sa.String(20), default="draft", comment="状态"),
        sa.Column("tags", sa.JSON(), comment="标签列表"),
        sa.Column("avg_accuracy", sa.Float(), default=0.0, comment="平均准确率"),
        sa.Column("avg_confidence", sa.Float(), default=0.0, comment="平均置信度"),
        sa.Column("total_usage", sa.Integer(), default=0, comment="总使用次数"),
        sa.Column("current_version_id", sa.String(), comment="当前版本ID"),
        sa.Column(
            "parent_id",
            sa.String(),
            sa.ForeignKey("prompt_templates.id"),
            comment="父模板ID",
        ),
        sa.Column("created_at", sa.DateTime(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), comment="更新时间"),
        sa.Column("created_by", sa.String(100), comment="创建人ID"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prompt_templates_doc_type", "prompt_templates", ["doc_type"])
    op.create_index("ix_prompt_templates_provider", "prompt_templates", ["provider"])

    # prompt_versions - Prompt版本表
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "template_id",
            sa.String(),
            sa.ForeignKey("prompt_templates.id"),
            nullable=False,
        ),
        sa.Column("version", sa.String(20), nullable=False, comment="版本号"),
        sa.Column("system_prompt", sa.Text(), nullable=False, comment="系统提示词快照"),
        sa.Column(
            "user_prompt_template",
            sa.Text(),
            nullable=False,
            comment="用户提示词模板快照",
        ),
        sa.Column("few_shot_examples", sa.JSON(), comment="Few-shot示例快照"),
        sa.Column("change_description", sa.String(500), comment="变更描述"),
        sa.Column("change_type", sa.String(50), comment="变更类型"),
        sa.Column(
            "auto_generated", sa.Boolean(), default=False, comment="是否为自动生成"
        ),
        sa.Column("accuracy", sa.Float(), comment="该版本的准确率"),
        sa.Column("confidence", sa.Float(), comment="该版本的平均置信度"),
        sa.Column("usage_count", sa.Integer(), default=0, comment="使用次数"),
        sa.Column("created_at", sa.DateTime(), comment="创建时间"),
        sa.Column("created_by", sa.String(100), comment="创建人ID"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_prompt_versions_template_id", "prompt_versions", ["template_id"]
    )

    # 添加外键: prompt_templates.current_version_id -> prompt_versions.id
    op.create_foreign_key(
        "fk_prompt_templates_current_version",
        "prompt_templates",
        "prompt_versions",
        ["current_version_id"],
        ["id"],
    )

    # extraction_feedback - 提取反馈表
    op.create_table(
        "extraction_feedback",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "template_id",
            sa.String(),
            sa.ForeignKey("prompt_templates.id"),
            nullable=False,
        ),
        sa.Column("version_id", sa.String(), sa.ForeignKey("prompt_versions.id")),
        sa.Column("doc_type", sa.String(50), comment="文档类型"),
        sa.Column("file_path", sa.String(500), comment="文件路径"),
        sa.Column("session_id", sa.String(100), comment="导入会话ID"),
        sa.Column("field_name", sa.String(100), comment="字段名称"),
        sa.Column("original_value", sa.Text(), comment="原始识别值"),
        sa.Column("corrected_value", sa.Text(), comment="用户修正后的值"),
        sa.Column("confidence_before", sa.Float(), comment="修正前的置信度"),
        sa.Column("user_action", sa.String(50), comment="用户动作"),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id"),
            comment="提交反馈的用户ID",
        ),
        sa.Column("created_at", sa.DateTime(), comment="创建时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_extraction_feedback_template_id", "extraction_feedback", ["template_id"]
    )
    op.create_index(
        "ix_extraction_feedback_version_id", "extraction_feedback", ["version_id"]
    )
    op.create_index(
        "ix_extraction_feedback_user_id", "extraction_feedback", ["user_id"]
    )

    # prompt_metrics - Prompt性能指标表
    op.create_table(
        "prompt_metrics",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "template_id",
            sa.String(),
            sa.ForeignKey("prompt_templates.id"),
            nullable=False,
        ),
        sa.Column("version_id", sa.String(), sa.ForeignKey("prompt_versions.id")),
        sa.Column("date", sa.Date(), nullable=False, comment="统计日期"),
        sa.Column("total_extractions", sa.Integer(), default=0, comment="总提取次数"),
        sa.Column(
            "successful_extractions", sa.Integer(), default=0, comment="成功提取次数"
        ),
        sa.Column(
            "corrected_fields", sa.Integer(), default=0, comment="用户修正的字段数"
        ),
        sa.Column("avg_accuracy", sa.Float(), default=0.0, comment="平均准确率"),
        sa.Column("avg_confidence", sa.Float(), default=0.0, comment="平均置信度"),
        sa.Column("created_at", sa.DateTime(), comment="创建时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prompt_metrics_template_id", "prompt_metrics", ["template_id"])
    op.create_index("ix_prompt_metrics_date", "prompt_metrics", ["date"])

    # ==================== TIER 10: PDF Import & Task Tables ====================

    # pdf_import_sessions - PDF导入会话表
    op.create_table(
        "pdf_import_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(100), unique=True, nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(1000)),
        sa.Column("content_type", sa.String(100), default="application/pdf"),
        sa.Column("status", sa.String(30), default="uploading", nullable=False),
        sa.Column("current_step", sa.String(30)),
        sa.Column("progress_percentage", sa.Float(), default=0.0),
        sa.Column("error_message", sa.Text()),
        sa.Column("extracted_text", sa.Text()),
        sa.Column("extracted_data", sa.JSON()),
        sa.Column("processing_result", sa.JSON()),
        sa.Column("validation_results", sa.JSON()),
        sa.Column("matching_results", sa.JSON()),
        sa.Column("confidence_score", sa.Float(), default=0.0),
        sa.Column("processing_method", sa.String(50)),
        sa.Column("ocr_used", sa.Boolean(), default=False),
        sa.Column("processing_options", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("user_id", sa.Integer()),
        sa.Column("organization_id", sa.Integer()),
    )
    op.create_index(
        "ix_pdf_import_sessions_session_id", "pdf_import_sessions", ["session_id"]
    )

    # pdf_import_session_logs - PDF导入会话日志表
    op.create_table(
        "pdf_import_session_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(100), nullable=False),
        sa.Column("step", sa.String(30), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Float()),
        sa.Column("memory_usage_mb", sa.Float()),
    )
    op.create_index(
        "ix_pdf_import_session_logs_session_id",
        "pdf_import_session_logs",
        ["session_id"],
    )

    # pdf_import_configurations - PDF导入配置表
    op.create_table(
        "pdf_import_configurations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(100), unique=True, nullable=False),
        sa.Column("prefer_ocr", sa.Boolean(), default=False),
        sa.Column("ocr_languages", sa.JSON()),
        sa.Column("dpi", sa.Integer(), default=300),
        sa.Column("max_pages", sa.Integer(), default=100),
        sa.Column("extraction_confidence_threshold", sa.Float(), default=0.7),
        sa.Column("validate_fields", sa.Boolean(), default=True),
        sa.Column("strict_validation", sa.Boolean(), default=False),
        sa.Column("enable_asset_matching", sa.Boolean(), default=True),
        sa.Column("enable_ownership_matching", sa.Boolean(), default=True),
        sa.Column("enable_duplicate_check", sa.Boolean(), default=True),
        sa.Column("matching_threshold", sa.Float(), default=0.8),
        sa.Column("auto_confirm_high_confidence", sa.Boolean(), default=False),
        sa.Column("notification_enabled", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_pdf_import_configurations_session_id",
        "pdf_import_configurations",
        ["session_id"],
    )

    # async_tasks - 异步任务表
    op.create_table(
        "async_tasks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("task_type", sa.String(50), nullable=False, comment="任务类型"),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            default="pending",
            comment="任务状态",
        ),
        sa.Column("title", sa.String(200), nullable=False, comment="任务标题"),
        sa.Column("description", sa.Text(), comment="任务描述"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("started_at", sa.DateTime(), comment="开始时间"),
        sa.Column("completed_at", sa.DateTime(), comment="完成时间"),
        sa.Column("progress", sa.Integer(), default=0, comment="进度百分比"),
        sa.Column("total_items", sa.Integer(), comment="总项目数"),
        sa.Column("processed_items", sa.Integer(), default=0, comment="已处理项目数"),
        sa.Column("failed_items", sa.Integer(), default=0, comment="失败项目数"),
        sa.Column("result_data", sa.JSON(), comment="结果数据"),
        sa.Column("error_message", sa.Text(), comment="错误信息"),
        sa.Column("user_id", sa.String(100), comment="创建用户ID"),
        sa.Column("session_id", sa.String(100), comment="会话ID"),
        sa.Column("parameters", sa.JSON(), comment="任务参数"),
        sa.Column("config", sa.JSON(), comment="任务配置"),
        sa.Column("is_active", sa.Boolean(), default=True, comment="是否活跃"),
        sa.Column("retry_count", sa.Integer(), default=0, comment="重试次数"),
        sa.Column("max_retries", sa.Integer(), default=3, comment="最大重试次数"),
        sa.PrimaryKeyConstraint("id"),
    )

    # task_history - 任务历史记录表
    op.create_table(
        "task_history",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False, comment="关联任务ID"),
        sa.Column("action", sa.String(100), nullable=False, comment="操作类型"),
        sa.Column("message", sa.Text(), comment="消息内容"),
        sa.Column("details", sa.JSON(), comment="详细信息"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("user_id", sa.String(100), comment="用户ID"),
        sa.PrimaryKeyConstraint("id"),
    )

    # excel_task_configs - Excel任务配置表
    op.create_table(
        "excel_task_configs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("config_name", sa.String(200), nullable=False, comment="配置名称"),
        sa.Column("config_type", sa.String(50), nullable=False, comment="配置类型"),
        sa.Column("task_type", sa.String(50), nullable=False, comment="任务类型"),
        sa.Column("field_mapping", sa.JSON(), comment="字段映射配置"),
        sa.Column("validation_rules", sa.JSON(), comment="验证规则配置"),
        sa.Column("format_config", sa.JSON(), comment="格式配置"),
        sa.Column("is_default", sa.Boolean(), default=False, comment="是否默认配置"),
        sa.Column("is_active", sa.Boolean(), default=True, comment="是否启用"),
        sa.Column("created_by", sa.String(100), comment="创建者"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ==================== TIER 11: Security Events Table ====================

    # security_events - 安全事件表
    op.create_table(
        "security_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False, comment="Event type"),
        sa.Column("severity", sa.String(20), nullable=False, comment="Severity level"),
        sa.Column("user_id", sa.String(), comment="User ID if applicable"),
        sa.Column("ip_address", sa.String(45), comment="IP address"),
        sa.Column("metadata", sa.JSON(), comment="Event metadata"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, comment="Event timestamp"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_events_event_type", "security_events", ["event_type"])
    op.create_index("ix_security_events_user_id", "security_events", ["user_id"])
    op.create_index("ix_security_events_ip_address", "security_events", ["ip_address"])
    op.create_index("ix_security_events_created_at", "security_events", ["created_at"])
    op.create_index(
        "ix_security_events_event_type_created_at",
        "security_events",
        ["event_type", "created_at"],
    )
    op.create_index(
        "ix_security_events_user_id_created_at",
        "security_events",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_security_events_ip_created_at",
        "security_events",
        ["ip_address", "created_at"],
    )
    op.create_index(
        "ix_security_events_severity_created_at",
        "security_events",
        ["severity", "created_at"],
    )


def downgrade() -> None:
    """Drop all tables in reverse order."""

    # TIER 11: Security
    op.drop_table("security_events")

    # TIER 10: PDF Import & Tasks
    op.drop_table("excel_task_configs")
    op.drop_table("task_history")
    op.drop_table("async_tasks")
    op.drop_table("pdf_import_configurations")
    op.drop_table("pdf_import_session_logs")
    op.drop_table("pdf_import_sessions")

    # TIER 9: LLM Prompt
    op.drop_table("prompt_metrics")
    op.drop_table("extraction_feedback")
    op.drop_constraint(
        "fk_prompt_templates_current_version", "prompt_templates", type_="foreignkey"
    )
    op.drop_table("prompt_versions")
    op.drop_table("prompt_templates")

    # TIER 8: Property Certificate
    op.drop_table("property_cert_assets")
    op.drop_table("property_certificate_owners")
    op.drop_table("property_certificates")
    op.drop_table("property_owners")

    # TIER 7: Dynamic Permissions
    op.drop_table("permission_audit_logs")
    op.drop_table("resource_permissions")
    op.drop_table("permission_delegations")
    op.drop_table("permission_requests")
    op.drop_table("dynamic_permission_audit")
    op.drop_table("permission_templates")
    op.drop_table("conditional_permissions")
    op.drop_table("temporary_permissions")
    op.drop_table("dynamic_permissions")

    # TIER 6: Contacts & Notifications
    op.drop_table("operation_logs")
    op.drop_table("notifications")
    op.drop_table("contacts")

    # TIER 5: Rent Contracts
    op.drop_table("collection_records")
    op.drop_table("rent_contract_attachments")
    op.drop_table("rent_contract_history")
    op.drop_table("service_fee_ledger")
    op.drop_table("rent_deposit_ledger")
    op.drop_table("rent_ledger")
    op.drop_table("rent_terms")
    op.drop_table("rent_contract_assets")
    op.drop_table("rent_contracts")

    # TIER 4: Assets
    op.drop_table("asset_custom_fields")
    op.drop_table("system_dictionaries")
    op.drop_table("asset_documents")
    op.drop_table("asset_history")
    op.drop_table("assets")

    # TIER 3: Projects & Ownerships
    op.drop_table("project_ownership_relations")
    op.drop_table("ownerships")
    op.drop_table("projects")

    # TIER 2: Enums
    op.drop_table("enum_field_history")
    op.drop_table("enum_field_usage")
    op.drop_table("enum_field_values")
    op.drop_table("enum_field_types")

    # TIER 1: Base Tables
    op.drop_table("organization_history")
    op.drop_table("audit_logs")
    op.drop_table("user_sessions")
    op.drop_table("user_role_assignments")
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("permissions")
    op.drop_table("users")
    op.drop_table("employees")
    op.drop_table("positions")
    op.drop_table("organizations")
