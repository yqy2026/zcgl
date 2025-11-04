#!/usr/bin/env python3
"""
自动修复typing问题的脚本
"""

import os
import re
from pathlib import Path

def fix_typing_imports(file_path: Path):
    """修复文件中的typing导入问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='gbk') as f:
            content = f.read()

    original_content = content

    # 1. 修复导入语句 - 移除未使用的typing导入
    content = re.sub(r'from typing import.*Dict.*List.*Any.*', '', content)
    content = re.sub(r'from typing import.*Any.*Dict.*List.*', '', content)
    content = re.sub(r'from typing import.*Dict.*List.*', '', content)
    content = re.sub(r'from typing import.*Any.*List.*', '', content)
    content = re.sub(r'from typing import Dict, List', '', content)
    content = re.sub(r'from typing import List, Dict', '', content)
    content = re.sub(r'from typing import Any, Dict', '', content)
    content = re.sub(r'from typing import Any, List', '', content)
    content = re.sub(r'from typing import Dict', '', content)
    content = re.sub(r'from typing import List', '', content)
    content = re.sub(r'from typing import Any', '', content)

    # 2. 替换类型注解
    content = content.replace('Dict[str, Any]', 'dict[str, Any]')
    content = content.replace('Dict[str, str]', 'dict[str, str]')
    content = content.replace('Dict[str, List[str]]', 'dict[str, list[str]]')
    content = content.replace('Dict[str, Any] | None', 'dict[str, Any] | None')
    content = content.replace('List[Any]', 'list[Any]')
    content = content.replace('List[str]', 'list[str]')
    content = content.replace('List[dict[str, Any]]', 'list[dict[str, Any]]')
    content = content.replace('List[int]', 'list[int]')
    content = content.replace('List[float]', 'list[float]')
    content = content.replace('List[bool]', 'list[bool]')

    # 3. 修复函数返回类型
    content = re.sub(r'-> List\[.*?\]:', lambda m: m.group(0).replace('List[', 'list['), content)
    content = re.sub(r'-> Dict\[.*?\]:', lambda m: m.group(0).replace('Dict[', 'dict['), content)

    # 4. 修复变量类型注解
    content = re.sub(r': List\[.*?\]', lambda m: m.group(0).replace('List[', 'list['), content)
    content = re.sub(r': Dict\[.*?\]', lambda m: m.group(0).replace('Dict[', 'dict['), content)

    # 5. 添加必要的typing导入（如果使用了typing）
    if ('dict[str, Any]' in content or 'list[Any]' in content) and 'from typing import' not in content:
        # 在文件开头添加必要的导入
        lines = content.split('\n')
        import_line = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('#') and not line.startswith('"""') and not line.startswith("'''"):
                import_line = i
                break

        # 检查是否需要导入Any
        need_any = 'Any' in content and 'from typing import Any' not in content
        if need_any:
            lines.insert(import_line, 'from typing import Any')

        content = '\n'.join(lines)

    # 6. 确保文件以换行符结尾
    if content and not content.endswith('\n'):
        content += '\n'

    # 如果内容有变化，写回文件
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 修复了 {file_path}")
        return True
    else:
        print(f"⏭️  跳过 {file_path} (无需修复)")
        return False

def fix_undefined_names(file_path: Path):
    """修复未定义的名称"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='gbk') as f:
            content = f.read()

    original_content = content

    # 添加常见未定义异常的导入
    if 'BusinessLogicError' in content and 'BusinessLogicError' not in content.split('from')[0]:
        # 在导入区域添加BusinessLogicError
        lines = content.split('\n')
        import_line = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('from ') or line.strip().startswith('import '):
                import_line = i + 1
            elif line.strip() and not line.startswith('#') and not line.startswith('"""') and not line.startswith("'''"):
                if import_line == 0:
                    import_line = i
                break

        # 添加异常定义
        exception_lines = [
            '# 业务逻辑异常定义',
            'class BusinessLogicError(Exception):',
            '    """业务逻辑错误"""',
            '    pass',
            '',
            'class AssetNotFoundError(Exception):',
            '    """资产未找到错误"""',
            '    pass',
            '',
            'class DuplicateAssetError(Exception):',
            '    """重复资产错误"""',
            '    pass',
            ''
        ]

        for line in reversed(exception_lines):
            lines.insert(import_line, line)

        content = '\n'.join(lines)

    # 如果内容有变化，写回文件
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 修复了未定义名称: {file_path}")
        return True
    else:
        return False

def main():
    """主函数"""
    src_dir = Path("src")

    if not src_dir.exists():
        print("❌ src目录不存在")
        return

    fixed_files = 0

    # 递归处理所有Python文件
    for py_file in src_dir.rglob("*.py"):
        if py_file.name == 'fix_typing_issues.py':
            continue

        print(f"🔧 处理文件: {py_file}")

        # 修复typing导入问题
        if fix_typing_imports(py_file):
            fixed_files += 1

        # 修复未定义名称
        if fix_undefined_names(py_file):
            fixed_files += 1

    print(f"\n🎉 修复完成！共修复了 {fixed_files} 个文件")

if __name__ == "__main__":
    main()