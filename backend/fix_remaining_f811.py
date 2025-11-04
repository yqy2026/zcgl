#!/usr/bin/env python3
"""
修复剩余的F811重复定义问题
"""

import os
import re
from pathlib import Path

def fix_remaining_f811():
    """修复剩余的F811问题"""
    print("开始修复剩余的F811重复定义问题...")

    # 需要修复的文件和对应的重复导入行
    files_to_fix = [
        ("src/decorators/permission.py", 35),
        ("src/services/auth_service.py", 32),
        ("src/services/dynamic_permission_service.py", 33),
        ("src/services/permission_delegation_service.py", 33),
        ("src/services/permission_inheritance_service.py", 34),
        ("src/services/rbac_service.py", 32),
    ]

    total_fixes = 0

    for file_path, line_number in files_to_fix:
        path = Path(file_path)
        if not path.exists():
            continue

        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            original_content = ''.join(lines)

            # 移除重复的BusinessLogicError导入
            for i, line in enumerate(lines):
                if "from ..exceptions import BusinessLogicError" in line and i + 1 != line_number:
                    # 确保这是我们要删除的行
                    if i + 1 == line_number:
                        lines[i] = lines[i].replace("from ..exceptions import BusinessLogicError", "")
                        print(f"修复 {file_path} 第{line_number}行: 移除重复的BusinessLogicError导入")
                        total_fixes += 1
                        break

            new_content = ''.join(lines)

            if new_content != original_content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

        except Exception as e:
            print(f"处理 {file_path} 时出错: {e}")

    print(f"\n修复完成，共修复 {total_fixes} 个重复导入")

    # 手动修复assets.py中的函数重复定义
    fix_assets_function_redefinitions()

def fix_assets_function_redefinitions():
    """修复assets.py中的函数重复定义"""
    print("\n修复assets.py中的函数重复定义...")

    file_path = Path("src/api/v1/assets.py")
    if not file_path.exists():
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 移除重复的函数定义
        # 找到并移除重复的函数定义
        patterns = [
            (r'async def validate_asset_data\([^:]*?\):.*?(?=\nasync def|\n@|\nclass|\n#|\Z)', "移除重复的validate_asset_data定义"),
            (r'async def get_ownership_entities\([^:]*?\):.*?(?=\nasync def|\n@|\nclass|\n#|\Z)', "移除重复的get_ownership_entities定义"),
            (r'async def get_business_categories\([^:]*?\):.*?(?=\nasync def|\n@|\nclass|\n#|\Z)', "移除重复的get_business_categories定义"),
        ]

        for pattern, description in patterns:
            while True:
                new_content = re.sub(pattern, '', content, flags=re.MULTILINE | re.DOTALL)
                if new_content != content:
                    print(f"  {description}")
                    content = new_content
                else:
                    break

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("assets.py函数重复定义修复完成")

    except Exception as e:
        print(f"处理assets.py时出错: {e}")

    # 修复statistics.py中的函数重复定义
    fix_statistics_function_redefinition()

def fix_statistics_function_redefinition():
    """修复statistics.py中的函数重复定义"""
    print("\n修复statistics.py中的函数重复定义...")

    file_path = Path("src/api/v1/statistics.py")
    if not file_path.exists():
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 移除重复的函数定义
        pattern = r'async def get_basic_statistics\([^:]*?\):.*?(?=\nasync def|\n@|\nclass|\n#|\Z)'

        while True:
            new_content = re.sub(pattern, '', content, flags=re.MULTILINE | re.DOTALL)
            if new_content != content:
                print("  移除重复的get_basic_statistics定义")
                content = new_content
            else:
                break

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("statistics.py函数重复定义修复完成")

    except Exception as e:
        print(f"处理statistics.py时出错: {e}")

def main():
    """主函数"""
    print("F811重复定义问题修复工具 (剩余问题)")
    print("=" * 60)

    fix_remaining_f811()

    print("\n验证修复结果...")
    # 运行ruff检查验证结果
    os.system('uv run ruff check src/ --select=F811 --statistics')

if __name__ == "__main__":
    main()