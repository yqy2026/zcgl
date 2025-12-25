"""
Fix dictionary Chinese labels that were corrupted during initialization
"""

import os
import sys

# Add project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import SessionLocal
from src.models.enum_field import EnumFieldValue


def fix_dictionary_labels():
    """Fix Chinese labels for all dictionary values"""

    # Correct labels mapping (value -> correct Chinese label)
    correct_labels = {
        # property_nature
        "commercial": "经营性",
        "non_commercial": "非经营性",
        # usage_status
        "rented": "出租",
        "vacant": "空置",
        "self_use": "自用",
        "public_housing": "公房",
        "pending_transfer": "待移交",
        "pending_disposal": "待处置",
        "other": "其他",
        # ownership_status
        "confirmed": "已确权",
        "unconfirmed": "未确权",
        "partial": "部分确权",
        # business_category
        "commercial": "商业",
        "office": "办公",
        "residential": "住宅",
        "warehouse": "仓储",
        "industrial": "工业",
        "other": "其他",
        # tenant_type
        "individual": "个人",
        "enterprise": "企业",
        "government": "政府机构",
        "other": "其他",
        # contract_status
        "active": "生效中",
        "expired": "已到期",
        "terminated": "已终止",
        "pending": "待签署",
        # business_model
        "sublease": "承租转租",
        "entrusted": "委托经营",
        "self_operated": "自营",
        "other": "其他",
        # operation_status
        "normal": "正常经营",
        "suspended": "停业整顿",
        "renovating": "装修中",
        "vacant_for_rent": "待招租",
        # ownership_category
        "state_owned": "国有资产",
        "collective": "集体资产",
        "private": "私有资产",
        "mixed": "混合所有制",
        "other": "其他",
        # certificated_usage
        "commercial": "商业",
        "office": "办公",
        "residential": "住宅",
        "industrial": "工业",
        "other": "其他",
        # actual_usage
        "commercial": "商业",
        "office": "办公",
        "residential": "住宅",
        "industrial": "工业",
        "other": "其他",
    }

    db = SessionLocal()
    updated_count = 0

    try:
        # Get all enum field values
        values = db.query(EnumFieldValue).all()

        print(f"Found {len(values)} dictionary values to check")

        for value in values:
            if value.value in correct_labels:
                correct_label = correct_labels[value.value]
                if value.label != correct_label:
                    old_label = value.label
                    value.label = correct_label
                    updated_count += 1
                    print(f"Updated: {value.value} '{old_label}' -> '{correct_label}'")

        db.commit()
        print(f"\nSuccessfully updated {updated_count} dictionary labels")

        # Show sample of updated labels
        print("\n=== Sample of Updated Labels ===")
        sample_values = db.query(EnumFieldValue).limit(10).all()
        for v in sample_values:
            print(f"{v.value:15} | {v.label:10} | {v.code}")

    except Exception as e:
        print(f"Error updating labels: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    fix_dictionary_labels()
