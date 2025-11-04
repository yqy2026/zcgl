#!/usr/bin/env python3
"""
全面修复E501行长度问题的脚本
"""

import re
import os
from pathlib import Path

def fix_line_length_comprehensive(file_path):
    """全面修复单个文件的行长度问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            if len(line) > 88:
                fixed_line = apply_comprehensive_fixes(line)
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

def apply_comprehensive_fixes(line):
    """应用全面的修复策略"""
    original_line = line

    # 1. 修复f-string中的逗号后断开
    if 'f"' in line or "f'" in line:
        line = fix_fstring_breaks(line)

    # 2. 修复函数调用中的长参数列表
    if '(' in line and ',' in line and len(line) > 88:
        line = fix_function_calls(line)

    # 3. 修复长字符串字面量
    if '"' in line and len(line) > 88:
        line = fix_long_strings(line)

    # 4. 修复赋值语句中的长表达式
    if '=' in line and len(line) > 88:
        line = fix_assignments(line)

    return line

def fix_fstring_breaks(line):
    """修复f-string的断开"""
    # 查找f-string中的断开点
    if 'f"' in line:
        # 在逗号、+号或逻辑运算符后断开
        for sep in [', ', ' + ', ' and ', ' or ']:
            if sep in line:
                parts = line.split(sep, 1)
                if len(parts) == 2:
                    return parts[0] + sep + '\n' + ' ' * get_indent(line) + parts[1]
    return line

def fix_function_calls(line):
    """修复函数调用中的长参数列表"""
    # 在逗号后断开，并保持适当的缩进
    if ', ' in line and '(' in line:
        # 找到最后一个逗号位置
        last_comma = line.rfind(', ')
        if last_comma > 0 and last_comma < len(line) - 20:
            return line[:last_comma + 1] + '\n' + ' ' * get_indent(line + 4) + line[last_comma + 2:]
    return line

def fix_long_strings(line):
    """修复长字符串"""
    # 在句号、感叹号、问号后断开
    for sep in ['。', '！', '？', '. ', '! ', '? ']:
        if sep in line:
            parts = line.split(sep, 1)
            if len(parts) == 2:
                return parts[0] + sep + '\n' + ' ' * get_indent(line) + parts[1]
    return line

def fix_assignments(line):
    """修复赋值语句"""
    if '=' in line:
        parts = line.split('=', 1)
        if len(parts) == 2 and len(parts[1]) > 60:
            indent = get_indent(line)
            return parts[0] + '=\n' + ' ' * (indent + 4) + parts[1].strip()
    return line

def get_indent(line):
    """获取行的缩进级别"""
    return len(line) - len(line.lstrip())

def main():
    """主函数"""
    # 需要修复的关键文件列表
    critical_files = [
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
    total_count = len(critical_files)

    for file_path in critical_files:
        full_path = Path(file_path)
        if full_path.exists():
            if fix_line_length_comprehensive(full_path):
                fixed_count += 1
        else:
            print(f"文件不存在: {file_path}")

    print(f"\n修复完成: {fixed_count}/{total_count} 个关键文件")

if __name__ == "__main__":
    main()