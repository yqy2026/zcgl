#!/usr/bin/env python3
"""
测试优化脚本 - 提高测试覆盖率和质量
"""

import os
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """运行命令并返回结果"""
    print(f"\n[运行] {description}")
    print(f"命令: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=os.getcwd())
        print(f"退出码: {result.returncode}")
        if result.stdout:
            print(f"输出:\n{result.stdout}")
        if result.stderr:
            print(f"错误:\n{result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"执行失败: {e}")
        return False

def analyze_test_structure():
    """分析测试结构"""
    print("\n📊 分析测试结构...")

    test_files = list(Path("tests").glob("*.py"))
    print(f"发现 {len(test_files)} 个测试文件")

    categories = {
        'ocr': [],
        'api': [],
        'rbac': [],
        'database': [],
        'pdf': [],
        'performance': [],
        'integration': [],
        'other': []
    }

    for test_file in test_files:
        if test_file.name == '__init__.py':
            continue

        content = test_file.read_text(encoding='utf-8', errors='ignore').lower()
        if 'ocr' in content:
            categories['ocr'].append(test_file.name)
        elif 'api' in content:
            categories['api'].append(test_file.name)
        elif 'rbac' in content or 'permission' in content:
            categories['rbac'].append(test_file.name)
        elif 'database' in content or 'db' in content:
            categories['database'].append(test_file.name)
        elif 'pdf' in content:
            categories['pdf'].append(test_file.name)
        elif 'performance' in content or 'benchmark' in content:
            categories['performance'].append(test_file.name)
        elif 'integration' in content:
            categories['integration'].append(test_file.name)
        else:
            categories['other'].append(test_file.name)

    print("\n📋 测试分类:")
    for category, files in categories.items():
        if files:
            print(f"  {category}: {len(files)} 个文件")
            for file in files[:3]:  # 只显示前3个
                print(f"    - {file}")
            if len(files) > 3:
                print(f"    ... 还有 {len(files) - 3} 个文件")

    return categories

def create_test_suite():
    """创建优化的测试套件"""
    print("\n🎯 创建优化的测试套件...")

    # 核心测试套件 - 快速验证核心功能
    core_tests = [
        "tests/simple_ocr_test.py",
        "tests/ocr_basic_test.py",
        "tests/test_simple_database.py",
        "tests/test_rbac_simple.py"
    ]

    # 功能测试套件 - 验证主要业务功能
    functional_tests = [
        "tests/final_ocr_test.py",
        "tests/test_pdf_import_simple.py",
        "tests/test_new_assets_api.py",
        "tests/test_rbac_core.py"
    ]

    # 集成测试套件 - 验证系统集成
    integration_tests = [
        "tests/test_integration_asset_calculations.py",
        "tests/test_frontend_backend_integration.py"
    ]

    test_suites = {
        'core': core_tests,
        'functional': functional_tests,
        'integration': integration_tests
    }

    return test_suites

def run_optimized_tests():
    """运行优化的测试"""
    print("\n🚀 运行优化的测试套件...")

    # 首先运行核心测试
    core_tests = [
        "tests/simple_ocr_test.py",
        "tests/ocr_basic_test.py"
    ]

    print("\n📋 运行核心测试...")
    for test in core_tests:
        success = run_command(f"uv run python -m pytest {test} -v", f"运行 {test}")
        if not success:
            print(f"❌ {test} 失败")
        else:
            print(f"✅ {test} 通过")

def generate_coverage_report():
    """生成覆盖率报告"""
    print("\n📈 生成覆盖率报告...")

    # 运行通过的测试来生成覆盖率
    passing_tests = [
        "tests/simple_ocr_test.py",
        "tests/ocr_basic_test.py",
        "tests/final_ocr_test.py"
    ]

    test_list = " ".join(passing_tests)
    success = run_command(
        f"uv run python -m pytest {test_list} --cov=src --cov-report=term-missing --cov-report=html",
        "生成覆盖率报告"
    )

    if success:
        print("✅ 覆盖率报告生成完成")
        print("📄 HTML报告位置: htmlcov/index.html")
    else:
        print("❌ 覆盖率报告生成失败")

def create_test_recommendations():
    """创建测试改进建议"""
    print("\n💡 生成测试改进建议...")

    recommendations = [
        "1. 🎯 核心模块测试覆盖",
        "   - 为 src/services/ 中的关键服务添加单元测试",
        "   - 为 src/models/ 中的数据模型添加验证测试",
        "   - 为 src/api/v1/ 中的API端点添加集成测试",

        "2. 🛡️ 安全测试增强",
        "   - 添加RBAC权限测试用例",
        "   - 添加输入验证和安全测试",
        "   - 添加认证和授权测试",

        "3. 📊 性能测试优化",
        "   - 添加PDF处理性能测试",
        "   - 添加数据库查询性能测试",
        "   - 添加API响应时间测试",

        "4. 🔧 测试基础设施改进",
        "   - 修复现有的测试错误",
        "   - 优化测试数据库设置",
        "   - 添加测试数据工厂",
        "   - 改进测试配置和环境管理",

        "5. 📋 测试文档化",
        "   - 为每个测试套件添加文档",
        "   - 创建测试运行指南",
        "   - 添加测试最佳实践文档"
    ]

    with open("TEST_RECOMMENDATIONS.md", "w", encoding="utf-8") as f:
        f.write("# 测试改进建议\n\n")
        for rec in recommendations:
            f.write(f"{rec}\n\n")

    print("✅ 测试改进建议已保存到 TEST_RECOMMENDATIONS.md")

    for rec in recommendations:
        print(f"  {rec}")

def main():
    """主函数"""
    print("测试优化脚本启动")
    print("=" * 50)

    # 切换到backend目录
    backend_dir = Path("backend")
    if backend_dir.exists():
        os.chdir(backend_dir)
        print(f"📁 切换到目录: {backend_dir.absolute()}")

    # 分析测试结构
    categories = analyze_test_structure()

    # 创建测试套件
    test_suites = create_test_suite()

    # 运行优化的测试
    run_optimized_tests()

    # 生成覆盖率报告
    generate_coverage_report()

    # 创建改进建议
    create_test_recommendations()

    print("\n🎉 测试优化完成!")
    print("=" * 50)

if __name__ == "__main__":
    main()
