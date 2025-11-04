#!/usr/bin/env python3
"""
渐进式修复E402导入问题
选择关键模块进行修复，避免一次性修改过多文件
"""

import os
import re
from pathlib import Path

def fix_e402_in_critical_modules():
    """修复关键模块中的E402导入问题"""
    print("开始渐进式修复E402导入问题...")

    # 关键模块列表，按优先级排序
    critical_modules = [
        "src/api/v1/assets.py",
        "src/api/v1/auth.py",
        "src/api/v1/statistics.py",
        "src/services/auth_service.py",
        "src/services/asset_service.py",
        "src/core/config.py",
        "src/main.py",
        "src/database.py",
        "src/middleware/error_recovery_middleware.py",
        "src/middleware/enhanced_security_middleware.py"
    ]

    total_fixes = 0

    for module_path in critical_modules:
        path = Path(module_path)
        if not path.exists():
            continue

        print(f"\n修复模块: {module_path}")
        fixes_in_file = fix_single_file(path)
        total_fixes += fixes_in_file

        if fixes_in_file > 0:
            print(f"  修复了 {fixes_in_file} 个导入问题")

    print(f"\n关键模块修复完成，共修复 {total_fixes} 个导入问题")
    return total_fixes

def fix_single_file(file_path):
    """修复单个文件的E402问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 将所有import语句移到文件顶部
        lines = content.split('\n')
        imports = []
        non_imports = []
        docstring_lines = []

        # 状态跟踪
        in_docstring = False
        docstring_complete = False
        has_shebang = False

        for line in lines:
            # 检查是否有shebang
            if line.startswith('#!') and not has_shebang:
                has_shebang = True
                non_imports.append(line)
                continue

            # 处理文档字符串
            if '"""' in line or "'''" in line:
                if not in_docstring:
                    # 开始文档字符串
                    in_docstring = True
                    docstring_lines.append(line)
                    # 检查是否在同一行结束
                    if line.count('"""') >= 2 or line.count("'''") >= 2:
                        in_docstring = False
                        docstring_complete = True
                else:
                    # 结束文档字符串
                    docstring_lines.append(line)
                    if '"""' in line or "'''" in line:
                        in_docstring = False
                        docstring_complete = True
                continue

            if in_docstring:
                docstring_lines.append(line)
                continue

            # 检查是否是import语句
            stripped = line.strip()
            if (stripped.startswith('import ') or
                stripped.startswith('from ') or
                stripped.startswith('# type: ignore')):  # type: ignore也算import相关
                imports.append(line)
            elif stripped == '' or stripped.startswith('#'):
                # 空行和注释保持原位置
                non_imports.append(line)
            else:
                # 非import语句
                non_imports.append(line)

        # 重新构建文件内容
        new_lines = []

        # 1. 添加shebang（如果有）
        if has_shebang and non_imports:
            new_lines.append(non_imports.pop(0))

        # 2. 添加空行
        new_lines.append('')

        # 3. 添加文档字符串（如果有）
        if docstring_lines:
            new_lines.extend(docstring_lines)
            new_lines.append('')

        # 4. 添加所有import语句
        if imports:
            # 去重并排序
            unique_imports = []
            seen = set()
            for imp in imports:
                stripped = imp.strip()
                if stripped and stripped not in seen:
                    unique_imports.append(imp)
                    seen.add(stripped)
                elif stripped == '' or stripped.startswith('#'):
                    # 保留空行和注释
                    unique_imports.append(imp)

            new_lines.extend(unique_imports)
            new_lines.append('')

        # 5. 添加其他内容
        new_lines.extend(non_imports)

        # 6. 清理多余的空行
        cleaned_lines = []
        prev_empty = False
        for line in new_lines:
            is_empty = line.strip() == ''
            if not (is_empty and prev_empty):
                cleaned_lines.append(line)
                prev_empty = is_empty
            else:
                prev_empty = is_empty

        new_content = '\n'.join(cleaned_lines)

        # 写入文件
        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return 1

        return 0

    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {e}")
        return 0

def verify_fixes():
    """验证修复结果"""
    print("\n验证修复结果...")

    # 检查关键模块的E402问题
    critical_modules = [
        "src/api/v1/assets.py",
        "src/api/v1/auth.py",
        "src/api/v1/statistics.py"
    ]

    remaining_issues = 0
    for module_path in critical_modules:
        path = Path(module_path)
        if path.exists():
            result = os.system(f'uv run ruff check {module_path} --select=E402')
            if result == 0:
                print(f"✅ {module_path} - 无E402问题")
            else:
                print(f"❌ {module_path} - 仍有E402问题")
                remaining_issues += 1

    print(f"\n验证完成，{len(critical_modules) - remaining_issues}/{len(critical_modules)} 个关键模块已修复")
    return remaining_issues == 0

def main():
    """主函数"""
    print("E402导入问题渐进式修复工具")
    print("=" * 60)

    # 修复关键模块
    total_fixes = fix_e402_in_critical_modules()

    # 验证结果
    success = verify_fixes()

    if success:
        print("\n🎉 关键模块E402修复成功！")
    else:
        print("\n⚠️ 部分模块仍有问题，需要手动检查")

    print(f"\n总计修复: {total_fixes} 个导入问题")

if __name__ == "__main__":
    main()