#!/usr/bin/env python3
"""
Low Coverage Module Finder

识别低覆盖率模块，生成改进任务列表。

Usage:
    python find_low_coverage_modules.py --backend-coverage coverage.xml --threshold 80
    python find_low_coverage_modules.py --frontend-coverage coverage/coverage-summary.json --threshold 70
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple


def parse_backend_coverage(coverage_xml: Path) -> Dict[str, float]:
    """
    解析后端覆盖率报告 (coverage.xml)

    Returns:
        {模块路径: 覆盖率百分比}
    """
    if not coverage_xml.exists():
        print(f"❌ 覆盖率文件不存在: {coverage_xml}")
        sys.exit(1)

    tree = ET.parse(coverage_xml)
    root = tree.getroot()

    modules = {}

    # 遍历所有 classes
    for package in root.findall(".//package"):
        package_name = package.attrib.get("name", "")
        for cls in package.findall(".//class"):
            class_name = cls.attrib.get("name", "")
            line_rate = float(cls.attrib.get("line-rate", 0))
            coverage_pct = line_rate * 100

            # 构建模块路径
            module_path = f"{package_name}.{class_name}" if package_name else class_name

            # 只统计 src/ 下的模块
            if "src/" in module_path or "src\\" in module_path:
                modules[module_path] = coverage_pct

    return modules


def parse_frontend_coverage(coverage_json: Path) -> Dict[str, float]:
    """
    解析前端覆盖率报告 (coverage-summary.json)

    Returns:
        {文件路径: 覆盖率百分比}
    """
    if not coverage_json.exists():
        print(f"❌ 覆盖率文件不存在: {coverage_json}")
        sys.exit(1)

    with open(coverage_json) as f:
        data = json.load(f)

    files = {}

    for file_path, file_data in data.items():
        if isinstance(file_data, dict) and "lines" in file_data:
            coverage_pct = file_data["lines"].get("pct", 0)
            # 只统计 src/ 下的文件
            if "src/" in file_path or "src\\" in file_path:
                files[file_path] = coverage_pct

    return files


def generate_priority_modules(
    modules: Dict[str, float],
    target: float,
    top_n: int = 10
) -> List[Tuple[str, float, float]]:
    """
    生成优先改进的模块列表

    Returns:
        [(模块名, 当前覆盖率, 差距), ...] 按差距排序
    """
    # 计算差距并排序
    prioritized = [
        (module, coverage, target - coverage)
        for module, coverage in modules.items()
        if coverage < target
    ]

    # 按差距降序排序（差距最大的优先）
    prioritized.sort(key=lambda x: x[2], reverse=True)

    return prioritized[:top_n]


def categorize_by_coverage(
    modules: Dict[str, float],
    target: float
) -> Dict[str, List[str]]:
    """
    按覆盖率范围分类模块

    Returns:
        {
            "critical": [...],  # < target - 20
            "high": [...],      # < target - 10
            "medium": [...],    # < target - 5
            "close": [...],     # < target
            "achieved": [...],  # >= target
        }
    """
    categories = {
        "critical": [],  # 严重低于目标
        "high": [],      # 显著低于目标
        "medium": [],    # 低于目标
        "close": [],     # 接近目标
        "achieved": [],  # 已达标
    }

    for module, coverage in modules.items():
        gap = target - coverage

        if coverage >= target:
            categories["achieved"].append(module)
        elif gap >= 20:
            categories["critical"].append(module)
        elif gap >= 10:
            categories["high"].append(module)
        elif gap >= 5:
            categories["medium"].append(module)
        else:
            categories["close"].append(module)

    return categories


def calculate_average_coverage(modules: Dict[str, float]) -> float:
    """计算平均覆盖率"""
    if not modules:
        return 0.0
    return sum(modules.values()) / len(modules)


def generate_markdown_report(
    backend_modules: Dict[str, float] = None,
    frontend_modules: Dict[str, float] = None,
    backend_target: float = 85.0,
    frontend_target: float = 75.0,
) -> str:
    """生成 Markdown 格式的报告"""
    report = []
    report.append("# 覆盖率分析报告\n")
    report.append(f"**生成时间**: {Path(__file__).stat().st_mtime}\n")
    report.append("---\n")

    # 后端报告
    if backend_modules:
        report.append("## 📊 后端覆盖率分析\n")
        avg_backend = calculate_average_coverage(backend_modules)
        report.append(f"**平均覆盖率**: {avg_backend:.1f}%\n")
        report.append(f"**目标覆盖率**: {backend_target}%\n")
        report.append(f"**差距**: {backend_target - avg_backend:.1f}%\n")

        backend_categories = categorize_by_coverage(backend_modules, backend_target)
        report.append(f"\n### 模块分类\n")
        report.append(f"- ✅ **已达标** ({len(backend_categories['achieved'])} 个): {backend_target}%+\n")
        report.append(f"- 🟡 **接近目标** ({len(backend_categories['close'])} 个): {backend_target-5:.0f}%-{backend_target}%\n")
        report.append(f"- 🟠 **需改进** ({len(backend_categories['medium'])} 个): {backend_target-10:.0f}%-{backend_target-5:.0f}%\n")
        report.append(f"- 🔴 **优先处理** ({len(backend_categories['high'])} 个): {backend_target-20:.0f}%-{backend_target-10:.0f}%\n")
        report.append(f"- 🚨 **严重不足** ({len(backend_categories['critical'])} 个): <{backend_target-20:.0f}%\n")

        priority = generate_priority_modules(backend_modules, backend_target, top_n=10)
        if priority:
            report.append(f"\n### 🎯 优先改进的 Top 10 模块\n")
            report.append("| 模块 | 当前覆盖率 | 差距 | 优先级 |\n")
            report.append("|------|-----------|------|--------|\n")
            for module, coverage, gap in priority:
                emoji = "🚨" if gap >= 20 else "🔴" if gap >= 10 else "🟠" if gap >= 5 else "🟡"
                report.append(f"| {emoji} `{module}` | {coverage:.1f}% | -{gap:.1f}% | {'高' if gap >= 10 else '中' if gap >= 5 else '低'} |\n")

    # 前端报告
    if frontend_modules:
        report.append("\n## 📊 前端覆盖率分析\n")
        avg_frontend = calculate_average_coverage(frontend_modules)
        report.append(f"**平均覆盖率**: {avg_frontend:.1f}%\n")
        report.append(f"**目标覆盖率**: {frontend_target}%\n")
        report.append(f"**差距**: {frontend_target - avg_frontend:.1f}%\n")

        frontend_categories = categorize_by_coverage(frontend_modules, frontend_target)
        report.append(f"\n### 模块分类\n")
        report.append(f"- ✅ **已达标** ({len(frontend_categories['achieved'])} 个): {frontend_target}%+\n")
        report.append(f"- 🟡 **接近目标** ({len(frontend_categories['close'])} 个): {frontend_target-5:.0f}%-{frontend_target}%\n")
        report.append(f"- 🟠 **需改进** ({len(frontend_categories['medium'])} 个): {frontend_target-10:.0f}%-{frontend_target-5:.0f}%\n")
        report.append(f"- 🔴 **优先处理** ({len(frontend_categories['high'])} 个): {frontend_target-20:.0f}%-{frontend_target-10:.0f}%\n")
        report.append(f"- 🚨 **严重不足** ({len(frontend_categories['critical'])} 个): <{frontend_target-20:.0f}%\n")

        priority = generate_priority_modules(frontend_modules, frontend_target, top_n=10)
        if priority:
            report.append(f"\n### 🎯 优先改进的 Top 10 文件\n")
            report.append("| 文件 | 当前覆盖率 | 差距 | 优先级 |\n")
            report.append("|------|-----------|------|--------|\n")
            for file_path, coverage, gap in priority:
                emoji = "🚨" if gap >= 20 else "🔴" if gap >= 10 else "🟠" if gap >= 5 else "🟡"
                # 简化文件名显示
                short_name = file_path.split("/")[-1] if "/" in file_path else file_path
                report.append(f"| {emoji} `{short_name}` | {coverage:.1f}% | -{gap:.1f}% | {'高' if gap >= 10 else '中' if gap >= 5 else '低'} |\n")

    # 建议任务
    report.append("\n---\n")
    report.append("## 📋 建议的改进任务\n")
    report.append("\n### 第1周目标: 基线评估 + 快速改进\n")

    if backend_modules:
        priority = generate_priority_modules(backend_modules, backend_target, top_n=5)
        report.append(f"\n#### 后端 (目标: 平均覆盖率提升 2%)\n")
        for i, (module, coverage, gap) in enumerate(priority, 1):
            report.append(f"{i}. **{module}** ({coverage:.1f}% → {coverage+2:.1f}%)\n")

    if frontend_modules:
        priority = generate_priority_modules(frontend_modules, frontend_target, top_n=5)
        report.append(f"\n#### 前端 (目标: 平均覆盖率提升 2%)\n")
        for i, (file_path, coverage, gap) in enumerate(priority, 1):
            short_name = file_path.split("/")[-1] if "/" in file_path else file_path
            report.append(f"{i}. **{short_name}** ({coverage:.1f}% → {coverage+2:.1f}%)\n")

    return "".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="识别低覆盖率模块，生成改进任务列表"
    )
    parser.add_argument(
        "--backend-coverage",
        type=Path,
        help="后端覆盖率文件 (coverage.xml)"
    )
    parser.add_argument(
        "--frontend-coverage",
        type=Path,
        help="前端覆盖率文件 (coverage-summary.json)"
    )
    parser.add_argument(
        "--backend-target",
        type=float,
        default=85.0,
        help="后端覆盖率目标 (默认: 85%%)"
    )
    parser.add_argument(
        "--frontend-target",
        type=float,
        default=75.0,
        help="前端覆盖率目标 (默认: 75%%)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        help="显示低于此阈值的模块"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("coverage_analysis_report.md"),
        help="输出报告文件 (默认: coverage_analysis_report.md)"
    )

    args = parser.parse_args()

    if not args.backend_coverage and not args.frontend_coverage:
        print("❌ 请提供至少一个覆盖率文件")
        print("用法示例:")
        print("  python find_low_coverage_modules.py --backend-coverage backend/coverage.xml")
        print("  python find_low_coverage_modules.py --frontend-coverage frontend/coverage/coverage-summary.json")
        print("  python find_low_coverage_modules.py --backend-coverage backend/coverage.xml --frontend-coverage frontend/coverage/coverage-summary.json")
        sys.exit(1)

    backend_modules = None
    frontend_modules = None

    if args.backend_coverage:
        print(f"📊 解析后端覆盖率: {args.backend_coverage}")
        backend_modules = parse_backend_coverage(args.backend_coverage)
        print(f"   找到 {len(backend_modules)} 个模块")

    if args.frontend_coverage:
        print(f"📊 解析前端覆盖率: {args.frontend_coverage}")
        frontend_modules = parse_frontend_coverage(args.frontend_coverage)
        print(f"   找到 {len(frontend_modules)} 个文件")

    # 生成报告
    report = generate_markdown_report(
        backend_modules,
        frontend_modules,
        args.backend_target,
        args.frontend_target
    )

    # 输出到文件
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n✅ 报告已生成: {args.output}")

    # 输出简短摘要
    if backend_modules:
        avg = calculate_average_coverage(backend_modules)
        below_target = sum(1 for c in backend_modules.values() if c < args.backend_target)
        print(f"\n📊 后端: 平均 {avg:.1f}%, {below_target}/{len(backend_modules)} 个模块低于目标 ({args.backend_target}%)")

    if frontend_modules:
        avg = calculate_average_coverage(frontend_modules)
        below_target = sum(1 for c in frontend_modules.values() if c < args.frontend_target)
        print(f"📊 前端: 平均 {avg:.1f}%, {below_target}/{len(frontend_modules)} 个文件低于目标 ({args.frontend_target}%)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
