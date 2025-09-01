#!/usr/bin/env python3
"""
土地物业资产管理系统状态检查脚本
"""

import requests
import json
from datetime import datetime

def check_backend():
    """检查后端服务状态"""
    try:
        # 检查基本健康状态
        response = requests.get("http://localhost:8001/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ 后端服务正常运行")
            print(f"   消息: {data.get('message', 'N/A')}")
            print(f"   时间戳: {data.get('timestamp', 'N/A')}")
            return True
        else:
            print(f"❌ 后端服务响应异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 后端服务连接失败: {e}")
        return False

def check_api_endpoints():
    """检查主要API端点"""
    endpoints = [
        ("/api/v1/assets/", "GET", "资产列表"),
        ("/api/v1/statistics/summary", "GET", "统计摘要"),
        ("/api/v1/occupancy/rate", "GET", "出租率"),
        ("/api/v1/backup/list", "GET", "备份列表"),
    ]
    
    print("\n🔍 检查API端点:")
    for endpoint, method, description in endpoints:
        try:
            url = f"http://localhost:8001{endpoint}"
            response = requests.request(method, url, timeout=5)
            if response.status_code in [200, 404]:  # 404也算正常，因为可能没有数据
                print(f"   ✅ {description} ({endpoint})")
            else:
                print(f"   ⚠️  {description} ({endpoint}) - 状态码: {response.status_code}")
        except Exception as e:
            print(f"   ❌ {description} ({endpoint}) - 错误: {e}")

def check_frontend():
    """检查前端服务状态"""
    try:
        response = requests.get("http://localhost:5174/", timeout=5)
        if response.status_code == 200:
            print("✅ 前端服务正常运行")
            print("   URL: http://localhost:5174/")
            return True
        else:
            print(f"❌ 前端服务响应异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 前端服务连接失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 土地物业资产管理系统状态检查")
    print("=" * 50)
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 检查后端
    backend_ok = check_backend()
    
    # 检查API端点
    if backend_ok:
        check_api_endpoints()
    
    print()
    
    # 检查前端
    frontend_ok = check_frontend()
    
    print()
    print("=" * 50)
    
    if backend_ok and frontend_ok:
        print("🎉 系统运行正常！")
        print("   后端API: http://localhost:8001/")
        print("   API文档: http://localhost:8001/docs")
        print("   前端界面: http://localhost:5174/")
    else:
        print("⚠️  系统存在问题，请检查服务状态")
    
    print()

if __name__ == "__main__":
    main()