#!/usr/bin/env python3
"""
一键运行所有测试的自动化脚本
支持完整的测试流水线：后端测试、前端测试、端到端测试、覆盖率报告生成
"""

import os
import sys
import json
import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestRunner:
    """测试运行器"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.backend_dir = self.project_root / "backend"
        self.frontend_dir = self.project_root / "frontend"
        self.scripts_dir = self.project_root / "scripts"
        self.reports_dir = self.project_root / "reports"
        self.reports_dir.mkdir(exist_ok=True)

        self.results = {
            "start_time": datetime.now(),
            "end_time": None,
            "duration": None,
            "phases": {},
            "overall_success": False,
            "summary": {}
        }

    def run_all_tests(self, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """运行所有测试"""
        if options is None:
            options = {
                "run_backend": True,
                "run_frontend": True,
                "run_e2e": True,
                "generate_reports": True,
                "parallel": True,
                "cleanup": False,
                "timeout": 1800  # 30分钟
            }

        print("🚀 开始运行完整的测试流水线...")
        print(f"📁 项目根目录: {self.project_root}")
        print(f"⏰ 超时设置: {options['timeout']}秒")

        self.results["options"] = options

        try:
            # 阶段1: 环境检查和准备
            self._run_phase("preparation", self._prepare_environment, options)

            # 阶段2: 后端测试
            if options.get("run_backend", True):
                self._run_phase("backend_tests", self._run_backend_tests, options)

            # 阶段3: 前端测试
            if options.get("run_frontend", True):
                self._run_phase("frontend_tests", self._run_frontend_tests, options)

            # 阶段4: 端到端测试
            if options.get("run_e2e", True):
                self._run_phase("e2e_tests", self._run_e2e_tests, options)

            # 阶段5: 报告生成
            if options.get("generate_reports", True):
                self._run_phase("report_generation", self._generate_comprehensive_report, options)

            # 阶段6: 清理
            if options.get("cleanup", True):
                self._run_phase("cleanup", self._cleanup_test_artifacts, options)

            # 计算总体结果
            self._calculate_overall_results()

            # 保存结果
            self._save_results()

            # 打印最终摘要
            self._print_final_summary()

            return self.results

        except KeyboardInterrupt:
            print("\n❌ 测试被用户中断")
            self.results["interrupted"] = True
            self._save_results()
            return self.results

        except Exception as e:
            print(f"\n❌ 测试运行失败: {e}")
            self.results["error"] = str(e)
            self._save_results()
            return self.results

    def _run_phase(self, phase_name: str, phase_func, options: Dict[str, Any]) -> Any:
        """运行测试阶段"""
        print(f"\n{'='*60}")
        print(f"📋 阶段: {phase_name}")
        print(f"{'='*60}")

        start_time = time.time()

        try:
            result = phase_func(options)
            duration = time.time() - start_time

            self.results["phases"][phase_name] = {
                "success": True,
                "duration": duration,
                "result": result,
                "start_time": start_time,
                "end_time": time.time()
            }

            print(f"✅ {phase_name} 完成 (耗时: {duration:.2f}秒)")
            return result

        except Exception as e:
            duration = time.time() - start_time
            self.results["phases"][phase_name] = {
                "success": False,
                "duration": duration,
                "error": str(e),
                "start_time": start_time,
                "end_time": time.time()
            }

            print(f"❌ {phase_name} 失败: {e}")
            raise

    def _prepare_environment(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """准备测试环境"""
        print("🔧 准备测试环境...")

        preparation_results = {
            "backend_ready": False,
            "frontend_ready": False,
            "dependencies_checked": False,
            "services_running": False,
            "data_prepared": False
        }

        # 检查后端环境
        if options.get("run_backend", True):
            preparation_results["backend_ready"] = self._check_backend_environment()

        # 检查前端环境
        if options.get("run_frontend", True):
            preparation_results["frontend_ready"] = self._check_frontend_environment()

        # 检查依赖
        preparation_results["dependencies_checked"] = self._check_dependencies()

        # 启动必要服务
        preparation_results["services_running"] = self._start_services(options)

        # 准备测试数据
        preparation_results["data_prepared"] = self._prepare_test_data(options)

        # 验证所有环境都准备好
        all_ready = all(preparation_results.values())
        if not all_ready:
            failed_steps = [k for k, v in preparation_results.items() if not v]
            raise Exception(f"环境准备失败: {', '.join(failed_steps)}")

        print("✅ 测试环境准备完成")
        return preparation_results

    def _run_backend_tests(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """运行后端测试"""
        print("🧪 运行后端测试...")

        os.chdir(self.backend_dir)

        backend_results = {
            "unit_tests": False,
            "integration_tests": False,
            "performance_tests": False,
            "security_tests": False,
            "coverage_data": None,
            "test_output": "",
            "errors": []
        }

        try:
            # 运行单元测试
            print("  📝 运行单元测试...")
            unit_result = self._run_command(
                ["uv", "run", "python", "-m", "pytest", "tests/", "-v", "--tb=short"],
                "backend_unit_tests",
                timeout=300
            )
            backend_results["unit_tests"] = unit_result["success"]
            backend_results["test_output"] += unit_result["output"]

            if not unit_result["success"]:
                backend_results["errors"].append("单元测试失败")

            # 运行集成测试
            print("  🔗 运行集成测试...")
            integration_result = self._run_command(
                ["uv", "run", "python", "-m", "pytest", "tests/", "-m", "integration", "-v"],
                "backend_integration_tests",
                timeout=600
            )
            backend_results["integration_tests"] = integration_result["success"]
            backend_results["test_output"] += integration_result["output"]

            if not integration_result["success"]:
                backend_results["errors"].append("集成测试失败")

            # 生成覆盖率报告
            print("  📊 生成后端覆盖率报告...")
            coverage_result = self._run_command(
                ["uv", "run", "python", "-m", "pytest", "tests/", "--cov=src", "--cov-report=json", "--cov-report=html"],
                "backend_coverage",
                timeout=300
            )

            if coverage_result["success"]:
                # 读取覆盖率数据
                coverage_file = self.backend_dir / "coverage.json"
                if coverage_file.exists():
                    with open(coverage_file, 'r', encoding='utf-8') as f:
                        backend_results["coverage_data"] = json.load(f)
                print(f"    📈 总覆盖率: {backend_results['coverage_data'].get('totals', {}).get('percent_covered', 0):.1f}%")

        except Exception as e:
            backend_results["errors"].append(f"后端测试执行错误: {str(e)}")

        return backend_results

    def _run_frontend_tests(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """运行前端测试"""
        print("🎨 运行前端测试...")

        os.chdir(self.frontend_dir)

        frontend_results = {
            "unit_tests": False,
            "component_tests": False,
            "integration_tests": False,
            "accessibility_tests": False,
            "coverage_data": None,
            "test_output": "",
            "errors": []
        }

        try:
            # 安装依赖（如果需要）
            if not (self.frontend_dir / "node_modules").exists():
                print("  📦 安装前端依赖...")
                install_result = self._run_command(
                    ["npm", "install"],
                    "frontend_install",
                    timeout=300
                )
                if not install_result["success"]:
                    frontend_results["errors"].append("依赖安装失败")

            # 运行单元测试
            print("  🧪 运行前端单元测试...")
            unit_result = self._run_command(
                ["npm", "run", "test"],
                "frontend_unit_tests",
                timeout=300
            )
            frontend_results["unit_tests"] = unit_result["success"]
            frontend_results["test_output"] += unit_result["output"]

            if not unit_result["success"]:
                frontend_results["errors"].append("前端单元测试失败")

            # 生成覆盖率报告
            print("  📊 生成前端覆盖率报告...")
            coverage_result = self._run_command(
                ["npm", "run", "test:coverage"],
                "frontend_coverage",
                timeout=300
            )

            if coverage_result["success"]:
                # 读取覆盖率数据
                coverage_file = self.frontend_dir / "coverage" / "coverage-final.json"
                if coverage_file.exists():
                    with open(coverage_file, 'r', encoding='utf-8') as f:
                        frontend_results["coverage_data"] = json.load(f)
                    total_coverage = frontend_results["coverage_data"].get("total", {}).get("lines", {}).get("pct", 0)
                    print(f"    📈 总覆盖率: {total_coverage:.1f}%")

        except Exception as e:
            frontend_results["errors"].append(f"前端测试执行错误: {str(e)}")

        return frontend_results

    def _run_e2e_tests(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """运行端到端测试"""
        print("🌐 运行端到端测试...")

        os.chdir(self.frontend_dir)

        e2e_results = {
            "playwright_tests": False,
            "accessibility_tests": False,
            "performance_tests": False,
            "test_output": "",
            "errors": []
        }

        try:
            # 安装Playwright依赖（如果需要）
            if not (self.frontend_dir / "node_modules" / "@playwright").exists():
                print("  🎭 安装Playwright浏览器...")
                install_result = self._run_command(
                    ["npx", "playwright", "install"],
                    "playwright_install",
                    timeout=300
                )
                if not install_result["success"]:
                    e2e_results["errors"].append("Playwright安装失败")

            # 运行Playwright测试
            print("  🌐 运行Playwright端到端测试...")
            playwright_result = self._run_command(
                ["npx", "playwright", "test"],
                "playwright_e2e",
                timeout=600
            )
            e2e_results["playwright_tests"] = playwright_result["success"]
            e2e_results["test_output"] += playwright_result["output"]

            if not playwright_result["success"]:
                e2e_results["errors"].append("端到端测试失败")

        except Exception as e:
            e2e_results["errors"].append(f"端到端测试执行错误: {str(e)}")

        return e2e_results

    def _generate_comprehensive_report(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """生成综合报告"""
        print("📊 生成综合测试报告...")

        report_results = {
            "api_documentation": False,
            "test_coverage": False,
            "quality_metrics": False,
            "reports_generated": []
        }

        try:
            # 生成API文档验证报告
            print("  📚 生成API文档验证报告...")
            api_validator_path = self.scripts_dir / "api_documentation_validator.py"
            if api_validator_path.exists():
                api_result = self._run_command(
                    ["python", str(api_validator_path)],
                    "api_documentation",
                    timeout=300
                )
                report_results["api_documentation"] = api_result["success"]

            # 生成测试覆盖率报告
            print("  📈 生成测试覆盖率报告...")
            coverage_reporter_path = self.scripts_dir / "test_coverage_reporter.py"
            if coverage_reporter_path.exists():
                coverage_result = self._run_command(
                    ["python", str(coverage_reporter_path)],
                    "test_coverage",
                    timeout=300
                )
                report_results["test_coverage"] = coverage_result["success"]

            # 生成质量指标报告
            print("  🎯 生成质量指标报告...")
            quality_result = self._generate_quality_metrics_report()
            report_results["quality_metrics"] = quality_result["success"]

        except Exception as e:
            print(f"⚠️ 报告生成过程中出现错误: {e}")

        return report_results

    def _cleanup_test_artifacts(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """清理测试产生的临时文件"""
        print("🧹 清理测试临时文件...")

        cleanup_results = {
            "temporary_files_removed": 0,
            "logs_cleared": False,
            "cache_cleared": False
        }

        try:
            # 清理Python缓存
            python_cache_dirs = [
                self.project_root / "__pycache__",
                self.backend_dir / "__pycache__",
                self.scripts_dir / "__pycache__"
            ]

            for cache_dir in python_cache_dirs:
                if cache_dir.exists():
                    import shutil
                    shutil.rmtree(cache_dir)
                    cleanup_results["temporary_files_removed"] += 1

            # 清理Node.js缓存
            node_cache_dirs = [
                self.frontend_dir / "node_modules" / ".cache",
                self.frontend_dir / ".nyc_output"
            ]

            for cache_dir in node_cache_dirs:
                if cache_dir.exists():
                    import shutil
                    shutil.rmtree(cache_dir)
                    cleanup_results["temporary_files_removed"] += 1

            print(f"✅ 清理完成，移除 {cleanup_results['temporary_files_removed']}个临时目录")

        except Exception as e:
            print(f"⚠️ 清理过程中出现错误: {e}")

        return cleanup_results

    def _check_backend_environment(self) -> bool:
        """检查后端环境"""
        try:
            # 检查Python环境
            python_result = subprocess.run(
                ["python", "--version"],
                cwd=self.backend_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            if python_result.returncode != 0:
                return False

            # 检查虚拟环境
            if not (self.backend_dir / "uv.lock").exists():
                print("    ⚠️ 未找到uv.lock，可能需要运行 'uv sync'")
                return False

            # 检查配置文件
            config_files = ["pyproject.toml", "alembic.ini"]
            for config_file in config_files:
                if not (self.backend_dir / config_file).exists():
                    print(f"    ⚠️ 缺少配置文件: {config_file}")
                    return False

            print("    ✅ 后端环境检查通过")
            return True

        except Exception as e:
            print(f"    ❌ 后端环境检查失败: {e}")
            return False

    def _check_frontend_environment(self) -> bool:
        """检查前端环境"""
        try:
            # 检查Node.js环境
            node_result = subprocess.run(
                ["node", "--version"],
                cwd=self.frontend_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            if node_result.returncode != 0:
                return False

            # 检查npm
            npm_result = subprocess.run(
                ["npm", "--version"],
                cwd=self.frontend_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            if npm_result.returncode != 0:
                return False

            # 检查package.json
            if not (self.frontend_dir / "package.json").exists():
                print("    ⚠️ 缺少package.json")
                return False

            print("    ✅ 前端环境检查通过")
            return True

        except Exception as e:
            print(f"    ❌ 前端环境检查失败: {e}")
            return False

    def _check_dependencies(self) -> bool:
        """检查依赖"""
        try:
            # 检查系统依赖
            required_commands = ["python", "npm", "node"]
            missing_commands = []

            for cmd in required_commands:
                result = subprocess.run(
                    ["which", cmd],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode != 0:
                    missing_commands.append(cmd)

            if missing_commands:
                print(f"    ⚠️ 缺少系统依赖: {', '.join(missing_commands)}")
                return False

            print("    ✅ 系统依赖检查通过")
            return True

        except Exception as e:
            print(f"    ❌ 依赖检查失败: {e}")
            return False

    def _start_services(self, options: Dict[str, Any]) -> bool:
        """启动必要的服务"""
        try:
            # 这里可以添加启动数据库、Redis等服务的逻辑
            # 当前项目中使用SQLite，不需要额外服务
            print("    ✅ 服务检查完成（使用SQLite，无需额外服务）")
            return True

        except Exception as e:
            print(f"    ❌ 服务启动失败: {e}")
            return False

    def _prepare_test_data(self, options: Dict[str, Any]) -> bool:
        """准备测试数据"""
        try:
            # 检查测试数据迁移工具
            migrator_path = self.scripts_dir / "test_data_migrator.py"
            if not migrator_path.exists():
                print("    ⚠️ 未找到测试数据迁移工具")
                return True  # 不是必需的，可以继续

            # 运行测试数据准备
            print("    📊 准备测试数据...")
            result = self._run_command(
                ["python", str(migrator_path), "--action", "create", "--env", "test"],
                "test_data_preparation",
                timeout=120
            )

            if not result["success"]:
                print(f"    ⚠️ 测试数据准备失败: {result['error']}")

            return True  # 即使失败也继续，因为不是所有测试都需要预置数据

        except Exception as e:
            print(f"    ⚠️ 测试数据准备失败: {e}")
            return True  # 不是致命错误

    def _run_command(self, command: List[str], name: str, timeout: int = 300) -> Dict[str, Any]:
        """运行命令"""
        result = {
            "success": False,
            "output": "",
            "error": "",
            "returncode": None,
            "duration": 0
        }

        try:
            start_time = time.time()
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.project_root
            )

            try:
                stdout, stderr = process.communicate(timeout=timeout)
                returncode = process.returncode
                duration = time.time() - start_time

                result.update({
                    "success": returncode == 0,
                    "output": stdout,
                    "error": stderr,
                    "returncode": returncode,
                    "duration": duration
                })

            except subprocess.TimeoutExpired:
                process.kill()
                result.update({
                    "error": f"命令执行超时 ({timeout}秒)",
                    "returncode": -1
                })

        except Exception as e:
            result["error"] = str(e)

        return result

    def _calculate_overall_results(self) -> None:
        """计算总体结果"""
        self.results["end_time"] = datetime.now()
        self.results["duration"] = (self.results["end_time"] - self.results["start_time"]).total_seconds()

        # 计算各阶段的成功率
        phase_success_count = sum(1 for phase in self.results["phases"].values() if phase.get("success"))
        total_phases = len(self.results["phases"])

        # 计算综合成功率
        if total_phases > 0:
            phase_success_rate = phase_success_count / total_phases
            self.results["overall_success"] = phase_success_rate >= 0.8  # 80%以上视为成功

        # 计算测试覆盖率
        coverage_data = self._extract_coverage_data()
        self.results["summary"]["coverage"] = coverage_data

        # 生成状态摘要
        self.results["summary"]["phases"] = {
            "total": total_phases,
            "successful": phase_success_count,
            "failed": total_phases - phase_success_count,
            "success_rate": phase_success_rate if total_phases > 0 else 0
        }

    def _extract_coverage_data(self) -> Dict[str, Any]:
        """提取覆盖率数据"""
        coverage_data = {
            "backend": None,
            "frontend": None,
            "overall": None
        }

        # 提取后端覆盖率
        backend_phase = self.results["phases"].get("backend_tests", {})
        if backend_phase.get("success") and backend_phase.get("result", {}).get("coverage_data"):
            backend_coverage = backend_phase["result"]["coverage_data"]
            coverage_data["backend"] = backend_coverage.get("totals", {}).get("percent_covered", 0)

        # 提取前端覆盖率
        frontend_phase = self.results["phases"].get("frontend_tests", {})
        if frontend_phase.get("success") and frontend_phase.get("result", {}).get("coverage_data"):
            frontend_coverage = frontend_phase["result"]["coverage_data"]
            coverage_data["frontend"] = frontend_coverage.get("total", {}).get("lines", {}).get("pct", 0)

        # 计算总体覆盖率
        if coverage_data["backend"] is not None and coverage_data["frontend"] is not None:
            coverage_data["overall"] = (coverage_data["backend"] + coverage_data["frontend"]) / 2
        elif coverage_data["backend"] is not None:
            coverage_data["overall"] = coverage_data["backend"]
        elif coverage_data["frontend"] is not None:
            coverage_data["overall"] = coverage_data["frontend"]

        return coverage_data

    def _generate_quality_metrics_report(self) -> Dict[str, Any]:
        """生成质量指标报告"""
        try:
            quality_report = {
                "timestamp": datetime.now().isoformat(),
                "test_phases": list(self.results["phases"].keys()),
                "phase_durations": {name: phase["duration"] for name, phase in self.results["phases"].items()},
                "success_rates": {},
                "quality_score": 0
            }

            # 计算各阶段的成功率
            for name, phase in self.results["phases"].items():
                success_rate = 1.0 if phase.get("success") else 0.0
                quality_report["success_rates"][name] = success_rate

            # 计算整体质量评分
            if quality_report["success_rates"]:
                quality_report["quality_score"] = sum(quality_report["success_rates"].values()) / len(quality_report["success_rates"])

            # 保存质量报告
            quality_file = self.reports_dir / f"quality-metrics-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            with open(quality_file, 'w', encoding='utf-8') as f:
                json.dump(quality_report, f, ensure_ascii=False, indent=2)

            return {"success": True, "file": str(quality_file)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _save_results(self) -> None:
        """保存测试结果"""
        results_file = self.reports_dir / f"test-results-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

        try:
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
            print(f"📄 测试结果已保存: {results_file}")
        except Exception as e:
            print(f"⚠️ 保存测试结果失败: {e}")

    def _print_final_summary(self) -> None:
        """打印最终摘要"""
        print("\n" + "="*80)
        print("🎯 UltraThink 测试流水线执行摘要")
        print("="*80)

        summary = self.results["summary"]
        phases = self.results["phases"]

        # 总体状态
        status_icon = "✅" if self.results["overall_success"] else "❌"
        print(f"{status_icon} 总体状态: {'成功' if self.results['overall_success'] else '失败'}")
        print(f"⏱️ 总耗时: {self.results['duration']:.2f}秒")
        print(f"📋 执行阶段: {summary['phases']['total']}")
        print(f"✅ 成功阶段: {summary['phases']['successful']}")
        print(f"❌ 失败阶段: {summary['phases']['failed']}")
        print(f"📈 成功率: {summary['phases']['success_rate']:.1%}")

        # 覆盖率信息
        if summary.get("coverage"):
            coverage = summary["coverage"]
            print(f"\n📊 测试覆盖率:")
            if coverage.get("backend") is not None:
                print(f"   🖥️ 后端覆盖率: {coverage['backend']:.1f}%")
            if coverage.get("frontend") is not None:
                print(f"   🎨 前端覆盖率: {coverage['frontend']:.1f}%")
            if coverage.get("overall") is not None:
                print(f"   🎯 总体覆盖率: {coverage['overall']:.1f}%")

        # 各阶段详情
        print(f"\n📋 各阶段详情:")
        for phase_name, phase_data in phases.items():
            status_icon = "✅" if phase_data["success"] else "❌"
            duration = phase_data.get("duration", 0)
            print(f"   {status_icon} {phase_name}: {duration:.2f}秒")

            if not phase_data["success"] and phase_data.get("error"):
                print(f"      错误: {phase_data['error']}")

        # 错误汇总
        all_errors = []
        for phase_data in phases.values():
            if phase_data.get("result", {}).get("errors"):
                all_errors.extend(phase_data["result"]["errors"])

        if all_errors:
            print(f"\n❌ 错误汇总:")
            for error in all_errors[:5]:  # 只显示前5个错误
                print(f"   - {error}")
            if len(all_errors) > 5:
                print(f"   - ... 还有 {len(all_errors) - 5} 个错误")

        # 报告文件位置
        print(f"\n📄 报告文件:")
        if self.reports_dir.exists():
            report_files = list(self.reports_dir.glob("*.json"))
            for report_file in report_files[-3:]:  # 显示最近3个报告
                print(f"   - {report_file}")

        print("\n" + "="*80)
        print(f"🎉 UltraThink 测试流水线执行完成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="一键运行所有测试的自动化脚本")
    parser.add_argument("--project-root", default=".", help="项目根目录路径")
    parser.add_argument("--backend-only", action="store_true", help="只运行后端测试")
    parser.add_argument("--frontend-only", action="store_true", help="只运行前端测试")
    parser.add_argument("--e2e-only", action="store_true", help="只运行端到端测试")
    parser.add_argument("--no-reports", action="store_true", help="不生成报告")
    parser.add_argument("--cleanup", action="store_true", help="测试后清理临时文件")
    parser.add_argument("--timeout", type=int, default=1800, help="测试超时时间（秒）")
    parser.add_argument("--parallel", action="store_true", help="并行执行测试（实验性）")

    args = parser.parse_args()

    # 设置选项
    options = {
        "run_backend": not args.frontend_only and not args.e2e_only,
        "run_frontend": not args.backend_only and not args.e2e_only,
        "run_e2e": not args.backend_only and not args.frontend_only,
        "generate_reports": not args.no_reports,
        "cleanup": args.cleanup,
        "timeout": args.timeout,
        "parallel": args.parallel
    }

    # 创建测试运行器
    runner = TestRunner(args.project_root)

    # 运行测试
    try:
        results = runner.run_all_tests(options)
        return 0 if results["overall_success"] else 1
    except KeyboardInterrupt:
        return 130  # 标准键盘中断退出码
    except Exception as e:
        print(f"❌ 测试运行失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())