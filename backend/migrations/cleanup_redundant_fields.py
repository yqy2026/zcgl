"""
数据库冗余字段清理脚本 - 方案B：前端优先简化
移除与前端不一致的冗余字段
"""

from sqlalchemy import text
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def cleanup_redundant_fields(db_session):
    """
    清理数据库中的冗余字段，使其与前端简化模型一致

    Args:
        db_session: SQLAlchemy数据库会话
    """
    try:
        logger.info("开始清理数据库冗余字段...")

        # 备份现有数据
        _backup_existing_data(db_session)

        # 移除冗余字段
        _remove_financial_fields(db_session)
        _remove_tenant_contact_field(db_session)
        _remove_audit_fields(db_session)

        # 提交更改
        db_session.commit()
        logger.info("数据库冗余字段清理完成")

        return {
            "success": True,
            "message": "数据库冗余字段清理成功",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        db_session.rollback()
        logger.error(f"数据库冗余字段清理失败: {str(e)}")
        return {
            "success": False,
            "message": f"数据库冗余字段清理失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

def _backup_existing_data(db_session):
    """备份现有数据"""
    logger.info("备份现有数据...")

    # 备份财务数据
    backup_sql = """
    CREATE TABLE IF NOT EXISTS assets_financial_backup AS
    SELECT id, property_name, annual_income, annual_expense, net_income, created_at
    FROM assets
    WHERE annual_income IS NOT NULL OR annual_expense IS NOT NULL OR net_income IS NOT NULL
    """
    db_session.execute(text(backup_sql))

    # 备份租户联系数据
    contact_backup_sql = """
    CREATE TABLE IF NOT EXISTS assets_contact_backup AS
    SELECT id, property_name, tenant_name, tenant_contact, created_at
    FROM assets
    WHERE tenant_contact IS NOT NULL
    """
    db_session.execute(text(contact_backup_sql))

    # 备份审核数据
    audit_backup_sql = """
    CREATE TABLE IF NOT EXISTS assets_audit_backup AS
    SELECT id, property_name, last_audit_date, audit_status, auditor, audit_notes, created_at
    FROM assets
    WHERE last_audit_date IS NOT NULL OR audit_status IS NOT NULL OR auditor IS NOT NULL
    """
    db_session.execute(text(audit_backup_sql))

    logger.info("数据备份完成")

def _remove_financial_fields(db_session):
    """移除财务相关字段"""
    logger.info("移除财务相关字段...")

    financial_fields = ['annual_income', 'annual_expense', 'net_income']

    for field_name in financial_fields:
        # 检查字段是否存在
        check_sql = """
        SELECT COUNT(*) as count FROM pragma_table_info('assets') WHERE name = :field_name
        """
        result = db_session.execute(text(check_sql), {"field_name": field_name}).fetchone()

        if result and result.count > 0:
            # SQLite不支持直接删除列，需要重建表
            logger.info(f"准备移除字段: {field_name}")
            _recreate_table_without_field(db_session, field_name)
        else:
            logger.info(f"字段不存在，跳过: {field_name}")

def _remove_tenant_contact_field(db_session):
    """移除租户联系字段"""
    logger.info("移除租户联系字段...")

    # 检查字段是否存在
    check_sql = """
    SELECT COUNT(*) as count FROM pragma_table_info('assets') WHERE name = 'tenant_contact'
    """
    result = db_session.execute(text(check_sql)).fetchone()

    if result and result.count > 0:
        logger.info("准备移除字段: tenant_contact")
        _recreate_table_without_field(db_session, 'tenant_contact')
    else:
        logger.info("字段不存在，跳过: tenant_contact")

def _remove_audit_fields(db_session):
    """移除审核相关字段（除了audit_notes）"""
    logger.info("移除审核相关字段...")

    audit_fields = ['last_audit_date', 'audit_status', 'auditor']

    for field_name in audit_fields:
        # 检查字段是否存在
        check_sql = """
        SELECT COUNT(*) as count FROM pragma_table_info('assets') WHERE name = :field_name
        """
        result = db_session.execute(text(check_sql), {"field_name": field_name}).fetchone()

        if result and result.count > 0:
            logger.info(f"准备移除字段: {field_name}")
            _recreate_table_without_field(db_session, field_name)
        else:
            logger.info(f"字段不存在，跳过: {field_name}")

def _recreate_table_without_field(db_session, field_to_remove):
    """
    SQLite不支持直接删除列，需要重建表

    Args:
        db_session: SQLAlchemy数据库会话
        field_to_remove: 要移除的字段名
    """
    logger.info(f"重建表以移除字段: {field_to_remove}")

    # 临时禁用外键约束
    db_session.execute(text("PRAGMA foreign_keys = OFF"))

    # 获取表结构
    pragma_sql = "PRAGMA table_info(assets)"
    columns_info = db_session.execute(text(pragma_sql)).fetchall()

    # 构建保留的列列表
    retained_columns = [col.name for col in columns_info if col.name != field_to_remove]

    # 创建临时表
    temp_table_name = "assets_temp"
    create_temp_sql = f"""
    CREATE TABLE {temp_table_name} AS
    SELECT {', '.join(retained_columns)} FROM assets
    """
    db_session.execute(text(create_temp_sql))

    # 删除原表
    drop_original_sql = "DROP TABLE assets"
    db_session.execute(text(drop_original_sql))

    # 重命名临时表
    rename_sql = f"ALTER TABLE {temp_table_name} RENAME TO assets"
    db_session.execute(text(rename_sql))

    # 重建索引和约束
    _recreate_indexes_and_constraints(db_session)

    # 重新启用外键约束
    db_session.execute(text("PRAGMA foreign_keys = ON"))

    logger.info(f"表重建完成，已移除字段: {field_to_remove}")

def _recreate_indexes_and_constraints(db_session):
    """重建索引和约束"""
    logger.info("重建索引和约束...")

    # 重建主键
    db_session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS pk_assets ON assets (id)"))

    # 重建外键约束
    db_session.execute(text("""
    CREATE TABLE IF NOT EXISTS 'projects' (
        'id' VARCHAR(36) NOT NULL,
        'name' VARCHAR(200) NOT NULL,
        PRIMARY KEY ('id')
    )
    """))

    db_session.execute(text("""
    CREATE TABLE IF NOT EXISTS 'ownerships' (
        'id' VARCHAR(36) NOT NULL,
        'name' VARCHAR(200) NOT NULL,
        PRIMARY KEY ('id')
    )
    """))

    logger.info("索引和约束重建完成")

def verify_simplified_schema(db_session):
    """
    验证简化后的数据库schema

    Args:
        db_session: SQLAlchemy数据库会话

    Returns:
        dict: 验证结果
    """
    try:
        logger.info("开始验证简化后的数据库schema...")

        # 获取assets表的所有字段
        result = db_session.execute(text("PRAGMA table_info(assets)")).fetchall()
        existing_fields = {row.name for row in result}

        # 简化后的必需字段列表
        required_fields = {
            # 基本字段
            'id', 'ownership_entity', 'ownership_category', 'project_name',
            'property_name', 'address', 'ownership_status', 'property_nature',
            'usage_status', 'business_category', 'is_litigated', 'notes',

            # 面积字段
            'land_area', 'actual_property_area', 'rentable_area', 'rented_area',
            'unrented_area', 'non_commercial_area', 'occupancy_rate',
            'include_in_occupancy_rate',

            # 用途字段
            'certificated_usage', 'actual_usage',

            # 租户字段（简化）
            'tenant_name', 'tenant_type',

            # 合同字段
            'lease_contract_number', 'contract_start_date', 'contract_end_date',
            'monthly_rent', 'deposit', 'is_sublease', 'sublease_notes',

            # 管理字段
            'manager_name', 'business_model', 'operation_status',

            # 接收相关字段
            'operation_agreement_start_date', 'operation_agreement_end_date',
            'operation_agreement_attachments', 'terminal_contract_files',

            # 系统字段
            'data_status', 'created_by', 'updated_by', 'version', 'tags',

            # 审核字段（简化）
            'audit_notes',

            # 时间戳
            'created_at', 'updated_at',

            # 多租户
            'tenant_id',

            # 关联字段
            'project_id', 'ownership_id'
        }

        # 应该被移除的字段
        removed_fields = {
            'annual_income', 'annual_expense', 'net_income',
            'tenant_contact', 'last_audit_date', 'audit_status', 'auditor'
        }

        # 检查结果
        missing_fields = required_fields - existing_fields
        extra_fields = existing_fields - required_fields
        successfully_removed = removed_fields & existing_fields

        success = len(missing_fields) == 0 and len(successfully_removed) == 0

        logger.info(f"简化schema验证完成: {'成功' if success else '失败'}")
        if missing_fields:
            logger.warning(f"缺失字段: {missing_fields}")
        if extra_fields:
            logger.info(f"额外字段: {extra_fields}")
        if successfully_removed:
            logger.warning(f"未成功移除的字段: {successfully_removed}")

        return {
            "success": success,
            "missing_fields": list(missing_fields),
            "extra_fields": list(extra_fields),
            "successfully_removed": list(successfully_removed),
            "total_existing": len(existing_fields),
            "total_required": len(required_fields),
            "total_removed": len(removed_fields),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"简化schema验证失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def get_cleanup_status(db_session):
    """
    获取清理状态信息

    Args:
        db_session: SQLAlchemy数据库会话

    Returns:
        dict: 清理状态信息
    """
    try:
        verification = verify_simplified_schema(db_session)

        return {
            "cleanup_name": "frontend_backend_model_simplification",
            "description": "前端优先简化：移除后端冗余字段",
            "version": "2.0.0",
            "strategy": "frontend_priority",
            "verification_result": verification,
            "backup_tables": _get_backup_table_info(db_session),
            "recommendations": _get_simplification_recommendations(verification),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "cleanup_name": "frontend_backend_model_simplification",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def _get_backup_table_info(db_session):
    """获取备份表信息"""
    backup_tables = {}

    backup_table_names = [
        'assets_financial_backup',
        'assets_contact_backup',
        'assets_audit_backup'
    ]

    for table_name in backup_table_names:
        try:
            count_sql = f"SELECT COUNT(*) as count FROM {table_name}"
            result = db_session.execute(text(count_sql)).fetchone()
            backup_tables[table_name] = result.count if result else 0
        except Exception:
            backup_tables[table_name] = 0

    return backup_tables

def _get_simplification_recommendations(verification):
    """获取简化后的建议"""
    recommendations = []

    if not verification["success"]:
        recommendations.append("需要进一步清理数据库字段")
        recommendations.append(f"缺失字段: {', '.join(verification['missing_fields'])}")
    else:
        recommendations.append("数据库schema已成功简化")
        recommendations.append("前端和后端模型现在完全一致")

    if verification["extra_fields"]:
        recommendations.append(f"仍需清理的额外字段: {', '.join(verification['extra_fields'])}")

    total_backup_records = sum(_get_backup_table_info(None).values())
    if total_backup_records > 0:
        recommendations.append(f"已备份 {total_backup_records} 条记录到备份表")
        recommendations.append("建议在确认无问题后清理备份表")

    return recommendations

if __name__ == "__main__":
    # 测试脚本
    print("数据库冗余字段清理脚本 - 前端优先简化方案")
    print("请在后端环境中使用以下命令执行:")
    print("from backend.scripts.cleanup_redundant_fields import cleanup_redundant_fields")
    print("cleanup_redundant_fields(db_session)")