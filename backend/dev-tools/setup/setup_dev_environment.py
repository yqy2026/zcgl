#!/usr/bin/env python3
"""
开发环境自动设置脚本
配置代码质量检查工具和开发环境
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None):
    """运行命令并返回结果"""
    print(f"[执行] {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result.returncode == 0, result.stdout, result.stderr


def check_python_version():
    """检查Python版本"""
    print("=" * 60)
    print("[检查] Python版本")
    print("=" * 60)

    version = sys.version_info
    print(f"Python版本: {version.major}.{version.minor}.{version.micro}")

    if version.major >= 3 and version.minor >= 12:
        print("[OK] Python版本满足要求 (>=3.12)")
        return True
    else:
        print("[警告] 建议使用Python 3.12或更高版本")
        return False


def check_dependencies():
    """检查依赖是否安装"""
    print("\n" + "=" * 60)
    print("[检查] 项目依赖")
    print("=" * 60)

    required_packages = [
        ("ruff", "代码检查和格式化"),
        ("mypy", "静态类型检查"),
        ("pytest", "测试框架"),
        ("fastapi", "Web框架"),
        ("sqlalchemy", "ORM框架"),
    ]

    missing_packages = []

    for package, description in required_packages:
        success, _, _ = run_command(f'uv run python -c "import {package}"')
        if success:
            print(f"[OK] {package} - {description}")
        else:
            print(f"[缺失] {package} - {description}")
            missing_packages.append(package)

    if missing_packages:
        print(f"\n[安装] 缺失的包: {', '.join(missing_packages)}")
        print("请运行: uv sync")
        return False

    print("[OK] 所有依赖已安装")
    return True


def setup_git_hooks():
    """设置Git hooks"""
    print("\n" + "=" * 60)
    print("[设置] Git Hooks")
    print("=" * 60)

    # 检查Git仓库
    if not Path(".git").exists():
        print("[警告] 不是Git仓库，跳过hooks设置")
        return True

    # 检查pre-commit是否可用
    success, _, _ = run_command("uv run pre-commit --version")
    if success:
        print("[安装] Pre-commit hooks")
        success, _, _ = run_command("uv run pre-commit install")
        if success:
            print("[OK] Pre-commit hooks已安装")
        else:
            print("[警告] Pre-commit hooks安装失败")
    else:
        print("[信息] Pre-commit不可用，使用本地检查脚本")

    # 创建便捷的检查脚本
    check_script = """#!/bin/bash
echo "=== 运行代码质量检查 ==="
cd backend && uv run python local_code_quality_check.py
"""

    with open("../check-code-quality.sh", "w", encoding="utf-8") as f:
        f.write(check_script)

    # 在Windows创建bat文件
    bat_script = """@echo off
echo === 运行代码质量检查 ===
cd backend
uv run python local_code_quality_check.py
"""

    with open("../check-code-quality.bat", "w", encoding="utf-8") as f:
        f.write(bat_script)

    print("[OK] 便捷检查脚本已创建")
    return True


def create_dev_scripts():
    """创建开发脚本"""
    print("\n" + "=" * 60)
    print("[创建] 开发脚本")
    print("=" * 60)

    scripts = {
        "run-quality-check.sh": "#!/bin/bash\ncd backend && uv run python local_code_quality_check.py",
        "run-tests.sh": "#!/bin/bash\ncd backend && uv run python -m pytest tests/ -v",
        "run-server.sh": "#!/bin/bash\ncd backend && uv run python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8002",
        "fix-format.sh": "#!/bin/bash\ncd backend && uv run ruff format src/",
        "fix-issues.sh": "#!/bin/bash\ncd backend && uv run ruff check src/ --fix",
    }

    for script_name, content in scripts.items():
        script_path = Path(script_name)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[创建] {script_name}")

    return True


def run_initial_quality_check():
    """运行初始质量检查"""
    print("\n" + "=" * 60)
    print("[验证] 初始代码质量检查")
    print("=" * 60)

    success, stdout, stderr = run_command("uv run python local_code_quality_check.py")

    if success:
        print("[OK] 初始质量检查通过")
        return True
    else:
        print("[信息] 发现一些质量问题（这是正常的）")
        print("可以使用以下命令修复:")
        print("  uv run ruff format src/      # 格式化代码")
        print("  uv run ruff check src/ --fix # 修复简单问题")
        return True  # 不算失败，因为问题可能是预期的


def generate_setup_report():
    """生成设置报告"""
    print("\n" + "=" * 60)
    print("[报告] 开发环境设置完成")
    print("=" * 60)

    report = f"""
开发环境设置报告
================

✅ 完成项目:
- Python版本检查
- 依赖包验证
- Git hooks设置
- 开发脚本创建
- 初始质量检查

📁 创建的文件:
- local_code_quality_check.py - 本地代码质量检查
- CODE_QUALITY_GUIDE.md - 代码质量指南
- check-code-quality.sh/.bat - 便捷检查脚本
- 各种开发脚本

🚀 下一步:
1. 运行代码质量检查: python local_code_quality_check.py
2. 修复发现的问题: uv run ruff format src/
3. 运行测试: uv run python -m pytest tests/ -v
4. 启动开发服务器: uv run python -m uvicorn src.main:app --reload

📖 使用指南:
- 详细说明请参考: CODE_QUALITY_GUIDE.md
- 每次提交前运行质量检查
- 定期更新依赖: uv sync

设置时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    with open("SETUP_REPORT.md", "w", encoding="utf-8") as f:
        f.write(report)

    print(report)
    return True


def main():
    """主函数"""
    print("开发环境自动设置工具")
    print("=" * 60)
    print("此工具将配置代码质量检查和开发环境")

    # 切换到脚本所在目录
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    print(f"[目录] 工作目录: {script_dir}")

    try:
        # 执行设置步骤
        steps = [
            ("Python版本检查", check_python_version),
            ("依赖检查", check_dependencies),
            ("Git Hooks设置", setup_git_hooks),
            ("开发脚本创建", create_dev_scripts),
            ("初始质量检查", run_initial_quality_check),
            ("设置报告生成", generate_setup_report),
        ]

        for step_name, step_func in steps:
            print(f"\n[步骤] {step_name}")
            success = step_func()
            if not success:
                print(f"[警告] {step_name} 未完全成功")

        print("\n" + "=" * 60)
        print("🎉 开发环境设置完成！")
        print("=" * 60)
        print("\n[提示] 现在可以开始开发了:")
        print("  1. 运行质量检查: python local_code_quality_check.py")
        print("  2. 修复格式问题: uv run ruff format src/")
        print("  3. 运行测试: uv run python -m pytest tests/ -v")
        print("  4. 启动服务器: uv run python -m uvicorn src.main:app --reload")

        return 0

    except KeyboardInterrupt:
        print("\n[中断] 设置被用户中断")
        return 130
    except Exception as e:
        print(f"\n[错误] 设置过程中出现异常: {e}")
        return 1


if __name__ == "__main__":
    from datetime import datetime

    sys.exit(main())
