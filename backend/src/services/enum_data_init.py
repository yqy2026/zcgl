"""
枚举字段数据初始化脚本

将 schemas/asset.py 中定义的标准枚举值同步到数据库的枚举管理表中，
使枚举字段管理功能与代码定义保持一致。
"""

import logging

from sqlalchemy.orm import Session

from ..models.enum_field import EnumFieldType, EnumFieldValue

logger = logging.getLogger(__name__)

# 标准枚举定义 - 与 schemas/asset.py 中的 Enum 类保持一致
STANDARD_ENUMS = {
    "ownership_status": {
        "name": "确权状态",
        "category": "资产管理",
        "description": "资产的确权状态",
        "values": [
            {"value": "已确权", "label": "已确权", "sort_order": 1},
            {"value": "未确权", "label": "未确权", "sort_order": 2},
            {"value": "部分确权", "label": "部分确权", "sort_order": 3},
            {"value": "无法确认业权", "label": "无法确认业权", "sort_order": 4},
        ],
    },
    "property_nature": {
        "name": "物业性质",
        "category": "资产管理",
        "description": "物业的经营性质分类",
        "values": [
            {"value": "经营性", "label": "经营性", "sort_order": 1},
            {"value": "非经营性", "label": "非经营性", "sort_order": 2},
            {"value": "经营-外部", "label": "经营-外部", "sort_order": 3},
            {"value": "经营-内部", "label": "经营-内部", "sort_order": 4},
            {"value": "经营-租赁", "label": "经营-租赁", "sort_order": 5},
            {"value": "非经营类-公配", "label": "非经营类-公配", "sort_order": 6},
            {"value": "非经营类-其他", "label": "非经营类-其他", "sort_order": 7},
            {"value": "经营类", "label": "经营类", "sort_order": 8},
            {"value": "非经营类", "label": "非经营类", "sort_order": 9},
            {"value": "经营-配套", "label": "经营-配套", "sort_order": 10},
            {"value": "非经营-配套", "label": "非经营-配套", "sort_order": 11},
            {"value": "经营-配套镇", "label": "经营-配套镇", "sort_order": 12},
            {"value": "非经营-配套镇", "label": "非经营-配套镇", "sort_order": 13},
            {"value": "经营-处置类", "label": "经营-处置类", "sort_order": 14},
            {"value": "非经营-处置类", "label": "非经营-处置类", "sort_order": 15},
            {"value": "非经营-公配房", "label": "非经营-公配房", "sort_order": 16},
            {"value": "非经营类-配套", "label": "非经营类-配套", "sort_order": 17},
        ],
    },
    "usage_status": {
        "name": "使用状态",
        "category": "资产管理",
        "description": "资产的使用状态",
        "values": [
            {"value": "出租", "label": "出租", "sort_order": 1},
            {"value": "空置", "label": "空置", "sort_order": 2},
            {"value": "自用", "label": "自用", "sort_order": 3},
            {"value": "公房", "label": "公房", "sort_order": 4},
            {"value": "其他", "label": "其他", "sort_order": 5},
            {"value": "转租", "label": "转租", "sort_order": 6},
            {"value": "公配", "label": "公配", "sort_order": 7},
            {"value": "空置规划", "label": "空置规划", "sort_order": 8},
            {"value": "空置预留", "label": "空置预留", "sort_order": 9},
            {"value": "配套", "label": "配套", "sort_order": 10},
            {"value": "空置配套", "label": "空置配套", "sort_order": 11},
            {"value": "空置配", "label": "空置配", "sort_order": 12},
            {"value": "待处置", "label": "待处置", "sort_order": 13},
            {"value": "待移交", "label": "待移交", "sort_order": 14},
            {"value": "闲置", "label": "闲置", "sort_order": 15},
        ],
    },
    "tenant_type": {
        "name": "租户类型",
        "category": "合同管理",
        "description": "租户的类型分类",
        "values": [
            {"value": "个人", "label": "个人", "sort_order": 1},
            {"value": "企业", "label": "企业", "sort_order": 2},
            {"value": "政府机构", "label": "政府机构", "sort_order": 3},
            {"value": "其他", "label": "其他", "sort_order": 4},
        ],
    },
    "business_model": {
        "name": "接收模式",
        "category": "资产管理",
        "description": "资产的接收/经营模式",
        "values": [
            {"value": "承租转租", "label": "承租转租", "sort_order": 1},
            {"value": "委托经营", "label": "委托经营", "sort_order": 2},
            {"value": "自营", "label": "自营", "sort_order": 3},
            {"value": "其他", "label": "其他", "sort_order": 4},
        ],
    },
    "operation_status": {
        "name": "经营状态",
        "category": "资产管理",
        "description": "资产的经营状态",
        "values": [
            {"value": "正常经营", "label": "正常经营", "sort_order": 1},
            {"value": "停业整顿", "label": "停业整顿", "sort_order": 2},
            {"value": "装修中", "label": "装修中", "sort_order": 3},
            {"value": "待招租", "label": "待招租", "sort_order": 4},
        ],
    },
    "data_status": {
        "name": "数据状态",
        "category": "系统",
        "description": "数据记录的状态",
        "values": [
            {"value": "正常", "label": "正常", "sort_order": 1},
            {"value": "已删除", "label": "已删除", "sort_order": 2},
            {"value": "已归档", "label": "已归档", "sort_order": 3},
        ],
    },
}


