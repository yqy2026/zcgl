#!/usr/bin/env python3
"""
修复 E402: 将所有导入移到文件顶部，docstring 放在导入之后

根据 PEP 8:
1. 所有 import 语句应该在文件顶部
2. 模块 docstring 应该在 import 之后，其他代码之前
"""

import re
from pathlib import Path


def fix_import_order(filepath: Path) -> bool:
    """修复单个文件的导入顺序"""
    content = filepath.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)

    # 分离: 导入行 | docstring | 异常类定义 | 其他代码
    imports = []
    docstring = []
    exception_defs = []
    others = []
    state = "start"

    for i, line in enumerate(lines):
        stripped = line.strip()
        is_import = stripped.startswith("import ") or stripped.startswith("from ")
        is_exception_def = re.match(r"^class\s+\w+Error\(|^class\s+\w*Exception\(", line)

        if state == "start":
            if is_import:
                state = "imports"
                imports.append(line)
            elif is_exception_def:
                state = "exceptions"
                exception_defs.append(line)
            elif '"""' in line or "'''" in line:
                state = "docstring"
                docstring.append(line)
            elif stripped and not stripped.startswith("#"):
                state = "others"
                others.append(line)
            else:
                others.append(line)

        elif state == "imports":
            if is_import:
                imports.append(line)
            elif '"""' in line or "'''" in line:
                state = "docstring"
                docstring.append(line)
            elif is_exception_def:
                state = "exceptions"
                exception_defs.append(line)
            elif stripped and not stripped.startswith("#"):
                state = "others"
                others.append(line)
            else:
                others.append(line)

        elif state == "docstring":
            docstring.append(line)
            # 检查 docstring 是否结束
            quote_count = sum(1 for line_str in docstring if ('"""' in line_str or "'''" in line_str))
            if quote_count >= 2:
                # Docstring ended
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    next_stripped = next_line.strip()
                    is_next_import = next_stripped.startswith(
                        "import "
                    ) or next_stripped.startswith("from ")
                    is_next_exception = re.match(
                        r"^class\s+\w+Error\(|^class\s+\w*Exception\(", next_line
                    )

                    if is_next_import:
                        state = "imports"
                    elif is_next_exception:
                        state = "exceptions"
                    else:
                        state = "others"
                else:
                    state = "others"

        elif state == "exceptions":
            if is_exception_def:
                exception_defs.append(line)
            elif '"""' in line or "'''" in line:
                state = "docstring"
                docstring.append(line)
            elif is_import:
                # E402: 在异常类定义之后发现导入
                imports.append(line)
            elif stripped and not stripped.startswith("#"):
                state = "others"
                others.append(line)
            else:
                others.append(line)

        else:  # others
            others.append(line)

    # 如果没有发现异常模式，保持原文件不变
    if not imports and not docstring:
        return False

    # 重新组合: 导入 -> 空行 -> docstring -> 异常类定义 -> 其他代码
    new_content_parts = []

    if imports:
        new_content_parts.extend(imports)
        new_content_parts.append("\n")

    if docstring:
        new_content_parts.extend(docstring)
        new_content_parts.append("\n")

    if exception_defs:
        new_content_parts.extend(exception_defs)
        # 如果有其他代码，添加空行分隔
        if others and others[0].strip() and not others[0].startswith("#"):
            new_content_parts.append("\n")

    new_content_parts.extend(others)

    new_content = "".join(new_content_parts)

    if new_content != content:
        filepath.write_text(new_content, encoding="utf-8")
        return True

    return False


def main():
    """主函数"""
    backend_dir = Path("/home/y/zcgl/backend/src")

    # 查找所有 Python 文件
    py_files = list(backend_dir.rglob("*.py"))

    fixed_count = 0
    for py_file in py_files:
        try:
            if fix_import_order(py_file):
                print(f"Fixed: {py_file.relative_to(backend_dir)}")
                fixed_count += 1
        except Exception as e:
            print(f"Error processing {py_file}: {e}")

    print(f"\nTotal files fixed: {fixed_count}")


if __name__ == "__main__":
    main()
