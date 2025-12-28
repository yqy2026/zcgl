"""
Update dictionary categories to match frontend configuration
"""

import os
import sys

# Add project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import SessionLocal


def update_dictionary_categories():
    """Update dictionary categories to match frontend config"""

    # Category mapping from frontend config
    category_mapping = {
        "property_nature": "资产属性",
        "usage_status": "资产状态",
        "ownership_status": "资产状态",
        "business_category": "资产分类",
        "tenant_type": "租赁信息",
        "contract_status": "租赁信息",
        "business_model": "接收信息",
        "operation_status": "经营信息",
        "ownership_category": "资产属性",
        "certificated_usage": "资产用途",
        "actual_usage": "资产用途",
    }

    db = SessionLocal()
    updated_count = 0

    try:
        from src.models.enum_field import EnumFieldType

        for code, category in category_mapping.items():
            # Update each enum field type category
            result = (
                db.query(EnumFieldType)
                .filter(EnumFieldType.code == code)
                .update({"category": category})
            )

            if result > 0:
                print(f"Updated {code}: {category}")
                updated_count += 1

        db.commit()
        print(f"\nSuccessfully updated {updated_count} dictionary categories")

        # Show updated categories
        print("\n=== Updated Categories ===")
        enum_types = db.query(EnumFieldType).all()
        categories = set()

        for et in enum_types:
            categories.add(et.category)
            print(f'{et.code:20} | {et.name:15} | {et.category or "未分类":10}')

        print(f"\n=== All Categories: {sorted(list(categories))}")

    except Exception as e:
        print(f"Error updating categories: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    update_dictionary_categories()
