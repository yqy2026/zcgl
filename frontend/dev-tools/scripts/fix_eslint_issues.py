#!/usr/bin/env python3
"""
前端ESLint问题自动修复脚本
按照优先级修复常见的ESLint错误和警告
"""

import os
import re
import subprocess
from pathlib import Path

def run_eslint_fix():
    """运行ESLint自动修复"""
    print("运行ESLint自动修复...")
    try:
        result = subprocess.run(
            ['npm', 'run', 'lint:fix'],
            cwd='.',
            capture_output=True,
            text=True,
            timeout=60
        )
        print(f"ESLint自动修复完成，退出码: {result.returncode}")
        if result.stdout:
            print(f"标准输出: {result.stdout}")
        if result.stderr:
            print(f"错误输出: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"ESLint自动修复失败: {e}")
        return False

def fix_unused_imports(file_path: str) -> int:
    """修复未使用的导入"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        fixes = 0

        # 移除未使用的React导入
        if 'import React' in content and 'React.' not in content and '<React' not in content:
            content = re.sub(r'import React[^\n]*\n', '', content)
            fixes += 1

        # 移除未使用的图标导入
        icon_pattern = r"import\s+\{[^}]+\}\s+from\s+['\"]@ant-design/icons['\"];\n"
        icon_imports = re.findall(icon_pattern, content)
        for import_stmt in icon_imports:
            icons = re.findall(r'(\w+)(?:\s+as\s+\w+)?', import_stmt)
            unused_icons = []
            for icon in icons:
                icon_name = icon[0]
                if icon_name not in content.replace(import_stmt, ''):
                    unused_icons.append(icon_name)

            if unused_icons:
                # 保留仍在使用的图标
                remaining_icons = [icon for icon in icons if icon[0] not in unused_icons]
                if remaining_icons:
                    icon_list = []
                    for i in remaining_icons:
                        if i[1]:
                            icon_list.append(f'{i[0]} as {i[1]}')
                        else:
                            icon_list.append(i[0])
                    new_import = f"import {{ {', '.join(icon_list)} }} from '@ant-design/icons';\n"
                    content = content.replace(import_stmt, new_import)
                else:
                    content = content.replace(import_stmt, '')
                fixes += 1

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"修复 {file_path} 中的 {fixes} 个未使用导入问题")
            return fixes

        return 0

    except Exception as e:
        print(f"处理 {file_path} 时出错: {e}")
        return 0

def fix_unused_variables(file_path: str) -> int:
    """修复未使用的变量"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        fixes = 0

        # 移除未使用的变量（简单模式）
        lines = content.split('\n')
        new_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # 检查未使用的变量声明
            unused_patterns = [
                r"^\s*const\s+\w+\s*=.*?//.*unused.*",
                r"^\s*let\s+\w+\s*=.*?//.*unused.*",
                r"^\s*var\s+\w+\s*=.*?//.*unused.*",
            ]

            is_unused = any(re.search(pattern, line) for pattern in unused_patterns)

            if not is_unused:
                new_lines.append(line)
            else:
                fixes += 1

            i += 1

        if fixes > 0:
            new_content = '\n'.join(new_lines)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"修复 {file_path} 中的 {fixes} 个未使用变量问题")
            return fixes

        return 0

    except Exception as e:
        print(f"处理 {file_path} 时出错: {e}")
        return 0

def fix_any_types(file_path: str) -> int:
    """修复any类型问题（添加类型注解）"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        fixes = 0

        # 简单的any类型修复策略
        any_patterns = [
            (r':\s*any\s*([,);])', ': unknown\\1'),  # 将any替换为unknown
            (r'<any>', '<unknown>'),                # 泛型中的any
        ]

        for pattern, replacement in any_patterns:
            matches = re.findall(pattern, content)
            if matches:
                content = re.sub(pattern, replacement, content)
                fixes += len(matches)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"修复 {file_path} 中的 {fixes} 个any类型问题")
            return fixes

        return 0

    except Exception as e:
        print(f"处理 {file_path} 时出错: {e}")
        return 0

def main():
    """主函数"""
    print("开始前端ESLint问题修复...")

    src_dir = Path("src")
    if not src_dir.exists():
        print("src目录不存在")
        return

    total_fixes = 0
    files_processed = 0

    # 首先运行ESLint自动修复
    eslint_success = run_eslint_fix()

    # 然后手动修复其他问题
    for py_file in src_dir.rglob("*.tsx"):
        if py_file.is_file() and not any(part.startswith('.') for part in py_file.parts):
            fixes = 0
            fixes += fix_unused_imports(str(py_file))
            fixes += fix_unused_variables(str(py_file))
            fixes += fix_any_types(str(py_file))

            total_fixes += fixes
            files_processed += 1

    print(f"\n处理完成:")
    print(f"  处理文件数: {files_processed}")
    print(f"  修复问题数: {total_fixes}")
    print(f"  ESLint自动修复: {'成功' if eslint_success else '失败'}")

if __name__ == "__main__":
    main()
