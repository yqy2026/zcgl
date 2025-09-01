#!/usr/bin/env python3
"""
测试资产CRUD功能
"""

import requests
import json
from datetime import datetime

def test_crud():
    base_url = 'http://localhost:8001'
    
    print('🔍 测试资产CRUD功能')
    print('=' * 40)
    
    # 1. 获取资产列表
    print('1. 获取资产列表...')
    r = requests.get(f'{base_url}/api/v1/assets/')
    if r.status_code == 200:
        data = r.json()
        print(f'   ✅ 成功，共 {len(data.get("items", []))} 项资产')
    else:
        print(f'   ❌ 失败: {r.status_code}')
        return False
    
    # 2. 创建资产
    print('\n2. 创建测试资产...')
    test_asset = {
        'property_name': f'系统测试物业_{datetime.now().strftime("%H%M%S")}',
        'address': '系统测试地址123号',
        'ownership_status': '已确权',
        'property_nature': '经营性',
        'usage_status': '出租',
        'ownership_entity': '国有'
    }
    
    r = requests.post(f'{base_url}/api/v1/assets/', json=test_asset)
    if r.status_code == 201:
        created = r.json()
        asset_id = created.get('id')
        print(f'   ✅ 成功创建，ID: {asset_id}')
    else:
        print(f'   ❌ 创建失败: {r.status_code}')
        print(f'   错误: {r.text}')
        return False
    
    # 3. 获取单个资产
    print('\n3. 获取资产详情...')
    r = requests.get(f'{base_url}/api/v1/assets/{asset_id}')
    if r.status_code == 200:
        print('   ✅ 成功获取详情')
    else:
        print(f'   ❌ 获取失败: {r.status_code}')
    
    # 4. 更新资产
    print('\n4. 更新资产...')
    update_data = {'notes': '系统测试更新'}
    r = requests.put(f'{base_url}/api/v1/assets/{asset_id}', json=update_data)
    if r.status_code == 200:
        print('   ✅ 成功更新')
    else:
        print(f'   ❌ 更新失败: {r.status_code}')
    
    # 5. 删除资产
    print('\n5. 删除测试资产...')
    r = requests.delete(f'{base_url}/api/v1/assets/{asset_id}')
    if r.status_code == 200:
        print('   ✅ 成功删除')
    else:
        print(f'   ❌ 删除失败: {r.status_code}')
    
    print('\n✅ 资产CRUD功能测试完成')
    return True

if __name__ == "__main__":
    test_crud()