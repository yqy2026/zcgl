#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地产资产管理系统 - 统一测试运行器
合并了简单测试运行器和测试覆盖报告功能
"""

import subprocess
import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

class UnifiedTestRunner:
    """统一测试运行器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.backend_dir = self.project_root / "backend"
        self.frontend_dir = self.project_root / "frontend"
        self.coverage_dir = self.project_root / "coverage"
        self.reports_dir = self.project_root / "docs" / "reports" / "test-results"

        # 确保目录存在
        self.coverage_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def run_command(self, cmd: list, cwd: Optional[Path] = None) -> Dict[str, Any]:
        """执行命令并返回结果"""
        try:
            print(f"[EXEC] Running: {' '.join(cmd)}")
            start_time = time.time()

            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )

            end_time = time.time()

            return {
                "success": result.returncode == 0,
                "duration": end_time - start_time,
                "command": ' '.join(cmd),
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {
                "success": False,
                "duration": 0,
                "command": ' '.join(cmd),
                "output": "",
                "error": str(e),
                "returncode": -1
            }

    def check_environment(self, component: str) -> bool:
        """检查运行环境"""
        print(f"\n[ENV] Checking {component} environment...")

        if component == "backend":
            # 检查Python环境
            result = self.run_command([sys.executable, "--version"])
            if not result["success"]:
                print("[ERROR] Python environment check failed")
                return False

            # 检查项目依赖
            result = self.run_command([sys.executable, "-m", "pip", "list"], cwd=self.backend_dir)
            if not result["success"]:
                print("[ERROR] Backend dependency check failed")
                return False

            # 检查pytest
            result = self.run_command([sys.executable, "-m", "pytest", "--version"], cwd=self.backend_dir)
            if not result["success"]:
                print("[ERROR] pytest not available in backend")
                return False

        elif component == "frontend":
            # 检查Node.js环境
            result = self.run_command(["node", "--version"], cwd=self.frontend_dir)
            if not result["success"]:
                print("[ERROR] Node.js not available")
                return False

            # 检查npm
            result = self.run_command(["npm", "--version"], cwd=self.frontend_dir)
            if not result["success"]:
                print("[ERROR] npm not available")
                return False

            # 检查package.json
            package_json = self.frontend_dir / "package.json"
            if not package_json.exists():
                print("[ERROR] package.json not found")
                return False

        print(f"[OK] {component} environment check passed")
        return True

    def run_backend_tests(self, coverage: bool = True, verbose: bool = True) -> Dict[str, Any]:
        """运行后端测试"""
        print("=" * 60)
        print("BACKEND TESTS")
        print("=" * 60)

        if not self.check_environment("backend"):
            return {"success": False, "error": "Environment check failed"}

        # 构建测试命令
        cmd = [sys.executable, "-m", "pytest", "tests/", "-v" if verbose else "-q"]

        if coverage:
            cmd.extend([
                "--cov=src",
                "--cov-report=term-missing",
                "--cov-report=html",
                "--cov-report=xml",
                "--cov-fail-under=60"
            ])
            print("[INFO] Coverage enabled")

        print(f"\n[TEST] Running backend tests...")
        result = self.run_command(cmd, cwd=self.backend_dir)

        if result["success"]:
            print("\n[SUCCESS] Backend tests completed successfully")
        else:
            print("\n[FAILED] Backend tests failed")

        return result

    def run_frontend_tests(self, coverage: bool = True) -> Dict[str, Any]:
        """运行前端测试"""
        print("=" * 60)
        print("FRONTEND TESTS")
        print("=" * 60)

        if not self.check_environment("frontend"):
            return {"success": False, "error": "Environment check failed"}

        # 安装依赖
        print("\n[INSTALL] Installing dependencies...")
        install_result = self.run_command(["npm", "install"], cwd=self.frontend_dir)
        if not install_result["success"]:
            print("[ERROR] npm install failed")
            return {"success": False, "error": "npm install failed"}

        # 构建测试命令
        cmd = ["npm", "test"]
        if coverage:
            cmd.append("-- --coverage")
            print("[INFO] Coverage enabled")

        print(f"\n[TEST] Running frontend tests...")
        result = self.run_command(cmd, cwd=self.frontend_dir)

        if result["success"]:
            print("\n[SUCCESS] Frontend tests completed successfully")
        else:
            print("\n[FAILED] Frontend tests failed")

        return result

    def generate_report(self, results: Dict[str, Dict[str, Any]], timestamp: str) -> str:
        """生成测试报告"""
        report = {
            "timestamp": timestamp,
            "project": "地产资产管理系统",
            "environment": {
                "python": sys.version,
                "platform": sys.platform
            },
            "results": {},
            "summary": {
                "total_components": len(results),
                "passed_components": sum(1 for r in results.values() if r["success"]),
                "failed_components": sum(1 for r in results.values() if not r["success"]),
                "overall_success": all(r["success"] for r in results.values()),
                "total_duration": sum(r["duration"] for r in results.values())
            }
        }

        for component, result in results.items():
            report["results"][component] = {
                "success": result["success"],
                "duration": result["duration"],
                "command": result["command"],
                "returncode": result["returncode"],
                "has_output": bool(result.get("output")),
                "has_error": bool(result.get("error"))
            }

        # 保存JSON报告
        report_path = self.reports_dir / f"test-report-{timestamp.replace(':', '-')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 生成Markdown报告
        md_path = self.reports_dir / f"test-report-{timestamp.replace(':', '-')}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# 地产资产管理系统 - 测试报告\n\n")
            f.write(f"**时间**: {timestamp}\n\n")
            f.write(f"## 总体状态: {'✅ PASSED' if report['summary']['overall_success'] else '❌ FAILED'}\n\n")

            f.write("### 测试组件结果\n\n")
            for component, result in results.items():
                status = "✅ PASSED" if result["success"] else "❌ FAILED"
                f.write(f"- **{component.upper()}**: {status} ({result['duration']:.2f}s)\n")

            f.write(f"\n### 统计信息\n\n")
            f.write(f"- 总组件数: {report['summary']['total_components']}\n")
            f.write(f"- 通过组件: {report['summary']['passed_components']}\n")
            f.write(f"- 失败组件: {report['summary']['failed_components']}\n")
            f.write(f"- 总耗时: {report['summary']['total_duration']:.2f}秒\n")

        return str(report_path)

    def run_all_tests(self, backend_only: bool = False, frontend_only: bool = False,
                     coverage: bool = True, verbose: bool = True) -> Dict[str, Any]:
        """运行所有测试"""
        print("地产资产管理系统 - 统一测试运行器")
        print("=" * 60)
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"项目根目录: {self.project_root}")

        results = {}
        timestamp = datetime.now().isoformat()

        # 运行后端测试
        if not frontend_only:
            results["backend"] = self.run_backend_tests(coverage=coverage, verbose=verbose)

        # 运行前端测试
        if not backend_only:
            results["frontend"] = self.run_frontend_tests(coverage=coverage)

        # 生成报告
        report_path = self.generate_report(results, timestamp)

        # 输出总结
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)

        for component, result in results.items():
            status = "PASS" if result["success"] else "FAIL"
            print(f"{component.upper()}: {status} ({result['duration']:.2f}s)")

        overall_success = all(results.values()) if results else False
        print(f"\n总体状态: {'PASSED' if overall_success else 'FAILED'}")
        print(f"报告路径: {report_path}")

        return {
            "success": overall_success,
            "results": results,
            "report_path": report_path
        }

def main():
    """主函数"""
    # 解析命令行参数
    backend_only = "--backend-only" in sys.argv
    frontend_only = "--frontend-only" in sys.argv
    no_coverage = "--no-coverage" in sys.argv
    quiet = "--quiet" in sys.argv or "-q" in sys.argv

    # 帮助信息
    if "--help" in sys.argv or "-h" in sys.argv:
        print("""
地产资产管理系统 - 统一测试运行器

用法:
    python unified_test_runner.py [选项]

选项:
    --backend-only    仅运行后端测试
    --frontend-only   仅运行前端测试
    --no-coverage     禁用覆盖率报告
    --quiet, -q       精简输出
    --help, -h        显示帮助信息

示例:
    python unified_test_runner.py                 # 运行所有测试
    python unified_test_runner.py --backend-only  # 仅运行后端测试
    python unified_test_runner.py --no-coverage   # 不生成覆盖率报告
        """)
        return 0

    runner = UnifiedTestRunner()
    result = runner.run_all_tests(
        backend_only=backend_only,
        frontend_only=frontend_only,
        coverage=not no_coverage,
        verbose=not quiet
    )

    return 0 if result["success"] else 1

if __name__ == "__main__":
    sys.exit(main())