#!/usr/bin/env python3
"""
代码质量评分计算脚本
基于各种质量报告计算综合质量分数
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import argparse


class QualityScoreCalculator:
    """代码质量评分计算器"""

    def __init__(self, reports_dir: Path = Path("reports")):
        self.reports_dir = reports_dir
        self.quality_score = {
            "overall_score": 0,
            "backend_score": 0,
            "frontend_score": 0,
            "backend": {},
            "frontend": {},
            "recommendations": [],
            "generated_at": ""
        }

    def calculate_backend_score(self) -> Dict[str, Any]:
        """计算后端质量分数"""
        backend_reports = self.reports_dir / "backend"
        score = 100
        issues = []
        details = {}

        # 读取安全扫描报告
        bandit_report = backend_reports / "bandit-report.json"
        if bandit_report.exists():
            try:
                with open(bandit_report, 'r') as f:
                    bandit_data = json.load(f)
                    high_issues = len([r for r in bandit_data.get('results', [])
                                     if r.get('issue_severity') == 'HIGH'])
                    medium_issues = len([r for r in bandit_data.get('results', [])
                                       if r.get('issue_severity') == 'MEDIUM'])

                    details['security_issues'] = high_issues + medium_issues
                    details['high_security_issues'] = high_issues
                    details['medium_security_issues'] = medium_issues

                    # 扣分：高危问题-10分/个，中危问题-5分/个
                    score -= high_issues * 10
                    score -= medium_issues * 5

                    if high_issues > 0:
                        issues.append(f"修复{high_issues}个高危安全问题")
                    if medium_issues > 0:
                        issues.append(f"修复{medium_issues}个中危安全问题")
            except Exception as e:
                print(f"Warning: Could not read bandit report: {e}")

        # 读取复杂度报告
        radon_report = backend_reports / "radon-report.json"
        if radon_report.exists():
            try:
                with open(radon_report, 'r') as f:
                    radon_data = json.load(f)

                    # 计算平均圈复杂度
                    total_complexity = 0
                    function_count = 0
                    complex_functions = 0

                    for module_name, module_data in radon_data.items():
                        for function_data in module_data:
                            complexity = function_data.get('complexity', 0)
                            total_complexity += complexity
                            function_count += 1
                            if complexity > 10:
                                complex_functions += 1

                    avg_complexity = total_complexity / function_count if function_count > 0 else 0

                    details['avg_complexity'] = round(avg_complexity, 2)
                    details['complex_functions'] = complex_functions
                    details['total_functions'] = function_count

                    # 扣分：复杂函数-3分/个，高平均复杂度-10分
                    score -= complex_functions * 3
                    if avg_complexity > 7:
                        score -= 10
                        issues.append("降低平均圈复杂度")

                    if complex_functions > 0:
                        issues.append(f"重构{complex_functions}个复杂函数")
            except Exception as e:
                print(f"Warning: Could not read radon report: {e}")

        # 读取可维护性指数
        maintainability_report = backend_reports / "maintainability-report.json"
        if maintainability_report.exists():
            try:
                with open(maintainability_report, 'r') as f:
                    maintainability_data = json.load(f)

                    # 计算平均可维护性指数
                    total_mi = 0
                    module_count = 0
                    low_mi_modules = 0

                    for module_name, mi_score in maintainability_data.items():
                        if isinstance(mi_score, (int, float)):
                            total_mi += mi_score
                            module_count += 1
                            if mi_score < 60:
                                low_mi_modules += 1

                    avg_mi = total_mi / module_count if module_count > 0 else 0

                    details['avg_maintainability_index'] = round(avg_mi, 2)
                    details['low_mi_modules'] = low_mi_modules

                    # 扣分：低可维护性模块-5分/个
                    score -= low_mi_modules * 5

                    if low_mi_modules > 0:
                        issues.append(f"改进{low_mi_modules}个模块的可维护性")
            except Exception as e:
                print(f"Warning: Could not read maintainability report: {e}")

        # 读取测试覆盖率报告
        coverage_xml = backend_reports / "coverage.xml"
        if coverage_xml.exists():
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(coverage_xml)
                root = tree.getroot()

                coverage_rate = 0
                for coverage in root.findall('.//coverage'):
                    line_rate = coverage.get('line-rate', '0')
                    if line_rate:
                        coverage_rate = max(coverage_rate, float(line_rate))

                coverage_percent = round(coverage_rate * 100, 2)
                details['coverage'] = coverage_percent

                # 扣分：测试覆盖率低于80%
                if coverage_percent < 80:
                    score -= (80 - coverage_percent) // 2
                    issues.append(f"提高测试覆盖率至80%以上（当前{coverage_percent}%）")
            except Exception as e:
                print(f"Warning: Could not read coverage report: {e}")

        # 确保分数在0-100范围内
        score = max(0, min(100, score))

        self.quality_score["backend"] = {
            "score": score,
            "issues": issues,
            **details
        }

        return {"score": score, "issues": issues, **details}

    def calculate_frontend_score(self) -> Dict[str, Any]:
        """计算前端质量分数"""
        frontend_reports = self.reports_dir / "frontend"
        score = 100
        issues = []
        details = {}

        # 读取ESLint报告
        eslint_report = frontend_reports / "eslint-report.json"
        if eslint_report.exists():
            try:
                with open(eslint_report, 'r') as f:
                    eslint_data = json.load(f)

                    error_count = len(eslint_data)
                    details['lint_issues'] = error_count

                    # 扣分：ESLint错误-2分/个
                    score -= error_count * 2

                    if error_count > 0:
                        issues.append(f"修复{error_count}个ESLint问题")
            except Exception as e:
                print(f"Warning: Could not read ESLint report: {e}")

        # 读取测试覆盖率报告
        coverage_summary = frontend_reports / "coverage" / "coverage-summary.json"
        if coverage_summary.exists():
            try:
                with open(coverage_summary, 'r') as f:
                    coverage_data = json.load(f)

                    lines_coverage = coverage_data.get('total', {}).get('lines', {}).get('pct', 0)
                    functions_coverage = coverage_data.get('total', {}).get('functions', {}).get('pct', 0)
                    branches_coverage = coverage_data.get('total', {}).get('branches', {}).get('pct', 0)
                    statements_coverage = coverage_data.get('total', {}).get('statements', {}).get('pct', 0)

                    # 计算平均覆盖率
                    avg_coverage = (lines_coverage + functions_coverage + branches_coverage + statements_coverage) / 4

                    details['coverage'] = round(avg_coverage, 2)
                    details['lines_coverage'] = lines_coverage
                    details['functions_coverage'] = functions_coverage

                    # 扣分：测试覆盖率低于70%
                    if avg_coverage < 70:
                        score -= (70 - avg_coverage) // 2
                        issues.append(f"提高测试覆盖率至70%以上（当前{round(avg_coverage, 2)}%）")
            except Exception as e:
                print(f"Warning: Could not read coverage report: {e}")

        # 检查bundle大小
        dist_dir = frontend_reports / "dist"
        if dist_dir.exists():
            try:
                total_size = 0
                js_files = 0

                for file_path in dist_dir.rglob("*.js"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
                        js_files += 1

                bundle_size_kb = total_size // 1024
                details['bundle_size'] = f"{bundle_size_kb}KB"
                details['js_files'] = js_files

                # 扣分：bundle大小超过1MB
                if bundle_size_kb > 1024:
                    score -= (bundle_size_kb - 1024) // 100
                    issues.append(f"优化bundle大小（当前{bundle_size_kb}KB）")
            except Exception as e:
                print(f"Warning: Could not analyze bundle size: {e}")

        # 确保分数在0-100范围内
        score = max(0, min(100, score))

        self.quality_score["frontend"] = {
            "score": score,
            "issues": issues,
            **details
        }

        return {"score": score, "issues": issues, **details}

    def calculate_overall_score(self):
        """计算总体质量分数"""
        backend_result = self.calculate_backend_score()
        frontend_result = self.calculate_frontend_score()

        backend_score = backend_result["score"]
        frontend_score = frontend_result["score"]

        # 加权平均：后端60%，前端40%
        overall_score = round(backend_score * 0.6 + frontend_score * 0.4)

        self.quality_score.update({
            "overall_score": overall_score,
            "backend_score": backend_score,
            "frontend_score": frontend_score,
            "recommendations": backend_result["issues"] + frontend_result["issues"],
            "generated_at": self._get_timestamp()
        })

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"

    def save_report(self, output_path: Path = None):
        """保存质量报告"""
        if output_path is None:
            output_path = self.reports_dir / "quality-score.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.quality_score, f, indent=2, ensure_ascii=False)

        print(f"📊 Quality Score Report Generated")
        print(f"📍 Location: {output_path}")
        print(f"🎯 Overall Score: {self.quality_score['overall_score']}/100")
        print(f"🐍 Backend Score: {self.quality_score['backend_score']}/100")
        print(f"⚛️ Frontend Score: {self.quality_score['frontend_score']}/100")

        if self.quality_score["recommendations"]:
            print(f"\n📝 Recommendations:")
            for rec in self.quality_score["recommendations"]:
                print(f"   • {rec}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Calculate code quality score")
    parser.add_argument("--reports-dir", default="reports", help="Reports directory path")
    parser.add_argument("--output", help="Output file path")

    args = parser.parse_args()

    print("🔍 Calculating Code Quality Score...")

    try:
        calculator = QualityScoreCalculator(Path(args.reports_dir))
        calculator.calculate_overall_score()
        calculator.save_report(Path(args.output) if args.output else None)

        # 设置退出码基于分数
        overall_score = calculator.quality_score["overall_score"]
        if overall_score < 70:
            print(f"\n❌ Quality score too low: {overall_score}/100")
            sys.exit(1)
        elif overall_score < 85:
            print(f"\n⚠️ Quality score needs improvement: {overall_score}/100")
            sys.exit(2)
        else:
            print(f"\n✅ Quality score acceptable: {overall_score}/100")
            sys.exit(0)

    except Exception as e:
        print(f"❌ Error calculating quality score: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()