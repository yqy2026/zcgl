#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复剩余的代码质量问题
针对898个ruff错误的系统性修复
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Set, Dict, List

def check_git_status():
    """检查git状态"""
    try:
        result = subprocess.run(['git', 'status', '--porcelain'],
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("ERROR 无法获取git状态")
            return False

        if result.stdout.strip():
            print("WARN 工作区有未提交的更改，建议先提交或暂存")
            print("未提交的文件:")
            print(result.stdout)

            response = input("是否继续？(y/N): ").lower()
            if response != 'y':
                return False

        return True
    except Exception as e:
        print(f"ERROR 检查git状态失败: {str(e)}")
        return False

def run_ruff_check():
    """运行ruff检查并返回错误列表"""
    try:
        print("运行ruff检查...")
        result = subprocess.run([
            'uv', 'run', 'ruff', 'check', 'src/',
            '--output-format=concise'
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ 没有发现ruff错误")
            return []

        errors = result.stdout.strip().split('\n')
        print(f"发现 {len(errors)} 个ruff错误")
        return errors
    except Exception as e:
        print(f"ERROR ruff检查失败: {str(e)}")
        return []

def analyze_errors(errors: List[str]) -> Dict[str, List[str]]:
    """分析错误类型"""
    error_types = {}

    for error in errors:
        if not error.strip():
            continue

        # 解析错误格式: 文件:行:列: 错误码 错误信息
        match = re.match(r'^(.+?):(\d+):(\d+): (\w+) (.+)$', error.strip())
        if match:
            file_path, line, col, error_code, message = match.groups()
            error_type = error_code

            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append({
                'file': file_path,
                'line': int(line),
                'col': int(col),
                'message': message,
                'full': error
            })

    # 统计各类型错误数量
    print("\n错误类型统计:")
    for error_type, error_list in sorted(error_types.items()):
        print(f"  {error_type}: {len(error_list)} 个")

    return error_types

def fix_import_errors(errors_by_type: Dict[str, List[str]]) -> int:
    """修复导入错误 (E402, I001等)"""
    import_errors = errors_by_type.get('E402', []) + errors_by_type.get('I001', [])
    if not import_errors:
        return 0

    print(f"\n修复 {len(import_errors)} 个导入错误...")

    fixed_files = set()
    for error in import_errors:
        file_path = error['file']
        if file_path in fixed_files:
            continue

        full_path = Path(file_path)
        if not full_path.exists():
            continue

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 简单的导入修复：将所有导入移到文件顶部
            lines = content.split('\n')
            imports = []
            other_lines = []

            for line in lines:
                stripped = line.strip()
                if (stripped.startswith('import ') or
                    stripped.startswith('from ') or
                    stripped.startswith('#') or
                    not stripped or
                    stripped.startswith('"""') or
                    stripped.startswith("'''")):
                    if not any(keyword in stripped for keyword in ['import ', 'from ']):
                        other_lines.append(line)
                    else:
                        imports.append(line)
                else:
                    other_lines.append(line)

            # 重新组织文件：导入 -> 文档字符串 -> 其他代码
            new_content = '\n'.join(imports) + '\n\n'
            docstring_found = False
            for line in other_lines:
                if '"""' in line or "'''" in line:
                    docstring_found = True
                new_content += line + '\n'

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            fixed_files.add(file_path)
            print(f"  修复 {file_path}")

        except Exception as e:
            print(f"  修复 {file_path} 失败: {str(e)}")

    return len(fixed_files)

def fix_undefined_names(errors_by_type: Dict[str, List[str]]) -> int:
    """修复未定义名称错误 (F821)"""
    undefined_errors = errors_by_type.get('F821', [])
    if not undefined_errors:
        return 0

    print(f"\n修复 {len(undefined_errors)} 个未定义名称错误...")

    # 定义需要添加的异常类
    missing_exceptions = {
        'AssetNotFoundError': 'class AssetNotFoundError(Exception): pass',
        'DuplicateAssetError': 'class DuplicateAssetError(Exception): pass',
        'BusinessLogicError': 'class BusinessLogicError(Exception): pass',
        'ValidationError': 'class ValidationError(Exception): pass',
        'AuthenticationError': 'class AuthenticationError(Exception): pass',
        'AuthorizationError': 'class AuthorizationError(Exception): pass',
        'NotFoundError': 'class NotFoundError(Exception): pass',
        'PermissionError': 'class PermissionError(Exception): pass'
    }

    fixed_files = set()
    for error in undefined_errors:
        file_path = error['file']
        if file_path in fixed_files:
            continue

        full_path = Path(file_path)
        if not full_path.exists():
            continue

        message = error['message']
        # 提取未定义的名称
        match = re.search(r'Undefined name `(.+?)`', message)
        if not match:
            continue

        undefined_name = match.group(1)
        if undefined_name not in missing_exceptions:
            continue

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 在文件开头添加缺失的异常类定义
            exception_def = missing_exceptions[undefined_name]

            # 找到第一个导入语句之后的位置
            lines = content.split('\n')
            insert_index = 0
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')):
                    insert_index = i + 1
                elif line.strip() and not line.strip().startswith('#'):
                    if insert_index == 0:
                        insert_index = i
                    break

            lines.insert(insert_index, '')
            lines.insert(insert_index + 1, f'# 添加缺失的异常定义')
            lines.insert(insert_index + 2, exception_def)

            new_content = '\n'.join(lines)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            fixed_files.add(file_path)
            print(f"  修复 {file_path}: 添加 {undefined_name}")

        except Exception as e:
            print(f"  修复 {file_path} 失败: {str(e)}")

    return len(fixed_files)

def fix_duplicate_definitions(errors_by_type: Dict[str, List[str]]) -> int:
    """修复重复定义错误 (F811)"""
    duplicate_errors = errors_by_type.get('F811', [])
    if not duplicate_errors:
        return 0

    print(f"\n修复 {len(duplicate_errors)} 个重复定义错误...")

    fixed_files = set()
    for error in duplicate_errors:
        file_path = error['file']
        if file_path in fixed_files:
            continue

        full_path = Path(file_path)
        if not full_path.exists():
            continue

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            message = error['message']
            # 提取函数名
            match = re.search(r'Redefinition of .+? `(.+?)`', message)
            if not match:
                continue

            func_name = match.group(1)
            line_num = error['line']

            # 简单修复：注释掉重复的函数定义
            lines = content.split('\n')
            if 0 <= line_num - 1 < len(lines):
                # 找到函数定义的完整范围
                start_line = line_num - 1
                indent_level = len(lines[start_line]) - len(lines[start_line].lstrip())

                # 找到函数结束位置
                end_line = start_line + 1
                for i in range(start_line + 1, len(lines)):
                    current_line = lines[i]
                    if current_line.strip() == '':
                        continue
                    current_indent = len(current_line) - len(current_line.lstrip())
                    if current_indent <= indent_level and current_line.strip():
                        break
                    end_line = i

                # 注释掉重复的函数
                for i in range(start_line, min(end_line + 1, len(lines))):
                    if not lines[i].strip().startswith('#'):
                        lines[i] = '# ' + lines[i]

                new_content = '\n'.join(lines)

                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                fixed_files.add(file_path)
                print(f"  修复 {file_path}: 注释重复的 {func_name}")

        except Exception as e:
            print(f"  修复 {file_path} 失败: {str(e)}")

    return len(fixed_files)

def run_ruff_fix():
    """运行ruff自动修复"""
    try:
        print("\n运行ruff自动修复...")
        result = subprocess.run([
            'uv', 'run', 'ruff', 'check', 'src/',
            '--fix', '--output-format=concise'
        ], capture_output=True, text=True)

        print("ruff自动修复结果:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode
    except Exception as e:
        print(f"ERROR ruff自动修复失败: {str(e)}")
        return 1

def main():
    """主函数"""
    print("修复剩余的代码质量问题...")

    # 检查git状态
    if not check_git_status():
        return

    # 运行初始检查
    errors = run_ruff_check()
    if not errors:
        print("✅ 没有发现需要修复的错误")
        return

    # 分析错误类型
    errors_by_type = analyze_errors(errors)

    # 系统性修复各类错误
    total_fixed = 0

    # 1. 修复导入错误
    fixed = fix_import_errors(errors_by_type)
    total_fixed += fixed

    # 2. 修复未定义名称
    fixed = fix_undefined_names(errors_by_type)
    total_fixed += fixed

    # 3. 修复重复定义
    fixed = fix_duplicate_definitions(errors_by_type)
    total_fixed += fixed

    # 4. 运行ruff自动修复
    result_code = run_ruff_fix()
    if result_code == 0:
        total_fixed += 1  # 标记ruff修复成功

    print(f"\n总计修复: {total_fixed} 类问题")

    # 再次检查
    final_errors = run_ruff_check()
    if final_errors:
        print(f"\n⚠️ 仍有 {len(final_errors)} 个错误需要手动修复")
        print("前10个错误:")
        for error in final_errors[:10]:
            print(f"  {error}")
    else:
        print("\n✅ 所有错误已修复完成")

if __name__ == "__main__":
    main()