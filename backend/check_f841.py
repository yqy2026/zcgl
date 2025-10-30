#!/usr/bin/env python3
"""检查F841未使用变量错误的脚本"""

import subprocess
import sys

def check_f841():
    """运行ruff检查F841错误"""
    try:
        result = subprocess.run(
            ['ruff', 'check', 'src/', '--select=F841'],
            capture_output=True,
            text=True,
            cwd='.',
            encoding='utf-8',
            errors='replace'
        )
        
        print("=== F841 未使用变量错误检查 ===")
        print(f"返回码: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            print(f"\n发现 {len(lines)} 个F841错误:")
            for i, line in enumerate(lines, 1):
                print(f"{i}. {line}")
        
        return result.stdout, result.returncode
        
    except Exception as e:
        print(f"运行ruff时出错: {e}")
        return "", 1

if __name__ == "__main__":
    check_f841()