#!/usr/bin/env python3
"""
Multi-Page Contract Extraction Test
多页合同提取测试 - 完整提取租金条款

Usage:
    cd backend
    python scripts/devtools/experiments/test_multipage_extract.py
"""

import asyncio
import base64
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()


async def test_multipage_extraction():
    """Test multi-page contract extraction with rent terms"""

    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.siliconflow.cn/v1")
    model = "deepseek-ai/DeepSeek-VL2"

    print("=" * 60)
    print("Multi-Page Contract Extraction Test")
    print("=" * 60)

    if not api_key:
        print("[ERROR] DEEPSEEK_API_KEY not set")
        return

    pdf_path = Path(
        "D:/code/zcgl/tools/pdf-samples/【包装合字（2025）第022号】租赁合同-番禺区洛浦南浦环岛西路29号1号商业楼14号铺-王军20250401-20280331.pdf"
    )

    if not pdf_path.exists():
        print("[ERROR] PDF not found")
        return

    # Convert multiple pages to images
    try:
        import fitz

        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        print(f"[INFO] PDF has {total_pages} pages")

        # Process first 3 pages (usually contains key info + rent table)
        pages_to_process = min(3, total_pages)
        images_base64 = []

        for i in range(pages_to_process):
            page = doc[i]
            mat = fitz.Matrix(120 / 72, 120 / 72)  # Lower DPI to save tokens
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            img_base64 = base64.b64encode(img_bytes).decode("utf-8")
            images_base64.append(img_base64)
            print(f"[INFO] Page {i + 1}: {len(img_bytes) / 1024:.1f} KB")

        doc.close()
    except Exception as e:
        print(f"[ERROR] Failed to convert PDF: {e}")
        return

    # Build content with multiple images
    content = []
    for i, img_b64 in enumerate(images_base64):
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            }
        )

    # Improved prompt for rent terms extraction
    prompt = """请分析这份中国房地产租赁合同的所有页面，提取以下信息并返回JSON格式：

{
    "contract_number": "合同编号（如：包装合字（2025）第022号）",
    "sign_date": "签订日期(YYYY-MM-DD)",
    "landlord_name": "出租方/甲方名称",
    "landlord_legal_rep": "法定代表人",
    "tenant_name": "承租方/乙方名称",
    "tenant_id": "身份证号",
    "tenant_phone": "乙方联系电话",
    "property_address": "租赁物业完整地址",
    "property_area": "建筑面积(数字)",
    "lease_start_date": "租赁起始日期(YYYY-MM-DD)",
    "lease_end_date": "租赁结束日期(YYYY-MM-DD)",
    "deposit": "押金(数字)",
    "rent_terms": [
        {
            "start_date": "该期开始日期(YYYY-MM-DD)",
            "end_date": "该期结束日期(YYYY-MM-DD)",
            "monthly_rent": "月租金(数字)",
            "description": "说明(如:第一年/递增3%等)"
        }
    ]
}

重要提示：
1. 仔细查看租金表格，每个时间段的租金都要列出来
2. 金额只填数字，日期格式YYYY-MM-DD
3. 合同编号要完整准确（包括年份和序号）
4. 只返回JSON，不要其他说明"""

    content.append({"type": "text", "text": prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.1,
        "max_tokens": 1500,
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
            print(f"[INFO] Cost: ~¥{usage.get('total_tokens', 0) * 0.99 / 1000000:.4f}")

            print("\n" + "=" * 60)
            print("EXTRACTION RESULT")
            print("=" * 60)

            # Clean and parse JSON
            json_str = content.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]

            try:
                result = json.loads(json_str)
                print(json.dumps(result, ensure_ascii=False, indent=2))

                # Highlight rent terms
                if "rent_terms" in result:
                    print("\n" + "-" * 40)
                    print("RENT TERMS EXTRACTED:")
                    print("-" * 40)
                    for term in result["rent_terms"]:
                        print(
                            f"  {term.get('start_date')} ~ {term.get('end_date')}: ¥{term.get('monthly_rent')}/月"
                        )
            except json.JSONDecodeError:
                print("[WARNING] Response is not valid JSON:")
                print(content)

    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_multipage_extraction())
