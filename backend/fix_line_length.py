#!/usr/bin/env python3
"""
快速修复E501行长度问题的脚本
"""

import re
import os
from pathlib import Path

def fix_line_length_issues(file_path):
    """修复单个文件的行长度问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            if len(line) > 88:
                # 尝试修复常见的长行模式
                fixed_line = fix_long_line(line)
                fixed_lines.append(fixed_line)
            else:
                fixed_lines.append(line)

        fixed_content = '\n'.join(fixed_lines)

        if fixed_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"已修复: {file_path}")
            return True
        return False

    except Exception as e:
        print(f"修复失败 {file_path}: {e}")
        return False

def fix_long_line(line):
    """修复单行长度问题"""
    # 修复f-string过长问题
    if 'f"' in line and ('错误:' in line or '执行' in line):
        # 查找f-string中的断开点
        if '，' in line and len(line) > 88:
            parts = line.split('，', 1)
            if len(parts) == 2:
                return parts[0] + '，\n' + ' ' * 20 + f'"{parts[1].strip().rstrip('"')}"'

    # 修复长字符串字面量
    if '"' in line and len(line) > 88:
        # 在逗号后断开
        if ', ' in line and '"' in line[line.find(', ') + 2:]:
            comma_pos = line.find(', ')
            if comma_pos > 0 and comma_pos < len(line) - 10:
                return line[:comma_pos + 1] + '\n' + ' ' * 20 + line[comma_pos + 2:]

    return line

def main():
    """主函数"""
    # 需要修复的文件列表（从CI错误中提取的关键文件）
    files_to_fix = [
        'src/api/v1/analytics.py',
        'src/api/v1/assets.py',
        'src/api/v1/__init__.py',
        'src/api/v1/statistics.py',
        'src/api/v1/monitoring.py',
        'src/core/enhanced_database.py',
        'src/services/asset_calculator.py',
        'src/services/auth_service.py',
        'src/decorators/permission.py',
        'src/middleware/enhanced_security_middleware.py',
        'src/validation/framework.py'
    ]

    fixed_count = 0
    total_count = len(files_to_fix)

    for file_path in files_to_fix:
        full_path = Path(file_path)
        if full_path.exists():
            if fix_line_length_issues(full_path):
                fixed_count += 1
        else:
            print(f"文件不存在: {file_path}")

    print(f"\n修复完成: {fixed_count}/{total_count} 个文件")

if __name__ == "__main__":
    main()