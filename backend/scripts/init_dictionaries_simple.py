"""
Simple dictionary initialization script without Unicode characters
"""

import sys
import os
import asyncio

# Add project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from src.database import SessionLocal, create_tables
from src.api.v1.dictionaries import quick_create_dictionary, SimpleDictionaryCreate


async def init_asset_dictionaries():
    """Initialize asset management dictionary data"""

    print("=" * 60)
    print("Initializing asset management dictionary data")
    print("=" * 60)

    # Define all dictionaries to initialize
    dictionaries_config = {
        "property_nature": {
            "description": "Property nature classification",
            "options": [
                {"label": "经营性", "value": "commercial", "code": "commercial"},
                {"label": "非经营性", "value": "non_commercial", "code": "non_commercial"}
            ]
        },
        "usage_status": {
            "description": "Asset usage status classification",
            "options": [
                {"label": "出租", "value": "rented", "code": "rented"},
                {"label": "空置", "value": "vacant", "code": "vacant"},
                {"label": "自用", "value": "self_use", "code": "self_use"},
                {"label": "公房", "value": "public_housing", "code": "public_housing"},
                {"label": "待移交", "value": "pending_transfer", "code": "pending_transfer"},
                {"label": "待处置", "value": "pending_disposal", "code": "pending_disposal"},
                {"label": "其他", "value": "other", "code": "other"}
            ]
        },
        "ownership_status": {
            "description": "Asset ownership status classification",
            "options": [
                {"label": "已确权", "value": "confirmed", "code": "confirmed"},
                {"label": "未确权", "value": "unconfirmed", "code": "unconfirmed"},
                {"label": "部分确权", "value": "partial", "code": "partial"}
            ]
        },
        "business_category": {
            "description": "Asset business category classification",
            "options": [
                {"label": "商业", "value": "commercial", "code": "commercial"},
                {"label": "办公", "value": "office", "code": "office"},
                {"label": "住宅", "value": "residential", "code": "residential"},
                {"label": "仓储", "value": "warehouse", "code": "warehouse"},
                {"label": "工业", "value": "industrial", "code": "industrial"},
                {"label": "其他", "value": "other", "code": "other"}
            ]
        },
        "tenant_type": {
            "description": "Tenant type classification",
            "options": [
                {"label": "个人", "value": "individual", "code": "individual"},
                {"label": "企业", "value": "enterprise", "code": "enterprise"},
                {"label": "政府机构", "value": "government", "code": "government"},
                {"label": "其他", "value": "other", "code": "other"}
            ]
        },
        "contract_status": {
            "description": "Rental contract status classification",
            "options": [
                {"label": "生效中", "value": "active", "code": "active"},
                {"label": "已到期", "value": "expired", "code": "expired"},
                {"label": "已终止", "value": "terminated", "code": "terminated"},
                {"label": "待签署", "value": "pending", "code": "pending"}
            ]
        },
        "business_model": {
            "description": "Asset business model classification",
            "options": [
                {"label": "承租转租", "value": "sublease", "code": "sublease"},
                {"label": "委托经营", "value": "entrusted", "code": "entrusted"},
                {"label": "自营", "value": "self_operated", "code": "self_operated"},
                {"label": "其他", "value": "other", "code": "other"}
            ]
        },
        "operation_status": {
            "description": "Asset operation status classification",
            "options": [
                {"label": "正常经营", "value": "normal", "code": "normal"},
                {"label": "停业整顿", "value": "suspended", "code": "suspended"},
                {"label": "装修中", "value": "renovating", "code": "renovating"},
                {"label": "待招租", "value": "vacant_for_rent", "code": "vacant_for_rent"}
            ]
        },
        "ownership_category": {
            "description": "Ownership category classification",
            "options": [
                {"label": "国有资产", "value": "state_owned", "code": "state_owned"},
                {"label": "集体资产", "value": "collective", "code": "collective"},
                {"label": "私有资产", "value": "private", "code": "private"},
                {"label": "混合所有制", "value": "mixed", "code": "mixed"},
                {"label": "其他", "value": "other", "code": "other"}
            ]
        },
        "certificated_usage": {
            "description": "Certificated usage classification",
            "options": [
                {"label": "商业", "value": "commercial", "code": "commercial"},
                {"label": "办公", "value": "office", "code": "office"},
                {"label": "住宅", "value": "residential", "code": "residential"},
                {"label": "工业", "value": "industrial", "code": "industrial"},
                {"label": "其他", "value": "other", "code": "other"}
            ]
        },
        "actual_usage": {
            "description": "Actual usage classification",
            "options": [
                {"label": "商业", "value": "commercial", "code": "commercial"},
                {"label": "办公", "value": "office", "code": "office"},
                {"label": "住宅", "value": "residential", "code": "residential"},
                {"label": "工业", "value": "industrial", "code": "industrial"},
                {"label": "其他", "value": "other", "code": "other"}
            ]
        }
    }

    db = SessionLocal()
    created_count = 0
    skipped_count = 0

    try:
        for dict_type, config in dictionaries_config.items():
            print(f"\nProcessing dictionary: {dict_type} - {config.get('description', '')}")

            try:
                # Create dictionary data
                dictionary_data = SimpleDictionaryCreate(
                    options=config["options"],
                    description=config.get("description")
                )

                # Call API to create dictionary
                result = await quick_create_dictionary(
                    dict_type=dict_type,
                    dictionary_data=dictionary_data,
                    db=db
                )

                print(f"  SUCCESS: Created {len(config['options'])} options")
                created_count += 1

            except Exception as e:
                if "已存在" in str(e) or "already exists" in str(e):
                    print(f"  WARNING: Dictionary already exists, skipping")
                    skipped_count += 1
                else:
                    print(f"  ERROR: Failed to create - {e}")

    except Exception as e:
        print(f"\nERROR: Initialization failed - {e}")
        return False

    finally:
        db.close()

    print(f"\n" + "=" * 60)
    print(f"Initialization complete!")
    print(f"SUCCESS: Created {created_count} dictionaries")
    print(f"WARNING: Skipped {skipped_count} existing dictionaries")
    print(f"TOTAL: Processed {len(dictionaries_config)} dictionaries")
    print("=" * 60)

    return True


def main():
    """Main function"""
    try:
        # Ensure database tables exist
        create_tables()

        # Run async initialization
        asyncio.run(init_asset_dictionaries())

        print("\nDictionary initialization complete! You can now use these dictionaries in the frontend.")

    except Exception as e:
        print(f"\nInitialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()