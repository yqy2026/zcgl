#!/usr/bin/env python3
"""
Test DeepSeek-VL2 for Structured Extraction
测试 DeepSeek-VL2 结构化合同提取

Usage:
    cd backend
    python scripts/test_deepseek_vl2.py
"""

import asyncio
import base64
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load .env
load_dotenv()


async def test_structured_extraction():
    """Test DeepSeek-VL2 for structured JSON extraction"""

    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.siliconflow.cn/v1")
    # Use DeepSeek-VL2 for vision understanding, not OCR
    model = "deepseek-ai/DeepSeek-VL2"

    print("=" * 60)
    print("DeepSeek-VL2 Structured Extraction Test")
    print("=" * 60)
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")

    if not api_key:
        print("[ERROR] DEEPSEEK_API_KEY not set")
        return

    # Find test PDF
    pdf_path = Path(
        "D:/code/zcgl/tools/pdf-samples/【包装合字（2025）第022号】租赁合同-番禺区洛浦南浦环岛西路29号1号商业楼14号铺-王军20250401-20280331.pdf"
    )

    if not pdf_path.exists():
        print(f"[ERROR] PDF not found: {pdf_path}")
        return

    print(f"\n[INFO] PDF: {pdf_path.name}")

    # Convert first page to image
    try:
        import fitz

        doc = fitz.open(str(pdf_path))
        page = doc[0]
        mat = fitz.Matrix(150 / 72, 150 / 72)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        print(f"[INFO] Converted page 1 to image ({len(img_bytes)/1024:.1f} KB)")
        doc.close()
    except Exception as e:
        print(f"[ERROR] Failed to convert PDF: {e}")
        return

    # Structured extraction prompt with JSON format requirement
    prompt = """请分析这份中国房地产租赁合同图片，提取以下信息并返回JSON格式：

{
    "contract_number": "合同编号",
    "sign_date": "签订日期(YYYY-MM-DD)",
    "landlord_name": "出租方/甲方名称",
    "landlord_legal_rep": "法定代表人",
    "landlord_phone": "甲方联系电话",
    "tenant_name": "承租方/乙方名称",
    "tenant_id": "身份证号或统一社会信用代码",
    "tenant_phone": "乙方联系电话",
    "property_address": "租赁物业地址",
    "property_area": "建筑面积(数字,平方米)",
    "lease_start_date": "合同开始日期(YYYY-MM-DD)",
    "lease_end_date": "合同结束日期(YYYY-MM-DD)",
    "deposit": "押金/保证金(数字)",
    "monthly_rent": "月租金(数字)"
}

重要提示：
1. 金额只填数字，日期格式YYYY-MM-DD，找不到的字段填null
2. 只返回JSON，不要其他说明文字"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_base64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
    }

    print(f"\n[INFO] Sending request to {base_url}/chat/completions...")

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{base_url}/chat/completions", json=payload, headers=headers
            )

            print(f"[INFO] Status: {response.status_code}")

            if response.status_code != 200:
                print(f"[ERROR] API Error: {response.text}")
                return

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            print(f"[INFO] Tokens: {usage}")
            print("\n" + "=" * 60)
            print("EXTRACTION RESULT")
            print("=" * 60)

            # Try to parse as JSON
            try:
                result = json.loads(content)
                print(json.dumps(result, ensure_ascii=False, indent=2))
            except json.JSONDecodeError:
                print("[WARNING] Response is not valid JSON:")
                print(content)

    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_structured_extraction())
