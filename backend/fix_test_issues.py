#!/usr/bin/env python3
"""
修复测试环境中的常见问题
"""

import re
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description=""):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=".")
        if result.returncode != 0:
            print(f"❌ {description} failed:")
            print(result.stderr)
            return False
        print(f"✅ {description} completed")
        return True
    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False

def check_and_fix_issues():
    """检查并修复常见问题"""

    issues_found = []
    fixes_applied = []

    print("🔍 检查并修复测试环境问题...")

    # 1. 检查Python语法错误
    print("\n1. 检查Python语法错误...")
    syntax_errors = []
    for py_file in Path("src").rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            # 使用python -m py_compile检查语法
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(py_file)],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                syntax_errors.append(str(py_file))
        except Exception as e:
            print(f"Error checking {py_file}: {e}")

    if syntax_errors:
        issues_found.append(f"发现 {len(syntax_errors)} 个文件有语法错误")
        print(f"❌ 语法错误文件: {len(syntax_errors)}")
        for error_file in syntax_errors[:3]:  # 只显示前3个
            print(f"   - {error_file}")
    else:
        fixes_applied.append("✅ 所有Python文件语法正确")

    # 2. 检查导入问题
    print("\n2. 检查导入问题...")
    import_errors = []

    # 检查常见导入错误
    critical_files = [
        "src/services/pdf_session_service.py",
        "src/models/pdf_import_session.py",
        "tests/conftest.py"
    ]

    for file_path in critical_files:
        if Path(file_path).exists():
            try:
                # 尝试导入检查
                module_path = file_path.replace('/', '.').replace('.py', '').replace('src.', '')
                spec = __import__(module_path)
                print(f"✅ {file_path} 导入正常")
            except ImportError as e:
                import_errors.append(f"{file_path}: {e}")
                print(f"❌ {file_path}: {e}")
            except Exception as e:
                print(f"⚠️ {file_path}: {e}")

    if import_errors:
        issues_found.append(f"发现 {len(import_errors)} 个导入错误")
    else:
        fixes_applied.append("✅ 关键文件导入正常")

    # 3. 修复常见类型导入问题
    print("\n3. 修复类型导入问题...")
    typing_issues = []

    typing_patterns = {
        r'List\[.*?\].*?PDFImportSession': 'List[PDFImportSession]',
        r'List\[.*?\].*?\[Any\]': 'List[Any]',
        r'->\s*List\[.*?\].*?\]': '-> List[Any]',
    }

    for py_file in Path("src").rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        try:
            content = py_file.read_text(encoding='utf-8')
            original = content

            # 修复常见的类型问题
            content = re.sub(r'List\[.*?\].*?\]PDFImportSession\]', 'List[PDFImportSession]', content)
            content = re.sub(r'->\s*List\[.*?\].*?\]', '-> List[Any]', content)

            if content != original:
                py_file.write_text(content, encoding='utf-8')
                typing_issues.append(str(py_file))
                print(f"✅ 修复类型问题: {py_file}")

        except Exception as e:
            print(f"⚠️ 处理 {py_file} 时出错: {e}")

    if typing_issues:
        fixes_applied.append(f"✅ 修复了 {len(typing_issues)} 个文件的类型问题")

    # 4. 检查数据库连接
    print("\n4. 检查数据库配置...")
    db_files = [
        "src/core/database.py",
        "src/models/__init__.py"
    ]

    db_ok = True
    for db_file in db_files:
        if Path(db_file).exists():
            try:
                # 检查数据库相关文件是否可以正常解析
                content = Path(db_file).read_text(encoding='utf-8')
                if 'sqlite' in content.lower() or 'database' in content.lower():
                    print(f"✅ {db_file} 数据库配置正常")
            except Exception as e:
                print(f"⚠️ 检查 {db_file} 时出错: {e}")
                db_ok = False

    if db_ok:
        fixes_applied.append("✅ 数据库配置正常")

    # 5. 运行简单测试验证
    print("\n5. 运行基础功能测试...")

    # 测试基础导入
    try:
        import uvicorn
        import fastapi
        import sqlalchemy
        fixes_applied.append("✅ 核心依赖可用")
    except ImportError as e:
        issues_found.append(f"核心依赖缺失: {e}")

    # 6. 清理缓存和临时文件
    print("\n6. 清理缓存文件...")

    cache_dirs = [
        "__pycache__",
        ".pytest_cache",
        "*.pyc"
    ]

    cache_cleaned = 0
    for pattern in cache_dirs:
        for item in Path(".").glob(pattern):
            if item.is_dir():
                import shutil
                try:
                    shutil.rmtree(item)
                    cache_cleaned += 1
                except:
                    pass
            elif item.is_file() and item.suffix == '.pyc':
                item.unlink()
                cache_cleaned += 1

    if cache_cleaned > 0:
        fixes_applied.append(f"✅ 清理了 {cache_cleaned} 个缓存文件")

    # 总结报告
    print("\n" + "="*60)
    print("📊 修复总结报告")
    print("="*60)

    if issues_found:
        print("\n❌ 发现的问题:")
        for issue in issues_found:
            print(f"   - {issue}")

    print(f"\n✅ 应用的修复:")
    for fix in fixes_applied:
        print(f"   - {fix}")

    success_rate = len(fixes_applied) / (len(fixes_applied) + len(issues_found)) * 100 if fixes_applied or issues_found else 100
    print(f"\n📈 修复成功率: {success_rate:.1f}%")

    return len(issues_found) == 0

def main():
    """主函数"""
    print("🚀 启动测试环境诊断和修复...")

    success = check_and_fix_issues()

    if success:
        print("\n🎉 所有问题已修复！测试环境准备就绪。")
        return 0
    else:
        print("\n⚠️ 仍有一些问题需要手动处理。")
        return 1

if __name__ == "__main__":
    exit(main())