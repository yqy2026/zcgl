# backend/scripts/seed_property_cert_prompts.py
"""
Seed Property Certificate Prompts
初始化产权证提取Prompt模板
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.database import get_session_factory


def seed_prompts(db):
    """创建产权证提取Prompt模板"""

    now = datetime.now(timezone.utc)
    prompts = [
        {
            "name": "property_cert_extraction_v1",
            "doc_type": "PROPERTY_CERT",
            "provider": "qwen",
            "description": "不动产权证（新版）提取Prompt",
            "system_prompt": "你是一个专业的文档信息提取助手，负责从中国不动产权证图像中提取结构化信息。",
            "user_prompt_template": """请分析这份中国不动产权证图像，提取以下信息并返回JSON格式：

{
    "certificate_number": "不动产权证号",
    "registration_date": "登记日期(YYYY-MM-DD)",
    "owner_name": "权利人姓名",
    "owner_id_type": "证件类型",
    "owner_id_number": "证件号码",
    "property_address": "坐落地址",
    "property_type": "用途(住宅/商业/工业/办公)",
    "building_area": "建筑面积",
    "land_area": "土地使用面积",
    "floor_info": "楼层信息",
    "land_use_type": "土地使用权类型(出让/划拨)",
    "land_use_term_start": "土地使用期限起(YYYY-MM-DD)",
    "land_use_term_end": "土地使用期限止(YYYY-MM-DD)",
    "co_ownership": "共有情况",
    "restrictions": "权利限制情况",
    "remarks": "备注"
}

提取规则：
1. 日期格式统一使用 YYYY-MM-DD
2. 面积只填数字，不需要单位
3. 确保证件号码和证书编号完整准确
4. 找不到的字段填 null
5. 只返回JSON，不要其他说明

文件名：{file_name}""",
            "version": "1.0.0",
            "status": "active",
            "tags": json.dumps(["optimized", "stable"]),
            "few_shot_examples": None,
            "avg_accuracy": 0.0,
            "avg_confidence": 0.0,
            "total_usage": 0,
            "current_version_id": None,
            "parent_id": None,
            "created_by": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "name": "property_cert_house_extraction_v1",
            "doc_type": "PROPERTY_CERT",
            "provider": "qwen",
            "description": "房屋所有权证（旧版）提取Prompt",
            "system_prompt": "你是一个专业的文档信息提取助手，负责从中国房屋所有权证图像中提取结构化信息。",
            "user_prompt_template": """请分析这份中国房屋所有权证图像，提取以下信息并返回JSON格式：

{
    "certificate_number": "房产证编号",
    "registration_date": "登记日期(YYYY-MM-DD)",
    "owner_name": "权利人姓名",
    "owner_id_type": "证件类型",
    "owner_id_number": "证件号码",
    "property_address": "房屋坐落",
    "property_type": "房屋性质",
    "building_area": "建筑面积",
    "floor_info": "楼层信息"
}

提取规则：
1. 房屋所有权证只包含房屋信息，不包含土地信息
2. 日期格式统一使用 YYYY-MM-DD
3. 面积只填数字，不需要单位
4. 找不到的字段填 null
5. 只返回JSON，不要其他说明

文件名：{file_name}""",
            "version": "1.0.0",
            "status": "active",
            "tags": json.dumps(["stable"]),
            "few_shot_examples": None,
            "avg_accuracy": 0.0,
            "avg_confidence": 0.0,
            "total_usage": 0,
            "current_version_id": None,
            "parent_id": None,
            "created_by": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "name": "property_cert_land_extraction_v1",
            "doc_type": "PROPERTY_CERT",
            "provider": "qwen",
            "description": "土地使用证提取Prompt",
            "system_prompt": "你是一个专业的文档信息提取助手，负责从中国土地使用证图像中提取结构化信息。",
            "user_prompt_template": """请分析这份中国土地使用证图像，提取以下信息并返回JSON格式：

{
    "certificate_number": "土地使用证号",
    "registration_date": "登记日期(YYYY-MM-DD)",
    "owner_name": "土地使用者姓名",
    "owner_id_type": "证件类型",
    "owner_id_number": "证件号码",
    "property_address": "土地坐落",
    "land_area": "土地面积",
    "land_use_type": "土地用途",
    "land_use_term_start": "使用期限起(YYYY-MM-DD)",
    "land_use_term_end": "使用期限止(YYYY-MM-DD)"
}

提取规则：
1. 土地使用证只包含土地信息，不包含房屋信息
2. 日期格式统一使用 YYYY-MM-DD
3. 面积只填数字，不需要单位
4. 找不到的字段填 null
5. 只返回JSON，不要其他说明

文件名：{file_name}""",
            "version": "1.0.0",
            "status": "active",
            "tags": json.dumps(["stable"]),
            "few_shot_examples": None,
            "avg_accuracy": 0.0,
            "avg_confidence": 0.0,
            "total_usage": 0,
            "current_version_id": None,
            "parent_id": None,
            "created_by": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "name": "property_cert_other_extraction_v1",
            "doc_type": "PROPERTY_CERT",
            "provider": "qwen",
            "description": "其他权属证明提取Prompt",
            "system_prompt": "你是一个专业的文档信息提取助手，负责从权属证明图像中提取结构化信息。",
            "user_prompt_template": """请分析这份权属证明图像，提取以下信息并返回JSON格式：

{
    "certificate_number": "证明编号",
    "registration_date": "登记日期(YYYY-MM-DD)",
    "owner_name": "权利人姓名",
    "owner_id_type": "证件类型",
    "owner_id_number": "证件号码",
    "property_address": "地址",
    "remarks": "备注"
}

提取规则：
1. 提取所有可见的关键信息
2. 日期格式统一使用 YYYY-MM-DD
3. 找不到的字段填 null
4. 只返回JSON，不要其他说明

文件名：{file_name}""",
            "version": "1.0.0",
            "status": "active",
            "tags": json.dumps(["fallback"]),
            "few_shot_examples": None,
            "avg_accuracy": 0.0,
            "avg_confidence": 0.0,
            "total_usage": 0,
            "current_version_id": None,
            "parent_id": None,
            "created_by": None,
            "created_at": now,
            "updated_at": now,
        },
    ]

    # Insert prompts using raw SQL
    for prompt_data in prompts:
        prompt_id = str(uuid.uuid4())
        sql_data = {k: v for k, v in prompt_data.items() if k != 'metadata'}
        query = text("""
            INSERT INTO prompt_templates (
                id, name, doc_type, provider, description,
                system_prompt, user_prompt_template, few_shot_examples,
                version, status, tags, avg_accuracy, avg_confidence,
                total_usage, current_version_id, parent_id, created_by,
                created_at, updated_at
            ) VALUES (
                :id, :name, :doc_type, :provider, :description,
                :system_prompt, :user_prompt_template, :few_shot_examples,
                :version, :status, :tags, :avg_accuracy, :avg_confidence,
                :total_usage, :current_version_id, :parent_id, :created_by,
                :created_at, :updated_at
            )
        """)
        db.execute(query, {**sql_data, "id": prompt_id})
        print(f"Created prompt: {prompt_data['name']}")

    db.commit()
    print(f"\nSeeded {len(prompts)} property certificate prompts")


if __name__ == "__main__":
    session_factory = get_session_factory()
    db = session_factory()
    try:
        seed_prompts(db)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()
