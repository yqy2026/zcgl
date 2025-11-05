#!/usr/bin/env python3
"""
系统性修复Python文件中的typing导入问题
"""

import re
from pathlib import Path


def fix_typing_imports(file_path: Path) -> bool:
    """修复单个文件的typing导入"""
    try:
        content = file_path.read_text(encoding="utf-8")
        original = content

        # 常见的需要修复的类型模式
        type_patterns = {
            r"\bList\b": "List",
            r"\bDict\b": "Dict",
            r"\bTuple\b": "Tuple",
            r"\bSet\b": "Set",
            r"\bOptional\b": "Optional",
            r"\bUnion\b": "Union",
            r"\bCallable\b": "Callable",
            r"\bAny\b": "Any",
        }

        # 检查文件中使用了哪些类型但没有导入
        used_types = set()
        for pattern, type_name in type_patterns.items():
            if re.search(pattern, content):
                used_types.add(type_name)

        # 检查是否已有typing导入
        has_typing_import = (
            "from typing import" in content or "import typing" in content
        )

        # 如果使用了类型但没有导入，则添加导入
        if used_types and not has_typing_import:
            # 找到合适的插入位置
            lines = content.split("\n")
            insert_pos = 0

            # 在第一个import后插入
            for i, line in enumerate(lines):
                if line.strip().startswith(("import ", "from ")):
                    insert_pos = i + 1
                elif line.strip() == "" and insert_pos > 0:
                    break

            # 构建导入语句
            import_types = sorted(list(used_types))
            import_line = f"from typing import {', '.join(import_types)}"

            # 插入导入语句
            lines.insert(insert_pos, import_line)
            content = "\n".join(lines)

        # 如果内容有变化，写回文件
        if content != original:
            file_path.write_text(content, encoding="utf-8")
            print(f"Fixed imports in: {file_path}")
            return True

        return False

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def main():
    """主函数"""
    print("Fixing typing imports...")

    fixed_count = 0
    src_dir = Path("src")

    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" not in str(py_file):
            if fix_typing_imports(py_file):
                fixed_count += 1

    print(f"Fixed imports in {fixed_count} files")


if __name__ == "__main__":
    main()
