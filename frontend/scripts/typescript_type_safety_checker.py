#!/usr/bin/env python3
"""
TypeScript类型安全性检查器
系统性识别和分析前端代码中的any类型使用情况
"""

import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class TypeIssue:
    """类型问题记录"""

    file_path: str
    line_number: int
    column: int
    issue_type: str
    severity: str  # critical, high, medium, low
    context: str
    pattern: str
    suggestion: str
    code_snippet: str


@dataclass
class FileAnalysis:
    """文件分析结果"""

    file_path: str
    total_issues: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    issues: List[TypeIssue]


class TypeScriptTypeSafetyChecker:
    """TypeScript类型安全性检查器"""

    def __init__(self, root_dir: str = "src"):
        self.root_dir = Path(root_dir)
        self.exclude_patterns = {
            "node_modules",
            ".git",
            "dist",
            "build",
            "coverage",
            "__tests__",
            ".next",
            ".nuxt",
            "temp",
            "tmp",
        }

        # 危险类型使用模式
        self.type_patterns = {
            # 直接使用any
            "direct_any": {
                "pattern": r"\bany\b",
                "severity": "high",
                "description": "直接使用any类型",
                "suggestion": "使用具体类型替代any",
            },
            # 函数参数any
            "param_any": {
                "pattern": r"\(\s*\w+\s*:\s*any\s*[,\)]",
                "severity": "critical",
                "description": "函数参数使用any类型",
                "suggestion": "定义具体的参数类型接口",
            },
            # 函数返回值any
            "return_any": {
                "pattern": r":\s*any\s*[{;]",
                "severity": "high",
                "description": "函数返回值使用any类型",
                "suggestion": "定义明确的返回值类型",
            },
            # 数组any
            "array_any": {
                "pattern": r"Array<any>|any\[\]",
                "severity": "high",
                "description": "数组元素使用any类型",
                "suggestion": "定义数组元素的具体类型",
            },
            # 对象属性any
            "object_property_any": {
                "pattern": r"\w+\s*:\s*any\s*[;,}]",
                "severity": "medium",
                "description": "对象属性使用any类型",
                "suggestion": "定义属性的具体类型",
            },
            # 泛型any
            "generic_any": {
                "pattern": r"<\s*any\s*>",
                "severity": "medium",
                "description": "泛型参数使用any类型",
                "suggestion": "使用具体的泛型约束",
            },
            # 类型断言为any
            "assertion_any": {
                "pattern": r"as\s+any\b",
                "severity": "critical",
                "description": "类型断言为any类型",
                "suggestion": "避免类型断言，使用类型守卫或具体类型",
            },
            # any类型变量声明
            "variable_any": {
                "pattern": r"(?:const|let|var)\s+\w+\s*:\s*any\s*[=;]",
                "severity": "high",
                "description": "变量声明使用any类型",
                "suggestion": "定义变量的具体类型",
            },
        }

        # 常见类型建议映射
        self.type_suggestions = {
            "API响应": "ApiResponse<T>",
            "函数参数": "interface SpecificParams { ... }",
            "事件对象": "React.MouseEvent | React.ChangeEvent",
            "表单数据": "interface FormData { ... }",
            "配置对象": "interface Config { ... }",
            "分页数据": "PaginationData<T>",
            "表格数据": "TableData<T>",
            "选择器选项": "SelectOption<T>",
            "用户信息": "UserInfo",
            "权限信息": "PermissionInfo",
        }

    def should_exclude_file(self, file_path: Path) -> bool:
        """判断文件是否应该被排除"""
        path_str = str(file_path)
        return any(exclude in path_str for exclude in self.exclude_patterns)

    def is_typescript_file(self, file_path: Path) -> bool:
        """判断是否为TypeScript文件"""
        return file_path.suffix in [".ts", ".tsx"]

    def analyze_line(
        self, line: str, line_number: int, file_path: str
    ) -> List[TypeIssue]:
        """分析单行代码中的类型问题"""
        issues = []

        for pattern_name, pattern_info in self.type_patterns.items():
            matches = re.finditer(pattern_info["pattern"], line)
            for match in matches:
                # 获取上下文
                start_pos = max(0, match.start() - 50)
                end_pos = min(len(line), match.end() + 50)
                context = line[start_pos:end_pos].strip()

                # 生成建议
                suggestion = self.generate_suggestion(pattern_name, context, line)

                issue = TypeIssue(
                    file_path=file_path,
                    line_number=line_number,
                    column=match.start() + 1,
                    issue_type=pattern_name,
                    severity=pattern_info["severity"],
                    context=context,
                    pattern=pattern_info["pattern"],
                    suggestion=suggestion,
                    code_snippet=line.strip(),
                )
                issues.append(issue)

        return issues

    def generate_suggestion(
        self, pattern_name: str, context: str, full_line: str
    ) -> str:
        """根据模式类型和上下文生成修复建议"""
        base_suggestion = self.type_patterns[pattern_name]["suggestion"]

        # 根据上下文提供更具体的建议
        if "api" in context.lower() or "response" in context.lower():
            return f"{base_suggestion} - 考虑使用: ApiResponse<T> 或接口定义"
        elif "event" in context.lower():
            return f"{base_suggestion} - 考虑使用: React.EventType 具体类型"
        elif "form" in context.lower():
            return f"{base_suggestion} - 考虑使用: FormData 接口定义"
        elif "table" in context.lower():
            return f"{base_suggestion} - 考虑使用: TableData<T> 泛型接口"
        elif "pagination" in context.lower():
            return f"{base_suggestion} - 考虑使用: PaginationConfig 接口"
        elif "props" in context.lower():
            return f"{base_suggestion} - 考虑使用: ComponentProps 接口定义"
        else:
            return base_suggestion

    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """分析单个文件"""
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line_number, line in enumerate(lines, 1):
                line_issues = self.analyze_line(
                    line.strip(), line_number, str(file_path)
                )
                issues.extend(line_issues)

        except Exception as e:
            print(f"分析文件 {file_path} 时出错: {e}")
            return FileAnalysis(
                file_path=str(file_path),
                total_issues=0,
                critical_issues=0,
                high_issues=0,
                medium_issues=0,
                low_issues=0,
                issues=[],
            )

        # 统计严重程度
        severity_counts = Counter(issue.severity for issue in issues)

        return FileAnalysis(
            file_path=str(file_path),
            total_issues=len(issues),
            critical_issues=severity_counts.get("critical", 0),
            high_issues=severity_counts.get("high", 0),
            medium_issues=severity_counts.get("medium", 0),
            low_issues=severity_counts.get("low", 0),
            issues=issues,
        )

    def scan_all_files(self) -> List[FileAnalysis]:
        """扫描所有TypeScript文件"""
        all_analyses = []

        print("🔍 开始扫描TypeScript文件...")

        for ts_file in self.root_dir.rglob("*.ts"):
            if self.should_exclude_file(ts_file):
                continue
            if not self.is_typescript_file(ts_file):
                continue

            print(f"📄 分析文件: {ts_file.relative_to(self.root_dir)}")
            analysis = self.analyze_file(ts_file)
            all_analyses.append(analysis)

        for tsx_file in self.root_dir.rglob("*.tsx"):
            if self.should_exclude_file(tsx_file):
                continue
            if not self.is_typescript_file(tsx_file):
                continue

            print(f"📄 分析文件: {tsx_file.relative_to(self.root_dir)}")
            analysis = self.analyze_file(tsx_file)
            all_analyses.append(analysis)

        return all_analyses

    def generate_report(self, analyses: List[FileAnalysis]) -> Dict:
        """生成综合报告"""
        total_issues = sum(analysis.total_issues for analysis in analyses)
        total_files = len(analyses)
        files_with_issues = len([a for a in analyses if a.total_issues > 0])

        # 统计严重程度
        severity_totals = {
            "critical": sum(a.critical_issues for a in analyses),
            "high": sum(a.high_issues for a in analyses),
            "medium": sum(a.medium_issues for a in analyses),
            "low": sum(a.low_issues for a in analyses),
        }

        # 找出问题最多的文件
        top_problematic_files = sorted(
            analyses, key=lambda x: x.total_issues, reverse=True
        )[:10]

        # 按问题类型统计
        issue_type_counts = defaultdict(int)
        for analysis in analyses:
            for issue in analysis.issues:
                issue_type_counts[issue.issue_type] += 1

        return {
            "summary": {
                "total_files_scanned": total_files,
                "files_with_issues": files_with_issues,
                "total_issues": total_issues,
                "severity_breakdown": severity_totals,
                "files_with_no_issues": total_files - files_with_issues,
                "type_safety_score": max(0, 100 - (total_issues / total_files * 10))
                if total_files > 0
                else 100,
            },
            "top_problematic_files": [
                {
                    "file_path": analysis.file_path,
                    "total_issues": analysis.total_issues,
                    "critical_issues": analysis.critical_issues,
                    "high_issues": analysis.high_issues,
                }
                for analysis in top_problematic_files
            ],
            "issue_type_distribution": dict(issue_type_counts),
            "detailed_analysis": [asdict(analysis) for analysis in analyses],
        }

    def save_report(
        self, report: Dict, output_path: str = "typescript_type_safety_report.json"
    ):
        """保存报告到文件"""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"📊 报告已保存到: {output_path}")
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")

    def print_summary(self, report: Dict):
        """打印报告摘要"""
        summary = report["summary"]

        print("\n" + "=" * 60)
        print("🎯 TypeScript类型安全性检查报告")
        print("=" * 60)

        print(f"📁 扫描文件总数: {summary['total_files_scanned']}")
        print(f"📄 存在问题的文件: {summary['files_with_issues']}")
        print(f"📋 无问题的文件: {summary['files_with_no_issues']}")
        print(f"🔍 发现问题总数: {summary['total_issues']}")
        print(f"⭐ 类型安全评分: {summary['type_safety_score']:.1f}/100")

        print("\n🚨 严重程度分布:")
        severity_emojis = {"critical": "🚨", "high": "🟠", "medium": "🟡", "low": "🟢"}

        for severity, count in summary["severity_breakdown"].items():
            emoji = severity_emojis.get(severity, "📋")
            print(f"  {emoji} {severity.upper()}: {count} 个问题")

        print("\n📊 问题类型分布:")
        issue_type_emojis = {
            "direct_any": "🔴",
            "param_any": "🚨",
            "return_any": "🟠",
            "array_any": "🟡",
            "object_property_any": "🟢",
            "generic_any": "🔵",
            "assertion_any": "💥",
            "variable_any": "⚠️",
        }

        for issue_type, count in report["issue_type_distribution"].items():
            emoji = issue_type_emojis.get(issue_type, "📋")
            print(f"  {emoji} {issue_type}: {count} 个")

        print("\n🔥 问题最多的文件 (前5名):")
        for i, file_info in enumerate(report["top_problematic_files"][:5], 1):
            print(f"  {i}. {file_info['file_path']}")
            print(
                f"     总问题: {file_info['total_issues']} | 严重: {file_info['critical_issues']} | 高: {file_info['high_issues']}"
            )

        print("\n" + "=" * 60)


