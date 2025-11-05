#!/usr/bin/env python3
"""
批量修复ruff错误的脚本
专注于语法错误、重复定义和未定义名称问题
"""

import re
from pathlib import Path


def fix_syntax_errors(file_path: str) -> int:
    """修复语法错误"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original_content = content
        fixes = 0

        # 修复逗号位置错误
        patterns = [
            (r"from ([^,\n]+),\s+([^\n]+)", r"from \1, \2"),  # 修复导入语句中的逗号
            (r"(\w+),\s*TypeVar", r"\1, TypeVar"),  # 修复TypeVar导入
            (
                r"class\s+(\w+)\s*\([^)]+\)\s*:\s*pass",
                r"class \1(\n    pass\n)",
            ),  # 修复单行类定义
        ]

        for pattern, replacement in patterns:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                content = new_content
                fixes += 1

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            if fixes > 0:
                print(f"修复 {file_path} 中的 {fixes} 个语法错误")
            return fixes

        return 0

    except Exception as e:
        print(f"处理 {file_path} 时出错: {e}")
        return 0


def fix_redefinition_errors(file_path: str) -> int:
    """修复重复定义错误"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original_content = content
        fixes = 0

        # 移除重复的BusinessLogicError定义
        business_logic_pattern = (
            r'class\s+BusinessLogicError\s*\([^)]*\)\s*:\s*"""[^"]*"""'
        )
        matches = list(re.finditer(business_logic_pattern, content))

        if len(matches) > 1:
            # 保留第一个，移除其他的
            first_match = matches[0]
            content = content[: first_match.start()] + first_match.group()

            # 移除后续的重复定义
            for match in reversed(matches[1:]):
                content = content[: match.start()] + content[match.end() :]

            fixes += len(matches) - 1

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            if fixes > 0:
                print(f"修复 {file_path} 中的 {fixes} 个重复定义错误")
            return fixes

        return 0

    except Exception as e:
        print(f"处理 {file_path} 时出错: {e}")
        return 0


def fix_undefined_names(file_path: str) -> int:
    """修复未定义名称错误"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original_content = content
        fixes = 0

        # 修复常见的未定义名称问题
        patterns = [
            (r'docs_data\.get\("paths"', r'api_data.get("paths"'),  # 修复docs_data问题
            (
                r"sensitive_fields\s*=",
                r'["owner_name", "contact_info"] =',
            ),  # 修复sensitive_fields问题
            (
                r"for field in sensitive_fields:",
                r'for field in ["owner_name", "contact_info"]:',
            ),  # 修复循环中的sensitive_fields
        ]

        for pattern, replacement in patterns:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                content = new_content
                fixes += 1

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            if fixes > 0:
                print(f"修复 {file_path} 中的 {fixes} 个未定义名称错误")
            return fixes

        return 0

    except Exception as e:
        print(f"处理 {file_path} 时出错: {e}")
        return 0


def main():
    """主函数"""
    print("开始修复ruff错误...")

    src_dir = Path("src")
    if not src_dir.exists():
        print("src目录不存在")
        return

    total_fixes = 0
    files_processed = 0

    # 处理所有Python文件
    for py_file in src_dir.rglob("*.py"):
        if py_file.is_file():
            fixes = 0
            fixes += fix_syntax_errors(str(py_file))
            fixes += fix_redefinition_errors(str(py_file))
            fixes += fix_undefined_names(str(py_file))

            total_fixes += fixes
            files_processed += 1

    print("\n处理完成:")
    print(f"  处理文件数: {files_processed}")
    print(f"  修复错误数: {total_fixes}")


if __name__ == "__main__":
    main()
