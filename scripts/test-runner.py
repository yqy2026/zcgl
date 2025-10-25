#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一测试运行器
提供前后端测试的统一执行和报告生成功能
"""

import argparse
import codecs
import json
import locale
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# 设置标准输出编码为UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def safe_print(*args, **kwargs):
    """安全打印函数，处理Unicode编码问题"""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # 如果编码失败，使用ASCII替换
        safe_args = [str(arg).encode('ascii', 'replace').decode('ascii') for arg in args]
        print(*safe_args, **kwargs)


class TestRunner:
    """测试运行器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.backend_dir = self.project_root / "backend"
        self.frontend_dir = self.project_root / "frontend"
        self.results_dir = self.project_root / "test-results"
        self.report_file = self.results_dir / "test-report.json"
        self.start_time = None
        self.end_time = None

    def run_all_tests(
        self,
        backend: bool = True,
        frontend: bool = True,
        parallel: bool = True,
        coverage: bool = True,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """运行所有测试"""
        self.start_time = datetime.now()
        print(f"[TEST] 开始运行测试 ({self.start_time.strftime('%Y-%m-%d %H:%M:%S')})")
        print(f"[TEST] 项目根目录: {self.project_root}")
        print(f"[TEST] 后端目录: {self.backend_dir}")
        print(f"[TEST] 前端目录: {self.frontend_dir}")

        # 确保结果目录存在
        self.results_dir.mkdir(exist_ok=True)

        results = {
            "execution_id": self._generate_execution_id(),
            "start_time": self.start_time.isoformat(),
            "backend": {},
            "frontend": {},
            "summary": {}
        }

        test_tasks = []
        if backend:
            test_tasks.append(("backend", self._run_backend_tests, {
                "coverage": coverage,
                "verbose": verbose
            }))
        if frontend:
            test_tasks.append(("frontend", self._run_frontend_tests, {
                "coverage": coverage,
                "verbose": verbose
            }))

        if parallel and len(test_tasks) > 1:
            # 并行执行测试
            results = self._run_tests_parallel(test_tasks, results)
        else:
            # 串行执行测试
            results = self._run_tests_sequential(test_tasks, results)

        self.end_time = datetime.now()
        results["end_time"] = self.end_time.isoformat()
        results["total_duration"] = (self.end_time - self.start_time).total_seconds()

        # 生成汇总报告
        self._generate_summary_report(results)

        # 保存报告
        self._save_results(results)

        print(f"[TEST] 测试执行完成 (耗时: {results['total_duration']:.2f}秒)")
        return results

    def run_backend_tests(
        self,
        coverage: bool = True,
        verbose: bool = False,
        specific_test: Optional[str] = None
    ) -> Dict[str, Any]:
        """运行后端测试"""
        print("[TEST] 运行后端测试...")
        return self._run_backend_tests({
            "coverage": coverage,
            "verbose": verbose,
            "specific_test": specific_test
        })

    def run_frontend_tests(
        self,
        coverage: bool = True,
        verbose: bool = False,
        specific_test: Optional[str] = None
    ) -> Dict[str, Any]:
        """运行前端测试"""
        print("🌐 运行前端测试...")
        return self._run_frontend_tests({
            "coverage": coverage,
            "verbose": verbose,
            "specific_test": specific_test
        })

    def _run_tests_parallel(
        self,
        test_tasks: List[Tuple[str, callable, Dict]],
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """并行运行测试"""
        import concurrent.futures

        print("⚡ 并行执行测试...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # 提交所有测试任务
            future_to_name = {}
            for name, test_func, options in test_tasks:
                future = executor.submit(test_func, options)
                future_to_name[future] = name

            # 等待所有任务完成
            for future in concurrent.futures.as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    result = future.result()
                    results[name] = result
                    print(f"✅ {name} 测试完成: {result.get('status', 'unknown')}")
                except Exception as e:
                    print(f"❌ {name} 测试失败: {e}")
                    results[name] = {
                        "status": "error",
                        "error": str(e),
                        "tests": 0,
                        "passed": 0,
                        "failed": 0,
                        "skipped": 0
                    }

        return results

    def _run_tests_sequential(
        self,
        test_tasks: List[Tuple[str, callable, Dict]],
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """串行运行测试"""
        print("📋 串行执行测试...")

        for name, test_func, options in test_tasks:
            try:
                print(f"▶️ 开始执行 {name} 测试...")
                result = test_func(options)
                results[name] = result
                print(f"✅ {name} 测试完成: {result.get('status', 'unknown')}")
            except Exception as e:
                print(f"❌ {name} 测试失败: {e}")
                results[name] = {
                    "status": "error",
                    "error": str(e),
                    "tests": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0
                }

        return results

    def _run_backend_tests(self, options: Dict) -> Dict[str, Any]:
        """运行后端测试的具体实现"""
        os.chdir(self.backend_dir)

        test_start = time.time()
        result = {
            "type": "backend",
            "start_time": datetime.now().isoformat(),
            "command": [],
            "stdout": "",
            "stderr": "",
            "tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "coverage": 0.0,
            "duration": 0.0,
            "status": "unknown"
        }

        try:
            # 构建测试命令
            cmd = ["uv", "run", "python", "-m", "pytest", "tests/"]

            if options.get("verbose"):
                cmd.append("-v")

            if options.get("coverage"):
                cmd.extend([
                    "--cov=src",
                    "--cov-report=xml",
                    "--cov-report=html",
                    "--cov-report=term-missing",
                    "--junit-xml=test-results-backend.xml"
                ])

            if options.get("specific_test"):
                cmd.append(options["specific_test"])

            result["command"] = cmd

            print(f"🔧 执行命令: {' '.join(cmd)}")

            # 执行测试
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30分钟超时
            )

            result["stdout"] = process.stdout
            result["stderr"] = process.stderr
            result["exit_code"] = process.returncode

            # 解析测试结果
            if process.returncode == 0:
                result["status"] = "passed"
                result["passed"] = self._parse_test_output(process.stdout)
            else:
                result["status"] = "failed"
                result["failed"] = self._parse_test_output(process.stdout)

            result["tests"] = result["passed"] + result["failed"]

            # 解析覆盖率
            if options.get("coverage"):
                result["coverage"] = self._parse_backend_coverage()

        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
            result["error"] = "测试执行超时"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        finally:
            result["duration"] = time.time() - test_start
            result["end_time"] = datetime.now().isoformat()

        # 复制测试结果到结果目录
        self._copy_backend_test_results()

        return result

    def _run_frontend_tests(self, options: Dict) -> Dict[str, Any]:
        """运行前端测试的具体实现"""
        os.chdir(self.frontend_dir)

        test_start = time.time()
        result = {
            "type": "frontend",
            "start_time": datetime.now().isoformat(),
            "command": [],
            "stdout": "",
            "stderr": "",
            "tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "coverage": 0.0,
            "duration": 0.0,
            "status": "unknown"
        }

        try:
            # 构建测试命令
            cmd = ["npm", "run", "test:ci"]

            result["command"] = cmd

            print(f"🌐 执行命令: {' '.join(cmd)}")

            # 执行测试
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1200  # 20分钟超时
            )

            result["stdout"] = process.stdout
            result["stderr"] = process.stderr
            result["exit_code"] = process.returncode

            # 解析测试结果
            if process.returncode == 0:
                result["status"] = "passed"
            else:
                result["status"] = "failed"

            # 解析覆盖率
            result["coverage"] = self._parse_frontend_coverage()

            # 解析测试统计
            stats = self._parse_frontend_test_stats(process.stdout)
            result.update(stats)

        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
            result["error"] = "测试执行超时"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        finally:
            result["duration"] = time.time() - test_start
            result["end_time"] = datetime.now().isoformat()

        # 复制测试结果到结果目录
        self._copy_frontend_test_results()

        return result

    def _parse_test_output(self, output: str) -> int:
        """解析pytest输出，获取测试数量"""
        try:
            # 查找类似 "X passed, Y failed, Z skipped" 的行
            import re
            pattern = r'(\d+)\s+(passed|failed|skipped)'
            matches = re.findall(pattern, output)

            total = 0
            for count, status in matches:
                if status in ["passed", "failed", "skipped"]:
                    total += int(count)

            return total
        except Exception:
            return 0

    def _parse_backend_coverage(self) -> float:
        """解析后端覆盖率"""
        try:
            coverage_file = self.backend_dir / "coverage.xml"
            if coverage_file.exists():
                import xml.etree.ElementTree as ET
                tree = ET.parse(coverage_file)
                root = tree.getroot()
                line_rate = float(root.get('line-rate', 0))
                return line_rate * 100
        except Exception:
            pass
        return 0.0

    def _parse_frontend_coverage(self) -> float:
        """解析前端覆盖率"""
        try:
            coverage_file = self.frontend_dir / "coverage" / "coverage-summary.json"
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    data = json.load(f)
                total = data.get('total', {})
                return total.get('lines', {}).get('pct', 0.0)
        except Exception:
            pass
        return 0.0

    def _parse_frontend_test_stats(self, output: str) -> Dict[str, int]:
        """解析前端测试统计"""
        try:
            # 查找Jest输出中的测试统计
            import re

            # 尝试匹配 "Test Suites: X passed, Y failed"
            suites_match = re.search(r'Test Suites:\s*(\d+)\s*passed,\s*(\d+)\s*failed', output)

            # 尝试匹配 "Tests: X passed, Y failed, Z skipped"
            tests_match = re.search(r'Tests:\s*(\d+)\s*passed,\s*(\d+)\s*failed,\s*(\d+)\s*skipped', output)

            stats = {"tests": 0, "passed": 0, "failed": 0, "skipped": 0}

            if tests_match:
                stats["passed"] = int(tests_match.group(1))
                stats["failed"] = int(tests_match.group(2))
                stats["skipped"] = int(tests_match.group(3))
                stats["tests"] = stats["passed"] + stats["failed"] + stats["skipped"]

            return stats
        except Exception:
            return {"tests": 0, "passed": 0, "failed": 0, "skipped": 0}

    def _copy_backend_test_results(self):
        """复制后端测试结果到结果目录"""
        backend_results_dir = self.results_dir / "backend"
        backend_results_dir.mkdir(exist_ok=True)

        files_to_copy = [
            "coverage.xml",
            "htmlcov/",
            "test-results-backend.xml",
            ".coverage"
        ]

        for file_pattern in files_to_copy:
            source = self.backend_dir / file_pattern
            if source.exists():
                dest = backend_results_dir / source.name
                if source.is_dir():
                    import shutil
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(source, dest)
                else:
                    import shutil
                    shutil.copy2(source, dest)

    def _copy_frontend_test_results(self):
        """复制前端测试结果到结果目录"""
        frontend_results_dir = self.results_dir / "frontend"
        frontend_results_dir.mkdir(exist_ok=True)

        files_to_copy = [
            "coverage/",
            "test-results.json"
        ]

        for file_pattern in files_to_copy:
            source = self.frontend_dir / file_pattern
            if source.exists():
                dest = frontend_results_dir / source.name
                if source.is_dir():
                    import shutil
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(source, dest)
                else:
                    import shutil
                    shutil.copy2(source, dest)

    def _generate_summary_report(self, results: Dict[str, Any]):
        """生成汇总报告"""
        summary = {
            "execution_id": results["execution_id"],
            "start_time": results["start_time"],
            "end_time": results["end_time"],
            "total_duration": results["total_duration"],
            "status": "unknown",
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0,
            "overall_coverage": 0.0,
            "backend_status": "skipped",
            "frontend_status": "skipped"
        }

        # 汇总结果
        if "backend" in results:
            backend = results["backend"]
            summary["total_tests"] += backend.get("tests", 0)
            summary["passed_tests"] += backend.get("passed", 0)
            summary["failed_tests"] += backend.get("failed", 0)
            summary["skipped_tests"] += backend.get("skipped", 0)
            summary["backend_status"] = backend.get("status", "unknown")

        if "frontend" in results:
            frontend = results["frontend"]
            summary["total_tests"] += frontend.get("tests", 0)
            summary["passed_tests"] += frontend.get("passed", 0)
            summary["failed_tests"] += frontend.get("failed", 0)
            summary["skipped_tests"] += frontend.get("skipped", 0)
            summary["frontend_status"] = frontend.get("status", "unknown")

        # 计算总体状态
        if summary["failed_tests"] > 0:
            summary["status"] = "failed"
        elif summary["passed_tests"] > 0:
            summary["status"] = "passed"
        else:
            summary["status"] = "unknown"

        # 计算总体覆盖率（加权平均）
        backend_cov = results.get("backend", {}).get("coverage", 0)
        frontend_cov = results.get("frontend", {}).get("coverage", 0)

        if backend_cov > 0 or frontend_cov > 0:
            summary["overall_coverage"] = (backend_cov * 0.6) + (frontend_cov * 0.4)

        results["summary"] = summary

    def _save_results(self, results: Dict[str, Any]):
        """保存测试结果"""
        try:
            with open(self.report_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            print(f"📄 测试报告已保存: {self.report_file}")

            # 生成可读报告
            self._generate_readable_report(results)
        except Exception as e:
            print(f"❌ 保存测试结果失败: {e}")

    def _generate_readable_report(self, results: Dict[str, Any]):
        """生成可读的测试报告"""
        report_file = self.results_dir / "test-report.md"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("# 测试执行报告\n\n")
                f.write(f"**执行ID**: {results['execution_id']}\n")
                f.write(f"**开始时间**: {results['start_time']}\n")
                f.write(f"**结束时间**: {results['end_time']}\n")
                f.write(f"**总耗时**: {results['total_duration']:.2f}秒\n\n")

                summary = results.get("summary", {})
                f.write("## 执行摘要\n\n")
                f.write(f"- **总体状态**: {summary.get('status', 'unknown')}\n")
                f.write(f"- **总测试数**: {summary.get('total_tests', 0)}\n")
                f.write(f"- **通过**: {summary.get('passed_tests', 0)}\n")
                f.write(f"- **失败**: {summary.get('failed_tests', 0)}\n")
                f.write(f"- **跳过**: {summary.get('skipped_tests', 0)}\n")
                f.write(f"- **总体覆盖率**: {summary.get('overall_coverage', 0):.1f}%\n\n")

                # 后端结果
                if "backend" in results:
                    f.write("## 后端测试结果\n\n")
                    backend = results["backend"]
                    f.write(f"- **状态**: {backend.get('status', 'unknown')}\n")
                    f.write(f"- **测试数**: {backend.get('tests', 0)}\n")
                    f.write(f"- **执行时间**: {backend.get('duration', 0):.2f}秒\n")
                    f.write(f"- **覆盖率**: {backend.get('coverage', 0):.1f}%\n\n")

                # 前端结果
                if "frontend" in results:
                    f.write("## 前端测试结果\n\n")
                    frontend = results["frontend"]
                    f.write(f"- **状态**: {frontend.get('status', 'unknown')}\n")
                    f.write(f"- **测试数**: {frontend.get('tests', 0)}\n")
                    f.write(f"- **执行时间**: {frontend.get('duration', 0):.2f}秒\n")
                    f.write(f"- **覆盖率**: {frontend.get('coverage', 0):.1f}%\n\n")

                f.write("---\n")
                f.write(f"*报告生成时间: {datetime.now().isoformat()}*\n")

            print(f"📄 可读报告已生成: {report_file}")
        except Exception as e:
            print(f"❌ 生成可读报告失败: {e}")

    def _generate_execution_id(self) -> str:
        """生成执行ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        return f"TEST_{timestamp}_{unique_id}"

    def cleanup_test_artifacts(self):
        """清理测试产物"""
        print("🧹 清理测试产物...")

        artifacts = [
            self.backend_dir / ".coverage",
            self.backend_dir / "htmlcov",
            self.backend_dir / "coverage.xml",
            self.frontend_dir / "coverage",
            self.frontend_dir / "test-results.json"
        ]

        for artifact in artifacts:
            try:
                if artifact.exists():
                    if artifact.is_dir():
                        import shutil
                        shutil.rmtree(artifact)
                    else:
                        artifact.unlink()
                    print(f"  ✅ 删除: {artifact}")
            except Exception as e:
                print(f"  ❌ 删除失败 {artifact}: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="地产资产管理系统统一测试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 运行所有测试
  python scripts/test-runner.py

  # 只运行后端测试
  python scripts/test-runner.py --backend-only

  # 只运行前端测试
  python scripts/test-runner.py --frontend-only

  # 运行特定测试
  python scripts/test-runner.py --backend-only --test tests/test_api.py

  # 生成覆盖率报告但不运行测试
  python scripts/test-runner.py --no-run --coverage-only

  # 清理测试产物
  python scripts/test-runner.py --cleanup
        """
    )

    # 测试选择选项
    parser.add_argument("--backend-only", action="store_true",
                       help="只运行后端测试")
    parser.add_argument("--frontend-only", action="store_true",
                       help="只运行前端测试")
    parser.add_argument("--test", type=str,
                       help="运行特定的测试文件或测试函数")

    # 执行选项
    parser.add_argument("--no-parallel", action="store_true",
                       help="不并行执行测试")
    parser.add_argument("--no-coverage", action="store_true",
                       help="不生成覆盖率报告")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="详细输出")

    # 报告选项
    parser.add_argument("--coverage-only", action="store_true",
                       help="只生成覆盖率报告，不运行测试")
    parser.add_argument("--cleanup", action="store_true",
                       help="清理测试产物")

    # 输出选项
    parser.add_argument("--output-dir", type=str,
                       help="指定结果输出目录")

    args = parser.parse_args()

    runner = TestRunner()

    if args.cleanup:
        runner.cleanup_test_artifacts()
        return 0

    if args.output_dir:
        runner.results_dir = Path(args.output_dir)
        runner.report_file = runner.results_dir / "test-report.json"

    backend = not args.frontend_only
    frontend = not args.backend_only
    parallel = not args.no_parallel
    coverage = not args.no_coverage

    if args.coverage_only:
        print("📊 只生成覆盖率报告...")
        # 这里可以添加只生成覆盖率报告的逻辑
        return 0

    try:
        results = runner.run_all_tests(
            backend=backend,
            frontend=frontend,
            parallel=parallel,
            coverage=coverage,
            verbose=args.verbose
        )

        # 根据测试结果设置退出码
        summary = results.get("summary", {})
        if summary.get("status") == "failed":
            return 1
        elif summary.get("status") == "error":
            return 2
        else:
            return 0

    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        return 130
    except Exception as e:
        print(f"❌ 测试运行失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())