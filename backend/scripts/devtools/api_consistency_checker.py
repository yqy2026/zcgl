from typing import Any

"""
API一致性检查工具
检查前后端API的一致性，包括路径、参数、响应格式等
"""

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class APIEndpoint:
    """API端点信息"""

    path: str
    method: str
    parameters: list[dict[str, Any]]
    response_model: str
    tags: list[str]
    summary: str


@dataclass
class Inconsistency:
    """不一致问题"""

    type: str  # 'missing_endpoint', 'path_mismatch', 'parameter_mismatch', 'response_mismatch'
    severity: str  # 'high', 'medium', 'low'
    description: str
    frontend_location: str
    backend_location: str
    suggestion: str


class APIConsistencyChecker:
    """API一致性检查器"""

    def __init__(self, frontend_dir: str = "../../frontend", backend_dir: str = "."):
        self.frontend_dir = Path(frontend_dir)
        self.backend_dir = Path(backend_dir)
        self.frontend_apis: dict[str, APIEndpoint] = {}
        self.backend_apis: dict[str, APIEndpoint] = {}
        self.inconsistencies: list[Inconsistency] = []

    def check_consistency(self) -> dict[str, Any]:
        """执行完整的一致性检查"""
        print("🔍 开始API一致性检查...")

        # 1. 扫描前端API调用
        print("📱 扫描前端API调用...")
        self._scan_frontend_apis()

        # 2. 扫描后端API定义
        print("🖥️ 扫描后端API定义...")
        self._scan_backend_apis()

        # 3. 检查不一致性
        print("⚖️ 检查不一致性...")
        self._check_inconsistencies()

        # 4. 生成报告
        report = self._generate_report()

        print(f"✅ 检查完成，发现 {len(self.inconsistencies)} 个问题")
        return report

    def _scan_frontend_apis(self) -> None:
        """扫描前端API调用"""
        # 扫描TypeScript/JavaScript文件中的API调用
        for file_path in self.frontend_dir.rglob("*.ts"):
            if "node_modules" in str(file_path):
                continue
            self._parse_frontend_file(file_path)

        for file_path in self.frontend_dir.rglob("*.tsx"):
            if "node_modules" in str(file_path):
                continue
            self._parse_frontend_file(file_path)

    def _parse_frontend_file(self, file_path: Path) -> None:
        """解析前端文件中的API调用"""
        try:
            content = file_path.read_text(encoding="utf-8")

            # 查找API调用模式
            patterns = [
                r'(?:axios\.|fetch\()[\'"](/api/v1/[^\'"]+)[\'"]',  # axios或fetch调用
                r'api\.[a-zA-Z_]+\([\'"]([^\'"]+)[\'"]',  # api对象调用
                r'[\'"](/api/v1/[^\'"]+)[\'"]',  # 直接路径字符串
            ]

            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    api_path = match.group(1)
                    method = self._extract_method_from_context(content, match.start())

                    if api_path:
                        key = f"{method.upper()}:{api_path}"
                        if key not in self.frontend_apis:
                            self.frontend_apis[key] = APIEndpoint(
                                path=api_path,
                                method=method.upper(),
                                parameters=[],
                                response_model="unknown",
                                tags=[],
                                summary=f"Frontend API call in {file_path.name}",
                            )

        except Exception as e:
            print(f"⚠️ 解析文件失败 {file_path}: {e}")

    def _extract_method_from_context(self, content: str, pos: int) -> str:
        """从上下文中提取HTTP方法"""
        # 在匹配位置前后查找HTTP方法关键词
        context_start = max(0, pos - 100)
        context_end = min(len(content), pos + 100)
        context = content[context_start:context_end].lower()

        if "get(" in context or ".get(" in context:
            return "GET"
        elif "post(" in context or ".post(" in context:
            return "POST"
        elif "put(" in context or ".put(" in context:
            return "PUT"
        elif "delete(" in context or ".delete(" in context:
            return "DELETE"
        elif "patch(" in context or ".patch(" in context:
            return "PATCH"

        return "GET"  # 默认

    def _scan_backend_apis(self) -> None:
        """扫描后端API定义"""
        # 扫描Python文件中的FastAPI路由定义
        for file_path in self.backend_dir.rglob("*.py"):
            if "__pycache__" in str(file_path):
                continue
            self._parse_backend_file(file_path)

    def _parse_backend_file(self, file_path: Path) -> None:
        """解析后端文件中的API定义"""
        try:
            content = file_path.read_text(encoding="utf-8")

            # 查找FastAPI路由装饰器
            router_pattern = (
                r'@(?:router|app)\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]'
            )
            matches = re.finditer(router_pattern, content)

            for match in matches:
                method = match.group(1).upper()
                path = match.group(2)

                # 提取函数信息
                func_info = self._extract_function_info(content, match.end())

                key = f"{method}:{path}"
                self.backend_apis[key] = APIEndpoint(
                    path=path,
                    method=method,
                    parameters=func_info.get("parameters", []),
                    response_model=func_info.get("response_model", "unknown"),
                    tags=func_info.get("tags", []),
                    summary=func_info.get("summary", ""),
                )

        except Exception as e:
            print(f"⚠️ 解析后端文件失败 {file_path}: {e}")

    def _extract_function_info(self, content: str, pos: int) -> dict[str, Any]:
        """提取函数信息"""
        # 简化版本：在装饰器后查找函数定义
        func_start = content.find("def ", pos)
        if func_start == -1:
            return {}

        # 提取函数文档字符串
        func_content = content[func_start : func_start + 1000]
        docstring_match = re.search(r'"""([^"]+)"""', func_content)
        summary = docstring_match.group(1).strip() if docstring_match else ""

        return {
            "summary": summary,
            "parameters": [],
            "response_model": "unknown",
            "tags": [],
        }

    def _check_inconsistencies(self) -> None:
        """检查不一致性"""
        # 1. 检查缺失的后端端点
        for key, frontend_api in self.frontend_apis.items():
            if key not in self.backend_apis:
                self.inconsistencies.append(
                    Inconsistency(
                        type="missing_endpoint",
                        severity="high",
                        description=f"前端调用但后端未定义: {frontend_api.method} {frontend_api.path}",
                        frontend_location=frontend_api.summary,
                        backend_location="未找到",
                        suggestion=f"请在后端实现 {frontend_api.method} {frontend_api.path} 端点",
                    )
                )

        # 2. 检查多余的后端端点
        for key, backend_api in self.backend_apis.items():
            if key not in self.frontend_apis:
                self.inconsistencies.append(
                    Inconsistency(
                        type="unused_endpoint",
                        severity="low",
                        description=f"后端已定义但前端未使用: {backend_api.method} {backend_api.path}",
                        frontend_location="未找到",
                        backend_location=backend_api.summary,
                        suggestion="考虑在前端使用此端点或删除未使用的后端代码",
                    )
                )

        # 3. 检查路径格式不一致
        self._check_path_format_inconsistencies()

        # 4. 检查命名约定不一致
        self._check_naming_conventions()

    def _check_path_format_inconsistencies(self) -> None:
        """检查路径格式不一致"""
        # 检查API版本前缀一致性
        for api in self.frontend_apis.values():
            if not api.path.startswith("/api/v"):
                self.inconsistencies.append(
                    Inconsistency(
                        type="path_format",
                        severity="medium",
                        description=f"前端API路径缺少版本前缀: {api.path}",
                        frontend_location=api.summary,
                        backend_location="",
                        suggestion=f"建议将路径改为 /api/v1{api.path}",
                    )
                )

    def _check_naming_conventions(self) -> None:
        """检查命名约定不一致"""
        # 检查复数形式一致性
        resource_patterns = {
            "/assets": "/asset",
            "/projects": "/project",
            "/ownerships": "/ownership",
            "/tasks": "/task",
        }

        for singular, plural in resource_patterns.items():
            for api in self.frontend_apis.values():
                if plural in api.path and api.method == "GET":
                    # 检查是否有对应的单数形式
                    singular_key = f"{api.method}:{api.path.replace(plural, singular)}"
                    if singular_key not in self.frontend_apis:
                        self.inconsistencies.append(
                            Inconsistency(
                                type="naming_convention",
                                severity="low",
                                description=f"建议保持命名一致性: {api.path}",
                                frontend_location=api.summary,
                                backend_location="",
                                suggestion=f"考虑添加 {singular_key} 端点或调整命名",
                            )
                        )

    def _generate_report(self) -> dict[str, Any]:
        """生成检查报告"""
        # 按严重程度分类
        high_issues = [i for i in self.inconsistencies if i.severity == "high"]
        medium_issues = [i for i in self.inconsistencies if i.severity == "medium"]
        low_issues = [i for i in self.inconsistencies if i.severity == "low"]

        # 按类型分类
        type_counts: dict[str, int] = {}
        for issue in self.inconsistencies:
            type_counts[issue.type] = type_counts.get(issue.type, 0) + 1

        report = {
            "summary": {
                "total_issues": len(self.inconsistencies),
                "high_severity": len(high_issues),
                "medium_severity": len(medium_issues),
                "low_severity": len(low_issues),
                "frontend_apis": len(self.frontend_apis),
                "backend_apis": len(self.backend_apis),
                "check_time": datetime.now().isoformat(),
            },
            "issues_by_type": type_counts,
            "high_priority_issues": [
                {
                    "type": issue.type,
                    "description": issue.description,
                    "suggestion": issue.suggestion,
                    "frontend_location": issue.frontend_location,
                }
                for issue in high_issues
            ],
            "all_issues": [
                {
                    "type": issue.type,
                    "severity": issue.severity,
                    "description": issue.description,
                    "suggestion": issue.suggestion,
                    "frontend_location": issue.frontend_location,
                    "backend_location": issue.backend_location,
                }
                for issue in self.inconsistencies
            ],
            "recommendations": self._generate_recommendations(),
        }

        return report

    def _generate_recommendations(self) -> list[str]:
        """生成改进建议"""
        recommendations = []

        if self.inconsistencies:
            recommendations.append("🔧 建议优先解决高严重性问题，确保核心功能正常")
            recommendations.append("📝 建议建立API文档规范，统一前后端接口定义")
            recommendations.append("🔄 建议实施API自动化测试，确保接口稳定性")
            recommendations.append("📋 建议定期运行一致性检查，及时发现问题")

        # 具体建议
        high_issues = [i for i in self.inconsistencies if i.severity == "high"]
        if high_issues:
            recommendations.append(
                f"⚠️ 发现 {len(high_issues)} 个高严重性问题，需要立即处理"
            )

        return recommendations

    def save_report(self, output_dir: str = "reports") -> None:
        """保存检查报告"""
        os.makedirs(output_dir, exist_ok=True)

        report = self._generate_report()

        # 保存JSON报告
        json_path = os.path.join(output_dir, "api_consistency_report.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 生成Markdown报告
        self._generate_markdown_report(report, output_dir)

        print(f"📄 报告已保存到: {json_path}")

    def _generate_markdown_report(
        self, report: dict[str, Any], output_dir: str
    ) -> None:
        """生成Markdown格式报告"""
        md_content = f"""# API一致性检查报告

## 概述

- **检查时间**: {report["summary"]["check_time"]}
- **总问题数**: {report["summary"]["total_issues"]}
- **高严重性**: {report["summary"]["high_severity"]} ⚠️
- **中等严重性**: {report["summary"]["medium_severity"]}
- **低严重性**: {report["summary"]["low_severity"]}
- **前端API数量**: {report["summary"]["frontend_apis"]}
- **后端API数量**: {report["summary"]["backend_apis"]}

## 问题分布

"""

        # 问题类型统计
        for issue_type, count in report["issues_by_type"].items():
            md_content += f"- **{issue_type}**: {count} 个\n"

        md_content += "\n"

        # 高优先级问题
        if report["high_priority_issues"]:
            md_content += "## 🚨 高优先级问题\n\n"
            for i, issue in enumerate(report["high_priority_issues"], 1):
                md_content += f"### {i}. {issue['type']}\n\n"
                md_content += f"**问题描述**: {issue['description']}\n\n"
                md_content += f"**建议修复**: {issue['suggestion']}\n\n"
                md_content += f"**前端位置**: {issue['frontend_location']}\n\n"
                md_content += "---\n\n"

        # 改进建议
        if report["recommendations"]:
            md_content += "## 💡 改进建议\n\n"
            for rec in report["recommendations"]:
                md_content += f"- {rec}\n"

        # 保存Markdown报告
        md_path = os.path.join(output_dir, "api_consistency_report.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)


def check_api_consistency(
    frontend_dir: str = "../../frontend",
    backend_dir: str = ".",
    output_dir: str = "reports",
) -> dict[str, Any]:
    """
    执行API一致性检查的便捷函数

    Args:
        frontend_dir: 前端代码目录
        backend_dir: 后端代码目录
        output_dir: 报告输出目录

    Returns:
        检查报告字典
    """
    checker = APIConsistencyChecker(frontend_dir, backend_dir)
    report = checker.check_consistency()
    checker.save_report(output_dir)
    return report


if __name__ == "__main__":
    print("🔍 API一致性检查工具")
    print("请在项目根目录运行此工具")

    # 示例用法
    # check_api_consistency()
