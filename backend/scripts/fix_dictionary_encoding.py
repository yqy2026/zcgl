"""
Direct database fix for Chinese labels encoding issue using raw SQLite
"""

import sqlite3
import sys
import os

def fix_dictionary_encoding():
    """Fix Chinese encoding issues directly in SQLite database"""

    # Correct labels mapping
    correct_labels = {
        # property_nature
        'commercial': '经营性',
        'non_commercial': '非经营性',

        # usage_status
        'rented': '出租',
        'vacant': '空置',
        'self_use': '自用',
        'public_housing': '公房',
        'pending_transfer': '待移交',
        'pending_disposal': '待处置',
        'other': '其他',

        # ownership_status
        'confirmed': '已确权',
        'unconfirmed': '未确权',
        'partial': '部分确权',

        # business_category - note: commercial maps to 商业 here
        'office': '办公',
        'residential': '住宅',
        'warehouse': '仓储',
        'industrial': '工业',

        # tenant_type
        'individual': '个人',
        'enterprise': '企业',
        'government': '政府机构',

        # contract_status
        'active': '生效中',
        'expired': '已到期',
        'terminated': '已终止',
        'pending': '待签署',

        # business_model
        'sublease': '承租转租',
        'entrusted': '委托经营',
        'self_operated': '自营',

        # operation_status
        'normal': '正常经营',
        'suspended': '停业整顿',
        'renovating': '装修中',
        'vacant_for_rent': '待招租',

        # ownership_category
        'state_owned': '国有资产',
        'collective': '集体资产',
        'private': '私有资产',
        'mixed': '混合所有制',

        # certificated_usage - note: commercial maps to 商业 here
        'office': '办公',
        'residential': '住宅',
        'industrial': '工业',

        # actual_usage - note: commercial maps to 商业 here
        'office': '办公',
        'residential': '住宅',
        'industrial': '工业'
    }

    # Connect to database with UTF-8 encoding
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'land_property.db')
    conn = sqlite3.connect(db_path)
    conn.text_factory = str  # Ensure proper Unicode handling
    cursor = conn.cursor()

    try:
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")

        # Get all enum field values with their types
        cursor.execute("""
            SELECT
                ev.id,
                ev.value,
                ev.label,
                et.code as type_code
            FROM enum_field_values ev
            JOIN enum_field_types et ON ev.enum_type_id = et.id
        """)

        rows = cursor.fetchall()
        updated_count = 0

        print(f"Found {len(rows)} dictionary values to check")

        for row in rows:
            id_val, value, current_label, type_code = row

            # Determine correct label based on type_code and value
            correct_label = None

            if type_code == 'property_nature':
                correct_label = correct_labels.get(value)
            elif type_code == 'usage_status':
                correct_label = correct_labels.get(value)
            elif type_code == 'ownership_status':
                correct_label = correct_labels.get(value)
            elif type_code == 'business_category':
                if value == 'commercial':
                    correct_label = '商业'
                else:
                    correct_label = correct_labels.get(value)
            elif type_code == 'tenant_type':
                correct_label = correct_labels.get(value)
            elif type_code == 'contract_status':
                correct_label = correct_labels.get(value)
            elif type_code == 'business_model':
                correct_label = correct_labels.get(value)
            elif type_code == 'operation_status':
                correct_label = correct_labels.get(value)
            elif type_code == 'ownership_category':
                correct_label = correct_labels.get(value)
            elif type_code == 'certificated_usage':
                if value == 'commercial':
                    correct_label = '商业'
                else:
                    correct_label = correct_labels.get(value)
            elif type_code == 'actual_usage':
                if value == 'commercial':
                    correct_label = '商业'
                else:
                    correct_label = correct_labels.get(value)

            if correct_label and current_label != correct_label:
                print(f"Updating {type_code}.{value}: '{current_label}' -> '{correct_label}'")
                cursor.execute(
                    "UPDATE enum_field_values SET label = ? WHERE id = ?",
                    (correct_label, id_val)
                )
                updated_count += 1

        conn.commit()
        print(f"\nSuccessfully updated {updated_count} dictionary labels")

        # Show verification
        print("\n=== Verification of Updated Labels ===")
        cursor.execute("""
            SELECT ev.value, ev.label, et.code as type_code
            FROM enum_field_values ev
            JOIN enum_field_types et ON ev.enum_type_id = et.id
            ORDER BY et.code, ev.value
            LIMIT 20
        """)

        verification_rows = cursor.fetchall()
        for value, label, type_code in verification_rows:
            print(f'{type_code:15} | {value:15} | {label:10}')

    except Exception as e:
        print(f"Error updating labels: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    fix_dictionary_encoding()