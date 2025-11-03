#!/usr/bin/env python3
"""
查找backend目录中所有F821错误的脚本
"""

import os
import subprocess
import sys
import json

def find_f821_errors():
    """查找F821错误"""
    backend_dir = r"D:\code\zcgl\backend"
    
    try:
        # 尝试使用ruff检查
        result = subprocess.run(
            ["uv", "run", "ruff", "check", "src/", "--select=F821", "--output-format=json"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        
        if result.stdout:
            try:
                errors = json.loads(result.stdout)
                print(f"找到 {len(errors)} 个F821错误:")
                for error in errors:
                    file_path = error.get('filename', '')
                    line = error.get('line', 0)
                    column = error.get('column', 0)
                    message = error.get('message', '')
                    code = error.get('code', '')
                    
                    if code == 'F821':
                        print(f"文件: {file_path}")
                        print(f"位置: 行 {line}, 列 {column}")
                        print(f"错误: {message}")
                        print(f"错误码: {code}")
                        print("-" * 50)
                
                return errors
            except json.JSONDecodeError:
                print("无法解析ruff输出，尝试其他方法...")
        
        # 如果ruff失败，使用pyflakes
        print("尝试使用pyflakes...")
        result = subprocess.run(
            ["uv", "run", "pyflakes", "src/"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        
        if result.stdout:
            lines = result.stdout.split('\n')
            f821_lines = [line for line in lines if 'undefined name' in line.lower()]
            print(f"找到 {len(f821_lines)} 个未定义名称错误:")
            for line in f821_lines:
                print(line)
            return f821_lines
        
        print("未找到F821错误")
        return []
        
    except Exception as e:
        print(f"执行检查时出错: {e}")
        return []

if __name__ == "__main__":
    errors = find_f821_errors()