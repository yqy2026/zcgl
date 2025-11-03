#!/usr/bin/env python3
"""
修复错误的类型注解: List[Any][Type] -> List[Type]
"""

import re
from pathlib import Path

def fix_list_typing_errors():
    """修复所有错误的List[Any][...]类型注解"""

    print("🔧 修复List[Any][...]类型注解错误...")

    src_dir = Path("src")
    fixed_files = []

    # 错误的模式
    wrong_pattern = r'List\[Any\]\[([^]]+)\]'

    # 修复为正确的模式
    def replace_wrong_typing(match):
        inner_type = match.group(1)
        return f'List[{inner_type}]'

    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        try:
            content = py_file.read_text(encoding='utf-8')
            original = content

            # 修复错误的类型注解
            content = re.sub(wrong_pattern, replace_wrong_typing, content)

            if content != original:
                py_file.write_text(content, encoding='utf-8')
                fixed_files.append(str(py_file))
                print(f"✅ 修复: {py_file}")

        except Exception as e:
            print(f"❌ 处理 {py_file} 时出错: {e}")

    print(f"\n📊 修复完成: {len(fixed_files)} 个文件")
    return fixed_files

def fix_dict_typing_errors():
    """修复错误的dict类型注解"""

    print("\n🔧 修复dict类型注解错误...")

    src_dir = Path("src")
    fixed_files = []

    # 修复模式
    fixes = [
        (r'-> Dict\[str, Any\]\[str, Any\]', '-> Dict[str, Any]'),
        (r'dict\[str, Any\]\[str\]', 'dict[str, str]'),
        (r'Dict\[str, Any\]\[str\]', 'Dict[str, str]'),
    ]

    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        try:
            content = py_file.read_text(encoding='utf-8')
            original = content

            # 应用所有修复
            for pattern, replacement in fixes:
                content = re.sub(pattern, replacement, content)

            if content != original:
                py_file.write_text(content, encoding='utf-8')
                fixed_files.append(str(py_file))
                print(f"✅ 修复: {py_file}")

        except Exception as e:
            print(f"❌ 处理 {py_file} 时出错: {e}")

    print(f"\n📊 Dict修复完成: {len(fixed_files)} 个文件")
    return fixed_files

def main():
    """主函数"""
    print("🚀 开始修复类型注解错误...")

    list_fixed = fix_list_typing_errors()
    dict_fixed = fix_dict_typing_errors()

    total_fixed = len(list_fixed) + len(dict_fixed)
    print(f"\n🎉 总计修复 {total_fixed} 个文件的类型注解错误")

    if total_fixed > 0:
        print("✅ 类型注解修复完成！")

if __name__ == "__main__":
    main()