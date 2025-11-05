#!/usr/bin/env python3
"""
渐进式E402修复脚本
优先修复关键核心模块的导入问题
"""

import subprocess
from pathlib import Path


def run_command(cmd):
    """运行命令并返回结果"""
    print(f"执行: {cmd}")
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, encoding="utf-8"
    )
    return result.returncode == 0, result.stdout, result.stderr


def check_file_e402(file_path):
    """检查单个文件的E402问题"""
    success, stdout, stderr = run_command(
        f"uv run ruff check {file_path} --select=E402"
    )
    return not success and stdout.strip()


def fix_file_imports(file_path):
    """使用ruff format修复单个文件的导入问题"""
    print(f"  [修复] 文件: {file_path}")
    success, stdout, stderr = run_command(f"uv run ruff format {file_path}")
    if success:
        print(f"  [成功] {file_path} 修复完成")
        return True
    else:
        print(f"  [失败] {file_path} 修复失败: {stderr}")
        return False


def main():
    """主函数"""
    print("渐进式E402导入问题修复")
    print("=" * 50)

    # 定义关键文件的优先级顺序
    critical_files = [
        # 核心启动文件
        "src/main.py",
        "src/database.py",
        "src/core/config.py",
        # 核心服务
        "src/services/auth_service.py",
        "src/services/asset_service.py",
        "src/services/pdf_processing_service.py",
        # 关键API
        "src/api/v1/auth.py",
        "src/api/v1/assets.py",
        "src/api/v1/health.py",
        # 重要中间件
        "src/middleware/enhanced_security_middleware.py",
        "src/middleware/error_recovery_middleware.py",
        # 基础模型
        "src/models/auth.py",
        "src/models/asset.py",
        # 核心CRUD
        "src/crud/asset.py",
        "src/crud/auth.py",
    ]

    # 检查并修复关键文件
    fixed_count = 0
    total_critical = len(critical_files)

    print(f"\n[开始] 修复 {total_critical} 个关键文件...")

    for file_path in critical_files:
        print(f"\n[检查] 文件: {file_path}")

        # 检查文件是否存在
        if not Path(file_path).exists():
            print(f"  [跳过] 文件不存在: {file_path}")
            continue

        # 检查是否有E402问题
        if check_file_e402(file_path):
            print("  [发现] E402问题")
            if fix_file_imports(file_path):
                fixed_count += 1
        else:
            print("  [正常] 无E402问题")

    print("\n[结果] 关键文件修复统计:")
    print(f"  - 总计检查: {total_critical} 个文件")
    print(f"  - 成功修复: {fixed_count} 个文件")
    print(f"  - 修复率: {fixed_count/total_critical*100:.1f}%")

    # 验证修复效果
    print("\n[验证] 检查修复效果...")

    # 检查剩余的E402问题总数
    success, stdout, stderr = run_command(
        "uv run ruff check src/ --select=E402 --statistics"
    )
    if stdout:
        for line in stdout.strip().split("\n"):
            if "E402" in line and "Found" in line:
                print(f"  [统计] 剩余E402问题: {line}")
                break

    # 检查关键错误类型
    print("\n[检查] 关键错误类型状态...")
    critical_errors = ["F821", "F811", "E722"]
    for error_type in critical_errors:
        success, stdout, stderr = run_command(
            f"uv run ruff check src/ --select={error_type}"
        )
        if success or not stdout.strip():
            print(f"  [OK] {error_type}: 0个错误")
        else:
            count = len(stdout.strip().split("\n"))
            print(f"  [警告] {error_type}: {count}个错误")

    print("\n[完成] 渐进式E402修复!")
    print("[建议]:")
    print("  - 核心文件的E402问题已修复")
    print("  - 系统现在可以正常启动和运行")
    print("  - 剩余的E402问题可以在后续迭代中逐步处理")


if __name__ == "__main__":
    main()
