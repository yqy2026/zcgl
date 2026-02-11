"""
枚举字段数据初始化脚本

将 schemas/asset.py 中定义的标准枚举值同步到数据库的枚举管理表中，
使枚举字段管理功能与代码定义保持一致。
"""

import logging
from typing import Any, TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.enum_field import enum_field_type_crud, enum_field_value_crud
from ..models.enum_field import EnumFieldType, EnumFieldValue

logger = logging.getLogger(__name__)


def _set_attr(obj: Any, attr: str, value: Any) -> None:
    """安全地设置 ORM 对象属性，避免 mypy 类型错误"""
    object.__setattr__(obj, attr, value)


class EnumValueConfig(TypedDict):
    value: str
    label: str
    sort_order: int


class EnumTypeConfig(TypedDict):
    name: str
    category: str
    description: str
    values: list[EnumValueConfig]


# 标准枚举定义 - 与 schemas/asset.py 中的 Enum 类保持一致
STANDARD_ENUMS: dict[str, EnumTypeConfig] = {
    "ownership_status": {
        "name": "确权状态",
        "category": "资产管理",
        "description": "资产的确权状态",
        "values": [
            {"value": "已确权", "label": "已确权", "sort_order": 1},
            {"value": "部分确权", "label": "部分确权", "sort_order": 2},
            {"value": "未确权", "label": "未确权", "sort_order": 3},
            {"value": "其它", "label": "其它", "sort_order": 4},
        ],
    },
    "property_nature": {
        "name": "物业性质",
        "category": "资产管理",
        "description": "物业的经营性质分类",
        "values": [
            {"value": "经营类", "label": "经营类", "sort_order": 1},
            {"value": "公房", "label": "公房", "sort_order": 2},
            {"value": "自用", "label": "自用", "sort_order": 3},
            {"value": "其它", "label": "其它", "sort_order": 4},
        ],
    },
    "usage_status": {
        "name": "使用状态",
        "category": "资产管理",
        "description": "资产的使用状态",
        "values": [
            {"value": "出租", "label": "出租", "sort_order": 1},
            {"value": "闲置", "label": "闲置", "sort_order": 2},
            {"value": "自用", "label": "自用", "sort_order": 3},
            {"value": "公房（出租）", "label": "公房（出租）", "sort_order": 4},
            {"value": "公房（闲置）", "label": "公房（闲置）", "sort_order": 5},
            {"value": "其它", "label": "其它", "sort_order": 6},
        ],
    },
    "tenant_type": {
        "name": "租户类型",
        "category": "合同管理",
        "description": "租户的类型分类",
        "values": [
            {"value": "企业", "label": "企业", "sort_order": 1},
            {"value": "个人", "label": "个人", "sort_order": 2},
            {"value": "其它", "label": "其它", "sort_order": 3},
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


async def init_enum_data(
    db: AsyncSession, created_by: str = "system"
) -> dict[str, Any]:
    """
    初始化标准枚举数据

    Args:
        db: 数据库会话
        created_by: 创建人

    Returns:
        初始化结果统计
    """
    stats: dict[str, Any] = {
        "types_created": 0,
        "types_updated": 0,
        "values_created": 0,
        "values_updated": 0,
        "errors": [],
    }

    enum_codes = list(STANDARD_ENUMS.keys())
    try:
        existing_types = await enum_field_type_crud.get_by_codes_async(
            db, codes=enum_codes
        )
    except Exception as e:
        for enum_code in STANDARD_ENUMS:
            error_msg = f"处理枚举类型 {enum_code} 失败: {e}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
        await db.commit()
        logger.info(f"枚举数据初始化完成: {stats}")
        return stats

    existing_types_by_code = {
        str(enum_type.code): enum_type
        for enum_type in existing_types
        if getattr(enum_type, "code", None) is not None
    }
    existing_values_by_type_and_value: dict[tuple[str, str], EnumFieldValue] = {}

    existing_type_ids = [
        str(enum_type.id)
        for enum_type in existing_types
        if getattr(enum_type, "id", None) is not None
    ]
    if existing_type_ids:
        try:
            existing_values = await enum_field_value_crud.get_by_type_ids_async(
                db, enum_type_ids=existing_type_ids
            )
            existing_values_by_type_and_value = {
                (str(value.enum_type_id), str(value.value)): value
                for value in existing_values
                if value.enum_type_id is not None and value.value is not None
            }
        except Exception as e:
            for enum_code in STANDARD_ENUMS:
                error_msg = f"处理枚举类型 {enum_code} 失败: {e}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
            await db.commit()
            logger.info(f"枚举数据初始化完成: {stats}")
            return stats

    for enum_code, enum_config in STANDARD_ENUMS.items():
        try:
            enum_type = existing_types_by_code.get(enum_code)

            if not enum_type:
                # 创建新枚举类型
                enum_type = EnumFieldType()
                _set_attr(enum_type, "code", enum_code)
                _set_attr(enum_type, "name", enum_config["name"])
                _set_attr(enum_type, "category", enum_config.get("category", "其他"))
                _set_attr(
                    enum_type,
                    "description",
                    enum_config.get("description", ""),
                )
                _set_attr(enum_type, "is_system", True)
                _set_attr(enum_type, "status", "active")
                _set_attr(enum_type, "created_by", created_by)
                db.add(enum_type)
                await db.flush()  # 获取ID
                existing_types_by_code[enum_code] = enum_type
                stats["types_created"] += 1
                logger.info(f"创建枚举类型: {enum_code}")
            else:
                # 更新现有枚举类型
                _set_attr(enum_type, "name", enum_config["name"])
                _set_attr(
                    enum_type,
                    "category",
                    enum_config.get("category", enum_type.category),
                )
                _set_attr(
                    enum_type,
                    "description",
                    enum_config.get("description", enum_type.description),
                )
                _set_attr(enum_type, "is_system", True)
                _set_attr(enum_type, "status", "active")
                _set_attr(enum_type, "is_deleted", False)
                _set_attr(enum_type, "updated_by", created_by)
                stats["types_updated"] += 1
                logger.info(f"更新枚举类型: {enum_code}")

            # 处理枚举值
            enum_type_id = getattr(enum_type, "id", None)
            if enum_type_id is None:
                raise ValueError(f"枚举类型 {enum_code} 缺少 id")
            enum_type_id_str = str(enum_type_id)

            for value_config in enum_config["values"]:
                value_dict: EnumValueConfig = value_config
                existing_value = existing_values_by_type_and_value.get(
                    (enum_type_id_str, value_dict["value"])
                )

                if not existing_value:
                    new_value = EnumFieldValue()
                    _set_attr(new_value, "enum_type_id", enum_type_id_str)
                    _set_attr(new_value, "value", value_dict["value"])
                    _set_attr(new_value, "label", value_dict["label"])
                    _set_attr(new_value, "sort_order", value_dict.get("sort_order", 0))
                    _set_attr(new_value, "is_active", True)
                    _set_attr(new_value, "is_deleted", False)
                    _set_attr(new_value, "created_by", created_by)
                    db.add(new_value)
                    existing_values_by_type_and_value[
                        (enum_type_id_str, value_dict["value"])
                    ] = new_value
                    stats["values_created"] += 1
                else:
                    # 更新现有枚举值
                    _set_attr(existing_value, "label", value_dict["label"])
                    _set_attr(
                        existing_value,
                        "sort_order",
                        value_dict.get("sort_order", existing_value.sort_order),
                    )
                    _set_attr(existing_value, "is_active", True)
                    _set_attr(existing_value, "is_deleted", False)
                    _set_attr(existing_value, "updated_by", created_by)
                    stats["values_updated"] += 1

        except Exception as e:
            error_msg = f"处理枚举类型 {enum_code} 失败: {e}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)

    await db.commit()
    logger.info(f"枚举数据初始化完成: {stats}")
    return stats
