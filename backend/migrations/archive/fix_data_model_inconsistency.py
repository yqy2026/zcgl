"""
修复前后端数据模型不一致问题 - 数据库迁移脚本
添加缺失的财务、租户联系、审核字段
"""

from sqlalchemy import text
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def upgrade_database(db_session):
    """
    执行数据库升级，添加缺失字段

    Args:
        db_session: SQLAlchemy数据库会话
    """
    try:
        logger.info("开始执行数据库升级迁移...")

        # 检查并添加财务字段
        _add_financial_fields(db_session)

        # 检查并添加租户联系字段
        _add_tenant_contact_field(db_session)

        # 检查并添加审核字段
        _add_audit_fields(db_session)

        # 提交更改
        db_session.commit()
        logger.info("数据库升级迁移完成")

        return {
            "success": True,
            "message": "数据库升级成功",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        db_session.rollback()
        logger.error(f"数据库升级失败: {str(e)}")
        return {
            "success": False,
            "message": f"数据库升级失败: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


def _add_financial_fields(db_session):
    """添加财务相关字段"""
    logger.info("检查并添加财务字段...")

    # 检查字段是否已存在
    check_sql = """
    SELECT COUNT(*) as count FROM pragma_table_info('assets') WHERE name = :field_name
    """

    financial_fields = [
        ("annual_income", "DECIMAL(15, 2)", "年收益（元）"),
        ("annual_expense", "DECIMAL(15, 2)", "年支出（元）"),
        ("net_income", "DECIMAL(15, 2)", "净收益（元）"),
    ]

    for field_name, field_type, comment in financial_fields:
        # 检查字段是否存在
        result = db_session.execute(
            text(check_sql), {"field_name": field_name}
        ).fetchone()

        if result and result.count == 0:
            # 字段不存在，添加字段
            alter_sql = f"""
            ALTER TABLE assets ADD COLUMN {field_name} {field_type} COMMENT '{comment}'
            """
            logger.info(f"添加字段: {field_name}")
            db_session.execute(text(alter_sql))
        else:
            logger.info(f"字段已存在，跳过: {field_name}")


def _add_tenant_contact_field(db_session):
    """添加租户联系字段"""
    logger.info("检查并添加租户联系字段...")

    # 检查字段是否已存在
    check_sql = """
    SELECT COUNT(*) as count FROM pragma_table_info('assets') WHERE name = 'tenant_contact'
    """

    result = db_session.execute(text(check_sql)).fetchone()

    if result and result.count == 0:
        # 字段不存在，添加字段
        alter_sql = """
        ALTER TABLE assets ADD COLUMN tenant_contact VARCHAR(100) COMMENT '租户联系方式'
        """
        logger.info("添加字段: tenant_contact")
        db_session.execute(text(alter_sql))
    else:
        logger.info("字段已存在，跳过: tenant_contact")


def _add_audit_fields(db_session):
    """添加审核相关字段"""
    logger.info("检查并添加审核字段...")

    # 检查字段是否已存在
    check_sql = """
    SELECT COUNT(*) as count FROM pragma_table_info('assets') WHERE name = :field_name
    """

    audit_fields = [
        ("last_audit_date", "DATE", "最后审核时间"),
        ("audit_status", "VARCHAR(20)", "审核状态"),
        ("auditor", "VARCHAR(100)", "审核人"),
    ]

    for field_name, field_type, comment in audit_fields:
        # 检查字段是否存在
        result = db_session.execute(
            text(check_sql), {"field_name": field_name}
        ).fetchone()

        if result and result.count == 0:
            # 字段不存在，添加字段
            alter_sql = f"""
            ALTER TABLE assets ADD COLUMN {field_name} {field_type} COMMENT '{comment}'
            """
            logger.info(f"添加字段: {field_name}")
            db_session.execute(text(alter_sql))
        else:
            logger.info(f"字段已存在，跳过: {field_name}")


def verify_database_schema(db_session):
    """
    验证数据库schema是否包含所有必需字段

    Args:
        db_session: SQLAlchemy数据库会话

    Returns:
        dict: 验证结果
    """
    try:
        logger.info("开始验证数据库schema...")

        # 获取assets表的所有字段
        result = db_session.execute(text("PRAGMA table_info(assets)")).fetchall()
        existing_fields = {row.name for row in result}

        # 必需的字段列表
        required_fields = {
            # 基本字段
            "id",
            "ownership_entity",
            "ownership_category",
            "project_name",
            "property_name",
            "address",
            "ownership_status",
            "property_nature",
            "usage_status",
            "business_category",
            "is_litigated",
            "notes",
            # 面积字段
            "land_area",
            "actual_property_area",
            "rentable_area",
            "rented_area",
            "unrented_area",
            "non_commercial_area",
            "occupancy_rate",
            "include_in_occupancy_rate",
            # 用途字段
            "certificated_usage",
            "actual_usage",
            # 租户字段
            "tenant_name",
            "tenant_contact",
            "tenant_type",
            # 合同字段
            "lease_contract_number",
            "contract_start_date",
            "contract_end_date",
            "monthly_rent",
            "deposit",
            "is_sublease",
            "sublease_notes",
            # 管理字段
            "manager_name",
            "business_model",
            "operation_status",
            # 财务字段 (新增)
            "annual_income",
            "annual_expense",
            "net_income",
            # 接收相关字段
            "operation_agreement_start_date",
            "operation_agreement_end_date",
            "operation_agreement_attachments",
            "terminal_contract_files",
            # 系统字段
            "data_status",
            "created_by",
            "updated_by",
            "version",
            "tags",
            # 审核字段 (新增)
            "last_audit_date",
            "audit_status",
            "auditor",
            "audit_notes",
            # 时间戳
            "created_at",
            "updated_at",
            # 多租户
            "tenant_id",
            # 关联字段
            "project_id",
            "ownership_id",
        }

        # 检查缺失字段
        missing_fields = required_fields - existing_fields
        extra_fields = existing_fields - required_fields

        success = len(missing_fields) == 0

        logger.info(f"数据库schema验证完成: {'成功' if success else '失败'}")
        if missing_fields:
            logger.warning(f"缺失字段: {missing_fields}")
        if extra_fields:
            logger.info(f"额外字段: {extra_fields}")

        return {
            "success": success,
            "missing_fields": list(missing_fields),
            "extra_fields": list(extra_fields),
            "total_existing": len(existing_fields),
            "total_required": len(required_fields),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"数据库schema验证失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def get_migration_status(db_session):
    """
    获取迁移状态信息

    Args:
        db_session: SQLAlchemy数据库会话

    Returns:
        dict: 迁移状态信息
    """
    try:
        verification = verify_database_schema(db_session)

        return {
            "migration_name": "fix_frontend_backend_data_model_inconsistency",
            "description": "修复前后端数据模型不一致问题",
            "version": "1.0.0",
            "verification_result": verification,
            "recommendations": _get_recommendations(verification),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "migration_name": "fix_frontend_backend_data_model_inconsistency",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def _get_recommendations(verification):
    """获取基于验证结果的建议"""
    recommendations = []

    if not verification["success"]:
        recommendations.append("需要执行数据库迁移以添加缺失字段")
        recommendations.append(f"缺失字段: {', '.join(verification['missing_fields'])}")
    else:
        recommendations.append("数据库schema已包含所有必需字段")

    if verification["extra_fields"]:
        recommendations.append(
            f"发现额外字段: {', '.join(verification['extra_fields'])}"
        )

    return recommendations


if __name__ == "__main__":
    # 测试脚本
    print("数据库迁移脚本 - 修复前后端数据模型不一致问题")
    print("请在后端环境中使用以下命令执行:")
    print("from backend.scripts.fix_data_model_inconsistency import upgrade_database")
    print("upgrade_database(db_session)")
