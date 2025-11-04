#!/usr/bin/env python3
"""
检查Python语法错误的简单脚本
"""

import ast
import os

def check_syntax_errors():
    """检查语法错误"""
    backend_dir = r"D:\code\zcgl\backend\src"
    errors = 0
    
    for root, dirs, files in os.walk(backend_dir):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    ast.parse(content)
                except SyntaxError as e:
                    print(f'语法错误在 {path}: {e}')
                    errors += 1
                except Exception as e:
                    # 忽略其他错误（如编码问题）
                    pass
    
    print(f'总共发现 {errors} 个语法错误')
    return errors

if __name__ == "__main__":
    check_syntax_errors()