"""
字典初始化脚本
运行此脚本来初始化系统所需的字典数据
"""

import asyncio
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.api.v1.system.dictionaries import (
    SimpleDictionaryCreate,
    quick_create_dictionary,
)
from src.database import async_session_scope, create_tables


async def init_asset_dictionaries():
    """初始化资产管理相关的字典数据"""

    print("=" * 60)
    print("初始化资产管理字典数据")
    print("=" * 60)

    # 定义所有需要初始化的字典
    dictionaries_config = {
        "property_nature": {
            "description": "物业性质分类",
            "options": [
                {"label": "经营性", "value": "commercial", "code": "commercial"},
                {
                    "label": "非经营性",
                    "value": "non_commercial",
                    "code": "non_commercial",
                },
            ],
        },
        "usage_status": {
            "description": "资产使用状态分类",
            "options": [
                {"label": "出租", "value": "rented", "code": "rented"},
                {"label": "空置", "value": "vacant", "code": "vacant"},
                {"label": "自用", "value": "self_use", "code": "self_use"},
                {"label": "公房", "value": "public_housing", "code": "public_housing"},
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
            "description": "资产确权状态分类",
            "options": [
                {"label": "已确权", "value": "confirmed", "code": "confirmed"},
                {"label": "未确权", "value": "unconfirmed", "code": "unconfirmed"},
                {"label": "部分确权", "value": "partial", "code": "partial"},
            ],
        },
        "business_category": {
            "description": "资产业态分类",
            "options": [
                {"label": "商业", "value": "commercial", "code": "commercial"},
                {"label": "办公", "value": "office", "code": "office"},
                {"label": "住宅", "value": "residential", "code": "residential"},
                {"label": "仓储", "value": "warehouse", "code": "warehouse"},
                {"label": "工业", "value": "industrial", "code": "industrial"},
                {"label": "其他", "value": "other", "code": "other"},
            ],
        },
        "tenant_type": {
            "description": "租户类型分类",
            "options": [
                {"label": "个人", "value": "individual", "code": "individual"},
                {"label": "企业", "value": "enterprise", "code": "enterprise"},
                {"label": "政府机构", "value": "government", "code": "government"},
                {"label": "其他", "value": "other", "code": "other"},
            ],
        },
        "contract_status": {
            "description": "租赁合同状态分类",
            "options": [
                {"label": "生效中", "value": "active", "code": "active"},
                {"label": "已到期", "value": "expired", "code": "expired"},
                {"label": "已终止", "value": "terminated", "code": "terminated"},
                {"label": "待签署", "value": "pending", "code": "pending"},
            ],
        },
        "business_model": {
            "description": "资产接收模式分类",
            "options": [
                {"label": "承租转租", "value": "sublease", "code": "sublease"},
                {"label": "委托经营", "value": "entrusted", "code": "entrusted"},
                {"label": "自营", "value": "self_operated", "code": "self_operated"},
                {"label": "其他", "value": "other", "code": "other"},
            ],
        },
        "operation_status": {
            "description": "资产经营状态分类",
            "options": [
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
        "ownership_category": {
            "description": "权属类别分类",
            "options": [
                {"label": "国有资产", "value": "state_owned", "code": "state_owned"},
                {"label": "集体资产", "value": "collective", "code": "collective"},
                {"label": "私有资产", "value": "private", "code": "private"},
                {"label": "混合所有制", "value": "mixed", "code": "mixed"},
                {"label": "其他", "value": "other", "code": "other"},
            ],
        },
    }

    created_count = 0
    skipped_count = 0

    try:
        async with async_session_scope() as db:
            for dict_type, config in dictionaries_config.items():
                print(f"\n处理字典: {dict_type} - {config.get('description', '')}")

                try:
                    dictionary_data = SimpleDictionaryCreate(
                        options=config["options"], description=config.get("description")
                    )

                    await quick_create_dictionary(
                        dict_type=dict_type, dictionary_data=dictionary_data, db=db
                    )

                    print(f"  ✅ 创建成功: {len(config['options'])} 个选项")
                    created_count += 1

                except Exception as e:
                    if "已存在" in str(e):
                        print("  ⚠️  字典已存在，跳过")
                        skipped_count += 1
                    else:
                        print(f"  ❌ 创建失败: {e}")

    except Exception as e:
        print(f"\n❌ 初始化过程中发生错误: {e}")
        return False

    print("\n" + "=" * 60)
    print("初始化完成!")
    print(f"✅ 成功创建: {created_count} 个字典")
    print(f"⚠️  跳过已存在: {skipped_count} 个字典")
    print(f"📊 总计处理: {len(dictionaries_config)} 个字典")
    print("=" * 60)

    return True


async def main():
    """主函数"""
    try:
        # 确保数据库表存在
        await create_tables()

        # 运行异步初始化
        await init_asset_dictionaries()

        print("\n🎉 字典初始化完成！现在可以在前端使用这些字典了。")

    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
