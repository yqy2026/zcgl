#!/usr/bin/env python3
"""
专门测试Excel预览功能是否读取真实数据
"""

import requests
import pandas as pd

def test_preview_real_data():
    """测试预览功能是否读取真实Excel数据"""
    
    # 1. 创建一个包含特定数据的Excel文件
    test_data = {
        "物业名称": ["真实测试物业X", "真实测试物业Y"],
        "地址": ["真实地址X", "真实地址Y"],
        "确权状态": ["已确权", "未确权"],
        "物业性质": ["经营性", "经营性"],
        "使用状态": ["出租", "自用"],
        "权属方": ["国有", "集体"]
    }
    
    df = pd.DataFrame(test_data)
    test_filename = "specific_test_preview.xlsx"
    df.to_excel(test_filename, index=False)
    
    print(f"✅ 创建测试文件: {test_filename}")
    print(f"   第一行数据: {test_data['物业名称'][0]}")
    
    # 2. 发送预览请求
    url = "http://localhost:8001/api/v1/excel/preview"
    
    with open(test_filename, "rb") as f:
        files = {
            "file": (test_filename, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        }
        
        response = requests.post(url, files=files)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 预览请求成功")
            print(f"   返回的第一行物业名称: {data['data'][0]['物业名称']}")
            
            # 检查是否返回真实数据
            expected_name = "真实测试物业X"
            actual_name = data['data'][0]['物业名称']
            
            if actual_name == expected_name:
                print("🎉 预览功能正确读取了真实Excel数据！")
                return True
            else:
                print(f"❌ 预览功能返回的是模拟数据，期望: {expected_name}, 实际: {actual_name}")
                return False
        else:
            print(f"❌ 预览请求失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False

if __name__ == "__main__":
    print("🔍 专门测试Excel预览功能")
    print("=" * 50)
    test_preview_real_data()