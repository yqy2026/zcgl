"""Quick test for single image extraction"""
from dotenv import load_dotenv
load_dotenv('.env')
import httpx
import os
import base64
import fitz

pdf_path = r'D:\ccode\zcgl\tools\pdf-samples\【包装合字（2025）第022号】租赁合同-番禺区洛浦南浦环岛西路29号1号商业楼14号铺-王军20250401-20280331.pdf'

# Convert first page to image with lower resolution
doc = fitz.open(pdf_path)
page = doc[0]
pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 108 DPI
img_data = pix.tobytes('png')
doc.close()
img_base64 = base64.b64encode(img_data).decode()
print(f'Image base64 length: {len(img_base64)}')

api_key = os.getenv('LLM_API_KEY')
print(f'API key: {api_key[:10]}...')

payload = {
    'model': 'glm-4v',
    'messages': [{
        'role': 'user',
        'content': [
            {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{img_base64}'}},
            {'type': 'text', 'text': '这是什么合同？合同编号是多少？'}
        ]
    }]
}

print('Sending request to glm-4v...')
try:
    response = httpx.post(
        'https://open.bigmodel.cn/api/paas/v4/chat/completions',
        json=payload,
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        timeout=120
    )
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print('SUCCESS!')
        print('Content:', data['choices'][0]['message']['content'])
        print('Usage:', data.get('usage'))
    else:
        print('ERROR:', response.text[:1500])
except Exception as e:
    print(f'Exception: {e}')
