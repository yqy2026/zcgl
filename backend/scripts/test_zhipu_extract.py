#!/usr/bin/env python3
"""
Zhipu GLM-4V Multi-Page Extraction Test
智谱 GLM-4V 多页合同提取测试

Usage:
    cd backend  
    python scripts/test_zhipu_extract.py
"""

import asyncio
import base64
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()


async def test_zhipu_extraction():
    """Test Zhipu GLM-4V for multi-page contract extraction"""
    
    api_key = os.getenv("ZHIPU_API_KEY") or os.getenv("LLM_API_KEY")
    base_url = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    # 测试 GLM-4.6V-Flash 轻量高速版本
    model = "glm-4.6v-flash"
    
    print("=" * 60)
    print("Zhipu GLM-4V Multi-Page Extraction Test")
    print("=" * 60)
    print(f"Model: {model}")
    
    if not api_key:
        print("[ERROR] ZHIPU_API_KEY not set")
        print("Please set ZHIPU_API_KEY in .env")
        return
    
    pdf_path = Path("D:/code/zcgl/tools/pdf-samples/【包装合字（2025）第022号】租赁合同-番禺区洛浦南浦环岛西路29号1号商业楼14号铺-王军20250401-20280331.pdf")
    
    if not pdf_path.exists():
        print(f"[ERROR] PDF not found")
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
            mat = fitz.Matrix(120/72, 120/72)
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
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"}
        })
    
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
2. 只返回JSON，不要其他说明"""

    content.append({"type": "text", "text": prompt})
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # Note: GLM-4V doesn't support max_tokens parameter
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.1
    }
    
    print(f"\n[INFO] Sending {len(images_base64)} pages to {model}...")
    
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers
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
                parts = json_str.split("```")
                for part in parts:
                    if part.strip().startswith("json"):
                        json_str = part.strip()[4:]
                        break
                    elif part.strip().startswith("{"):
                        json_str = part.strip()
                        break
            
            try:
                result = json.loads(json_str)
                print(json.dumps(result, ensure_ascii=False, indent=2))
                
                if "rent_terms" in result:
                    print("\n" + "-" * 40)
                    print("RENT TERMS:")
                    for term in result["rent_terms"]:
                        print(f"  {term.get('start_date')} ~ {term.get('end_date')}: ¥{term.get('monthly_rent')}/月")
            except:
                print(content)
            
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_zhipu_extraction())
