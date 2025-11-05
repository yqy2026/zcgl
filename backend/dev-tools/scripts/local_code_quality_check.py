#!/usr/bin/env python3
"""
本地代码质量检查脚本
作为 pre-commit hooks 的本地替代方案
在每次提交前运行此脚本进行代码质量检查
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd, cwd=None):
    """运行命令并返回结果"""
    print(f"[执行] {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result.returncode == 0, result.stdout, result.stderr


class CodeQualityChecker:
    """代码质量检查器"""

    def __init__(self, project_root=None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.results = {}
        self.start_time = datetime.now()

    def check_ruff_issues(self):
        """检查 Ruff 问题"""
        print("\n" + "=" * 60)
        print("[Ruff] 代码质量检查")
        print("=" * 60)

        # 检查关键错误类型
        critical_checks = [
            ("F821", "未定义名称"),
            ("F811", "重复定义"),
            ("E722", "裸异常处理"),
            ("E402", "导入顺序"),
        ]

        results = {}

        for error_code, description in critical_checks:
            print(f"\n[检查] {description} ({error_code})")
            success, stdout, stderr = run_command(
                f"uv run ruff check src/ --select={error_code} --statistics"
            )

            if success or "Found 0 errors" in stdout:
                print(f"   [OK] 无 {description} 问题")
                results[error_code] = {"status": "PASS", "count": 0}
            else:
                # 提取错误数量
                count = 0
                for line in stdout.strip().split("\n"):
                    if "Found" in line and "errors" in line:
                        try:
                            count = int(line.split("Found")[1].split()[0])
                        except:
                            pass
                        break

                print(f"   [ISSUE] 发现 {count} 个 {description} 问题")
                results[error_code] = {"status": "ISSUES_FOUND", "count": count}

                # 显示前几个错误
                lines = stdout.strip().split("\n")[:5]
                for line in lines:
                    if error_code in line:
                        print(f"   示例: {line}")

        self.results["ruff"] = results
        return results

    def check_ruff_format(self):
        """检查代码格式"""
        print("\n" + "=" * 60)
        print("[Ruff Format] 代码格式检查")
        print("=" * 60)

        success, stdout, stderr = run_command("uv run ruff format --check src/")

        if success:
            print("[OK] 代码格式正确")
            self.results["format"] = {"status": "PASS"}
        else:
            print("[ISSUE] 发现格式问题")
            # 显示需要格式化的文件
            for line in stdout.strip().split("\n")[:10]:
                if line.strip():
                    print(f"   文件: {line}")
            self.results["format"] = {"status": "NEEDS_FORMATTING"}

        return self.results["format"]

    def check_mypy_types(self):
        """检查 MyPy 类型"""
        print("\n" + "=" * 60)
        print("[MyPy] 类型检查")
        print("=" * 60)

        # 检查几个核心文件
        core_files = [
            "src/main.py",
            "src/core/config.py",
            "src/services/auth_service.py",
        ]

        type_errors = 0
        for file_path in core_files:
            if Path(file_path).exists():
                print(f"\n[检查] {file_path}")
                success, stdout, stderr = run_command(
                    f"uv run mypy {file_path} --ignore-missing-imports --no-error-summary"
                )

                if success:
                    print(f"   [OK] {file_path} 类型检查通过")
                else:
                    print(f"   [ISSUE] {file_path} 有类型问题")
                    type_errors += 1
                    # 显示关键错误
                    for line in stderr.strip().split("\n")[:3]:
                        if "error:" in line.lower():
                            print(f"   错误: {line}")

        if type_errors == 0:
            self.results["mypy"] = {"status": "PASS"}
            print("\n[OK] 所有核心文件类型检查通过")
        else:
            self.results["mypy"] = {"status": "TYPE_ISSUES", "count": type_errors}
            print(f"\n[ISSUE] {type_errors} 个文件有类型问题")

        return self.results["mypy"]

    def check_import_organization(self):
        """检查导入组织"""
        print("\n" + "=" * 60)
        print("[Import] 导入组织检查")
        print("=" * 60)

        # 检查是否有未使用的导入
        success, stdout, stderr = run_command(
            "uv run ruff check src/ --select=F401 --statistics"
        )

        if success or "Found 0 errors" in stdout:
            print("[OK] 无未使用导入")
            unused_imports = 0
        else:
            unused_imports = 0
            for line in stdout.strip().split("\n"):
                if "Found" in line and "errors" in line:
                    try:
                        unused_imports = int(line.split("Found")[1].split()[0])
                    except:
                        pass
                    break
            print(f"[INFO] 发现 {unused_imports} 个未使用导入")

        self.results["imports"] = {"status": "PASS", "unused_count": unused_imports}
        return self.results["imports"]

    def check_complexity(self):
        """检查代码复杂度"""
        print("\n" + "=" * 60)
        print("[Complexity] 代码复杂度检查")
        print("=" * 60)

        # 使用 ruff 检查复杂度相关的规则
        complexity_rules = ["C901", "PLR0912", "PLR0913", "PLR0915"]

        total_issues = 0
        for rule in complexity_rules:
            success, stdout, stderr = run_command(
                f"uv run ruff check src/ --select={rule}"
            )

            if not success and stdout.strip():
                count = len(stdout.strip().split("\n"))
                total_issues += count
                print(f"[INFO] {rule}: {count} 个问题")

        if total_issues == 0:
            print("[OK] 无复杂度问题")
            self.results["complexity"] = {"status": "PASS", "count": 0}
        else:
            print(f"[INFO] 发现 {total_issues} 个复杂度相关问题")
            self.results["complexity"] = {
                "status": "COMPLEXITY_ISSUES",
                "count": total_issues,
            }

        return self.results["complexity"]

    def generate_report(self):
        """生成检查报告"""
        print("\n" + "=" * 60)
        print("[报告] 代码质量检查汇总")
        print("=" * 60)

        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        print(f"\n[统计] 检查耗时: {duration:.2f} 秒")
        print(f"[统计] 检查时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 汇总各类检查结果
        summaries = []

        # Ruff 检查
        if "ruff" in self.results:
            ruff_results = self.results["ruff"]
            total_errors = sum(
                result.get("count", 0) for result in ruff_results.values()
            )
            if total_errors == 0:
                summaries.append("[Ruff] 关键错误检查: 通过 ✅")
            else:
                summaries.append(f"[Ruff] 关键错误检查: 发现 {total_errors} 个问题 ⚠️")

        # 格式检查
        if "format" in self.results:
            format_status = self.results["format"]["status"]
            summaries.append(
                "[格式] 代码格式: 通过 ✅"
                if format_status == "PASS"
                else "[格式] 代码格式: 需要修复 ⚠️"
            )

        # 类型检查
        if "mypy" in self.results:
            mypy_status = self.results["mypy"]["status"]
            summaries.append(
                "[类型] MyPy检查: 通过 ✅"
                if mypy_status == "PASS"
                else "[类型] MyPy检查: 有问题 ⚠️"
            )

        # 导入检查
        if "imports" in self.results:
            unused_count = self.results["imports"]["unused_count"]
            summaries.append(
                f"[导入] 未使用导入: {unused_count} 个"
                + (" ✅" if unused_count == 0 else " ⚠️")
            )

        # 复杂度检查
        if "complexity" in self.results:
            complexity_count = self.results["complexity"]["count"]
            summaries.append(
                f"[复杂度] 代码复杂度: {complexity_count} 个问题"
                + (" ✅" if complexity_count == 0 else " ⚠️")
            )

        # 显示汇总
        for summary in summaries:
            print(f"   {summary}")

        # 生成详细报告
        report_data = {
            "timestamp": end_time.isoformat(),
            "duration_seconds": duration,
            "results": self.results,
            "summary": summaries,
        }

        # 保存报告
        report_file = self.project_root / "code_quality_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"\n[报告] 详细报告已保存: {report_file}")

        # 返回整体状态
        critical_issues = 0
        if "ruff" in self.results:
            critical_issues += sum(
                result.get("count", 0) for result in self.results["ruff"].values()
            )

        if critical_issues == 0:
            print("\n[结论] 🎉 代码质量检查通过！可以安全提交代码。")
            return True
        else:
            print(f"\n[结论] ⚠️ 发现 {critical_issues} 个关键问题，建议修复后再提交。")
            return False


def main():
    """主函数"""
    print("本地代码质量检查工具")
    print("=" * 60)
    print("此工具将检查代码质量，确保符合项目标准")
    print("建议在每次 git commit 前运行此检查")

    # 切换到脚本所在目录
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    print(f"\n[目录] 工作目录: {script_dir}")

    # 创建检查器
    checker = CodeQualityChecker(script_dir)

    # 执行各项检查
    try:
        checker.check_ruff_issues()
        checker.check_ruff_format()
        checker.check_mypy_types()
        checker.check_import_organization()
        checker.check_complexity()

        # 生成报告
        success = checker.generate_report()

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n[中断] 检查被用户中断")
        return 130
    except Exception as e:
        print(f"\n[错误] 检查过程中出现异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
