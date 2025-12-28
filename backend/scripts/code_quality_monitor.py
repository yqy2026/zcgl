#!/usr/bin/env python3
"""
代码质量监控脚本
用于每日代码质量检查、问题统计和趋势分析
"""

import argparse
import csv
import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/code_quality_monitor.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class QualityIssue:
    """代码质量问题"""

    file: str
    line: int
    column: int
    error_code: str
    message: str
    severity: str  # error, warning, info
    tool: str  # ruff, mypy, bandit, etc.


@dataclass
class QualityMetrics:
    """代码质量指标"""

    total_issues: int
    error_count: int
    warning_count: int
    info_count: int
    files_with_issues: int
    total_files: int
    complexity_score: float
    duplication_percentage: float
    security_issues: int
    type_errors: int


class CodeQualityMonitor:
    """代码质量监控器"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.src_dir = self.project_root / "src"
        self.reports_dir = self.project_root / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.history_file = self.reports_dir / "quality_history.json"

    def run_ruff_check(self) -> list[QualityIssue]:
        """运行Ruff代码检查"""
        logger.info("运行Ruff代码检查...")
        try:
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ruff",
                    "check",
                    "--format",
                    "json",
                    str(self.src_dir),
                ],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
            )

            if result.returncode not in [0, 1]:  # 0: 无问题, 1: 发现问题
                logger.error(f"Ruff检查失败: {result.stderr}")
                return []

            issues = []
            if result.stdout.strip():
                ruff_results = json.loads(result.stdout)
                for item in ruff_results:
                    issue = QualityIssue(
                        file=item.get("filename", ""),
                        line=item.get("location", {}).get("row", 0),
                        column=item.get("location", {}).get("column", 0),
                        error_code=item.get("code", ""),
                        message=item.get("message", ""),
                        severity="error" if item.get("type") == "error" else "warning",
                        tool="ruff",
                    )
                    issues.append(issue)

            logger.info(f"Ruff检查发现 {len(issues)} 个问题")
            return issues

        except Exception as e:
            logger.error(f"Ruff检查异常: {e}")
            return []

    def run_mypy_check(self) -> list[QualityIssue]:
        """运行MyPy类型检查"""
        logger.info("运行MyPy类型检查...")
        try:
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "mypy",
                    "--config-file",
                    "pyproject.toml",
                    "--json",
                    str(self.src_dir),
                ],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
            )

            issues = []
            if result.stdout.strip():
                mypy_results = json.loads(result.stdout)
                for item in mypy_results:
                    issue = QualityIssue(
                        file=item.get("file", ""),
                        line=item.get("line", 0),
                        column=item.get("column", 0),
                        error_code=item.get("code", ""),
                        message=item.get("message", ""),
                        severity="error",
                        tool="mypy",
                    )
                    issues.append(issue)

            logger.info(f"MyPy检查发现 {len(issues)} 个问题")
            return issues

        except Exception as e:
            logger.error(f"MyPy检查异常: {e}")
            return []

    def run_bandit_check(self) -> list[QualityIssue]:
        """运行Bandit安全扫描"""
        logger.info("运行Bandit安全扫描...")
        try:
            report_file = self.reports_dir / "bandit_report.json"
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "bandit",
                    "-r",
                    str(self.src_dir),
                    "-f",
                    "json",
                    "-o",
                    str(report_file),
                ],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
            )

            issues = []
            if report_file.exists():
                with open(report_file, encoding="utf-8") as f:
                    bandit_results = json.load(f)

                for item in bandit_results.get("results", []):
                    issue = QualityIssue(
                        file=item.get("filename", ""),
                        line=item.get("line_number", 0),
                        column=0,
                        error_code=item.get("test_id", ""),
                        message=item.get("issue_text", ""),
                        severity=item.get("issue_severity", "low").lower(),
                        tool="bandit",
                    )
                    issues.append(issue)

            logger.info(f"Bandit发现 {len(issues)} 个安全问题")
            return issues

        except Exception as e:
            logger.error(f"Bandit扫描异常: {e}")
            return []

    def run_complexity_analysis(self) -> float:
        """运行代码复杂度分析"""
        logger.info("运行代码复杂度分析...")
        try:
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "radon",
                    "cc",
                    "--average",
                    "--min",
                    "C",
                    str(self.src_dir),
                ],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
            )

            if result.returncode == 0 and result.stdout.strip():
                # 解析平均复杂度
                lines = result.stdout.strip().split("\n")
                for line in reversed(lines):
                    if "Average complexity:" in line:
                        complexity = float(
                            line.split("Average complexity:")[1].strip().split()[0]
                        )
                        logger.info(f"平均代码复杂度: {complexity}")
                        return complexity

            return 0.0

        except Exception as e:
            logger.error(f"复杂度分析异常: {e}")
            return 0.0

    def run_duplication_analysis(self) -> float:
        """运行代码重复度分析"""
        logger.info("运行代码重复度分析...")
        try:
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "jscpd",
                    str(self.src_dir),
                    "--min-lines",
                    "5",
                    "--min-tokens",
                    "50",
                    "--reporters",
                    "json",
                ],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
            )

            report_file = self.project_root / "jscpd-report.json"
            if report_file.exists():
                with open(report_file, encoding="utf-8") as f:
                    jscpd_results = json.load(f)

                duplication_percentage = jscpd_results.get("statistics", {}).get(
                    "percentage", 0.0
                )
                logger.info(f"代码重复度: {duplication_percentage}%")
                report_file.unlink()  # 清理临时文件
                return duplication_percentage

            return 0.0

        except Exception as e:
            logger.error(f"重复度分析异常: {e}")
            return 0.0

    def get_total_files(self) -> int:
        """获取Python文件总数"""
        return len(list(self.src_dir.rglob("*.py")))

    def analyze_all(self) -> tuple[list[QualityIssue], QualityMetrics]:
        """综合代码质量分析"""
        logger.info("开始综合代码质量分析...")

        all_issues = []

        # 运行各项检查
        all_issues.extend(self.run_ruff_check())
        all_issues.extend(self.run_mypy_check())
        all_issues.extend(self.run_bandit_check())

        # 计算指标
        total_files = self.get_total_files()
        files_with_issues = len(set(issue.file for issue in all_issues))
        error_count = sum(1 for issue in all_issues if issue.severity == "error")
        warning_count = sum(1 for issue in all_issues if issue.severity == "warning")
        info_count = sum(1 for issue in all_issues if issue.severity == "info")

        complexity_score = self.run_complexity_analysis()
        duplication_percentage = self.run_duplication_analysis()

        security_issues = sum(1 for issue in all_issues if issue.tool == "bandit")
        type_errors = sum(1 for issue in all_issues if issue.tool == "mypy")

        metrics = QualityMetrics(
            total_issues=len(all_issues),
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            files_with_issues=files_with_issues,
            total_files=total_files,
            complexity_score=complexity_score,
            duplication_percentage=duplication_percentage,
            security_issues=security_issues,
            type_errors=type_errors,
        )

        logger.info(
            f"分析完成: {len(all_issues)} 个问题, 复杂度: {complexity_score:.2f}, 重复度: {duplication_percentage:.2f}%"
        )
        return all_issues, metrics

    def save_report(self, issues: list[QualityIssue], metrics: QualityMetrics) -> Path:
        """保存质量报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"quality_report_{timestamp}.json"

        report_data = {
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "total_issues": metrics.total_issues,
                "error_count": metrics.error_count,
                "warning_count": metrics.warning_count,
                "info_count": metrics.info_count,
                "files_with_issues": metrics.files_with_issues,
                "total_files": metrics.total_files,
                "complexity_score": metrics.complexity_score,
                "duplication_percentage": metrics.duplication_percentage,
                "security_issues": metrics.security_issues,
                "type_errors": metrics.type_errors,
            },
            "issues": [
                {
                    "file": issue.file,
                    "line": issue.line,
                    "column": issue.column,
                    "error_code": issue.error_code,
                    "message": issue.message,
                    "severity": issue.severity,
                    "tool": issue.tool,
                }
                for issue in issues
            ],
        }

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        logger.info(f"质量报告已保存: {report_file}")
        return report_file

    def update_history(self, metrics: QualityMetrics):
        """更新历史记录"""
        history = []
        if self.history_file.exists():
            with open(self.history_file, encoding="utf-8") as f:
                history = json.load(f)

        history.append(
            {
                "date": datetime.now().isoformat(),
                "metrics": {
                    "total_issues": metrics.total_issues,
                    "error_count": metrics.error_count,
                    "warning_count": metrics.warning_count,
                    "complexity_score": metrics.complexity_score,
                    "duplication_percentage": metrics.duplication_percentage,
                },
            }
        )

        # 只保留最近90天的记录
        cutoff_date = datetime.now() - timedelta(days=90)
        history = [
            h for h in history if datetime.fromisoformat(h["date"]) > cutoff_date
        ]

        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        logger.info("历史记录已更新")

    def generate_trend_chart(self) -> Path | None:
        """生成质量趋势图"""
        if not self.history_file.exists():
            return None

        with open(self.history_file, encoding="utf-8") as f:
            history = json.load(f)

        if len(history) < 2:
            return None

        dates = [datetime.fromisoformat(h["date"]) for h in history]
        total_issues = [h["metrics"]["total_issues"] for h in history]
        complexity_scores = [h["metrics"]["complexity_score"] for h in history]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

        # 问题数量趋势
        ax1.plot(dates, total_issues, "b-", marker="o", label="总问题数")
        ax1.set_ylabel("问题数量")
        ax1.set_title("代码质量问题趋势")
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # 复杂度趋势
        ax2.plot(dates, complexity_scores, "r-", marker="s", label="平均复杂度")
        ax2.set_ylabel("复杂度分数")
        ax2.set_xlabel("日期")
        ax2.set_title("代码复杂度趋势")
        ax2.grid(True, alpha=0.3)
        ax2.legend()

        # 格式化日期
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()
        chart_file = self.reports_dir / "quality_trends.png"
        plt.savefig(chart_file, dpi=300, bbox_inches="tight")
        plt.close()

        logger.info(f"趋势图已生成: {chart_file}")
        return chart_file

    def generate_csv_report(self, issues: list[QualityIssue]) -> Path:
        """生成CSV格式问题报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = self.reports_dir / f"issues_{timestamp}.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["文件", "行号", "列号", "错误代码", "严重程度", "工具", "问题描述"]
            )

            for issue in sorted(issues, key=lambda x: (x.file, x.line)):
                writer.writerow(
                    [
                        issue.file,
                        issue.line,
                        issue.column,
                        issue.error_code,
                        issue.severity,
                        issue.tool,
                        issue.message,
                    ]
                )

        logger.info(f"CSV报告已生成: {csv_file}")
        return csv_file

    def print_summary(self, issues: list[QualityIssue], metrics: QualityMetrics):
        """打印质量摘要"""
        print("\n" + "=" * 60)
        print("代码质量监控报告")
        print("=" * 60)
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"项目路径: {self.project_root}")
        print()
        print("质量指标:")
        print(f"  总问题数: {metrics.total_issues}")
        print(
            f"  错误数: {metrics.error_count} | 警告数: {metrics.warning_count} | 信息数: {metrics.info_count}"
        )
        print(f"  涉及文件: {metrics.files_with_issues}/{metrics.total_files}")
        print(f"  平均复杂度: {metrics.complexity_score:.2f}")
        print(f"  代码重复度: {metrics.duplication_percentage:.2f}%")
        print(f"  安全问题: {metrics.security_issues}")
        print(f"  类型错误: {metrics.type_errors}")

        if issues:
            print("\n问题分布:")
            tool_counts = {}
            severity_counts = {}

            for issue in issues:
                tool_counts[issue.tool] = tool_counts.get(issue.tool, 0) + 1
                severity_counts[issue.severity] = (
                    severity_counts.get(issue.severity, 0) + 1
                )

            print("按工具分类:")
            for tool, count in sorted(tool_counts.items()):
                print(f"  {tool}: {count}")

            print("按严重程度分类:")
            for severity, count in sorted(severity_counts.items()):
                print(f"  {severity}: {count}")

            print("\n前10个问题:")
            for i, issue in enumerate(
                sorted(issues, key=lambda x: (x.severity, x.file, x.line))[:10]
            ):
                print(
                    f"  {i+1}. {issue.file}:{issue.line} - {issue.error_code}: {issue.message}"
                )

        print("\n" + "=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="代码质量监控工具")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--format", choices=["json", "csv", "chart"], help="输出格式")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--history", action="store_true", help="生成历史趋势图")

    args = parser.parse_args()

    monitor = CodeQualityMonitor(args.project_root)

    # 运行分析
    issues, metrics = monitor.analyze_all()

    # 保存报告
    report_file = monitor.save_report(issues, metrics)
    monitor.update_history(metrics)

    # 生成其他格式报告
    if args.format == "csv" or args.history:
        csv_file = monitor.generate_csv_report(issues)

    if args.history:
        chart_file = monitor.generate_trend_chart()

    # 打印摘要
    monitor.print_summary(issues, metrics)

    print(f"\n详细报告已保存: {report_file}")

    # 如果问题数量超过阈值，返回非零退出码
    if metrics.error_count > 10 or metrics.security_issues > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
