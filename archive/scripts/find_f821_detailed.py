#!/usr/bin/env python3
"""
更精确地查找F821错误的脚本
"""

import os
import subprocess
import sys
import json

def find_f821_errors_detailed():
    """详细查找F821错误"""
    backend_dir = r"D:\code\zcgl\backend"
    
    try:
        # 使用ruff检查并获取详细输出
        result = subprocess.run(
            ["uv", "run", "ruff", "check", "src/", "--select=F821", "--output-format=full"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        
        if result.stdout:
            print("详细F821错误信息:")
            print(result.stdout)
        
        if result.stderr:
            print("错误输出:")
            print(result.stderr)
            
        return result.stdout
        
    except Exception as e:
        print(f"执行检查时出错: {e}")
        return ""

if __name__ == "__main__":
    errors = find_f821_errors_detailed()