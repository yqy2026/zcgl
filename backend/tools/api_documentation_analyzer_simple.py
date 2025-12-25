#!/usr/bin/env python3
"""
API文档分析器 - 全面分析API端点并生成文档
"""

import ast
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


class APIDocumentationAnalyzer:
    """API文档分析器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.api_dir = self.project_root / "src" / "api"
        self.analysis_result = {
            "summary": {},
            "endpoints": [],
            "modules": [],
            "statistics": {},
            "documentation_gaps": []
        }

    def analyze_api_structure(self) -> dict[str, Any]:
        """分析API结构"""
        print("开始分析API结构...")

        # 扫描所有API文件
        api_files = self._find_api_files()
        print(f"找到 {len(api_files)} 个API文件")

        # 分析每个API文件
        for api_file in api_files:
            self._analyze_api_file(api_file)

        # 计算统计信息
        self._calculate_statistics()

        # 识别文档缺失
        self._identify_documentation_gaps()

        return self.analysis_result

    def _find_api_files(self) -> list[Path]:
        """查找所有API文件"""
        api_files = []
        for file_path in self.api_dir.rglob("*.py"):
            if file_path.name != "__init__.py" and not file_path.name.startswith("_"):
                api_files.append(file_path)
        return sorted(api_files)

    def _analyze_api_file(self, file_path: Path):
        """分析单个API文件"""
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            # 解析AST
            try:
                tree = ast.parse(content)
            except SyntaxError:
                print(f"语法错误文件: {file_path}")
                return

            module_info = {
                "file": str(file_path.relative_to(self.project_root)),
                "module_name": file_path.stem,
                "path": str(file_path.relative_to(self.api_dir)),
                "endpoints": [],
                "imports": [],
                "decorators": [],
                "has_docstring": False,
                "docstring": ""
            }

            # 分析文档字符串
            if ast.get_docstring(tree):
                module_info["has_docstring"] = True
                module_info["docstring"] = ast.get_docstring(tree)

            # 分析导入
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_info["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module_info["imports"].append(f"from {node.module}")

            # 分析路由端点
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    endpoint_info = self._analyze_endpoint(node, content)
                    if endpoint_info:
                        module_info["endpoints"].append(endpoint_info)

            self.analysis_result["modules"].append(module_info)

        except Exception as e:
            print(f"分析文件失败 {file_path}: {e}")

    def _analyze_endpoint(self, node: ast.FunctionDef, content: str) -> dict[str, Any] | None:
        """分析API端点"""
        # 检查是否有路由装饰器
        route_decorator = None
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                if decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                    route_decorator = decorator
                    break

        if not route_decorator:
            return None

        # 提取路由信息
        endpoint_info = {
            "name": node.name,
            "method": route_decorator.func.attr.upper(),
            "path": "",
            "summary": "",
            "description": "",
            "parameters": [],
            "responses": {},
            "has_docstring": bool(ast.get_docstring(node)),
            "docstring": ast.get_docstring(node) or "",
            "line_number": node.lineno
        }

        # 提取路由路径
        if route_decorator.args:
            if isinstance(route_decorator.args[0], ast.Constant):
                endpoint_info["path"] = route_decorator.args[0].value

        # 提取summary参数
        for keyword in route_decorator.keywords:
            if keyword.arg == "summary" and isinstance(keyword.value, ast.Constant):
                endpoint_info["summary"] = keyword.value.value

        # 从文档字符串中提取详细信息
        if endpoint_info["docstring"]:
            self._extract_docstring_info(endpoint_info)

        return endpoint_info

    def _extract_docstring_info(self, endpoint_info: dict[str, Any]):
        """从文档字符串中提取信息"""
        docstring = endpoint_info["docstring"]

        # 提取描述（第一行）
        lines = docstring.split('\n')
        if lines:
            endpoint_info["description"] = lines[0].strip()

        # 提取参数信息（简单模式）
        param_pattern = r'@param\s+(\w+):\s*(.+)'
        params = re.findall(param_pattern, docstring)
        for param_name, param_desc in params:
            endpoint_info["parameters"].append({
                "name": param_name,
                "description": param_desc.strip()
            })

        # 提取返回信息
        return_pattern = r'@return:\s*(.+)'
        return_match = re.search(return_pattern, docstring)
        if return_match:
            endpoint_info["return_description"] = return_match.group(1).strip()

    def _calculate_statistics(self):
        """计算统计信息"""
        total_endpoints = sum(len(module["endpoints"]) for module in self.analysis_result["modules"])
        modules_with_docs = sum(1 for module in self.analysis_result["modules"] if module["has_docstring"])
        endpoints_with_docs = sum(
            1 for module in self.analysis_result["modules"]
            for endpoint in module["endpoints"]
            if endpoint["has_docstring"]
        )

        method_counts = {}
        for module in self.analysis_result["modules"]:
            for endpoint in module["endpoints"]:
                method = endpoint["method"]
                method_counts[method] = method_counts.get(method, 0) + 1

        self.analysis_result["statistics"] = {
            "total_modules": len(self.analysis_result["modules"]),
            "total_endpoints": total_endpoints,
            "modules_with_documentation": modules_with_docs,
            "endpoints_with_documentation": endpoints_with_docs,
            "module_documentation_rate": round(modules_with_docs / len(self.analysis_result["modules"]) * 100, 1) if self.analysis_result["modules"] else 0,
            "endpoint_documentation_rate": round(endpoints_with_docs / total_endpoints * 100, 1) if total_endpoints > 0 else 0,
            "method_distribution": method_counts,
            "avg_endpoints_per_module": round(total_endpoints / len(self.analysis_result["modules"]), 1) if self.analysis_result["modules"] else 0
        }

    def _identify_documentation_gaps(self):
        """识别文档缺失"""
        gaps = []

        # 检查模块文档缺失
        for module in self.analysis_result["modules"]:
            if not module["has_docstring"]:
                gaps.append({
                    "type": "module_documentation",
                    "file": module["file"],
                    "module": module["module_name"],
                    "severity": "medium",
                    "description": f"模块 {module['module_name']} 缺少文档字符串"
                })

        # 检查端点文档缺失
        for module in self.analysis_result["modules"]:
            for endpoint in module["endpoints"]:
                if not endpoint["has_docstring"]:
                    gaps.append({
                        "type": "endpoint_documentation",
                        "file": module["file"],
                        "module": module["module_name"],
                        "endpoint": f"{endpoint['method']} {endpoint['path']}",
                        "severity": "high",
                        "description": f"端点 {endpoint['method']} {endpoint['path']} 缺少文档字符串"
                    })

                if not endpoint["summary"]:
                    gaps.append({
                        "type": "endpoint_summary",
                        "file": module["file"],
                        "module": module["module_name"],
                        "endpoint": f"{endpoint['method']} {endpoint['path']}",
                        "severity": "medium",
                        "description": f"端点 {endpoint['method']} {endpoint['path']} 缺少summary描述"
                    })

        self.analysis_result["documentation_gaps"] = sorted(gaps, key=lambda x: (x["severity"], x["file"]))

    def generate_documentation_report(self) -> str:
        """生成文档报告"""
        report = []
        stats = self.analysis_result["statistics"]

        report.append("# API文档分析报告")
        report.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**分析范围**: {stats['total_modules']} 个模块，{stats['total_endpoints']} 个端点")

        # 概览统计
        report.append("\n## 概览统计")
        report.append(f"- **总模块数**: {stats['total_modules']}")
        report.append(f"- **总端点数**: {stats['total_endpoints']}")
        report.append(f"- **平均每模块端点数**: {stats['avg_endpoints_per_module']}")
        report.append(f"- **模块文档覆盖率**: {stats['module_documentation_rate']}%")
        report.append(f"- **端点文档覆盖率**: {stats['endpoint_documentation_rate']}%")

        # HTTP方法分布
        report.append("\n## HTTP方法分布")
        for method, count in sorted(stats['method_distribution'].items()):
            report.append(f"- **{method}**: {count} 个端点")

        # 模块详情
        report.append("\n## 模块详情")
        for module in sorted(self.analysis_result["modules"], key=lambda x: len(x["endpoints"]), reverse=True):
            report.append(f"\n### {module['module_name']}")
            report.append(f"**文件**: `{module['file']}`")
            report.append(f"**端点数**: {len(module['endpoints'])}")
            report.append(f"**有文档**: {'是' if module['has_docstring'] else '否'}")

            if module["endpoints"]:
                report.append("**端点列表**:")
                for endpoint in module["endpoints"]:
                    doc_status = "是" if endpoint["has_docstring"] else "否"
                    summary = endpoint["summary"] or endpoint["description"] or "无描述"
                    report.append(f"- `{endpoint['method']} {endpoint['path']}` {doc_status} - {summary}")

        # 文档缺失
        if self.analysis_result["documentation_gaps"]:
            report.append("\n## 文档缺失问题")

            high_priority = [gap for gap in self.analysis_result["documentation_gaps"] if gap["severity"] == "high"]
            medium_priority = [gap for gap in self.analysis_result["documentation_gaps"] if gap["severity"] == "medium"]

            if high_priority:
                report.append("\n### 高优先级问题")
                for gap in high_priority[:10]:  # 只显示前10个
                    report.append(f"- **{gap['file']}**: {gap['description']}")

            if medium_priority:
                report.append("\n### 中优先级问题")
                for gap in medium_priority[:10]:  # 只显示前10个
                    report.append(f"- **{gap['file']}**: {gap['description']}")

        # 改进建议
        report.append("\n## 改进建议")
        report.append("1. **优先为缺失文档的端点添加docstring**")
        report.append("2. **统一API文档格式，使用OpenAPI规范**")
        report.append("3. **为复杂端点添加参数和响应示例**")
        report.append("4. **建立自动化文档检查工具**")
        report.append("5. **定期审查和更新文档内容**")

        return "\n".join(report)

    def save_analysis_result(self, output_file: str):
        """保存分析结果"""
        output_path = self.project_root / output_file

        # 生成详细报告
        report = self.generate_documentation_report()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        # 保存JSON数据
        json_path = output_path.with_suffix('.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_result, f, ensure_ascii=False, indent=2)

        print(f"报告已保存到: {output_path}")
        print(f"数据已保存到: {json_path}")


def main():
    """主函数"""
    project_root = Path(__file__).parent.parent
    analyzer = APIDocumentationAnalyzer(project_root)

    print("开始API文档分析...")
    analysis_result = analyzer.analyze_api_structure()

    # 输出关键统计
    stats = analysis_result["statistics"]
    print("\n分析完成:")
    print(f"   总模块数: {stats['total_modules']}")
    print(f"   总端点数: {stats['total_endpoints']}")
    print(f"   模块文档覆盖率: {stats['module_documentation_rate']}%")
    print(f"   端点文档覆盖率: {stats['endpoint_documentation_rate']}%")
    print(f"   文档缺失问题: {len(analysis_result['documentation_gaps'])} 个")

    # 保存报告
    analyzer.save_analysis_result("docs/API_DOCUMENTATION_ANALYSIS.md")

    print("\nAPI文档分析完成!")


if __name__ == "__main__":
    main()
