#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件命名规范检查脚本
检查前端和后端文件是否符合项目命名规范
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# 设置控制台编码为 UTF-8
if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass


class FileNamingChecker:
    """文件命名规范检查器"""

    def __init__(self):
        self.errors = []
        self.warnings = []

    # Frontend 规则
    # 组件文件：PascalCase
    FRONTEND_COMPONENT_PATTERN = re.compile(r'^[A-Z][a-zA-Z0-9]*\.tsx?$')

    # Hook 文件：use 前缀 + PascalCase（可以是 .ts 或 .tsx）
    FRONTEND_HOOK_PATTERN = re.compile(r'^use[A-Z][a-zA-Z0-9]*\.tsx?$')

    # 测试文件：.test. 后缀（只匹配文件名）
    FRONTEND_TEST_PATTERN = re.compile(r'^.+\.(test|spec)\.(tsx?|js)$')

    # Service/Util/Type 文件：camelCase
    FRONTEND_CAMELCASE_PATTERN = re.compile(r'^[a-z][a-zA-Z0-9]*\.ts$')

    # 类型定义文件：.d.ts
    FRONTEND_DTS_PATTERN = re.compile(r'^.+\.(d\.ts|d\.tsx)$')

    # Backend 规则
    # Python 源文件：snake_case
    BACKEND_SNAKECASE_PATTERN = re.compile(r'^[a-z][a-z0-9_]*\.py$')

    # 测试文件：test_ 前缀或 _test.py 后缀
    BACKEND_TEST_PATTERN = re.compile(r'^(test_.+|.+_test)\.py$')

    def check_frontend_file(self, filepath: str) -> None:
        """
        检查前端文件命名规范

        规则：
        - 组件文件（components/）：PascalCase
        - Hook 文件（hooks/）：use 前缀 + PascalCase
        - 测试文件（__tests__/）：.test. 后缀
        - Service/Util/Type 文件：camelCase
        - 类型定义文件：.d.ts
        """
        filename = os.path.basename(filepath)
        path_parts = Path(filepath).parts

        # 检查是否是测试文件
        if '__tests__' in path_parts:
            if not self.FRONTEND_TEST_PATTERN.match(filename):
                self.errors.append(
                    f"❌ {filepath}\n"
                    f"   测试文件应使用 .test. 后缀\n"
                    f"   当前: {filename}\n"
                    f"   期望: {{ComponentName}}.test.tsx 或 {{name}}.test.ts"
                )
            return

        # 检查是否是类型定义文件
        if self.FRONTEND_DTS_PATTERN.match(filename):
            return  # 类型定义文件符合规范

        # 检查组件文件（components/ 目录下）
        if 'components' in path_parts:
            if not self.FRONTEND_COMPONENT_PATTERN.match(filename):
                self.errors.append(
                    f"❌ {filepath}\n"
                    f"   组件文件应使用 PascalCase\n"
                    f"   当前: {filename}\n"
                    f"   期望: {{ComponentName}}.tsx 或 {{ComponentName}}.ts"
                )
            return

        # 检查 Hook 文件（hooks/ 目录下）
        if 'hooks' in path_parts:
            if not self.FRONTEND_HOOK_PATTERN.match(filename):
                self.errors.append(
                    f"❌ {filepath}\n"
                    f"   Hook 文件应使用 use 前缀 + PascalCase\n"
                    f"   当前: {filename}\n"
                    f"   期望: use{{FeatureName}}.ts"
                )
            return

        # 检查页面文件（pages/ 目录下）
        if 'pages' in path_parts:
            if not self.FRONTEND_COMPONENT_PATTERN.match(filename):
                self.errors.append(
                    f"❌ {filepath}\n"
                    f"   页面文件应使用 PascalCase\n"
                    f"   当前: {filename}\n"
                    f"   期望: {{FeatureName}}Page.tsx"
                )
            return

        # 检查 Store 文件（store/ 目录下）
        if 'store' in path_parts:
            if not (filename.startswith('use') and self.FRONTEND_COMPONENT_PATTERN.match(filename[3:]) or
                    self.FRONTEND_CAMELCASE_PATTERN.match(filename)):
                self.errors.append(
                    f"❌ {filepath}\n"
                    f"   Store 文件应使用 use 前缀 + PascalCase 或 camelCase\n"
                    f"   当前: {filename}\n"
                    f"   期望: use{{StoreName}}.ts"
                )
            return

        # 检查 service/api/util 文件
        if any(x in path_parts for x in ['services', 'api', 'utils', 'types', 'constants']):
            if not self.FRONTEND_CAMELCASE_PATTERN.match(filename):
                self.errors.append(
                    f"❌ {filepath}\n"
                    f"   Service/Util/Type 文件应使用 camelCase\n"
                    f"   当前: {filename}\n"
                    f"   期望: {{featureName}}.ts 或 {{description}}.ts"
                )
            return

    def check_backend_file(self, filepath: str) -> None:
        """
        检查后端文件命名规范

        规则：
        - Python 源文件：snake_case
        - 测试文件：test_ 前缀或 _test.py 后缀
        """
        filename = os.path.basename(filepath)
        path_parts = Path(filepath).parts

        # 检查测试文件
        if 'tests' in path_parts or 'test' in path_parts:
            if not self.BACKEND_TEST_PATTERN.match(filename):
                self.errors.append(
                    f"❌ {filepath}\n"
                    f"   测试文件应使用 test_ 前缀或 _test.py 后缀\n"
                    f"   当前: {filename}\n"
                    f"   期望: test_{{feature}}.py 或 {{feature}}_test.py"
                )
            return

        # 检查常规 Python 文件
        if not self.BACKEND_SNAKECASE_PATTERN.match(filename):
            self.errors.append(
                f"❌ {filepath}\n"
                f"   Python 文件应使用 snake_case\n"
                f"   当前: {filename}\n"
                f"   期望: {{feature_name}}.py"
            )

    def check_file(self, filepath: str) -> bool:
        """
        检查单个文件的命名规范

        返回: True 如果文件符合规范，False 否则
        """
        # 获取文件名
        filename = os.path.basename(filepath)

        # 跳过特殊文件（这些是标准命名，不需要检查）
        special_files = [
            '__init__.py',      # Python 模块初始化文件
            '__init__.tsx',     # React 模块初始化文件
            '__init__.ts',      # TypeScript 模块初始化文件
            'index.tsx',        # React 组件导出文件
            'index.ts',         # TypeScript 模块导出文件
            'conftest.py',      # pytest 配置文件
            'pytest.ini',       # pytest 配置文件
            'setup.py',         # Python 安装脚本
            'setup.cfg',        # Python 配置文件
        ]

        if filename in special_files:
            return True

        # 跳过特定目录
        skip_patterns = [
            'node_modules',
            '.venv',
            'venv',
            '__pycache__',
            '.pytest_cache',
            '.mypy_cache',
            'dist',
            'build',
            'coverage',
            '.git',
            'migrations',
            'alembic',
            'fixtures',  # 测试夹具文件
            'test_utils',  # 测试工具文件
        ]

        if any(pattern in filepath for pattern in skip_patterns):
            return True

        # 跳过配置文件和特殊文件扩展名
        skip_extensions = [
            '.md',
            '.json',
            '.yaml',
            '.yml',
            '.txt',
            '.toml',
            '.ini',
            '.cfg',
            '.example',
            '.sample',
        ]

        if any(filepath.endswith(ext) for ext in skip_extensions):
            return True

        # 检查前端文件
        if filepath.endswith(('.ts', '.tsx', '.js', '.jsx')):
            if 'frontend' in filepath or filepath.startswith('frontend/'):
                self.check_frontend_file(filepath)
                return True

        # 检查后端文件
        if filepath.endswith('.py'):
            if 'backend' in filepath or filepath.startswith('backend/'):
                self.check_backend_file(filepath)
                return True

        return True

    def print_results(self) -> None:
        """打印检查结果"""
        if not self.errors:
            print("✅ 所有文件命名符合规范！")
            return

        print(f"\n❌ 发现 {len(self.errors)} 个文件命名问题：\n")
        for error in self.errors:
            print(error)
            print()

        if self.warnings:
            print(f"\n⚠️  {len(self.warnings)} 个警告：\n")
            for warning in self.warnings:
                print(warning)
                print()

    def has_errors(self) -> bool:
        """返回是否有错误"""
        return len(self.errors) > 0


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python check_file_naming.py <file1> [file2] ...")
        print("或通过 pre-commit hook 自动调用")
        sys.exit(0)

    checker = FileNamingChecker()

    # 检查所有传入的文件
    for filepath in sys.argv[1:]:
        if os.path.exists(filepath):
            checker.check_file(filepath)

    # 打印结果
    checker.print_results()

    # 返回适当的退出码
    if checker.has_errors():
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
