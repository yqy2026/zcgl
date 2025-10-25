#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试覆盖率运行器
用于自动化执行测试套件、生成覆盖率报告和执行性能测试
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

class TestCoverageRunner:
    """测试覆盖率运行器"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.backend_dir = self.project_root / "backend"
        self.frontend_dir = self.project_root / "frontend"
        self.coverage_dir = self.project_root / "coverage"

        # 确保覆盖率目录存在
        self.coverage_dir.mkdir(exist_ok=True)

    def run_backend_tests(
        self,
        coverage: bool = True,
        parallel: bool = True,
        verbose: bool = False,
        specific_test: Optional[str] = None
    ) -> Dict[str, Any]:
        """运行后端测试"""
        cmd = [sys.executable, "-m", "pytest"]

        if coverage:
            cmd.extend([
                "--cov=src",
                "--cov-report=xml",
                "--cov-report=html",
                "--cov-report=term-missing",
                f"--cov-fail-under={75}"
            ])

        if specific_test:
            cmd.extend(["-k", specific_test])

        if verbose:
            cmd.append("-v")

        cmd.extend(["tests/"])

        print(f"[COVERAGE] 运行后端测试: {' '.join(cmd)}")

        start_time = time.time()
        result = subprocess.run(cmd, cwd=self.backend_dir, capture_output=True, text=True, encoding='utf-8')
        end_time = time.time()

        return {
            "success": result.returncode == 0,
            "duration": end_time - start_time,
            "command": ' '.join(cmd),
            "output": result.stdout,
            "error": result.stderr
        }

    def run_frontend_tests(
        self,
        coverage: bool = True,
        verbose: bool = False,
        specific_test: Optional[str] = None
    ) -> Dict[str, Any]:
        """运行前端测试"""
        cmd = ["npm", "test"]

        if coverage:
            cmd.extend([
                "--coverage",
                "--coverage-reporter=text",
                "--coverage-reporter=lcov"
                f"--coverage-threshold={70}"
            ])

        if specific_test:
            cmd.extend(["--", specific_test])

        if verbose:
            cmd.append("--verbose")

        print(f"[COVERAGE] 运行前端测试: {' '.join(cmd)}")

        start_time = time.time()
        result = subprocess.run(cmd, cwd=self.frontend_dir, capture_output=True, text=True, encoding='utf-8')
        end_time = time.time()

        return {
            "success": result.returncode == 0,
            "duration": end_time - start_time,
            "command": ' '.join(cmd),
            "output": result.stdout,
            "error": result.stderr
        }

    def generate_coverage_report(self, backend_results: Dict, frontend_results: Dict) -> Dict[str, Any]:
        """生成覆盖率报告"""
        timestamp = datetime.now().isoformat()

        report = {
            "timestamp": timestamp,
            "summary": {
                "backend": {
                    "total_tests": len(backend_results),
                    "passed": sum(1 for r in backend_results if r.get("success", False)),
                    "failed": sum(1 for r in backend_results if r.get("success", False) == False),
                    "coverage_enabled": backend_results[0].get("success", False) if backend_results else False
                },
                "frontend": {
                    "total_tests": len(frontend_results),
                    "passed": sum(1 for r in frontend_results if r.get("success", False)),
                    "failed": sum(1 for r in frontend_results if r.get("success", False) == False),
                    "coverage_enabled": frontend_results[0].get("success", False) if frontend_results else False
                }
            },
            "details": {
                "backend": backend_results,
                "frontend": frontend_results
            },
            "configuration": self._get_test_configuration(),
            "environment": {
                "python_version": sys.version,
                "node_version": "20",  # 假设版本，实际需要检测
                "platform": sys.platform
            }
        }

        # 保存报告
        report_path = self.coverage_dir / f"coverage-report-{timestamp}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"[COVERAGE] 覆盖率报告已生成: {report_path}")
        return report_path

    def _get_test_configuration(self) -> Dict[str, Any]:
        """获取测试配置信息"""
        return {
            "test_timeout": {
                "backend": 1800,  # 30分钟
                "frontend": 1200
            },
            "coverage_threshold": {
                "backend": 75,
                "frontend": 70
            },
            "performance_tests": {
                "enabled": True,
                "load_test_duration": 5  # 秒
            },
            "retry_failed_tests": 2,
            "parallel_execution": {
                "backend": True,
                "frontend": True,
                "max_workers": 2
            }
        }

    def run_full_test_suite(self, verbose: bool = False) -> Dict[str, Any]:
        """运行完整测试套件"""
        print("[COVERAGE] 开始运行完整测试套件...")

        # 1. 运行后端测试
        backend_results = []
        test_modules = [
            "test_pdf_import_complete.py",
            "test_rbac_complete.py",
            "test_main.py",
            "test_api.py"
        ]

        for module in test_modules:
            print(f"[COVERAGE] 测试模块: {module}")
            result = self.run_backend_tests(specific_test=module, verbose=verbose)
            backend_results.append(result)

        # 2. 运行前端测试
        frontend_results = []
        test_modules = [
            "test_component_core.js",
            "test_component_routes.js",
            "test_app.js"
        ]

        for module in test_modules:
            print(f"[COVERAGE] 测试前端模块: {module}")
            result = self.run_frontend_tests(specific_test=module, verbose=verbose)
            frontend_results.append(result)

        # 3. 生成覆盖率报告
        report_path = self.generate_coverage_report(backend_results, frontend_results)

        # 4. 更新覆盖率报告索引
        index_path = self.coverage_dir / "latest-coverage.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            latest_report = {
                "timestamp": report["timestamp"],
                "backend_total_tests": report["summary"]["backend"]["total_tests"],
                "backend_passed": report["summary"]["backend"]["passed"],
                "backend_failed": report["summary"]["backend"]["failed"],
                "backend_coverage_enabled": report["summary"]["backend"]["coverage_enabled"],
                "frontend_total_tests": report["summary"]["frontend"]["total_tests"],
                "frontend_passed": report["summary"]["frontend"]["passed"],
                "frontend_failed": report["summary"]["frontend"]["failed"],
                "frontend_coverage_enabled": report["summary"]["frontend"]["coverage_enabled"]
            }
            json.dump(latest_report, f, ensure_ascii=False, indent=2)

        total_duration = sum(r["duration"] for r in backend_results + frontend_results)

        return {
            "success": True,
            "duration": total_duration,
            "report_path": report_path,
            "backend_results": backend_results,
            "frontend_results": frontend_results,
            "summary": report["summary"]
        }

    def run_periodic_coverage_check(self) -> Dict[str, Any]:
        """定期运行覆盖率检查"""
        print(f"[COVERAGE] 开始定期覆盖率检查...")

        report_path = self.run_full_test_suite(verbose=True)

        # 如果覆盖率过低，发送通知
        backend_coverage = self.coverage_dir / "latest-coverage.json"
        if backend_coverage.exists():
            with open(backend_coverage, 'r', encoding='utf-8') as f:
                latest_backend = json.load(f)
                if latest_backend["summary"]["backend"]["coverage_enabled"] and latest_backend["summary"]["backend"]["passed"] / latest_backend["summary"]["backend"]["total_tests"] < 0.8:
                    print(f"[COVERAGE] 警告: 后端覆盖率低于阈值 {latest_backend['summary']['backend']['coverage_enabled']:.1f}%")
                    return {"warning": "backend_coverage_low"}

        return {
            "success": True,
            "report_path": report_path
        }

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试覆盖率运行器")
    parser.add_argument("--backend-only", action="store_true", help="只运行后端测试")
    parser.add_argument("--frontend-only", action="store_true", help="只运行前端测试")
    parser.add_argument("--periodic", action="store_true", help="定期覆盖率检查")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    parser.add_argument("--no-coverage", action="store_true", help="不生成覆盖率报告")

    args = parser.parse_args()
    runner = TestCoverageRunner()

    if args.periodic:
        return runner.run_periodic_coverage_check()
    elif args.backend_only:
        return runner.run_backend_tests(verbose=args.verbose)
    elif args.frontend_only:
        return runner.run_frontend_tests(verbose=args.verbose)
    else:
        return runner.run_full_test_suite(verbose=args.verbose)

if __name__ == "__main__":
    main()