"""
字典数据迁移脚本
将系统字典数据迁移到枚举字段，并初始化资产相关的字典
"""

import asyncio
import os
import sys
import uuid

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select

from src.database import async_session_scope, create_tables
from src.models.system_dictionary import SystemDictionary
from src.models.enum_field import EnumFieldType, EnumFieldValue


async def migrate_system_dictionaries():
    """迁移现有系统字典到枚举字段"""
    try:
        async with async_session_scope() as db:
            print("开始迁移系统字典...")

            dict_type_result = await db.execute(
                select(SystemDictionary.dict_type).distinct()
            )
            dict_types = dict_type_result.all()

            migrated_count = 0

            for dict_type_row in dict_types:
                dict_type = dict_type_row[0]
                if not dict_type:
                    continue

                print(f"迁移字典类型: {dict_type}")

                existing_enum_result = await db.execute(
                    select(EnumFieldType).where(EnumFieldType.code == dict_type)
                )
                existing_enum_type = existing_enum_result.scalars().first()

                if existing_enum_type:
                    print(f"  枚举类型 {dict_type} 已存在，跳过")
                    continue

                enum_type = EnumFieldType(
                    id=str(uuid.uuid4()),
                    name=dict_type.replace("_", " ").title(),
                    code=dict_type,
                    category="系统字典迁移",
                    description=f"从系统字典迁移的 {dict_type}",
                    is_system=True,
                    is_hierarchical=False,
                    is_multiple=False,
                    status="active",
                    created_by="系统迁移",
                    updated_by="系统迁移",
                )
                db.add(enum_type)
                await db.flush()

                dict_items_result = await db.execute(
                    select(SystemDictionary)
                    .where(SystemDictionary.dict_type == dict_type)
                    .order_by(SystemDictionary.sort_order)
                )
                dict_items = list(dict_items_result.scalars().all())

                for item in dict_items:
                    enum_value = EnumFieldValue(
                        id=str(uuid.uuid4()),
                        enum_type_id=enum_type.id,
                        label=item.dict_label,
                        value=item.dict_value,
                        code=item.dict_code,
                        sort_order=item.sort_order,
                        is_active=item.is_active,
                        level=1,
                        created_by="系统迁移",
                        updated_by="系统迁移",
                    )
                    db.add(enum_value)

                migrated_count += 1
                print(f"  迁移完成，包含 {len(dict_items)} 个选项")

            await db.commit()
            print(f"系统字典迁移完成，共迁移 {migrated_count} 个字典类型")

    except Exception as e:
        print(f"迁移失败: {e}")
        raise


