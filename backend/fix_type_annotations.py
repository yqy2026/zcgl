#!/usr/bin/env python3
"""
批量修复类型注解错误的脚本
将 dict[str, Any][KeyType, ValueType] 格式修复为正确的 dict[KeyType, ValueType] 格式
"""

import os
import re
from pathlib import Path

def fix_type_annotations(file_path: str) -> int:
    """修复单个文件中的类型注解错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复模式: dict[str, Any][KeyType, ValueType] -> dict[KeyType, ValueType]
        patterns = [
            # 基本模式
            (r'dict\[str, Any\]\[([^]]+)\]', r'dict[\1]'),
            # 更复杂的嵌套模式
            (r'dict\[str, Any\]\[str, ([^]]+)\]', r'dict[str, \1]'),
            (r'dict\[str, Any\]\[([^,]+), list\[dict\[str, Any\]\]\]', r'dict[\1, list[dict[str, Any]]]'),
        ]

        changes_made = 0
        for pattern, replacement in patterns:
            matches = re.findall(pattern, content)
            if matches:
                new_content = re.sub(pattern, replacement, content)
                if new_content != content:
                    content = new_content
                    changes_made += len(matches)

        # 如果有修改，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed {changes_made} type annotations in {file_path}")
            return changes_made

        return 0

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0

def main():
    """主函数"""
    print("开始修复类型注解错误...")

    src_dir = Path("src")
    if not src_dir.exists():
        print("src目录不存在")
        return

    total_fixes = 0
    files_processed = 0

    # 递归处理所有Python文件
    for py_file in src_dir.rglob("*.py"):
        if py_file.is_file():
            fixes = fix_type_annotations(str(py_file))
            total_fixes += fixes
            files_processed += 1

    print(f"\n处理完成:")
    print(f"  处理文件数: {files_processed}")
    print(f"  修复错误数: {total_fixes}")

if __name__ == "__main__":
    main()