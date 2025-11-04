#!/usr/bin/env python3
"""
修复E402导入问题 - 模块导入不在文件顶部
专门处理大量的E402错误，将所有import语句移动到文件顶部
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def extract_imports(content: str) -> List[Tuple[str, int]]:
    """提取所有import语句及其位置"""
    imports = []
    lines = content.split('\n')

    for i, line in enumerate(lines):
        stripped = line.strip()
        # 匹配各种import语句
        if (stripped.startswith('import ') or
            stripped.startswith('from ') or
            stripped.startswith('# 添加导入') or
            stripped.startswith('# 导入')):
            imports.append((line, i))

    return imports

def separate_imports(imports: List[Tuple[str, int]]) -> Tuple[List[str], List[str], List[str]]:
    """分离不同类型的导入"""
    stdlib_imports = []
    third_party_imports = []
    local_imports = []

    for line, _ in imports:
        stripped = line.strip()

        # 跳过注释
        if stripped.startswith('#') and not ('导入' in stripped or 'import' in stripped):
            continue

        # 标准库导入
        if any(stripped.startswith(f'import {lib}') or
               stripped.startswith(f'from {lib}')
               for lib in ['os', 'sys', 're', 'json', 'datetime', 'time', 'uuid',
                          'logging', 'pathlib', 'collections', 'hashlib', 'secrets',
                          'typing', 'enum', 'abc', 'itertools', 'functools', 'decimal',
                          'io', 'math', 'statistics', 'sqlite3', 'threading', 'asyncio',
                          'inspect', 'textwrap', 'string', 'unicodedata', 'zoneinfo']):
            stdlib_imports.append(line)

        # 第三方库导入
        elif any(stripped.startswith(f'import {lib}') or
                 stripped.startswith(f'from {lib}')
                 for lib in ['fastapi', 'sqlalchemy', 'pydantic', 'uvicorn', 'python-multipart',
                            'python-jose', 'passlib', 'bcrypt', 'alembic', 'pytest', 'redis',
                            'httpx', 'aiofiles', 'jinja2', 'starlette', 'pydantic_settings',
                            'pdfplumber', 'paddleocr', 'jieba', 'spacy', 'opencv-python',
                            'pillow', 'numpy', 'pandas', 'openpyxl', 'xlsxwriter']):
            third_party_imports.append(line)

        # 本地导入
        else:
            local_imports.append(line)

    return stdlib_imports, third_party_imports, local_imports

def organize_imports(stdlib_imports: List[str], third_party_imports: List[str],
                    local_imports: List[str]) -> List[str]:
    """组织导入语句的顺序"""
    organized_imports = []

    # 添加标准库导入
    if stdlib_imports:
        organized_imports.append("# 标准库导入")
        organized_imports.extend(sorted(set(stdlib_imports), key=lambda x: x.strip()))
        organized_imports.append("")

    # 添加第三方库导入
    if third_party_imports:
        organized_imports.append("# 第三方库导入")
        organized_imports.extend(sorted(set(third_party_imports), key=lambda x: x.strip()))
        organized_imports.append("")

    # 添加本地导入
    if local_imports:
        organized_imports.append("# 本地导入")
        organized_imports.extend(sorted(set(local_imports), key=lambda x: x.strip()))
        organized_imports.append("")

    return organized_imports

def fix_file_imports(file_path: Path) -> int:
    """修复单个文件的导入问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 提取所有导入语句
        imports = extract_imports(content)
        if not imports:
            return 0

        # 分离不同类型的导入
        stdlib_imports, third_party_imports, local_imports = separate_imports(imports)

        # 组织导入语句
        organized_imports = organize_imports(stdlib_imports, third_party_imports, local_imports)

        # 移除原有的import语句
        lines = content.split('\n')
        non_import_lines = []
        import_line_numbers = set(line_num for _, line_num in imports)

        for i, line in enumerate(lines):
            if i not in import_line_numbers:
                non_import_lines.append(line)

        # 找到第一个非注释、非空行的位置
        first_code_line = 0
        for i, line in enumerate(non_import_lines):
            if line.strip() and not line.strip().startswith('"""') and not line.strip().startswith("'''"):
                first_code_line = i
                break

        # 构建新的内容
        new_lines = []

        # 添加文件开头的注释（如果有）
        for i in range(first_code_line):
            if non_import_lines[i].strip():
                new_lines.append(non_import_lines[i])

        # 添加空行分隔
        if new_lines:
            new_lines.append("")

        # 添加组织好的导入语句
        new_lines.extend(organized_imports)

        # 添加剩余的代码
        new_lines.extend(non_import_lines[first_code_line:])

        # 写回文件
        new_content = '\n'.join(new_lines)

        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return len(imports)

        return 0

    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {e}")
        return 0

def fix_e402_errors() -> None:
    """修复所有E402错误"""
    print("开始修复E402导入问题...")

    src_dir = Path("src")
    if not src_dir.exists():
        print("src目录不存在")
        return

    total_files = 0
    total_imports_fixed = 0

    # 遍历所有Python文件
    for py_file in src_dir.rglob("*.py"):
        if py_file.is_file() and py_file.name != '__init__.py':
            imports_fixed = fix_file_imports(py_file)
            if imports_fixed > 0:
                total_files += 1
                total_imports_fixed += imports_fixed
                print(f"修复 {py_file}: {imports_fixed} 个导入")

    print(f"\n修复完成:")
    print(f"  处理文件数: {total_files}")
    print(f"  修复导入数: {total_imports_fixed}")

def main():
    """主函数"""
    print("E402导入问题修复工具")
    print("=" * 50)

    fix_e402_errors()

    print("\n验证修复结果...")
    # 运行ruff检查验证结果
    os.system('uv run ruff check src/ --statistics')

if __name__ == "__main__":
    main()