async def initialize_asset_dictionaries():
    """初始化资产相关的字典数据"""
    try:
        async with async_session_scope() as db:
            print("初始化资产相关字典...")

            # 定义资产相关的字典数据
            asset_dictionaries = {
                "property_nature": {
                    "name": "物业性质",
                    "description": "资产物业性质分类",
                    "values": [
                        {"label": "经营性", "value": "commercial", "code": "commercial"},
                        {
                            "label": "非经营性",
                            "value": "non_commercial",
                            "code": "non_commercial",
                        },
                    ],
                },
                "usage_status": {
                    "name": "使用状态",
                    "description": "资产使用状态分类",
                    "values": [
                        {"label": "出租", "value": "rented", "code": "rented"},
                        {"label": "空置", "value": "vacant", "code": "vacant"},
                        {"label": "自用", "value": "self_use", "code": "self_use"},
                        {
                            "label": "公房",
                            "value": "public_housing",
                            "code": "public_housing",
                        },
                        {
                            "label": "待移交",
                            "value": "pending_transfer",
                            "code": "pending_transfer",
                        },
                        {
                            "label": "待处置",
                            "value": "pending_disposal",
                            "code": "pending_disposal",
                        },
                        {"label": "其他", "value": "other", "code": "other"},
                    ],
                },
                "ownership_status": {
                    "name": "确权状态",
                    "description": "资产确权状态分类",
                    "values": [
                        {"label": "已确权", "value": "confirmed", "code": "confirmed"},
                        {"label": "未确权", "value": "unconfirmed", "code": "unconfirmed"},
                        {"label": "部分确权", "value": "partial", "code": "partial"},
                    ],
                },
                "business_category": {
                    "name": "业态类别",
                    "description": "资产业态分类",
                    "values": [
                        {"label": "商业", "value": "commercial", "code": "commercial"},
                        {"label": "办公", "value": "office", "code": "office"},
                        {"label": "住宅", "value": "residential", "code": "residential"},
                        {"label": "仓储", "value": "warehouse", "code": "warehouse"},
                        {"label": "工业", "value": "industrial", "code": "industrial"},
                        {"label": "其他", "value": "other", "code": "other"},
                    ],
                },
                "tenant_type": {
                    "name": "租户类型",
                    "description": "租户类型分类",
                    "values": [
                        {"label": "个人", "value": "individual", "code": "individual"},
                        {"label": "企业", "value": "enterprise", "code": "enterprise"},
                        {"label": "政府机构", "value": "government", "code": "government"},
                        {"label": "其他", "value": "other", "code": "other"},
                    ],
                },
                "contract_status": {
                    "name": "合同状态",
                    "description": "租赁合同状态分类",
                    "values": [
                        {"label": "生效中", "value": "active", "code": "active"},
                        {"label": "已到期", "value": "expired", "code": "expired"},
                        {"label": "已终止", "value": "terminated", "code": "terminated"},
                        {"label": "待签署", "value": "pending", "code": "pending"},
                    ],
                },
                "business_model": {
                    "name": "接收模式",
                    "description": "资产接收模式分类",
                    "values": [
                        {"label": "承租转租", "value": "sublease", "code": "sublease"},
                        {"label": "委托经营", "value": "entrusted", "code": "entrusted"},
                        {
                            "label": "自营",
                            "value": "self_operated",
                            "code": "self_operated",
                        },
                        {"label": "其他", "value": "other", "code": "other"},
                    ],
                },
                "operation_status": {
                    "name": "经营状态",
                    "description": "资产经营状态分类",
                    "values": [
                        {"label": "正常经营", "value": "normal", "code": "normal"},
                        {"label": "停业整顿", "value": "suspended", "code": "suspended"},
                        {"label": "装修中", "value": "renovating", "code": "renovating"},
                        {
                            "label": "待招租",
                            "value": "vacant_for_rent",
                            "code": "vacant_for_rent",
                        },
                    ],
                },
            }

            created_count = 0

            for dict_code, dict_config in asset_dictionaries.items():
                existing_result = await db.execute(
                    select(EnumFieldType).where(EnumFieldType.code == dict_code)
                )
                existing_type = existing_result.scalars().first()

                if existing_type:
                    print(f"  字典 {dict_code} 已存在，跳过")
                    continue

                print(f"创建字典: {dict_code} - {dict_config['name']}")

                enum_type = EnumFieldType(
                    id=str(uuid.uuid4()),
                    name=dict_config["name"],
                    code=dict_code,
                    category="资产管理",
                    description=dict_config["description"],
                    is_system=True,
                    is_hierarchical=False,
                    is_multiple=False,
                    status="active",
                    created_by="系统初始化",
                    updated_by="系统初始化",
                )
                db.add(enum_type)
                await db.flush()

                for i, value_config in enumerate(dict_config["values"]):
                    enum_value = EnumFieldValue(
                        id=str(uuid.uuid4()),
                        enum_type_id=enum_type.id,
                        label=value_config["label"],
                        value=value_config["value"],
                        code=value_config["code"],
                        sort_order=i + 1,
                        is_active=True,
                        level=1,
                        created_by="系统初始化",
                        updated_by="系统初始化",
                    )
                    db.add(enum_value)

                created_count += 1
                print(f"  创建完成，包含 {len(dict_config['values'])} 个选项")

            await db.commit()
            print(f"资产字典初始化完成，共创建 {created_count} 个字典类型")

    except Exception as e:
        print(f"初始化失败: {e}")
        raise


async def main():
    """主函数"""
    print("=" * 50)
    print("字典数据迁移和初始化")
    print("=" * 50)

    try:
        # 确保数据库表存在
        await create_tables()

        # 1. 迁移现有系统字典
        await migrate_system_dictionaries()

        # 2. 初始化资产相关字典
        await initialize_asset_dictionaries()

        print("\n" + "=" * 50)
        print("迁移和初始化完成！")
        print("=" * 50)

    except Exception as e:
        print(f"\n迁移失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
