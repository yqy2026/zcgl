#!/usr/bin/env python3
"""
自动修复typing问题的简化脚本
"""

import re
from pathlib import Path


def fix_file(file_path: Path):
    """修复单个文件"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(file_path, encoding="gbk") as f:
            content = f.read()

    original_content = content

    # 替换常见的typing问题
    replacements = [
        (r"from typing import.*Dict.*List.*Any.*", ""),
        (r"from typing import.*Any.*Dict.*List.*", ""),
        (r"from typing import.*Dict.*List.*", ""),
        (r"from typing import.*Any.*List.*", ""),
        (r"from typing import Dict, List", ""),
        (r"from typing import List, Dict", ""),
        (r"from typing import Any, Dict", ""),
        (r"from typing import Any, List", ""),
        (r"from typing import Dict", ""),
        (r"from typing import List", ""),
        (r"from typing import Any", ""),
        (r"Dict\[str, Any\]", "dict[str, Any]"),
        (r"Dict\[str, str\]", "dict[str, str]"),
        (r"List\[Any\]", "list[Any]"),
        (r"List\[str\]", "list[str]"),
        (r"List\[dict\[str, Any\]\]", "list[dict[str, Any]]"),
        (r"List\[int\]", "list[int]"),
        (r"-> List\[", "-> list["),
        (r"-> Dict\[", "-> dict["),
        (r": List\[", ": list["),
        (r": Dict\[", ": dict["),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)

    # 添加必要的异常定义
    if "BusinessLogicError" in content and "class BusinessLogicError" not in content:
        lines = content.split("\n")
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("from ") or line.strip().startswith("import "):
                insert_pos = i + 1
            elif line.strip() and not line.startswith("#") and insert_pos == 0:
                insert_pos = i
                break

        exceptions = [
            "class BusinessLogicError(Exception):",
            '    """Business logic error"""',
            "    pass",
            "",
            "class AssetNotFoundError(Exception):",
            '    """Asset not found error"""',
            "    pass",
            "",
            "class DuplicateAssetError(Exception):",
            '    """Duplicate asset error"""',
            "    pass",
            "",
        ]

        for exc in reversed(exceptions):
            lines.insert(insert_pos, exc)

        content = "\n".join(lines)

    # 确保文件以换行符结尾
    if content and not content.endswith("\n"):
        content += "\n"

    # 如果有变化，写回文件
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Fixed: {file_path}")
        return True
    return False


def main():
    """主函数"""
    src_dir = Path("src")

    if not src_dir.exists():
        print("src directory not found")
        return

    fixed_count = 0
    total_files = 0

    for py_file in src_dir.rglob("*.py"):
        if py_file.name.startswith("fix_typing"):
            continue

        total_files += 1
        print(f"Processing: {py_file}")
        if fix_file(py_file):
            fixed_count += 1

    print(f"\nCompleted: {fixed_count}/{total_files} files fixed")


if __name__ == "__main__":
    main()
