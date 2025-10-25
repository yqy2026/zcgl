#!/usr/bin/env python3
"""
测试覆盖率质量门禁检查脚本
检查测试覆盖率是否满足设定的阈值要求
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any


class QualityGateChecker:
    """质量门禁检查器"""

    def __init__(self, backend_threshold: float = 80.0, frontend_threshold: float = 70.0, total_threshold: float = 75.0):
        self.backend_threshold = backend_threshold
        self.frontend_threshold = frontend_threshold
        self.total_threshold = total_threshold
        self.coverage_file = Path("coverage-summary.json")
        self.output_file = Path("quality-gate-result.json")

    def load_coverage_data(self) -> Dict[str, Any]:
        """加载覆盖率数据"""
        if not self.coverage_file.exists():
            print(f"❌ 覆盖率文件不存在: {self.coverage_file}")
            sys.exit(1)

        try:
            with open(self.coverage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 读取覆盖率文件失败: {e}")
            sys.exit(1)

    def check_thresholds(self, coverage_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查覆盖率阈值"""
        backend_coverage = coverage_data.get('backend_coverage', 0.0)
        frontend_coverage = coverage_data.get('frontend_coverage', 0.0)
        total_coverage = coverage_data.get('overall_coverage', 0.0)

        failed_checks = []

        # 检查后端覆盖率
        if backend_coverage < self.backend_threshold:
            failed_checks.append(
                f"后端覆盖率 {backend_coverage:.1f}% 低于阈值 {self.backend_threshold}%"
            )

        # 检查前端覆盖率
        if frontend_coverage < self.frontend_threshold:
            failed_checks.append(
                f"前端覆盖率 {frontend_coverage:.1f}% 低于阈值 {self.frontend_threshold}%"
            )

        # 检查总体覆盖率
        if total_coverage < self.total_threshold:
            failed_checks.append(
                f"总体覆盖率 {total_coverage:.1f}% 低于阈值 {self.total_threshold}%"
            )

        # 检查测试通过率
        pass_rate = coverage_data.get('pass_rate', 0.0)
        if pass_rate < 95.0:  # 要求95%以上的测试通过率
            failed_checks.append(
                f"测试通过率 {pass_rate:.1f}% 低于阈值 95.0%"
            )

        # 检查模块覆盖率
        modules = coverage_data.get('module_metrics', [])
        low_coverage_modules = [
            module for module in modules
            if module.get('coverage_percentage', 0) < 50.0
        ]

        if low_coverage_modules:
            failed_checks.append(
                f"存在 {len(low_coverage_modules)} 个模块覆盖率低于50%"
            )

        # 检查是否有未测试的关键模块
        critical_modules = self._identify_critical_modules(modules)
        untested_critical = [
            module for module in critical_modules
            if module.get('coverage_percentage', 0) < 80.0
        ]

        if untested_critical:
            failed_checks.append(
                f"关键模块测试覆盖不足: {[m['module_name'] for m in untested_critical]}"
            )

        passed = len(failed_checks) == 0

        result = {
            "passed": passed,
            "thresholds": {
                "backend": self.backend_threshold,
                "frontend": self.frontend_threshold,
                "total": self.total_threshold,
                "pass_rate": 95.0,
                "min_module_coverage": 50.0
            },
            "current_coverage": {
                "backend": backend_coverage,
                "frontend": frontend_coverage,
                "total": total_coverage,
                "pass_rate": pass_rate
            },
            "failed_checks": failed_checks,
            "passed_checks": self._get_passed_checks(coverage_data),
            "recommendations": self._generate_recommendations(failed_checks, coverage_data),
            "severity": self._calculate_severity(failed_checks, coverage_data),
            "risk_level": self._calculate_risk_level(failed_checks, coverage_data)
        }

        return result

    def _identify_critical_modules(self, modules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """识别关键模块"""
        critical_keywords = [
            'auth', 'security', 'rbac', 'permission',
            'core', 'main', 'api',
            'database', 'model', 'crud',
            'asset', 'rent', 'contract'
        ]

        critical_modules = []
        for module in modules:
            module_name = module.get('module_name', '').lower()
            if any(keyword in module_name for keyword in critical_keywords):
                critical_modules.append(module)

        return critical_modules

    def _get_passed_checks(self, coverage_data: Dict[str, Any]) -> List[str]:
        """获取通过的检查项"""
        passed_checks = []
        backend_coverage = coverage_data.get('backend_coverage', 0.0)
        frontend_coverage = coverage_data.get('frontend_coverage', 0.0)
        total_coverage = coverage_data.get('overall_coverage', 0.0)
        pass_rate = coverage_data.get('pass_rate', 0.0)

        if backend_coverage >= self.backend_threshold:
            passed_checks.append(
                f"后端覆盖率 {backend_coverage:.1f}% 达到阈值 {self.backend_threshold}%"
            )

        if frontend_coverage >= self.frontend_threshold:
            passed_checks.append(
                f"前端覆盖率 {frontend_coverage:.1f}% 达到阈值 {self.frontend_threshold}%"
            )

        if total_coverage >= self.total_threshold:
            passed_checks.append(
                f"总体覆盖率 {total_coverage:.1f}% 达到阈值 {self.total_threshold}%"
            )

        if pass_rate >= 95.0:
            passed_checks.append(
                f"测试通过率 {pass_rate:.1f}% 达到阈值 95.0%"
            )

        modules = coverage_data.get('module_metrics', [])
        high_coverage_modules = [
            module for module in modules
            if module.get('coverage_percentage', 0) >= 80.0
        ]

        if high_coverage_modules:
            passed_checks.append(
                f"有 {len(high_coverage_modules)} 个模块覆盖率超过80%"
            )

        return passed_checks

    def _generate_recommendations(self, failed_checks: List[str], coverage_data: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        backend_coverage = coverage_data.get('backend_coverage', 0.0)
        frontend_coverage = coverage_data.get('frontend_coverage', 0.0)

        # 基于失败检查项生成建议
        for check in failed_checks:
            if "后端覆盖率" in check:
                recommendations.extend([
                    "增加后端单元测试用例",
                    "为未覆盖的核心业务逻辑编写测试",
                    "检查测试配置是否正确包含所有源文件",
                    "考虑使用测试覆盖率工具识别未测试的代码路径"
                ])
            elif "前端覆盖率" in check:
                recommendations.extend([
                    "增加组件测试用例",
                    "为未覆盖的组件编写单元测试",
                    "增加集成测试和端到端测试",
                    "检查测试配置是否正确排除不需要测试的文件"
                ])
            elif "测试通过率" in check:
                recommendations.extend([
                    "修复失败的测试用例",
                    "检查测试环境和数据的一致性",
                    "更新过时的测试断言",
                    "分析测试失败的根本原因"
                ])
            elif "模块覆盖率低于50%" in check:
                recommendations.extend([
                    "优先为低覆盖率模块编写测试",
                    "分析模块的复杂性和风险",
                    "考虑重构复杂的模块以提高可测试性"
                ])
            elif "关键模块测试覆盖不足" in check:
                recommendations.extend([
                    "优先提升关键模块的测试覆盖率",
                    "为核心功能编写全面的测试用例",
                    "增加边界条件和异常情况的测试"
                ])

        # 通用建议
        if backend_coverage < 60:
            recommendations.append("后端覆盖率严重不足，建议制定测试覆盖率改进计划")

        if frontend_coverage < 60:
            recommendations.append("前端覆盖率严重不足，建议增加组件和功能测试")

        if coverage_data.get('total_tests', 0) < 100:
            recommendations.append("测试用例数量偏少，建议增加测试用例覆盖更多场景")

        # 去重并限制建议数量
        unique_recommendations = list(set(recommendations))
        return unique_recommendations[:8]  # 最多返回8条建议

    def _calculate_severity(self, failed_checks: List[str], coverage_data: Dict[str, Any]) -> str:
        """计算问题严重程度"""
        if not failed_checks:
            return "none"

        backend_coverage = coverage_data.get('backend_coverage', 100.0)
        frontend_coverage = coverage_data.get('frontend_coverage', 100.0)
        total_coverage = coverage_data.get('overall_coverage', 100.0)

        # 计算严重程度
        if (backend_coverage < 50 or frontend_coverage < 50 or total_coverage < 60):
            return "critical"
        elif (backend_coverage < 70 or frontend_coverage < 60 or total_coverage < 70):
            return "high"
        elif len(failed_checks) >= 3:
            return "medium"
        else:
            return "low"

    def _calculate_risk_level(self, failed_checks: List[str], coverage_data: Dict[str, Any]) -> str:
        """计算风险级别"""
        if not failed_checks:
            return "low"

        severity = self._calculate_severity(failed_checks, coverage_data)

        # 考虑项目规模和复杂性
        total_modules = coverage_data.get('total_modules', 0)
        critical_modules_untested = any("关键模块" in check for check in failed_checks)

        if severity == "critical" or critical_modules_untested:
            return "high"
        elif severity == "high" or total_modules > 50:
            return "medium"
        else:
            return "low"

    def save_result(self, result: Dict[str, Any]):
        """保存质量门禁结果"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"💾 质量门禁结果已保存: {self.output_file}")
        except Exception as e:
            print(f"❌ 保存质量门禁结果失败: {e}")

    def print_result(self, result: Dict[str, Any]):
        """打印质量门禁结果"""
        if result["passed"]:
            print("✅ 质量门禁检查通过")
            print("\n📊 覆盖率指标:")
            print(f"  - 后端覆盖率: {result['current_coverage']['backend']:.1f}% (阈值: {result['thresholds']['backend']}%)")
            print(f"  - 前端覆盖率: {result['current_coverage']['frontend']:.1f}% (阈值: {result['thresholds']['frontend']}%)")
            print(f"  - 总体覆盖率: {result['current_coverage']['total']:.1f}% (阈值: {result['thresholds']['total']}%)")
            print(f"  - 测试通过率: {result['current_coverage']['pass_rate']:.1f}% (阈值: {result['thresholds']['pass_rate']}%)")

            if result['passed_checks']:
                print("\n✅ 通过的检查项:")
                for check in result['passed_checks']:
                    print(f"  - {check}")
        else:
            print("❌ 质量门禁检查失败")
            print("\n📊 当前覆盖率指标:")
            print(f"  - 后端覆盖率: {result['current_coverage']['backend']:.1f}% (阈值: {result['thresholds']['backend']}%)")
            print(f"  - 前端覆盖率: {result['current_coverage']['frontend']:.1f}% (阈值: {result['thresholds']['frontend']}%)")
            print(f"  - 总体覆盖率: {result['current_coverage']['total']:.1f}% (阈值: {result['thresholds']['total']}%)")
            print(f"  - 测试通过率: {result['current_coverage']['pass_rate']:.1f}% (阈值: {result['thresholds']['pass_rate']}%)")

            print(f"\n🚨 失败检查项 ({len(result['failed_checks'])}):")
            for check in result['failed_checks']:
                print(f"  - {check}")

            if result['recommendations']:
                print(f"\n💡 改进建议:")
                for rec in result['recommendations']:
                    print(f"  - {rec}")

        print(f"\n📈 严重程度: {result['severity'].upper()}")
        print(f"⚠️  风险级别: {result['risk_level'].upper()}")

    def generate_summary_report(self, result: Dict[str, Any]):
        """生成汇总报告"""
        report_file = self.output_file.parent / "quality-gate-summary.md"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("# 测试质量门禁报告\n\n")
                f.write(f"**检查结果**: {'✅ 通过' if result['passed'] else '❌ 失败'}\n")
                f.write(f"**严重程度**: {result['severity'].upper()}\n")
                f.write(f"**风险级别**: {result['risk_level'].upper()}\n\n")

                f.write("## 覆盖率阈值\n\n")
                thresholds = result['thresholds']
                current = result['current_coverage']

                f.write("| 指标 | 当前值 | 阈值 | 状态 |\n")
                f.write("|------|--------|------|------|\n")

                backend_status = "✅" if current['backend'] >= thresholds['backend'] else "❌"
                frontend_status = "✅" if current['frontend'] >= thresholds['frontend'] else "❌"
                total_status = "✅" if current['total'] >= thresholds['total'] else "❌"
                pass_rate_status = "✅" if current['pass_rate'] >= thresholds['pass_rate'] else "❌"

                f.write(f"| 后端覆盖率 | {current['backend']:.1f}% | {thresholds['backend']}% | {backend_status} |\n")
                f.write(f"| 前端覆盖率 | {current['frontend']:.1f}% | {thresholds['frontend']}% | {frontend_status} |\n")
                f.write(f"| 总体覆盖率 | {current['total']:.1f}% | {thresholds['total']}% | {total_status} |\n")
                f.write(f"| 测试通过率 | {current['pass_rate']:.1f}% | {thresholds['pass_rate']}% | {pass_rate_status} |\n")

                if not result['passed']:
                    f.write("\n## 失败检查项\n\n")
                    for i, check in enumerate(result['failed_checks'], 1):
                        f.write(f"{i}. {check}\n")

                    f.write("\n## 改进建议\n\n")
                    for i, rec in enumerate(result['recommendations'], 1):
                        f.write(f"{i}. {rec}\n")

                f.write(f"\n---\n*生成时间: {Path.cwd()}*\n")

            print(f"📄 质量门禁汇总报告已生成: {report_file}")

        except Exception as e:
            print(f"❌ 生成汇总报告失败: {e}")

    def run(self) -> int:
        """运行质量门禁检查"""
        print("🚀 开始测试质量门禁检查...")
        print(f"📊 阈值设置: 后端 {self.backend_threshold}%, 前端 {self.frontend_threshold}%, 总体 {self.total_threshold}%")

        # 加载覆盖率数据
        coverage_data = self.load_coverage_data()

        # 检查阈值
        result = self.check_thresholds(coverage_data)

        # 保存结果
        self.save_result(result)

        # 打印结果
        self.print_result(result)

        # 生成汇总报告
        self.generate_summary_report(result)

        # 返回退出码
        return 0 if result["passed"] else 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='测试覆盖率质量门禁检查')
    parser.add_argument('--backend-threshold', type=float, default=80.0,
                       help='后端覆盖率阈值 (默认: 80.0)')
    parser.add_argument('--frontend-threshold', type=float, default=70.0,
                       help='前端覆盖率阈值 (默认: 70.0)')
    parser.add_argument('--total-threshold', type=float, default=75.0,
                       help='总体覆盖率阈值 (默认: 75.0)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='详细输出')

    args = parser.parse_args()

    checker = QualityGateChecker(
        backend_threshold=args.backend_threshold,
        frontend_threshold=args.frontend_threshold,
        total_threshold=args.total_threshold
    )

    try:
        return checker.run()
    except KeyboardInterrupt:
        print("\n⚠️  质量门禁检查被中断")
        return 1
    except Exception as e:
        print(f"❌ 质量门禁检查失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())