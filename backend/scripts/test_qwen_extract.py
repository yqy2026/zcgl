#!/usr/bin/env python3
"""
Qwen-VL Multi-Page Extraction Test
通义千问 Qwen-VL 多页合同提取测试

Usage:
    cd backend
    python scripts/test_qwen_extract.py
"""

import asyncio
import base64
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()


async def test_qwen_extraction():
    """Test Qwen-VL for multi-page contract extraction"""

    api_key = os.getenv("DASHSCOPE_API_KEY")
    base_url = os.getenv(
        "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    model = os.getenv("QWEN_VISION_MODEL", "qwen-vl-plus")

    print("=" * 60)
    print("Qwen-VL Multi-Page Extraction Test")
    print("=" * 60)
    print(f"Model: {model}")

    if not api_key:
        print("[ERROR] DASHSCOPE_API_KEY not set")
        return

    pdf_path = Path(
        "D:/code/zcgl/tools/pdf-samples/【包装合字（2025）第022号】租赁合同-番禺区洛浦南浦环岛西路29号1号商业楼14号铺-王军20250401-20280331.pdf"
    )

    if not pdf_path.exists():
        print("[ERROR] PDF not found")
        return

    # Convert pages to images
    try:
        import fitz

        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        print(f"[INFO] PDF has {total_pages} pages")

        # Process first 3 pages
        pages_to_process = min(3, total_pages)
        images_base64 = []

        for i in range(pages_to_process):
            page = doc[i]
            mat = fitz.Matrix(120 / 72, 120 / 72)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            img_base64 = base64.b64encode(img_bytes).decode("utf-8")
            images_base64.append(img_base64)
            print(f"[INFO] Page {i+1}: {len(img_bytes)/1024:.1f} KB")

        doc.close()
    except Exception as e:
        print(f"[ERROR] Failed to convert PDF: {e}")
        return

    # Build content
    content = []
    for img_b64 in images_base64:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            }
        )

    prompt = """请仔细分析这份租赁合同的所有页面图片，提取准确信息并返回JSON：

{
    "contract_number": "合同编号（完整，如：包装合字（2025）第022号）",
    "landlord_name": "出租方/甲方名称",
    "landlord_legal_rep": "法定代表人",
    "landlord_phone": "甲方联系电话",
    "tenant_name": "承租方/乙方名称",
    "tenant_id": "身份证号",
    "tenant_phone": "乙方联系电话",
    "property_address": "物业地址",
    "property_area": "建筑面积(数字)",
    "lease_start_date": "租赁起始日期(YYYY-MM-DD)",
    "lease_end_date": "租赁结束日期(YYYY-MM-DD)",
    "deposit": "押金(数字)",
    "rent_terms": [
        {
            "start_date": "开始日期",
            "end_date": "结束日期",
            "monthly_rent": "月租金(数字)"
        }
    ]
}

关键提示：
1. 租金表格在第2或第3页，请仔细识别每个时期的月租金
2. 合同期限是2025年4月1日至2028年3月31日
3. 只返回JSON"""

    content.append({"type": "text", "text": prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.1,
        "max_tokens": 2000,
    }

    print(f"\n[INFO] Sending {len(images_base64)} pages to {model}...")

    try:
        async with httpx.AsyncClient(timeout=180) as client:
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

            # Parse JSON
            json_str = content.strip()
            if "```" in json_str:
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]

            try:
                result = json.loads(json_str)
                print(json.dumps(result, ensure_ascii=False, indent=2))

                if "rent_terms" in result:
                    print("\n" + "-" * 40)
                    print("RENT TERMS:")
                    for term in result["rent_terms"]:
                        print(
                            f"  {term.get('start_date')} ~ {term.get('end_date')}: ¥{term.get('monthly_rent')}/月"
                        )
            except:
                print(content)

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_qwen_extraction())
