#!/usr/bin/env python3
"""
简化版质量监控系统
Simple Quality Monitoring System

针对Windows编码问题优化的版本，确保所有输出都使用标准ASCII字符
"""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


class SimpleQualityMonitor:
    """简化质量监控器"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent

    def run_quick_check(self):
        """运行快速质量检查"""
        print("=" * 50)
        print("Quality Monitor - Quick Check")
        print("=" * 50)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        results = {}

        # 1. 语法检查
        print("1. Syntax Check...")
        syntax_result = self._check_syntax()
        results['syntax'] = syntax_result
        print(f"   Score: {syntax_result['score']:.1f} - {syntax_result['status']}")
        if syntax_result['issues']:
            print(f"   Issues Found: {len(syntax_result['issues'])}")

        # 2. 导入检查
        print("\n2. Import Check...")
        import_result = self._check_imports()
        results['import'] = import_result
        print(f"   Score: {import_result['score']:.1f} - {import_result['status']}")
        if import_result['failed_imports']:
            print(f"   Failed Imports: {len(import_result['failed_imports'])}")

        # 3. 基本测试
        print("\n3. Basic Tests...")
        test_result = self._run_basic_tests()
        results['tests'] = test_result
        print(f"   Score: {test_result['score']:.1f} - {test_result['status']}")
        print(f"   Passed: {test_result['passed']}, Failed: {test_result['failed']}")
        print(f"   Execution Time: {test_result['execution_time']:.1f}s")

        # 4. 计算总分
        overall_score = (syntax_result['score'] + import_result['score'] + test_result['score']) / 3
        overall_status = self._get_status(overall_score)

        print("\n" + "=" * 50)
        print(f"Overall Score: {overall_score:.1f} - {overall_status}")
        print("=" * 50)

        # 5. 生成报告
        self._save_simple_report(results, overall_score, overall_status)

        return overall_score

    def _check_syntax(self):
        """检查语法"""
        try:
            # 使用ruff检查语法
            result = subprocess.run(
                ["ruff", "check", "src/", "--select=E,F", "--output-format=json"],
                capture_output=True,
                text=True,
                cwd=self.base_dir
            )

            if result.stdout and result.returncode == 0:
                try:
                    import json
                    errors = json.loads(result.stdout)
                    error_count = len(errors)
                except:
                    error_count = result.stdout.count('\n')
            else:
                error_count = 0

            if result.returncode != 0:
                error_count += 1

            score = max(0, 100 - error_count * 10)
            status = self._get_status(score)

            return {
                'score': score,
                'status': status,
                'error_count': error_count,
                'issues': error_count > 0
            }

        except Exception as e:
            print(f"   Error running syntax check: {e}")
            return {
                'score': 0,
                'status': 'ERROR',
                'error_count': -1,
                'issues': True
            }

    def _check_imports(self):
        """检查模块导入"""
        modules_to_test = [
            "src.main",
            "src.models.asset",
            "src.api.v1.assets"
        ]

        successful_imports = 0
        failed_imports = []

        for module in modules_to_test:
            try:
                __import__(module)
                successful_imports += 1
            except ImportError:
                failed_imports.append(module)
            except Exception as e:
                failed_imports.append(f"{module} ({type(e).__name__})")

        total_modules = len(modules_to_test)
        score = (successful_imports / total_modules) * 100
        status = self._get_status(score)

        return {
            'score': score,
            'status': status,
            'total_modules': total_modules,
            'successful_imports': successful_imports,
            'failed_imports': failed_imports
        }

    def _run_basic_tests(self):
        """运行基本测试"""
        test_files = [
            "tests/test_main.py",
            "tests/test_quick_suite.py"
        ]

        start_time = time.time()

        try:
            result = subprocess.run(
                ["python", "-m", "pytest"] + test_files + ["-v", "--tb=no"],
                capture_output=True,
                text=True,
                cwd=self.base_dir
            )

            execution_time = time.time() - start_time

            # 解析结果
            output = result.stdout + result.stderr
            passed = output.count("PASSED")
            failed = output.count("FAILED")
            error = output.count("ERROR")

            total = passed + failed + error

            if total > 0:
                success_rate = (passed / total) * 100
                score = success_rate
            else:
                success_rate = 0
                score = 0

            # 性能评分
            if execution_time <= 30:
                performance_score = 100
            else:
                performance_score = max(0, 100 - (execution_time - 30) * 2)

            # 综合评分
            final_score = (score + performance_score) / 2
            status = self._get_status(final_score)

            return {
                'score': final_score,
                'status': status,
                'passed': passed,
                'failed': failed,
                'error': error,
                'total': total,
                'success_rate': success_rate,
                'execution_time': execution_time,
                'performance_score': performance_score
            }

        except Exception as e:
            print(f"   Error running tests: {e}")
            return {
                'score': 0,
                'status': 'ERROR',
                'passed': 0,
                'failed': 0,
                'error': 1,
                'total': 0,
                'execution_time': 0,
                'performance_score': 0
            }

    def _get_status(self, score):
        """根据分数获取状态"""
        if score >= 90:
            return "EXCELLENT"
        elif score >= 80:
            return "GOOD"
        elif score >= 70:
            return "SATISFACTORY"
        elif score >= 60:
            return "NEEDS_IMPROVEMENT"
        else:
            return "POOR"

    def _save_simple_report(self, results, overall_score, overall_status):
        """保存简化报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = self.base_dir / "reports"
        report_dir.mkdir(exist_ok=True)

        report_file = report_dir / f"simple_quality_{timestamp}.txt"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("Quality Monitor Report\n")
                f.write("=" * 30 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Overall Score: {overall_score:.1f}\n")
                f.write(f"Overall Status: {overall_status}\n\n")

                f.write("Detailed Results:\n")
                f.write("-" * 20 + "\n")

                for check_name, result in results.items():
                    f.write(f"{check_name.upper()}:\n")
                    f.write(f"  Score: {result['score']:.1f}\n")
                    f.write(f"  Status: {result['status']}\n")

                    if check_name == 'syntax':
                        f.write(f"  Errors: {result.get('error_count', 0)}\n")
                    elif check_name == 'import':
                        f.write(f"  Successful: {result.get('successful_imports', 0)}/{result.get('total_modules', 0)}\n")
                        if result.get('failed_imports'):
                            f.write(f"  Failed: {', '.join(result['failed_imports'])}\n")
                    elif check_name == 'tests':
                        f.write(f"  Passed: {result.get('passed', 0)}\n")
                        f.write(f"  Failed: {result.get('failed', 0)}\n")
                        f.write(f"  Time: {result.get('execution_time', 0):.1f}s\n")

                    f.write("\n")

            print(f"\nReport saved: {report_file}")

        except Exception as e:
            print(f"Error saving report: {e}")


def main():
    """主函数"""
    monitor = SimpleQualityMonitor()

    try:
        score = monitor.run_quick_check()

        # 根据分数设置退出代码
        if score >= 70:
            print("\nQuality Check: PASSED")
            sys.exit(0)
        else:
            print("\nQuality Check: NEEDS_IMPROVEMENT")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nQuality Check: CANCELLED")
        sys.exit(2)
    except Exception as e:
        print(f"\nQuality Check: ERROR - {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
