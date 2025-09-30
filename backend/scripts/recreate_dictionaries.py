"""
Recreate dictionary data with proper Chinese encoding
"""

import sys
import os

# Add project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.models.enum_field import EnumFieldType, EnumFieldValue


def recreate_dictionaries():
    """Recreate all dictionary data with proper Chinese encoding"""

    db = SessionLocal()

    try:
        # Delete all existing enum field values and types
        print("Clearing existing dictionary data...")
        db.query(EnumFieldValue).delete()
        db.query(EnumFieldType).delete()
        db.commit()
        print("Existing data cleared.")

        # Dictionary configuration with proper Chinese labels
        dictionaries_config = {
            'property_nature': {
                'name': '物业性质',
                'category': '资产属性',
                'description': '物业性质分类',
                'options': [
                    {'label': '经营性', 'value': 'commercial', 'code': 'commercial'},
                    {'label': '非经营性', 'value': 'non_commercial', 'code': 'non_commercial'}
                ]
            },
            'usage_status': {
                'name': '使用状态',
                'category': '资产状态',
                'description': '资产使用状态分类',
                'options': [
                    {'label': '出租', 'value': 'rented', 'code': 'rented'},
                    {'label': '空置', 'value': 'vacant', 'code': 'vacant'},
                    {'label': '自用', 'value': 'self_use', 'code': 'self_use'},
                    {'label': '公房', 'value': 'public_housing', 'code': 'public_housing'},
                    {'label': '待移交', 'value': 'pending_transfer', 'code': 'pending_transfer'},
                    {'label': '待处置', 'value': 'pending_disposal', 'code': 'pending_disposal'},
                    {'label': '其他', 'value': 'other', 'code': 'other'}
                ]
            },
            'ownership_status': {
                'name': '权属状态',
                'category': '资产状态',
                'description': '资产权属状态分类',
                'options': [
                    {'label': '已确权', 'value': 'confirmed', 'code': 'confirmed'},
                    {'label': '未确权', 'value': 'unconfirmed', 'code': 'unconfirmed'},
                    {'label': '部分确权', 'value': 'partial', 'code': 'partial'}
                ]
            },
            'business_category': {
                'name': '业态分类',
                'category': '资产分类',
                'description': '资产业态分类',
                'options': [
                    {'label': '商业', 'value': 'commercial', 'code': 'commercial'},
                    {'label': '办公', 'value': 'office', 'code': 'office'},
                    {'label': '住宅', 'value': 'residential', 'code': 'residential'},
                    {'label': '仓储', 'value': 'warehouse', 'code': 'warehouse'},
                    {'label': '工业', 'value': 'industrial', 'code': 'industrial'},
                    {'label': '其他', 'value': 'other', 'code': 'other'}
                ]
            },
            'tenant_type': {
                'name': '租户类型',
                'category': '租赁信息',
                'description': '租户类型分类',
                'options': [
                    {'label': '个人', 'value': 'individual', 'code': 'individual'},
                    {'label': '企业', 'value': 'enterprise', 'code': 'enterprise'},
                    {'label': '政府机构', 'value': 'government', 'code': 'government'},
                    {'label': '其他', 'value': 'other', 'code': 'other'}
                ]
            },
            'contract_status': {
                'name': '合同状态',
                'category': '租赁信息',
                'description': '合同状态分类',
                'options': [
                    {'label': '生效中', 'value': 'active', 'code': 'active'},
                    {'label': '已到期', 'value': 'expired', 'code': 'expired'},
                    {'label': '已终止', 'value': 'terminated', 'code': 'terminated'},
                    {'label': '待签署', 'value': 'pending', 'code': 'pending'}
                ]
            },
            'business_model': {
                'name': '接收模式',
                'category': '接收信息',
                'description': '接收模式分类',
                'options': [
                    {'label': '承租转租', 'value': 'sublease', 'code': 'sublease'},
                    {'label': '委托经营', 'value': 'entrusted', 'code': 'entrusted'},
                    {'label': '自营', 'value': 'self_operated', 'code': 'self_operated'},
                    {'label': '其他', 'value': 'other', 'code': 'other'}
                ]
            },
            'operation_status': {
                'name': '经营状态',
                'category': '经营信息',
                'description': '经营状态分类',
                'options': [
                    {'label': '正常经营', 'value': 'normal', 'code': 'normal'},
                    {'label': '停业整顿', 'value': 'suspended', 'code': 'suspended'},
                    {'label': '装修中', 'value': 'renovating', 'code': 'renovating'},
                    {'label': '待招租', 'value': 'vacant_for_rent', 'code': 'vacant_for_rent'}
                ]
            },
            'ownership_category': {
                'name': '权属类别',
                'category': '资产属性',
                'description': '权属类别分类',
                'options': [
                    {'label': '国有资产', 'value': 'state_owned', 'code': 'state_owned'},
                    {'label': '集体资产', 'value': 'collective', 'code': 'collective'},
                    {'label': '私有资产', 'value': 'private', 'code': 'private'},
                    {'label': '混合所有制', 'value': 'mixed', 'code': 'mixed'},
                    {'label': '其他', 'value': 'other', 'code': 'other'}
                ]
            },
            'certificated_usage': {
                'name': '证载用途',
                'category': '资产用途',
                'description': '证载用途分类',
                'options': [
                    {'label': '商业', 'value': 'commercial', 'code': 'commercial'},
                    {'label': '办公', 'value': 'office', 'code': 'office'},
                    {'label': '住宅', 'value': 'residential', 'code': 'residential'},
                    {'label': '工业', 'value': 'industrial', 'code': 'industrial'},
                    {'label': '其他', 'value': 'other', 'code': 'other'}
                ]
            },
            'actual_usage': {
                'name': '实际用途',
                'category': '资产用途',
                'description': '实际用途分类',
                'options': [
                    {'label': '商业', 'value': 'commercial', 'code': 'commercial'},
                    {'label': '办公', 'value': 'office', 'code': 'office'},
                    {'label': '住宅', 'value': 'residential', 'code': 'residential'},
                    {'label': '工业', 'value': 'industrial', 'code': 'industrial'},
                    {'label': '其他', 'value': 'other', 'code': 'other'}
                ]
            }
        }

        print("Creating dictionary types and values...")
        created_types = 0
        created_values = 0

        for dict_code, config in dictionaries_config.items():
            print(f"\nProcessing: {dict_code} - {config['name']}")

            # Create enum field type
            enum_type = EnumFieldType(
                code=dict_code,
                name=config['name'],
                category=config['category'],
                description=config['description'],
                is_system=True,
                is_multiple=False,
                is_hierarchical=False,
                status='active'
            )

            db.add(enum_type)
            db.flush()  # Get the ID
            created_types += 1

            # Create enum field values
            for i, option in enumerate(config['options']):
                enum_value = EnumFieldValue(
                    enum_type_id=enum_type.id,
                    label=option['label'],
                    value=option['value'],
                    code=option['code'],
                    sort_order=i + 1,
                    is_active=True
                )

                db.add(enum_value)
                created_values += 1

            print(f"  Created type: {config['name']}")
            print(f"  Created {len(config['options'])} values")

        db.commit()
        print(f"\n" + "="*60)
        print(f"Dictionary recreation complete!")
        print(f"Created {created_types} dictionary types")
        print(f"Created {created_values} dictionary values")
        print("="*60)

        # Verify the data
        print("\n=== Verification ===")
        types = db.query(EnumFieldType).all()
        for t in types:
            print(f"{t.code}: {t.name} ({t.category})")
            values = db.query(EnumFieldValue).filter(EnumFieldValue.enum_type_id == t.id).all()
            for v in values[:3]:  # Show first 3 values
                print(f"  {v.value}: {v.label}")
            if len(values) > 3:
                print(f"  ... and {len(values) - 3} more")
            print()

    except Exception as e:
        print(f"Error recreating dictionaries: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    recreate_dictionaries()