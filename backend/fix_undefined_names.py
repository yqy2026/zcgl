#!/usr/bin/env python3
"""
修复F821未定义名称问题
专门处理未定义变量、函数和类的问题
"""

import os
import re
from pathlib import Path

def fix_undefined_names():
    """修复未定义名称问题"""
    print("开始修复F821未定义名称问题...")

    # 定义常见修复模式
    fixes = [
        # 修复 auth.py 中的 days 问题
        {
            "file": "src/crud/auth.py",
            "pattern": r"days\s*=\s*7\s*#.*\n\s*return",
            "replacement": "days = 7  # 默认7天\n                return"
        },
        # 修复 auth.py 中缺少的 db 参数
        {
            "file": "src/crud/auth.py",
            "pattern": r"def.*clean_expired_sessions\([^)]*\):",
            "replacement": lambda m: m.group(0).replace(")", ", db: Session)")
        },
        # 修复 rbac.py 中的 days 和 db 问题
        {
            "file": "src/crud/rbac.py",
            "pattern": r"days\s*=\s*30\s*#.*\n\s*return",
            "replacement": "days = 30  # 默认30天\n                return"
        },
        # 修复 enhanced_security_middleware.py 中的 request 和 credentials 问题
        {
            "file": "src/middleware/enhanced_security_middleware.py",
            "pattern": r"async def.*call_next[^:]*:\s*\n.*request",
            "replacement": "async def call_next(self, request: Request, call_next):\n        request"
        },
        # 修复 data_security.py 中的 data 问题
        {
            "file": "src/services/data_security.py",
            "pattern": r"def.*sanitize_data[^:]*:\s*\n.*data",
            "replacement": "def sanitize_data(self, data: Any) -> Any:\n        data"
        },
        # 修复 asset_calculator.py 中的各种未定义问题
        {
            "file": "src/services/asset_calculator.py",
            "pattern": r"def.*calculate[^:]*:\s*\n.*asset_data",
            "replacement": "def calculate(self, asset_data: dict) -> dict:\n        asset_data"
        },
        {
            "file": "src/services/asset_calculator.py",
            "pattern": r"assets\s*=\s*\[\].*?for asset_data in",
            "replacement": "assets = []\n        for asset_data in"
        },
        {
            "file": "src/services/asset_calculator.py",
            "pattern": r"category_field\s*=\s*None",
            "replacement": "category_field = None"
        }
    ]

    # 逐个文件修复
    total_fixes = 0
    for fix in fixes:
        file_path = Path(fix["file"])
        if not file_path.exists():
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            pattern = fix["pattern"]

            if callable(fix["replacement"]):
                new_content = re.sub(pattern, fix["replacement"], content, flags=re.MULTILINE)
            else:
                new_content = content.replace(pattern, fix["replacement"])

            if new_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                total_fixes += 1
                print(f"修复 {file_path}")

        except Exception as e:
            print(f"处理 {file_path} 时出错: {e}")

    print(f"\n修复完成，共修复 {total_fixes} 个文件")

def main():
    """主函数"""
    print("F821未定义名称问题修复工具")
    print("=" * 50)

    fix_undefined_names()

    print("\n验证修复结果...")
    # 运行ruff检查验证结果
    os.system('uv run ruff check src/ --select=F821 --statistics')

if __name__ == "__main__":
    main()