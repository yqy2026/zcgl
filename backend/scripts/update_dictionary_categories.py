"""
Update dictionary categories to match frontend configuration
"""

import asyncio
import os
import sys

# Add project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select, update

from src.database import async_session_scope


async def update_dictionary_categories():
    """Update dictionary categories to match frontend config"""

    # Category mapping from frontend config
    category_mapping = {
        "property_nature": "资产属性",
        "usage_status": "资产状态",
        "ownership_status": "资产状态",
        "business_category": "资产分类",
        "tenant_type": "租赁信息",
        "contract_status": "租赁信息",
        "revenue_mode": "经营信息",
        "operation_status": "经营信息",
        "ownership_category": "资产属性",
        "certificated_usage": "资产用途",
        "actual_usage": "资产用途",
    }

    updated_count = 0

    try:
        from src.models.enum_field import EnumFieldType

        async with async_session_scope() as db:
            for code, category in category_mapping.items():
                result = await db.execute(
                    update(EnumFieldType)
                    .where(EnumFieldType.code == code)
                    .values(category=category)
                )
                if (result.rowcount or 0) > 0:
                    print(f"Updated {code}: {category}")
                    updated_count += 1

            await db.commit()
            print(f"\nSuccessfully updated {updated_count} dictionary categories")

            # Show updated categories
            print("\n=== Updated Categories ===")
            enum_types = list(
                (await db.execute(select(EnumFieldType))).scalars().all()
            )
            categories = set()

            for et in enum_types:
                categories.add(et.category)
                print(f"{et.code:20} | {et.name:15} | {et.category or '未分类':10}")

            print(f"\n=== All Categories: {sorted(list(categories))}")

    except Exception as e:
        print(f"Error updating categories: {e}")


if __name__ == "__main__":
    asyncio.run(update_dictionary_categories())