def main():
    """主函数"""
    print("🎯 启动TypeScript类型安全性检查器")

    # 创建检查器实例
    checker = TypeScriptTypeSafetyChecker()

    # 扫描所有文件
    analyses = checker.scan_all_files()

    # 生成报告
    report = checker.generate_report(analyses)

    # 打印摘要
    checker.print_summary(report)

    # 保存详细报告
    checker.save_report(report)

    print(f"\n✅ 类型安全性检查完成!")
    print(f"📋 详细报告请查看: typescript_type_safety_report.json")

    # 根据结果提供行动建议
    if report["summary"]["total_issues"] > 0:
        print(f"\n🎯 修复建议:")
        print("1. 🚨 优先修复 CRITICAL 级别问题 - 类型断言和函数参数")
        print("2. 🟠 重点修复 HIGH 级别问题 - 直接any类型和返回值")
        print("3. 🟡 逐步修复 MEDIUM 级别问题 - 对象属性和泛型")
        print("4. 🟢 最后修复 LOW 级别问题 - 其他类型使用")

        critical_count = report["summary"]["severity_breakdown"].get("critical", 0)
        if critical_count > 0:
            print(f"\n⚠️  发现 {critical_count} 个CRITICAL级别问题，建议立即修复！")


if __name__ == "__main__":
    main()
