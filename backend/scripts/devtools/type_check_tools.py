#!/usr/bin/env python3
"""
类型检查工具集
用于快速定位和分类 mypy 类型错误

Usage:
    python type_check_tools.py                    # 完整报告
    python type_check_tools.py --quick-wins       # 快速胜利文件
    python type_check_tools.py --by-tier          # 按层级分组
    python type_check_tools.py --trend            # 错误趋势
"""

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


# 预编译正则表达式
ERROR_CODE_PATTERN = re.compile(r"\[([a-z-]+)\]")
FILE_ERROR_PATTERN = re.compile(r"^([\w\\/\.]+):(\d+): error:")


def run_mypy(source_dir: str = "src") -> str:
    """运行 mypy 并获取输出"""
    result = subprocess.run(
        ["python", "-m", "mypy", source_dir, "--show-error-codes"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
    )
    return result.stdout


def categorize_errors(errors_text: str) -> dict[str, list[str]]:
    """按错误代码分类"""
    categories = defaultdict(list)

    for line in errors_text.split("\n"):
        if match := ERROR_CODE_PATTERN.search(line):
            error_code = match.group(1)
            categories[error_code].append(line)

    return dict(categories)


def group_by_file(errors_text: str) -> dict[str, list[str]]:
    """按文件分组错误"""
    files = defaultdict(list)

    for line in errors_text.split("\n"):
        if match := FILE_ERROR_PATTERN.match(line):
            filepath = match.group(1)
            files[filepath].append(line)

    # 按错误数量排序
    return dict(sorted(files.items(), key=lambda x: len(x[1]), reverse=True))


def find_quick_wins(errors_text: str, max_errors: int = 5) -> dict[str, list[str]]:
    """查找可以快速修复的文件（<=5个错误）"""
    files_by_error_count = group_by_file(errors_text)
    return {
        f: errors for f, errors in files_by_error_count.items() if len(errors) <= max_errors
    }


def classify_by_tier(files_errors: dict[str, list[str]]) -> dict[str, dict[str, Any]]:
    """按 Tier 分层分类文件"""
    tiers = {
        "Tier 0 (Core)": {
            "patterns": ["database.py", "core/security", "core/config", "core/jwt", "models/", "schemas/"],
            "files": {},
        },
        "Tier 1 (Business)": {
            "patterns": ["api/v1/", "services/", "crud/"],
            "files": {},
        },
        "Tier 2 (Utils)": {
            "patterns": ["utils/", "middleware/", "validation/"],
            "files": {},
        },
        "Tier 3 (3rd Party)": {
            "patterns": ["services/document", "services/excel"],
            "files": {},
        },
    }

    for filepath, errors in files_errors.items():
        classified = False
        for tier_name, tier_data in tiers.items():
            for pattern in tier_data["patterns"]:
                if pattern in filepath:
                    tier_data["files"][filepath] = errors
                    classified = True
                    break
            if classified:
                break

        if not classified:
            # 未分类的文件归入 Tier 2
            tiers["Tier 2 (Utils)"]["files"][filepath] = errors

    # 统计每个 tier 的错误数
    for tier_name, tier_data in tiers.items():
        tier_data["error_count"] = sum(len(errs) for errs in tier_data["files"].values())
        tier_data["file_count"] = len(tier_data["files"])

    return tiers


def print_report(errors_text: str):
    """打印完整报告"""
    print("=" * 80)
    print(" MyPy 类型检查报告")
    print("=" * 80)

    # 1. 错误分类统计
    print("\n【错误分类统计】")
    categories = categorize_errors(errors_text)
    for code, lines in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {code:25s}: {len(lines):4d} 个")

    total_errors = sum(len(lines) for lines in categories.values())
    print(f"  {'总计':25s}: {total_errors:4d} 个")

    # 2. Top 20 问题文件
    print("\n【Top 20 问题文件】")
    files = group_by_file(errors_text)
    for i, (f, errs) in enumerate(list(files.items())[:20], 1):
        print(f"  {i:2d}. {f:60s} ({len(errs):3d} errors)")

    # 3. 快速胜利
    print("\n【快速胜利文件 (≤5 错误)】")
    quick_wins = find_quick_wins(errors_text)
    print(f"  共 {len(quick_wins)} 个文件可快速修复")
    if quick_wins:
        for f, errs in list(quick_wins.items())[:10]:
            print(f"    • {f:60s} ({len(errs)} errors)")

    # 4. 按分层统计
    print("\n【按 Tier 分层统计】")
    tiers = classify_by_tier(files)
    for tier_name, tier_data in tiers.items():
        print(f"  {tier_name:20s}: {tier_data['error_count']:4d} errors in {tier_data['file_count']:3d} files")


def print_quick_wins(errors_text: str, max_errors: int = 5):
    """打印快速胜利文件列表"""
    quick_wins = find_quick_wins(errors_text, max_errors)
    print(f"找到 {len(quick_wins)} 个快速胜利文件（≤{max_errors} 个错误）：\n")

    for filepath, errors in sorted(quick_wins.items(), key=lambda x: len(x[1])):
        print(f"{filepath} ({len(errors)} errors):")
        for error in errors[:3]:  # 只显示前3个错误
            print(f"  {error}")
        if len(errors) > 3:
            print(f"  ... and {len(errors) - 3} more")
        print()


def print_by_tier(errors_text: str):
    """按 Tier 分层打印"""
    files = group_by_file(errors_text)
    tiers = classify_by_tier(files)

    print("【按 Tier 分层统计】\n")
    for tier_name, tier_data in tiers.items():
        print(f"{tier_name}")
        print(f"  错误数: {tier_data['error_count']}")
        print(f"  文件数: {tier_data['file_count']}")

        # 显示前 5 个问题文件
        if tier_data["files"]:
            print("  Top 5 问题文件:")
            sorted_files = sorted(
                tier_data["files"].items(), key=lambda x: len(x[1]), reverse=True
            )[:5]
            for f, errs in sorted_files:
                print(f"    • {f}: {len(errs)} errors")
        print()


def print_trend():
    """打印错误趋势（如果 Git 历史可用）"""
    print("【错误趋势分析】")
    print("  功能开发中...")
    print("  未来将显示：")
    print("    - 过去 10 次提交的错误变化")
    print("    - 每周错误减少趋势")
    print("    - 各 Tier 的改进幅度")


def main():
    parser = argparse.ArgumentParser(description="MyPy 类型检查工具")
    parser.add_argument(
        "--quick-wins",
        action="store_true",
        help="显示快速胜利文件（≤5个错误）",
    )
    parser.add_argument("--by-tier", action="store_true", help="按 Tier 分层显示")
    parser.add_argument("--trend", action="store_true", help="显示错误趋势")
    parser.add_argument(
        "--max-errors", type=int, default=5, help="快速胜利的最大错误数（默认: 5）"
    )
    parser.add_argument(
        "--source-dir", default="src", help="源代码目录（默认: src）"
    )

    args = parser.parse_args()

    print("正在运行 mypy 检查...")
    errors = run_mypy(args.source_dir)

    if args.quick_wins:
        print_quick_wins(errors, args.max_errors)
    elif args.by_tier:
        print_by_tier(errors)
    elif args.trend:
        print_trend()
    else:
        print_report(errors)


if __name__ == "__main__":
    main()
