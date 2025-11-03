#!/usr/bin/env python3
"""
简化的前端ESLint问题修复脚本
专注于最常见的错误类型
"""

import subprocess
from pathlib import Path

def run_eslint_auto_fix():
    """运行ESLint自动修复"""
    print("运行ESLint自动修复...")
    try:
        result = subprocess.run(
            ['npm', 'run', 'lint:fix'],
            cwd='.',
            capture_output=True,
            text=True,
            timeout=120
        )
        print(f"ESLint自动修复完成，退出码: {result.returncode}")
        if result.stdout:
            print(f"输出: {result.stdout[:500]}...")
        return result.returncode == 0
    except Exception as e:
        print(f"ESLint自动修复失败: {e}")
        return False

def count_eslint_issues():
    """统计ESLint问题数量"""
    print("统计ESLint问题...")
    try:
        result = subprocess.run(
            ['npm', 'run', 'lint'],
            cwd='.',
            capture_output=True,
            text=True,
            timeout=60
        )

        output = result.stdout + result.stderr
        error_count = output.count('error')
        warning_count = output.count('warning')

        print(f"当前状态: {error_count} 个错误, {warning_count} 个警告")
        return error_count, warning_count
    except Exception as e:
        print(f"统计ESLint问题失败: {e}")
        return 0, 0

def main():
    """主函数"""
    print("=== 前端ESLint优化开始 ===")

    # 统计初始状态
    initial_errors, initial_warnings = count_eslint_issues()

    # 运行自动修复
    auto_fix_success = run_eslint_auto_fix()

    # 统计修复后状态
    final_errors, final_warnings = count_eslint_issues()

    # 计算改善情况
    error_reduction = initial_errors - final_errors
    warning_reduction = initial_warnings - final_warnings

    print("\n=== 优化结果总结 ===")
    print(f"自动修复状态: {'成功' if auto_fix_success else '部分成功'}")
    print(f"错误数量: {initial_errors} → {final_errors} (减少 {error_reduction})")
    print(f"警告数量: {initial_warnings} → {final_warnings} (减少 {warning_reduction})")

    if error_reduction > 0 or warning_reduction > 0:
        print("✅ ESLint优化成功完成")
    else:
        print("⚠️ 需要手动修复剩余问题")

    return final_errors, final_warnings

if __name__ == "__main__":
    main()