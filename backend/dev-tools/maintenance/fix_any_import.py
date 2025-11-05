#!/usr/bin/env python3
"""
修复Any导入问题
"""

from pathlib import Path


def fix_any_imports(file_path: Path):
    """修复文件中的Any导入问题"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(file_path, encoding="gbk") as f:
            content = f.read()

    original_content = content

    # 如果文件使用了Any但没有导入，添加导入
    if "Any" in content and "from typing import Any" not in content:
        # 找到导入区域
        lines = content.split("\n")
        import_pos = 0

        for i, line in enumerate(lines):
            if line.strip().startswith("from ") or line.strip().startswith("import "):
                import_pos = i + 1
            elif line.strip() and not line.startswith("#") and import_pos == 0:
                import_pos = i
                break

        # 添加Any导入
        lines.insert(import_pos, "from typing import Any")
        content = "\n".join(lines)

    # 如果有变化，写回文件
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Fixed Any import: {file_path}")
        return True
    return False


def main():
    src_dir = Path("src")
    fixed_count = 0

    for py_file in src_dir.rglob("*.py"):
        if py_file.name.startswith("fix_"):
            continue

        if fix_any_imports(py_file):
            fixed_count += 1

    print(f"Fixed Any imports in {fixed_count} files")


if __name__ == "__main__":
    main()
