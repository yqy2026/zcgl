#!/usr/bin/env python3
"""
测试覆盖率计算脚本
计算后端和前端的测试覆盖率，并生成汇总报告
"""

import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any


class CoverageCalculator:
    """覆盖率计算器"""

    def __init__(self):
        self.results_dir = Path("results")
        self.output_file = Path("coverage-summary.json")
        self.backend_threshold = 80.0
        self.frontend_threshold = 70.0
        self.total_threshold = 75.0

    def parse_backend_coverage(self) -> Dict[str, Any]:
        """解析后端覆盖率报告"""
        coverage_file = self.results_dir / "backend" / "coverage.xml"

        if not coverage_file.exists():
            print(f"⚠️  后端覆盖率文件不存在: {coverage_file}")
            return {
                "backend_coverage": 0.0,
                "backend_lines_covered": 0,
                "backend_lines_total": 0,
                "backend_modules": []
            }

        print(f"📊 解析后端覆盖率: {coverage_file}")

        try:
            tree = ET.parse(coverage_file)
            root = tree.getroot()

            # 计算总体覆盖率
            total_lines = 0
            covered_lines = 0
            modules = []

            for package in root.findall('.//package'):
                package_name = package.get('name', '').replace('src/', '')
                lines_valid = int(package.get('line-rate', '0') * 100)

                # 获取更详细的模块信息
                module_info = self._parse_module_coverage(package)
                if module_info:
                    modules.append(module_info)

                # 计算行数
                lines_element = package.find('lines')
                if lines_element is not None:
                    for line in lines_element.findall('line'):
                        total_lines += 1
                        if line.get('hits') != '0':
                            covered_lines += 1

            backend_coverage = (covered_lines / total_lines * 100) if total_lines > 0 else 0.0

            print(f"✅ 后端覆盖率: {backend_coverage:.1f}% ({covered_lines}/{total_lines})")

            return {
                "backend_coverage": backend_coverage,
                "backend_lines_covered": covered_lines,
                "backend_lines_total": total_lines,
                "backend_modules": modules
            }

        except Exception as e:
            print(f"❌ 解析后端覆盖率失败: {e}")
            return {
                "backend_coverage": 0.0,
                "backend_lines_covered": 0,
                "backend_lines_total": 0,
                "backend_modules": []
            }

    def _parse_module_coverage(self, package_element) -> Optional[Dict[str, Any]]:
        """解析单个模块的覆盖率信息"""
        try:
            package_name = package_element.get('name', '').replace('src/', '')
            line_rate = float(package_element.get('line-rate', 0))
            branch_rate = float(package_element.get('branch-rate', 0))
            complexity = int(package_element.get('complexity', 0))

            # 计算行数
            lines_element = package_element.find('lines')
            lines_covered = 0
            lines_total = 0
            branches_covered = 0
            branches_total = 0
            functions_covered = 0
            functions_total = 0

            if lines_element is not None:
                for line in lines_element.findall('line'):
                    if line.get('branch'):
                        branches_total += 1
                        if line.get('hits') != '0':
                            branches_covered += 1
                    else:
                        functions_total += 1
                        if line.get('hits') != '0':
                            functions_covered += 1

                    lines_total += 1
                    if line.get('hits') != '0':
                        lines_covered += 1

            return {
                "module_name": package_name,
                "coverage_percentage": line_rate * 100,
                "lines_covered": lines_covered,
                "lines_total": lines_total,
                "branches_covered": branches_covered,
                "branches_total": branches_total,
                "functions_covered": functions_covered,
                "functions_total": functions_total,
                "complexity": complexity,
                "last_updated": str(Path.cwd()),
                "file_path": f"src/{package_name}"
            }

        except Exception as e:
            print(f"⚠️  解析模块覆盖率失败: {e}")
            return None

    def parse_frontend_coverage(self) -> Dict[str, Any]:
        """解析前端覆盖率报告"""
        # 尝试多种可能的覆盖率报告格式
        coverage_files = [
            self.results_dir / "frontend" / "coverage" / "coverage-summary.json",
            self.results_dir / "frontend" / "coverage" / "lcov.info",
            self.results_dir / "frontend" / "coverage-summary.json"
        ]

        coverage_data = None
        for coverage_file in coverage_files:
            if coverage_file.exists():
                print(f"📊 解析前端覆盖率: {coverage_file}")
                coverage_data = self._parse_coverage_file(coverage_file)
                if coverage_data:
                    break

        if not coverage_data:
            print(f"⚠️  前端覆盖率文件不存在")
            return {
                "frontend_coverage": 0.0,
                "frontend_lines_covered": 0,
                "frontend_lines_total": 0,
                "frontend_modules": []
            }

        return coverage_data

    def _parse_coverage_file(self, coverage_file: Path) -> Optional[Dict[str, Any]]:
        """解析覆盖率文件"""
        try:
            if coverage_file.suffix == '.json':
                with open(coverage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return self._parse_json_coverage(data, coverage_file)

            elif coverage_file.name == 'lcov.info':
                return self._parse_lcov_coverage(coverage_file)

            return None

        except Exception as e:
            print(f"❌ 解析覆盖率文件失败 {coverage_file}: {e}")
            return None

    def _parse_json_coverage(self, data: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """解析JSON格式的覆盖率数据"""
        if 'total' in data:
            # Jest覆盖率格式
            total = data['total']
            lines = total.get('lines', {})

            frontend_coverage = lines.get('pct', 0.0)
            lines_covered = lines.get('covered', 0)
            lines_total = lines.get('total', 0)

            modules = []
            if 'files' in data:
                for file_path, file_data in data['files'].items():
                    module_name = self._extract_module_name_from_path(file_path)
                    if file_data.get('lines'):
                        lines_data = file_data['lines']
                        modules.append({
                            "module_name": module_name,
                            "coverage_percentage": lines_data.get('pct', 0.0),
                            "lines_covered": lines_data.get('covered', 0),
                            "lines_total": lines_data.get('total', 0),
                            "functions_covered": file_data.get('functions', {}).get('covered', 0),
                            "functions_total": file_data.get('functions', {}).get('total', 0),
                            "branches_covered": file_data.get('branches', {}).get('covered', 0),
                            "branches_total": file_data.get('branches', {}).get('total', 0),
                            "last_updated": str(Path.cwd()),
                            "file_path": file_path
                        })

            print(f"✅ 前端覆盖率 (Jest): {frontend_coverage:.1f}% ({lines_covered}/{lines_total})")

            return {
                "frontend_coverage": frontend_coverage,
                "frontend_lines_covered": lines_covered,
                "frontend_lines_total": lines_total,
                "frontend_modules": modules
            }

        return None

    def _parse_lcov_coverage(self, lcov_file: Path) -> Dict[str, Any]:
        """解析LCOV格式的覆盖率数据"""
        try:
            # 这里可以添加LCOV解析逻辑
            # 由于篇幅限制，这里提供一个简化版本
            print(f"⚠️  LCOV格式解析未实现，返回0%")
            return {
                "frontend_coverage": 0.0,
                "frontend_lines_covered": 0,
                "frontend_lines_total": 0,
                "frontend_modules": []
            }
        except Exception as e:
            print(f"❌ 解析LCOV失败: {e}")
            return None

    def _extract_module_name_from_path(self, file_path: str) -> str:
        """从文件路径提取模块名称"""
        # 移除src/前缀和文件扩展名
        if file_path.startswith('src/'):
            file_path = file_path[4:]

        # 将路径转换为模块名
        parts = file_path.split('/')
        if len(parts) > 1:
            return '/'.join(parts[:-1])  # 返回目录名作为模块名

        # 移除扩展名
        name = parts[0] if parts else file_path
        name = name.replace('.tsx', '').replace('.ts', '').replace('.jsx', '').replace('.js', '')
        return name

    def parse_test_results(self) -> Dict[str, Any]:
        """解析测试结果"""
        backend_results = self._parse_backend_test_results()
        frontend_results = self._parse_frontend_test_results()

        # 汇总测试结果
        total_tests = backend_results['total_tests'] + frontend_results['total_tests']
        passed_tests = backend_results['passed_tests'] + frontend_results['passed_tests']
        failed_tests = backend_results['failed_tests'] + frontend_results['failed_tests']
        skipped_tests = backend_results['skipped_tests'] + frontend_results['skipped_tests']

        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0.0

        print(f"🧪 测试结果汇总:")
        print(f"   总测试数: {total_tests}")
        print(f"   通过: {passed_tests}")
        print(f"   失败: {failed_tests}")
        print(f"   跳过: {skipped_tests}")
        print(f"   通过率: {pass_rate:.1f}%")

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "skipped_tests": skipped_tests,
            "pass_rate": pass_rate,
            "backend_test_results": backend_results,
            "frontend_test_results": frontend_results
        }

    def _parse_backend_test_results(self) -> Dict[str, int]:
        """解析后端测试结果"""
        junit_file = self.results_dir / "backend" / "test-results-backend.xml"

        if not junit_file.exists():
            print(f"⚠️  后端测试结果文件不存在: {junit_file}")
            return {"total_tests": 0, "passed_tests": 0, "failed_tests": 0, "skipped_tests": 0}

        try:
            tree = ET.parse(junit_file)
            root = tree.getroot()

            total_tests = int(root.get('tests', 0))
            failures = int(root.get('failures', 0))
            errors = int(root.get('errors', 0))
            skipped = int(root.get('skipped', 0))

            passed_tests = total_tests - failures - errors - skipped
            failed_tests = failures + errors

            return {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "skipped_tests": skipped
            }

        except Exception as e:
            print(f"❌ 解析后端测试结果失败: {e}")
            return {"total_tests": 0, "passed_tests": 0, "failed_tests": 0, "skipped_tests": 0}

    def _parse_frontend_test_results(self) -> Dict[str, int]:
        """解析前端测试结果"""
        # 尝试查找前端测试结果文件
        test_files = [
            self.results_dir / "frontend" / "test-results.json",
            self.results_dir / "frontend" / "coverage" / "test-results.json"
        ]

        for test_file in test_files:
            if test_file.exists():
                return self._parse_jest_results(test_file)

        print(f"⚠️  前端测试结果文件不存在")
        return {"total_tests": 0, "passed_tests": 0, "failed_tests": 0, "skipped_tests": 0}

    def _parse_jest_results(self, test_file: Path) -> Dict[str, int]:
        """解析Jest测试结果"""
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'numTotalTests' in data:
                # Jest 27+ 格式
                total_tests = data['numTotalTests']
                passed_tests = data['numPassedTests']
                failed_tests = data['numFailedTests']
                skipped_tests = data['numPendingTests']
            else:
                # 尝试其他格式
                total_tests = 0
                passed_tests = 0
                failed_tests = 0
                skipped_tests = 0

            return {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "skipped_tests": skipped_tests
            }

        except Exception as e:
            print(f"❌ 解析前端测试结果失败: {e}")
            return {"total_tests": 0, "passed_tests": 0, "failed_tests": 0, "skipped_tests": 0}

    def calculate_overall_coverage(self, backend_data: Dict[str, Any], frontend_data: Dict[str, Any]) -> Dict[str, Any]:
        """计算总体覆盖率"""
        backend_coverage = backend_data.get('backend_coverage', 0.0)
        frontend_coverage = frontend_data.get('frontend_coverage', 0.0)

        # 根据权重计算总体覆盖率
        # 这里给后端更高的权重，因为它包含更多业务逻辑
        backend_weight = 0.6
        frontend_weight = 0.4

        overall_coverage = (backend_coverage * backend_weight) + (frontend_coverage * frontend_weight)

        # 计算总行数
        total_lines = backend_data.get('backend_lines_total', 0) + frontend_data.get('frontend_lines_total', 0)
        total_covered = backend_data.get('backend_lines_covered', 0) + frontend_data.get('frontend_lines_covered', 0)

        # 合并所有模块
        all_modules = backend_data.get('backend_modules', []) + frontend_data.get('frontend_modules', [])

        # 计算质量门禁结果
        modules_above_threshold = sum(1 for module in all_modules
                                    if module.get('coverage_percentage', 0) >= 50.0)

        return {
            "overall_coverage": overall_coverage,
            "total_lines": total_lines,
            "total_covered": total_lines,
            "total_modules": len(all_modules),
            "modules_above_threshold": modules_above_threshold,
            "modules_below_threshold": len(all_modules) - modules_above_threshold
        }

    def generate_summary(self) -> Dict[str, Any]:
        """生成覆盖率摘要"""
        print("🚀 开始计算测试覆盖率...")

        # 解析后端覆盖率
        backend_data = self.parse_backend_coverage()

        # 解析前端覆盖率
        frontend_data = self.parse_frontend_coverage()

        # 解析测试结果
        test_results = self.parse_test_results()

        # 计算总体覆盖率
        overall_data = self.calculate_overall_coverage(backend_data, frontend_data)

        # 构建摘要报告
        summary = {
            "project_name": "land-property-management",
            "generated_at": str(Path.cwd()),
            "backend_coverage": backend_data.get('backend_coverage', 0.0),
            "frontend_coverage": frontend_data.get('frontend_coverage', 0.0),
            "overall_coverage": overall_data['overall_coverage'],
            "total_coverage": overall_data['overall_coverage'],  # 兼容性字段
            "module_metrics": overall_data.get('all_modules', []),
            "total_modules": overall_data['total_modules'],
            "modules_above_threshold": overall_data['modules_above_threshold'],
            "modules_below_threshold": overall_data['modules_below_threshold'],
            "test_execution_time": None,  # 可以从其他地方获取
            "total_tests": test_results['total_tests'],
            "passed_tests": test_results['passed_tests'],
            "failed_tests": test_results['failed_tests'],
            "skipped_tests": test_results['skipped_tests'],
            "pass_rate": test_results['pass_rate'],
            **backend_data,
            **frontend_data,
            **overall_data
        }

        print(f"✅ 覆盖率计算完成:")
        print(f"   后端: {summary['backend_coverage']:.1f}%")
        print(f"   前端: {summary['frontend_coverage']:.1f}%")
        print(f"   总体: {summary['overall_coverage']:.1f}%")

        return summary

    def save_summary(self, summary: Dict[str, Any]):
        """保存覆盖率摘要"""
        try:
            # 确保输出目录存在
            self.output_file.parent.mkdir(parents=True, exist_ok=True)

            # 保存JSON格式
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            print(f"💾 覆盖率摘要已保存: {self.output_file}")

            # 生成可读的报告
            self._generate_readable_report(summary)

        except Exception as e:
            print(f"❌ 保存覆盖率摘要失败: {e}")

    def _generate_readable_report(self, summary: Dict[str, Any]):
        """生成可读的覆盖率报告"""
        report_file = self.output_file.parent / "coverage-report.md"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("# 测试覆盖率报告\n\n")
                f.write(f"**项目**: {summary['project_name']}\n")
                f.write(f"**生成时间**: {summary['generated_at']}\n\n")

                f.write("## 覆盖率概览\n\n")
                f.write(f"- **总体覆盖率**: {summary['overall_coverage']:.1f}%\n")
                f.write(f"- **后端覆盖率**: {summary['backend_coverage']:.1f}%\n")
                f.write(f"- **前端覆盖率**: {summary['frontend_coverage']:.1f}%\n\n")

                f.write("## 测试结果\n\n")
                f.write(f"- **总测试数**: {summary['total_tests']}\n")
                f.write(f"- **通过**: {summary['passed_tests']}\n")
                f.write(f"- **失败**: {summary['failed_tests']}\n")
                f.write(f"- **跳过**: {summary['skipped_tests']}\n")
                f.write(f"- **通过率**: {summary['pass_rate']:.1f}%\n\n")

                f.write("## 模块详情\n\n")
                f.write("| 模块 | 覆盖率 | 行覆盖率 | 文件路径 |\n")
                f.write("|------|--------|----------|----------|\n")

                for module in summary.get('module_metrics', [])[:20]:  # 只显示前20个
                    coverage = module.get('coverage_percentage', 0)
                    lines = f"{module.get('lines_covered', 0)}/{module.get('lines_total', 0)}"
                    path = module.get('file_path', '')
                    f.write(f"| {module.get('module_name', '')} | {coverage:.1f}% | {lines} | {path} |\n")

            print(f"📄 可读报告已生成: {report_file}")

        except Exception as e:
            print(f"❌ 生成可读报告失败: {e}")


def main():
    """主函数"""
    calculator = CoverageCalculator()

    try:
        # 生成覆盖率摘要
        summary = calculator.generate_summary()

        # 保存摘要
        calculator.save_summary(summary)

        # 输出关键指标供其他脚本使用
        print(f"BACKEND_COVERAGE={summary['backend_coverage']:.1f}")
        print(f"FRONTEND_COVERAGE={summary['frontend_coverage']:.1f}")
        print(f"OVERALL_COVERAGE={summary['overall_coverage']:.1f}")

        return 0

    except Exception as e:
        print(f"❌ 计算覆盖率失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())