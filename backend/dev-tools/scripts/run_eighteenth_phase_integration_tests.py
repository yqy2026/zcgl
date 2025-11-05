"""
第十八阶段：全栈集成测试深化执行脚本
执行所有第十八阶段创建的集成测试套件并生成综合报告
"""

import subprocess
import sys
import time
from datetime import datetime
from typing import Any


class EighteenthPhaseIntegrationTestRunner:
    """第十八阶段集成测试执行器"""

    def __init__(self):
        self.test_suites = [
            {
                "name": "前后端集成测试",
                "file": "test_frontend_backend_integration_stable.py",
                "description": "验证前端API服务与后端API的集成",
            },
            {
                "name": "数据库集成测试",
                "file": "test_database_integration_stable.py",
                "description": "验证数据库模型、连接池、事务管理",
            },
            {
                "name": "第三方服务集成测试",
                "file": "test_third_party_service_integration_stable.py",
                "description": "验证Redis、S3、SMTP等第三方服务集成",
            },
            {
                "name": "性能压力测试",
                "file": "test_performance_pressure_stable.py",
                "description": "验证系统在高负载下的性能表现",
            },
            {
                "name": "安全渗透测试",
                "file": "test_security_penetration_stable.py",
                "description": "验证系统安全防护能力",
            },
        ]

        self.test_results = []
        self.start_time = datetime.now()

    def run_test_suite(self, suite_info: dict[str, str]) -> dict[str, Any]:
        """运行单个测试套件"""
        print(f"\n{'='*80}")
        print(f"执行测试套件: {suite_info['name']}")
        print(f"描述: {suite_info['description']}")
        print(f"文件: {suite_info['file']}")
        print(f"{'='*80}")

        start_time = time.time()

        try:
            # 执行测试文件
            result = subprocess.run(
                [sys.executable, suite_info["file"]],
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
            )

            execution_time = time.time() - start_time

            # 解析测试结果
            result_data = {
                "suite_name": suite_info["name"],
                "file": suite_info["file"],
                "description": suite_info["description"],
                "execution_time": execution_time,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
            }

            # 从输出中提取测试统计信息
            test_stats = self._parse_test_output(result.stdout)
            result_data.update(test_stats)

            # 打印测试结果摘要
            self._print_test_summary(result_data)

            return result_data

        except subprocess.TimeoutExpired:
            print(f"[TIMEOUT] {suite_info['name']} 执行超时")
            return {
                "suite_name": suite_info["name"],
                "file": suite_info["file"],
                "success": False,
                "timeout": True,
                "execution_time": 300,
                "error": "测试执行超时",
            }

        except Exception as e:
            print(f"[ERROR] {suite_info['name']} 执行失败: {str(e)}")
            return {
                "suite_name": suite_info["name"],
                "file": suite_info["file"],
                "success": False,
                "execution_time": time.time() - start_time,
                "error": str(e),
            }

    def _parse_test_output(self, output: str) -> dict[str, Any]:
        """解析测试输出以提取统计信息"""
        stats = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "pass_rate": 0.0,
            "performance_metrics": {},
            "security_metrics": {},
            "error_details": [],
        }

        lines = output.split("\n")

        for line in lines:
            # 查找测试结果摘要
            if "测试结果:" in line or "通过率:" in line:
                if ":" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        metric_name = parts[0].strip()
                        metric_value = parts[1].strip()

                        if "通过" in metric_name and "/" in metric_value:
                            try:
                                passed, total = metric_value.split("/")
                                stats["passed_tests"] = int(passed.strip())
                                stats["total_tests"] = int(total.split()[0].strip())
                            except ValueError:
                                pass

                        elif "通过率" in metric_name and "%" in metric_value:
                            try:
                                rate_str = metric_value.replace("%", "")
                                stats["pass_rate"] = float(rate_str)
                            except ValueError:
                                pass

            # 查找性能指标
            elif "平均响应时间:" in line:
                try:
                    time_str = line.split(":")[1].strip().replace("s", "")
                    stats["performance_metrics"]["avg_response_time"] = float(time_str)
                except (ValueError, IndexError):
                    pass

            elif "吞吐量:" in line and "操作/秒" in line:
                try:
                    throughput_str = line.split(":")[1].strip().split()[0]
                    stats["performance_metrics"]["throughput"] = float(throughput_str)
                except (ValueError, IndexError):
                    pass

            # 查找安全指标
            elif "防护率:" in line and "%" in line:
                try:
                    rate_str = line.split(":")[1].strip().replace("%", "")
                    stats["security_metrics"]["protection_rate"] = float(rate_str)
                except (ValueError, IndexError):
                    pass

            elif "阻止率:" in line and "%" in line:
                try:
                    rate_str = line.split(":")[1].strip().replace("%", "")
                    stats["security_metrics"]["blocking_rate"] = float(rate_str)
                except (ValueError, IndexError):
                    pass

            # 查找错误信息
            elif "[FAIL]" in line or "[ERROR]" in line:
                stats["error_details"].append(line.strip())

        # 计算失败测试数量
        stats["failed_tests"] = stats["total_tests"] - stats["passed_tests"]

        return stats

    def _print_test_summary(self, result_data: dict[str, Any]):
        """打印测试结果摘要"""
        status = "[PASS]" if result_data["success"] else "[FAIL]"
        print(f"{status} {result_data['suite_name']}")
        print(f"执行时间: {result_data['execution_time']:.2f}秒")

        if "total_tests" in result_data and result_data["total_tests"] > 0:
            print(
                f"测试结果: {result_data['passed_tests']}/{result_data['total_tests']} 通过"
            )
            print(f"通过率: {result_data['pass_rate']:.1f}%")

        if "performance_metrics" in result_data and result_data["performance_metrics"]:
            print("性能指标:")
            for metric, value in result_data["performance_metrics"].items():
                print(f"  {metric}: {value}")

        if "security_metrics" in result_data and result_data["security_metrics"]:
            print("安全指标:")
            for metric, value in result_data["security_metrics"].items():
                print(f"  {metric}: {value}")

        if not result_data["success"] and "error" in result_data:
            print(f"错误信息: {result_data['error']}")

    def run_all_tests(self) -> dict[str, Any]:
        """运行所有测试套件"""
        print("开始执行第十八阶段全栈集成测试深化")
        print(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试套件数量: {len(self.test_suites)}")

        total_start_time = time.time()

        # 执行所有测试套件
        for i, suite in enumerate(self.test_suites, 1):
            print(f"\n[{i}/{len(self.test_suites)}] 开始执行: {suite['name']}")

            result = self.run_test_suite(suite)
            self.test_results.append(result)

            # 在测试套件之间添加短暂延迟
            if i < len(self.test_suites):
                time.sleep(2)

        total_execution_time = time.time() - total_start_time
        end_time = datetime.now()

        # 生成综合报告
        report = self._generate_comprehensive_report(total_execution_time, end_time)

        return report

    def _generate_comprehensive_report(
        self, total_execution_time: float, end_time: datetime
    ) -> dict[str, Any]:
        """生成综合测试报告"""
        print(f"\n{'='*80}")
        print("第十八阶段全栈集成测试深化 - 综合报告")
        print(f"{'='*80}")

        # 统计总体结果
        total_suites = len(self.test_results)
        successful_suites = sum(1 for r in self.test_results if r["success"])
        failed_suites = total_suites - successful_suites

        total_tests = sum(r.get("total_tests", 0) for r in self.test_results)
        total_passed = sum(r.get("passed_tests", 0) for r in self.test_results)
        total_failed = total_tests - total_passed

        overall_success_rate = (
            (successful_suites / total_suites) * 100 if total_suites > 0 else 0
        )
        overall_test_pass_rate = (
            (total_passed / total_tests) * 100 if total_tests > 0 else 0
        )

        # 性能指标汇总
        performance_summary = {}
        all_response_times = []
        all_throughputs = []

        for result in self.test_results:
            if "performance_metrics" in result:
                metrics = result["performance_metrics"]
                if "avg_response_time" in metrics:
                    all_response_times.append(metrics["avg_response_time"])
                if "throughput" in metrics:
                    all_throughputs.append(metrics["throughput"])

        if all_response_times:
            performance_summary["avg_response_time"] = sum(all_response_times) / len(
                all_response_times
            )
            performance_summary["max_response_time"] = max(all_response_times)
            performance_summary["min_response_time"] = min(all_response_times)

        if all_throughputs:
            performance_summary["avg_throughput"] = sum(all_throughputs) / len(
                all_throughputs
            )

        # 安全指标汇总
        security_summary = {}
        all_protection_rates = []
        all_blocking_rates = []

        for result in self.test_results:
            if "security_metrics" in result:
                metrics = result["security_metrics"]
                if "protection_rate" in metrics:
                    all_protection_rates.append(metrics["protection_rate"])
                if "blocking_rate" in metrics:
                    all_blocking_rates.append(metrics["blocking_rate"])

        if all_protection_rates:
            security_summary["avg_protection_rate"] = sum(all_protection_rates) / len(
                all_protection_rates
            )

        if all_blocking_rates:
            security_summary["avg_blocking_rate"] = sum(all_blocking_rates) / len(
                all_blocking_rates
            )

        # 打印综合报告
        print(
            f"执行时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} - {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(f"总执行时间: {total_execution_time:.2f}秒")
        print()

        print("测试套件执行结果:")
        print(f"  总套件数: {total_suites}")
        print(f"  成功套件: {successful_suites}")
        print(f"  失败套件: {failed_suites}")
        print(f"  套件成功率: {overall_success_rate:.1f}%")
        print()

        print("测试用例执行结果:")
        print(f"  总测试数: {total_tests}")
        print(f"  通过测试: {total_passed}")
        print(f"  失败测试: {total_failed}")
        print(f"  测试通过率: {overall_test_pass_rate:.1f}%")
        print()

        if performance_summary:
            print("性能指标汇总:")
            for metric, value in performance_summary.items():
                if "time" in metric:
                    print(f"  {metric}: {value:.3f}s")
                else:
                    print(f"  {metric}: {value:.2f}")
            print()

        if security_summary:
            print("安全指标汇总:")
            for metric, value in security_summary.items():
                print(f"  {metric}: {value:.1f}%")
            print()

        # 详细结果
        print("各测试套件详细结果:")
        for result in self.test_results:
            status = "PASS" if result["success"] else "FAIL"
            print(f"  [{status}] {result['suite_name']}")
            if "pass_rate" in result:
                print(f"    通过率: {result['pass_rate']:.1f}%")
            if "execution_time" in result:
                print(f"    执行时间: {result['execution_time']:.2f}秒")

        # 生成综合评估
        print(f"\n{'='*80}")
        print("综合评估:")

        if overall_success_rate >= 80:
            grade = "优秀"
            emoji = "🎉"
        elif overall_success_rate >= 70:
            grade = "良好"
            emoji = "👍"
        elif overall_success_rate >= 60:
            grade = "及格"
            emoji = "✅"
        else:
            grade = "需要改进"
            emoji = "⚠️"

        print(f"{emoji} 第十八阶段全栈集成测试深化评级: {grade}")
        print(f"整体成功率: {overall_success_rate:.1f}%")

        if overall_success_rate >= 80:
            print("系统集成质量优秀，可以进入生产环境部署阶段。")
        elif overall_success_rate >= 60:
            print("系统集成质量良好，建议优化后进行生产部署。")
        else:
            print("系统集成需要改进，请解决关键问题后重新测试。")

        # 构建返回报告
        report = {
            "execution_period": {
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_execution_time": total_execution_time,
            },
            "suite_summary": {
                "total_suites": total_suites,
                "successful_suites": successful_suites,
                "failed_suites": failed_suites,
                "success_rate": overall_success_rate,
            },
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": total_passed,
                "failed_tests": total_failed,
                "pass_rate": overall_test_pass_rate,
            },
            "performance_summary": performance_summary,
            "security_summary": security_summary,
            "detailed_results": self.test_results,
            "grade": grade,
            "recommendation": self._get_recommendation(overall_success_rate),
        }

        return report

    def _get_recommendation(self, success_rate: float) -> str:
        """根据成功率获取建议"""
        if success_rate >= 80:
            return "系统集成质量优秀，满足生产环境部署要求。"
        elif success_rate >= 70:
            return "系统集成质量良好，建议修复少数问题后部署。"
        elif success_rate >= 60:
            return "系统集成基本达标，需要优化关键问题。"
        else:
            return "系统集成存在重大问题，需要重新设计和实现。"

    def save_report(self, report: dict[str, Any], filename: str = None):
        """保存测试报告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"EIGHTEENTH_PHASE_INTEGRATION_TEST_REPORT_{timestamp}.json"

        try:
            import json

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\n报告已保存到: {filename}")
        except Exception as e:
            print(f"\n保存报告失败: {str(e)}")


def main():
    """主函数"""
    runner = EighteenthPhaseIntegrationTestRunner()

    try:
        # 运行所有测试
        report = runner.run_all_tests()

        # 保存报告
        runner.save_report(report)

        # 返回适当的退出码
        if report["suite_summary"]["success_rate"] >= 70:
            return 0
        else:
            return 1

    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 2
    except Exception as e:
        print(f"\n测试执行过程中发生错误: {str(e)}")
        return 3


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
