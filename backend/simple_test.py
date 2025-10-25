#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的API测试验证
"""
import sys
import subprocess

def main():
    """主函数"""
    # 运行单个测试
    result = subprocess.run([
        sys.executable,
        "-m", "pytest",
        "tests/test_api.py::test_root_endpoint",
        "-v",
        "--tb=short"
    ], capture_output=True, text=True, encoding='utf-8')

    print(f"退出码: {result.returncode}")
    if result.stdout:
        # 只显示最后几行
        lines = result.stdout.strip().split('\n')[-5:]
        for line in lines:
            print(f"输出: {line}")
    if result.stderr:
        print(f"错误: {result.stderr.strip()[:200]}")

if __name__ == "__main__":
    main()