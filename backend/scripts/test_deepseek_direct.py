#!/usr/bin/env python3
"""
Direct DeepSeek-OCR API Test
直接测试硅基流动 DeepSeek-OCR API

Usage:
    cd backend
    python scripts/test_deepseek_direct.py
"""

import asyncio
import base64
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load .env
load_dotenv()


async def test_direct_api():
    """Test DeepSeek-OCR API directly"""

    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.siliconflow.cn/v1")
    model = os.getenv("DEEPSEEK_VISION_MODEL", "deepseek-ai/DeepSeek-OCR")

    print("=" * 60)
    print("DeepSeek-OCR Direct API Test")
    print("=" * 60)
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")

    if not api_key:
        print("[ERROR] DEEPSEEK_API_KEY not set")
        return

    # Find test PDF and convert first page to image
    pdf_path = Path(
        "D:/code/zcgl/tools/pdf-samples/【包装合字（2025）第022号】租赁合同-番禺区洛浦南浦环岛西路29号1号商业楼14号铺-王军20250401-20280331.pdf"
    )

    if not pdf_path.exists():
        print(f"[ERROR] PDF not found: {pdf_path}")
        return

    print(f"\n[INFO] PDF: {pdf_path.name}")

    # Convert first page to image using PyMuPDF
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(str(pdf_path))
        page = doc[0]  # First page only

        # Render at 150 DPI for good quality
        mat = fitz.Matrix(150 / 72, 150 / 72)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")

        print(f"[INFO] Converted page 1 to image ({len(img_bytes) / 1024:.1f} KB)")
        doc.close()
    except Exception as e:
        print(f"[ERROR] Failed to convert PDF: {e}")
        return

    # Build API request - Simple OCR prompt for DeepSeek-OCR
    # DeepSeek-OCR is designed for OCR, not structured extraction
    prompt = "请识别这份文档中的所有文字内容，按原文格式输出。"

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
        "max_tokens": 4096,
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
            print("OCR RESULT (First 2000 chars)")
            print("=" * 60)
            print(content[:2000])

            if len(content) > 2000:
                print(f"\n... ({len(content) - 2000} more characters)")

    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_direct_api())
