"""Debug script to compare working vs failing API calls"""
from dotenv import load_dotenv

load_dotenv('.env')
import asyncio
import base64
import os
import sys

import httpx

sys.path.insert(0, 'src')
from services.core.zhipu_vision_service import ZhipuVisionService
from services.document.pdf_to_images import pdf_to_images

pdf = r'D:\ccode\zcgl\tools\pdf-samples\【包装合字（2025）第022号】租赁合同-番禺区洛浦南浦环岛西路29号1号商业楼14号铺-王军20250401-20280331.pdf'
images = pdf_to_images(pdf, max_pages=1, dpi=150)
img_path = images[0]

with open(img_path, 'rb') as f:
    img_base64 = base64.b64encode(f.read()).decode('utf-8')

api_key = os.getenv('LLM_API_KEY')
short_prompt = '这份合同的合同编号是什么？'
long_prompt = """请分析这份中国房地产租赁合同图片，提取以下信息并返回JSON格式：

{
    "contract_number": "合同编号",
    "landlord_name": "出租方名称"
}

请只返回JSON。"""

async def test_direct(prompt, label):
    """Direct API call - this typically works"""
    payload = {
        'model': 'glm-4v',
        'messages': [{
            'role': 'user',
            'content': [
                {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{img_base64}'}},
                {'type': 'text', 'text': prompt}
            ]
        }],
        'temperature': 0.1
    }

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            'https://open.bigmodel.cn/api/paas/v4/chat/completions',
            json=payload,
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        )
        print(f'[{label}] Status: {response.status_code}')
        if response.status_code == 200:
            print(f'[{label}] SUCCESS: {response.json()["choices"][0]["message"]["content"][:100]}')
        else:
            print(f'[{label}] ERROR: {response.text[:200]}')

async def test_service(prompt, label):
    """Using ZhipuVisionService - this fails"""
    svc = ZhipuVisionService()
    try:
        result = await svc.extract_from_images([img_path], prompt, temperature=0.1)
        print(f'[{label}] SUCCESS: {result.content[:100]}')
    except Exception as e:
        print(f'[{label}] ERROR: {e}')

async def main():
    print('=' * 60)
    print('Test 1: Direct call with short prompt')
    await test_direct(short_prompt, 'DIRECT-SHORT')

    print('\n' + '=' * 60)
    print('Test 2: Direct call with long prompt')
    await test_direct(long_prompt, 'DIRECT-LONG')

    print('\n' + '=' * 60)
    print('Test 3: Service call with short prompt')
    await test_service(short_prompt, 'SERVICE-SHORT')

    print('\n' + '=' * 60)
    print('Test 4: Service call with long prompt')
    await test_service(long_prompt, 'SERVICE-LONG')

if __name__ == '__main__':
    asyncio.run(main())
