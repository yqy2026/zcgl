#!/usr/bin/env python3
"""
检查后端进程的DEV_MODE设置
"""

import os
import sys
import requests

def check_dev_mode():
    """检查DEV_MODE环境变量"""
    print("=== 检查DEV_MODE环境变量 ===")
    print(f"当前进程DEV_MODE: {os.getenv('DEV_MODE', 'not set')}")
    print(f"所有环境变量:")
    for key, value in os.environ.items():
        if 'DEV' in key or 'MODE' in key:
            print(f"  {key} = {value}")

def test_simple_api():
    """测试简单API调用"""
    print("\n=== 测试API调用 ===")

    try:
        # 测试健康检查
        response = requests.get("http://localhost:8002/api/health", timeout=5)
        print(f"健康检查: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"健康数据: {data}")

        # 测试资产API不带认证
        response = requests.get("http://localhost:8002/api/assets", timeout=5)
        print(f"资产API(无认证): {response.status_code}")
        if response.status_code == 401:
            data = response.json()
            print(f"401错误详情: {data}")

    except Exception as e:
        print(f"API测试失败: {e}")

def test_with_headers():
    """测试带不同头部的API调用"""
    print("\n=== 测试不同认证头部 ===")

    headers_list = [
        {"Authorization": "Bearer mock_token_dev", "Content-Type": "application/json"},
        {"Authorization": "mock_token_dev", "Content-Type": "application/json"},
        {"X-Dev-Mode": "true", "Authorization": "Bearer mock_token_dev", "Content-Type": "application/json"},
    ]

    for i, headers in enumerate(headers_list):
        print(f"\n测试头部配置 {i+1}: {headers}")
        try:
            response = requests.get("http://localhost:8002/api/assets", headers=headers, timeout=5)
            print(f"状态码: {response.status_code}")
            if response.status_code != 200:
                print(f"错误响应: {response.text[:200]}...")
        except Exception as e:
            print(f"请求失败: {e}")

if __name__ == "__main__":
    check_dev_mode()
    test_simple_api()
    test_with_headers()