def init_enum_data(db: Session, created_by: str = "system") -> dict:
    """
    初始化标准枚举数据

    Args:
        db: 数据库会话
        created_by: 创建人

    Returns:
        初始化结果统计
    """
    stats = {
        "types_created": 0,
        "types_updated": 0,
        "values_created": 0,
        "values_updated": 0,
        "errors": [],
    }

    for enum_code, enum_config in STANDARD_ENUMS.items():
        try:
            # 查找或创建枚举类型
            enum_type = (
                db.query(EnumFieldType).filter(EnumFieldType.code == enum_code).first()
            )

            if not enum_type:
                # 创建新枚举类型
                enum_type = EnumFieldType(
                    code=enum_code,
                    name=enum_config["name"],
                    category=enum_config.get("category", "其他"),
                    description=enum_config.get("description", ""),
                    is_system=True,
                    status="active",
                    created_by=created_by,
                )
                db.add(enum_type)
                db.flush()  # 获取ID
                stats["types_created"] += 1
                logger.info(f"创建枚举类型: {enum_code}")
            else:
                # 更新现有枚举类型
                enum_type.name = enum_config["name"]
                enum_type.category = enum_config.get("category", enum_type.category)
                enum_type.description = enum_config.get(
                    "description", enum_type.description
                )
                enum_type.is_system = True
                enum_type.status = "active"
                enum_type.is_deleted = False
                enum_type.updated_by = created_by
                stats["types_updated"] += 1
                logger.info(f"更新枚举类型: {enum_code}")

            # 处理枚举值
            for value_config in enum_config["values"]:
                existing_value = (
                    db.query(EnumFieldValue)
                    .filter(
                        EnumFieldValue.enum_type_id == enum_type.id,
                        EnumFieldValue.value == value_config["value"],
                    )
                    .first()
                )

                if not existing_value:
                    # 创建新枚举值
                    new_value = EnumFieldValue(
                        enum_type_id=enum_type.id,
                        value=value_config["value"],
                        label=value_config["label"],
                        sort_order=value_config.get("sort_order", 0),
                        is_active=True,
                        is_deleted=False,
                        created_by=created_by,
                    )
                    db.add(new_value)
                    stats["values_created"] += 1
                else:
                    # 更新现有枚举值
                    existing_value.label = value_config["label"]
                    existing_value.sort_order = value_config.get(
                        "sort_order", existing_value.sort_order
                    )
                    existing_value.is_active = True
                    existing_value.is_deleted = False
                    existing_value.updated_by = created_by
                    stats["values_updated"] += 1

        except Exception as e:
            error_msg = f"处理枚举类型 {enum_code} 失败: {e}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)

    db.commit()
    logger.info(f"枚举数据初始化完成: {stats}")
    return stats


def add_legacy_enum_values(db: Session, created_by: str = "system") -> dict:
    """
    添加遗留数据中存在但标准定义中没有的枚举值

    这些值可能来自旧系统导入的数据，需要添加到枚举管理中以避免验证错误
    """
    # 遗留值映射：旧值 -> 添加到哪个枚举类型
    LEGACY_VALUES = {
        "ownership_status": [
            {"value": "正常", "label": "正常 (遗留)", "sort_order": 99},
        ],
        "usage_status": [
            {"value": "已出租", "label": "已出租 (遗留)", "sort_order": 99},
        ],
        "business_model": [
            {"value": "整体出租", "label": "整体出租 (遗留)", "sort_order": 99},
        ],
        "operation_status": [
            {"value": "正常", "label": "正常 (遗留)", "sort_order": 99},
        ],
    }

    stats = {"values_added": 0, "errors": []}

    for enum_code, legacy_values in LEGACY_VALUES.items():
        try:
            enum_type = (
                db.query(EnumFieldType).filter(EnumFieldType.code == enum_code).first()
            )

            if not enum_type:
                stats["errors"].append(f"枚举类型 {enum_code} 不存在")
                continue

            for value_config in legacy_values:
                existing = (
                    db.query(EnumFieldValue)
                    .filter(
                        EnumFieldValue.enum_type_id == enum_type.id,
                        EnumFieldValue.value == value_config["value"],
                    )
                    .first()
                )

                if not existing:
                    new_value = EnumFieldValue(
                        enum_type_id=enum_type.id,
                        value=value_config["value"],
                        label=value_config["label"],
                        sort_order=value_config.get("sort_order", 99),
                        is_active=True,
                        is_deleted=False,
                        created_by=created_by,
                    )
                    db.add(new_value)
                    stats["values_added"] += 1
                    logger.info(f"添加遗留枚举值: {enum_code}.{value_config['value']}")

        except Exception as e:
            stats["errors"].append(f"处理遗留值 {enum_code} 失败: {e}")

    db.commit()
    logger.info(f"遗留枚举值添加完成: {stats}")
    return stats
