#!/usr/bin/env python3
"""
简化测试优化脚本
"""

import os
import subprocess
from pathlib import Path

def run_test(test_file):
    """运行单个测试文件"""
    print(f"\n运行测试: {test_file}")
    try:
        result = subprocess.run(
            f"uv run python -m pytest {test_file} -v",
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"✓ {test_file} 通过")
            return True
        else:
            print(f"✗ {test_file} 失败")
            print(f"错误: {result.stderr}")
            return False
    except Exception as e:
        print(f"执行失败: {e}")
        return False

def main():
    """主函数"""
    print("=== 简化测试优化脚本 ===")

    # 切换到backend目录
    if Path("../backend").exists():
        os.chdir("../backend")

    # 定义优先测试列表
    priority_tests = [
        "tests/simple_ocr_test.py",
        "tests/ocr_basic_test.py",
        "tests/final_ocr_test.py",
        "tests/test_simple_database.py"
    ]

    print("\n=== 运行优先测试 ===")
    passed = 0
    total = len(priority_tests)

    for test in priority_tests:
        if Path(test).exists():
            if run_test(test):
                passed += 1
        else:
            print(f"! 测试文件不存在: {test}")

    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")

    # 运行覆盖率测试
    print("\n=== 生成覆盖率报告 ===")
    working_tests = []
    for test in priority_tests:
        if Path(test).exists():
            working_tests.append(test)

    if working_tests:
        test_string = " ".join(working_tests)
        cmd = f"uv run python -m pytest {test_string} --cov=src --cov-report=term-missing"
        print(f"执行: {cmd}")

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("错误:", result.stderr)

    print("\n=== 完成 ===")

if __name__ == "__main__":
    main()