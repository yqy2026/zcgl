#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查API状态并修复最关键的问题
"""

import subprocess
import sys
from pathlib import Path

def run_api_consistency_check():
    """运行API一致性检查"""
    try:
        print("运行API一致性检查...")
        result = subprocess.run([
            'python', '-m', 'pytest',
            'tests/test_api_consistency.py',
            '-v', '--tb=short'
        ], capture_output=True, text=True, cwd='backend')

        print("API一致性检查结果:")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        print("返回码:", result.returncode)

        return result.returncode == 0
    except Exception as e:
        print(f"API一致性检查失败: {str(e)}")
        return False

def check_missing_apis():
    """检查缺失的API"""
    missing_apis_file = Path("backend/src/api/v1/missing_apis.py")
    if missing_apis_file.exists():
        print("OK missing_apis.py 文件存在")

        # 检查文件内容
        with open(missing_apis_file, 'r', encoding='utf-8') as f:
            content = f.read()

        if 'missing_apis_router' in content and len(content) > 1000:
            print("OK missing_apis.py 包含API路由定义")
        else:
            print("ERROR missing_apis.py 可能不完整")
    else:
        print("ERROR missing_apis.py 文件不存在")

def check_api_registration():
    """检查API路由注册"""
    init_file = Path("backend/src/api/v1/__init__.py")
    if init_file.exists():
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()

        if 'missing_apis_router' in content and 'missing_apis_router' in content:
            print("OK missing_apis_router 已注册")
        else:
            print("ERROR missing_apis_router 未注册")
    else:
        print("ERROR __init__.py 文件不存在")

def main():
    """主函数"""
    print("检查API状态...")

    print("\n1. 检查缺失的API文件...")
    check_missing_apis()

    print("\n2. 检查API路由注册...")
    check_api_registration()

    print("\n3. 运行API一致性检查...")
    success = run_api_consistency_check()

    if success:
        print("\nOK API一致性检查通过")
    else:
        print("\nERROR API一致性检查失败")

if __name__ == "__main__":
    main()