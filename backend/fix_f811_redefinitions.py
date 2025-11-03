#!/usr/bin/env python3
"""
修复F811重复定义问题
"""

import os
import re
from pathlib import Path

def fix_f811_redefinitions():
    """修复F811重复定义问题"""
    print("开始修复F811重复定义问题...")

    # 需要修复的文件列表
    files_to_fix = [
        "src/api/v1/assets.py",
        "src/api/v1/statistics.py",
        "src/crud/rbac.py",
        "src/crud/task.py",
        "src/decorators/permission.py",
        "src/services/auth_service.py",
        "src/services/dynamic_permission_service.py",
        "src/services/permission_delegation_service.py",
        "src/services/permission_inheritance_service.py",
        "src/services/rbac_service.py"
    ]

    total_fixes = 0

    for file_path in files_to_fix:
        path = Path(file_path)
        if not path.exists():
            continue

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 移除重复的BusinessLogicError定义
            # 保留第一个，移除后续的
            business_logic_pattern = r'(from.*exceptions.*import.*BusinessLogicError.*\n)'
            matches = list(re.finditer(business_logic_pattern, content, re.MULTILINE))

            if len(matches) > 1:
                # 保留第一个
                first_match = matches[0]
                content = content[:first_match.start()] + first_match.group()

                # 移除后续的重复定义
                for match in reversed(matches[1:]):
                    content = content[:match.start()] + content[match.end():]

                print(f"修复 {file_path} 中的BusinessLogicError重复定义")
                total_fixes += 1

            # 移除重复的函数定义（针对assets.py）
            if "assets.py" in file_path:
                # 查找重复的函数定义模式
                func_patterns = [
                    r'async def validate_asset_data\([^)]*\):.*?(?=\nasync def|\n@|\nclass|\n#|\Z)',
                    r'async def get_ownership_entities\([^)]*\):.*?(?=\nasync def|\n@|\nclass|\n#|\Z)',
                    r'async def get_business_categories\([^)]*\):.*?(?=\nasync def|\n@|\nclass|\n#|\Z)'
                ]

                for pattern in func_patterns:
                    matches = list(re.finditer(pattern, content, re.MULTILINE | re.DOTALL))
                    if len(matches) > 1:
                        # 保留第一个，移除后续的
                        first_match = matches[0]
                        content = content[:first_match.end()] + first_match.group()

                        # 移除后续的重复定义
                        for match in reversed(matches[1:]):
                            content = content[:match.start()] + content[match.end():]

                        func_name = pattern.split('(')[0].split()[-1]
                        print(f"修复 {file_path} 中的{func_name}重复定义")
                        total_fixes += 1

            # 移除重复的函数定义（针对statistics.py）
            if "statistics.py" in file_path:
                pattern = r'async def get_basic_statistics\([^)]*\):.*?(?=\nasync def|\n@|\nclass|\n#|\Z)'
                matches = list(re.finditer(pattern, content, re.MULTILINE | re.DOTALL))
                if len(matches) > 1:
                    first_match = matches[0]
                    content = content[:first_match.end()] + first_match.group()

                    for match in reversed(matches[1:]):
                        content = content[:match.start()] + content[match.end():]

                    print(f"修复 {file_path} 中的get_basic_statistics重复定义")
                    total_fixes += 1

            if content != original_content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)

        except Exception as e:
            print(f"处理 {file_path} 时出错: {e}")

    print(f"\n修复完成，共修复 {total_fixes} 个重复定义")

def main():
    """主函数"""
    print("F811重复定义问题修复工具")
    print("=" * 50)

    fix_f811_redefinitions()

    print("\n验证修复结果...")
    # 运行ruff检查验证结果
    os.system('uv run ruff check src/ --select=F811 --statistics')

if __name__ == "__main__":
    main()