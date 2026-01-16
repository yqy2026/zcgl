"""Direct test of async vision API call"""
from dotenv import load_dotenv

load_dotenv('.env')
import asyncio
import base64
import os
import sys

import httpx

sys.path.insert(0, 'src')
from services.document.pdf_to_images import pdf_to_images


async def test():
    pdf = r'D:\ccode\zcgl\tools\pdf-samples\【包装合字（2025）第022号】租赁合同-番禺区洛浦南浦环岛西路29号1号商业楼14号铺-王军20250401-20280331.pdf'

    # Convert PDF to image
    images = pdf_to_images(pdf, max_pages=1, dpi=150)
    print(f'Created image: {images[0]}')

    # Read and encode
    with open(images[0], 'rb') as f:
        img_base64 = base64.b64encode(f.read()).decode()
    print(f'Base64 length: {len(img_base64)}')

    api_key = os.getenv('LLM_API_KEY')
    print(f'API key: {api_key[:15]}...')

    payload = {
        'model': 'glm-4v',
        'messages': [{
            'role': 'user',
            'content': [
                {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{img_base64}'}},
                {'type': 'text', 'text': '这是什么合同？合同编号是多少？'}
            ]
        }],
        'temperature': 0.1
    }

    print('Sending async request...')
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            'https://open.bigmodel.cn/api/paas/v4/chat/completions',
            json=payload,
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        )
        print(f'Status: {response.status_code}')
        if response.status_code == 200:
            data = response.json()
            print('SUCCESS!')
            print('Content:', data['choices'][0]['message']['content'])
        else:
            print('ERROR:', response.text[:800])

if __name__ == '__main__':
    asyncio.run(test())
