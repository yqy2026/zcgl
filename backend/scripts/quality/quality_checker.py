#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基本质量检查工具
Basic Quality Checker

适用于所有环境的基础质量检查，不依赖外部工具
"""

import os
import sys
import ast
import time
import subprocess
from datetime import datetime
from pathlib import Path


class BasicQualityChecker:
    """基础质量检查器"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.src_dir = self.base_dir / "src"
        self.tests_dir = self.base_dir / "tests"

    def run_comprehensive_check(self):
        """运行综合质量检查"""
        print("=" * 60)
        print("COMPREHENSIVE QUALITY CHECK REPORT")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Project: {self.base_dir.name}")
        print()

        # 1. 项目结构检查
        structure_score = self._check_project_structure()

        # 2. 语法检查
        syntax_score = self._check_syntax_basic()

        # 3. 测试执行检查
        test_score = self._check_tests_executable()

        # 4. 文档检查
        doc_score = self._check_documentation()

        # 5. 配置文件检查
        config_score = self._check_configuration()

        # 计算总分
        scores = [structure_score, syntax_score, test_score, doc_score, config_score]
        overall_score = sum(scores) / len(scores)

        print("CHECK RESULTS:")
        print("-" * 40)
        print(f"Project Structure:   {structure_score}/100")
        print(f"Code Syntax:        {syntax_score}/100")
        print(f"Test Execution:     {test_score}/100")
        print(f"Documentation:       {doc_score}/100")
        print(f"Configuration:       {config_score}/100")
        print("-" * 40)
        print(f"OVERALL SCORE:       {overall_score:.1f}/100")
        print()

        # 质量等级
        if overall_score >= 90:
            grade = "A (Excellent)"
        elif overall_score >= 80:
            grade = "B (Good)"
        elif overall_score >= 70:
            grade = "C (Satisfactory)"
        elif overall_score >= 60:
            grade = "D (Needs Improvement)"
        else:
            grade = "F (Poor)"

        print(f"QUALITY GRADE:       {grade}")
        print("=" * 60)

        # 保存报告
        self._save_report(overall_score, grade, {
            'structure': structure_score,
            'syntax': syntax_score,
            'tests': test_score,
            'documentation': doc_score,
            'configuration': config_score
        })

        return overall_score

    def _check_project_structure(self):
        """检查项目结构"""
        print("Checking project structure...")

        required_dirs = ["src", "tests", "scripts"]
        required_files = [
            "src/main.py",
            "pyproject.toml",
            "README.md"
        ]

        score = 100
        missing_items = []

        # 检查目录
        for dir_name in required_dirs:
            dir_path = self.base_dir / dir_name
            if not dir_path.exists():
                missing_items.append(f"Directory: {dir_name}")
                score -= 15

        # 检查文件
        for file_path in required_files:
            full_path = self.base_dir / file_path
            if not full_path.exists():
                missing_items.append(f"File: {file_path}")
                score -= 10

        if missing_items:
            print(f"  Missing: {len(missing_items)} items")
            for item in missing_items:
                print(f"    - {item}")
        else:
            print("  All required structure present")

        return max(0, score)

    def _check_syntax_basic(self):
        """基础语法检查"""
        print("Checking Python syntax...")

        python_files = list(self.src_dir.rglob("*.py"))
        if not python_files:
            print("  No Python files found")
            return 0

        syntax_errors = 0
        total_files = len(python_files)

        for py_file in python_files[:10]:  # 检查前10个文件
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content)
            except SyntaxError as e:
                syntax_errors += 1
                print(f"    Syntax Error in {py_file.name}: {e}")
            except UnicodeDecodeError:
                print(f"    Encoding Error in {py_file.name}")
                syntax_errors += 1
            except Exception as e:
                print(f"    Error reading {py_file.name}: {e}")

        if syntax_errors == 0:
            print(f"  All {min(total_files, 10)} files have valid syntax")
        else:
            print(f"  Found {syntax_errors} syntax errors in {min(total_files, 10)} files")

        # 计算分数
        error_rate = syntax_errors / min(total_files, 10)
        score = max(0, 100 - (error_rate * 100))

        return score

    def _check_tests_executable(self):
        """检查测试是否可执行"""
        print("Checking test execution...")

        # 查找测试文件
        test_files = [
            self.tests_dir / "test_main.py",
            self.tests_dir / "test_quick_suite.py"
        ]

        executable_tests = 0
        total_tests = 0

        for test_file in test_files:
            if test_file.exists():
                total_tests += 1

                try:
                    start_time = time.time()
                    result = subprocess.run(
                        [sys.executable, "-m", "pytest", str(test_file), "-q", "--tb=no"],
                        capture_output=True,
                        text=True,
                        cwd=self.base_dir,
                        timeout=30
                    )
                    execution_time = time.time() - start_time

                    if result.returncode == 0:
                        executable_tests += 1
                        print(f"    {test_file.name}: PASSED ({execution_time:.1f}s)")
                    else:
                        print(f"    {test_file.name}: FAILED ({execution_time:.1f}s)")

                except subprocess.TimeoutExpired:
                    print(f"    {test_file.name}: TIMEOUT")
                except Exception as e:
                    print(f"    {test_file.name}: ERROR - {e}")

        if total_tests == 0:
            print("  No test files found")
            return 0

        success_rate = executable_tests / total_tests
        score = success_rate * 100

        print(f"  {executable_tests}/{total_tests} tests executable ({success_rate*100:.1f}%)")

        return score

    def _check_documentation(self):
        """检查文档"""
        print("Checking documentation...")

        doc_files = [
            "README.md",
            "CLAUDE.md"
        ]

        doc_count = 0
        for doc_file in doc_files:
            if (self.base_dir / doc_file).exists():
                doc_count += 1

        # 检查代码文档
        python_files = list(self.src_dir.rglob("*.py"))
        docstring_count = 0

        for py_file in python_files[:5]:  # 检查前5个文件
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '"""' in content or "'''" in content:
                        docstring_count += 1
            except:
                pass

        score = 0

        # 基础文档分数 (50%)
        if doc_count >= 2:
            score += 50
            print(f"  Basic documentation: {doc_count}/2 files found")
        else:
            print(f"  Basic documentation: {doc_count}/2 files found")

        # 代码文档分数 (50%)
        if docstring_count >= 3:
            score += 50
            print(f"  Code documentation: {docstring_count}/5 files have docstrings")
        else:
            print(f"  Code documentation: {docstring_count}/5 files have docstrings")

        return score

    def _check_configuration(self):
        """检查配置文件"""
        print("Checking configuration...")

        config_files = [
            "pyproject.toml",
            "alembic.ini",
            ".env.example"
        ]

        score = 100
        missing_configs = []

        for config_file in config_files:
            if (self.base_dir / config_file).exists():
                print(f"    Found: {config_file}")
            else:
                missing_configs.append(config_file)
                score -= 30

        if missing_configs:
            print(f"  Missing configuration: {len(missing_configs)} files")
            for config in missing_configs:
                print(f"    - {config}")
        else:
            print("  All configuration files present")

        return max(0, score)

    def _save_report(self, overall_score, grade, scores):
        """保存质量报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = self.base_dir / "reports"
        report_dir.mkdir(exist_ok=True)

        report_file = report_dir / f"quality_check_{timestamp}.txt"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("QUALITY CHECK REPORT\n")
                f.write("=" * 40 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Overall Score: {overall_score:.1f}/100\n")
                f.write(f"Quality Grade: {grade}\n\n")

                f.write("DETAILED RESULTS:\n")
                f.write("-" * 40 + "\n")

                f.write(f"Project Structure:   {scores['structure']}/100\n")
                f.write(f"Code Syntax:        {scores['syntax']}/100\n")
                f.write(f"Test Execution:     {scores['tests']}/100\n")
                f.write(f"Documentation:       {scores['documentation']}/100\n")
                f.write(f"Configuration:       {scores['configuration']}/100\n")
                f.write("-" * 40 + "\n")

                # 添加改进建议
                f.write("RECOMMENDATIONS:\n")
                f.write("-" * 40 + "\n")

                if scores['structure'] < 100:
                    f.write("- Ensure all required directories and files exist\n")
                if scores['syntax'] < 80:
                    f.write("- Fix syntax errors in Python files\n")
                if scores['tests'] < 80:
                    f.write("- Ensure tests are executable and passing\n")
                if scores['documentation'] < 70:
                    f.write("- Add missing documentation and docstrings\n")
                if scores['configuration'] < 80:
                    f.write("- Complete configuration files setup\n")

            print(f"\nReport saved: {report_file}")

        except Exception as e:
            print(f"Error saving report: {e}")


def main():
    """主函数"""
    checker = BasicQualityChecker()

    try:
        score = checker.run_comprehensive_check()

        # 根据分数设置退出代码
        if score >= 80:
            print("QUALITY CHECK: PASSED - Good quality")
            sys.exit(0)
        elif score >= 60:
            print("QUALITY CHECK: WARNING - Needs improvement")
            sys.exit(1)
        else:
            print("QUALITY CHECK: FAILED - Poor quality")
            sys.exit(2)

    except KeyboardInterrupt:
        print("\nQUALITY CHECK: CANCELLED")
        sys.exit(3)
    except Exception as e:
        print(f"\nQUALITY CHECK: ERROR - {e}")
        sys.exit(4)


if __name__ == "__main__":
    main()