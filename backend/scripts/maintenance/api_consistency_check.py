#!/usr/bin/env python3
"""
API一致性检查脚本

用于检查前后端API的一致性，包括：
1. 端点路径一致性
2. 响应格式一致性
3. 数据模型一致性
4. 参数验证一致性
"""

import ast
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass


@dataclass
class APIEndpoint:
    """API端点信息"""
    path: str
    method: str
    response_model: str = None
    parameters: List[str] = None
    description: str = ""

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []


@dataclass
class ConsistencyIssue:
    """一致性问题"""
    issue_type: str
    severity: str  # critical, warning, info
    message: str
    frontend_file: str = None
    backend_file: str = None
    line_number: int = None


class APIConsistencyChecker:
    """API一致性检查器"""

    def __init__(self, backend_path: str, frontend_path: str):
        self.backend_path = Path(backend_path)
        self.frontend_path = Path(frontend_path)
        self.issues: List[ConsistencyIssue] = []

    def run_checks(self) -> List[ConsistencyIssue]:
        """运行所有检查"""
        print("开始API一致性检查...")

        # 检查1: 提取后端API端点
        backend_endpoints = self.extract_backend_endpoints()
        print(f"找到 {len(backend_endpoints)} 个后端API端点")

        # 检查2: 提取前端API调用
        frontend_calls = self.extract_frontend_api_calls()
        print(f"* 找到 {len(frontend_calls)} 个前端API调用")

        # 检查3: 路径一致性检查
        self.check_path_consistency(backend_endpoints, frontend_calls)

        # 检查4: 数据模型一致性检查
        self.check_model_consistency()

        # 检查5: 响应格式一致性检查
        self.check_response_format_consistency(backend_endpoints)

        # 检查6: 参数一致性检查
        self.check_parameter_consistency(backend_endpoints, frontend_calls)

        print(f"\n检查完成，发现 {len(self.issues)} 个问题")
        return self.issues

    def extract_backend_endpoints(self) -> Dict[str, APIEndpoint]:
        """提取后端API端点"""
        endpoints = {}

        # 查找所有API路由文件
        api_files = list(self.backend_path.glob("src/api/v1/*.py"))
        api_files = [f for f in api_files if f.name != "__init__.py"]

        for api_file in api_files:
            try:
                with open(api_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 使用正则表达式提取路由定义
                router_pattern = r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
                matches = re.finditer(router_pattern, content)

                for match in matches:
                    method = match.group(1).upper()
                    path = match.group(2)

                    # 查找响应模型
                    response_model_match = re.search(
                        rf'@router\.{method.lower()}\s*\([^)]*response_model=([A-Za-z_][A-Za-z0-9_]*)',
                        content[match.start():match.start()+500]
                    )
                    response_model = response_model_match.group(1) if response_model_match else None

                    endpoint_key = f"{method}:{path}"
                    endpoints[endpoint_key] = APIEndpoint(
                        path=path,
                        method=method,
                        response_model=response_model
                    )

            except Exception as e:
                self.issues.append(ConsistencyIssue(
                    issue_type="extraction_error",
                    severity="warning",
                    message=f"无法解析后端API文件 {api_file}: {str(e)}",
                    backend_file=str(api_file)
                ))

        return endpoints

    def extract_frontend_api_calls(self) -> Dict[str, APIEndpoint]:
        """提取前端API调用"""
        calls = {}

        # 查找所有服务文件
        service_files = list(self.frontend_path.glob("src/services/*.ts"))

        for service_file in service_files:
            try:
                with open(service_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 使用正则表达式提取API调用
                api_call_pattern = r'apiClient\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
                matches = re.finditer(api_call_pattern, content)

                for match in matches:
                    method = match.group(1).upper()
                    path = match.group(2)

                    endpoint_key = f"{method}:{path}"
                    calls[endpoint_key] = APIEndpoint(
                        path=path,
                        method=method
                    )

            except Exception as e:
                self.issues.append(ConsistencyIssue(
                    issue_type="extraction_error",
                    severity="warning",
                    message=f"无法解析前端服务文件 {service_file}: {str(e)}",
                    frontend_file=str(service_file)
                ))

        return calls

    def check_path_consistency(self, backend_endpoints: Dict[str, APIEndpoint], frontend_calls: Dict[str, APIEndpoint]):
        """检查路径一致性"""
        print("\n* 检查API路径一致性...")

        # 找出前端调用但后端不存在的API
        missing_endpoints = []
        for key, frontend_call in frontend_calls.items():
            if key not in backend_endpoints:
                missing_endpoints.append(key)
                self.issues.append(ConsistencyIssue(
                    issue_type="missing_endpoint",
                    severity="critical",
                    message=f"前端调用但后端不存在的API: {frontend_call.method} {frontend_call.path}",
                    frontend_file="前端服务文件"
                ))

        # 找出后端存在但前端未使用的API（信息性）
        unused_endpoints = []
        for key, backend_endpoint in backend_endpoints.items():
            if key not in frontend_calls:
                unused_endpoints.append(key)
                self.issues.append(ConsistencyIssue(
                    issue_type="unused_endpoint",
                    severity="info",
                    message=f"后端存在但前端未使用的API: {backend_endpoint.method} {backend_endpoint.path}",
                    backend_file="后端API文件"
                ))

        print(f"  *  缺失的端点: {len(missing_endpoints)}")
        print(f"  *  未使用的端点: {len(unused_endpoints)}")

    def check_model_consistency(self):
        """检查数据模型一致性"""
        print("\n* 检查数据模型一致性...")

        # 检查前端类型定义
        asset_types_file = self.frontend_path / "src/types/asset.ts"
        backend_model_file = self.backend_path / "src/models/asset.py"

        if asset_types_file.exists() and backend_model_file.exists():
            frontend_fields = self.extract_type_fields(asset_types_file)
            backend_fields = self.extract_model_fields(backend_model_file)

            # 找出前端有但后端没有的字段
            missing_in_backend = set(frontend_fields) - set(backend_fields)
            for field in missing_in_backend:
                self.issues.append(ConsistencyIssue(
                    issue_type="missing_field",
                    severity="warning",
                    message=f"前端类型定义中存在但后端模型中缺失的字段: {field}",
                    frontend_file=str(asset_types_file)
                ))

            # 找出后端有但前端没有的字段
            missing_in_frontend = set(backend_fields) - set(frontend_fields)
            for field in missing_in_frontend:
                self.issues.append(ConsistencyIssue(
                    issue_type="missing_field",
                    severity="warning",
                    message=f"后端模型中存在但前端类型定义中缺失的字段: {field}",
                    backend_file=str(backend_model_file)
                ))

            print(f"  *  前端缺失字段: {len(missing_in_frontend)}")
            print(f"  *  后端缺失字段: {len(missing_in_backend)}")

    def check_response_format_consistency(self, backend_endpoints: Dict[str, APIEndpoint]):
        """检查响应格式一致性"""
        print("\n* 检查响应格式一致性...")

        # 检查是否有统一的响应模型
        response_models = {}
        for endpoint in backend_endpoints.values():
            if endpoint.response_model:
                response_models[endpoint.response_model] = response_models.get(endpoint.response_model, 0) + 1

        # 检查响应模型命名规范
        for model_name in response_models:
            if not model_name.endswith('Response'):
                self.issues.append(ConsistencyIssue(
                    issue_type="response_format",
                    severity="warning",
                    message=f"响应模型命名不规范，建议以'Response'结尾: {model_name}",
                    backend_file="后端API文件"
                ))

        print(f"  * 响应模型数量: {len(response_models)}")

    def check_parameter_consistency(self, backend_endpoints: Dict[str, APIEndpoint], frontend_calls: Dict[str, APIEndpoint]):
        """检查参数一致性"""
        print("\n* 检查参数一致性...")

        # 这里可以扩展更复杂的参数检查逻辑
        # 目前只做基本的路径参数检查

        inconsistent_params = 0
        for key in set(backend_endpoints.keys()) & set(frontend_calls.keys()):
            backend_path = backend_endpoints[key].path
            frontend_path = frontend_calls[key].path

            # 检查路径参数是否一致
            backend_params = re.findall(r'\{([^}]+)\}', backend_path)
            frontend_params = re.findall(r'\{([^}]+)\}', frontend_path) or []

            if set(backend_params) != set(frontend_params):
                inconsistent_params += 1
                self.issues.append(ConsistencyIssue(
                    issue_type="parameter_mismatch",
                    severity="critical",
                    message=f"路径参数不匹配: 后端={backend_params}, 前端={frontend_params}",
                    backend_file="后端API文件",
                    frontend_file="前端服务文件"
                ))

        print(f"  *  参数不匹配的端点: {inconsistent_params}")

    def extract_type_fields(self, types_file: Path) -> Set[str]:
        """从类型文件中提取字段名"""
        fields = set()
        try:
            with open(types_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 使用正则表达式提取接口字段
            interface_pattern = r'interface\s+\w+\s*\{([^}]+)\}'
            matches = re.finditer(interface_pattern, content, re.DOTALL)

            for match in matches:
                interface_content = match.group(1)
                field_pattern = r'(\w+)(?:\?)?\s*:'
                field_matches = re.findall(field_pattern, interface_content)
                fields.update(field_matches)

        except Exception as e:
            print(f"无法提取类型字段: {e}")

        return fields

    def extract_model_fields(self, model_file: Path) -> Set[str]:
        """从模型文件中提取字段名"""
        fields = set()
        try:
            with open(model_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 使用正则表达式提取模型字段
            field_pattern = r'(\w+)\s*=\s*Column\s*\('
            field_matches = re.findall(field_pattern, content)
            fields.update(field_matches)

        except Exception as e:
            print(f"无法提取模型字段: {e}")

        return fields

    def print_summary(self):
        """打印检查结果摘要"""
        if not self.issues:
            print("\n✅ 所有API一致性检查通过！")
            return

        print("\n* 问题摘要:")

        # 按严重程度分组
        critical = [i for i in self.issues if i.severity == "critical"]
        warnings = [i for i in self.issues if i.severity == "warning"]
        info = [i for i in self.issues if i.severity == "info"]

        print(f"  * 严重问题: {len(critical)}")
        print(f"  *  警告: {len(warnings)}")
        print(f"  *  信息: {len(info)}")

        if critical:
            print("\n* 严重问题:")
            for issue in critical:
                print(f"  - {issue.message}")

        if warnings:
            print("\n*  警告:")
            for issue in warnings[:5]:  # 只显示前5个警告
                print(f"  - {issue.message}")
            if len(warnings) > 5:
                print(f"  ... 还有 {len(warnings) - 5} 个警告")

    def save_report(self, output_file: str):
        """保存检查报告到文件"""
        report = {
            "timestamp": "2025-01-20T12:00:00Z",
            "total_issues": len(self.issues),
            "issues": [
                {
                    "type": issue.issue_type,
                    "severity": issue.severity,
                    "message": issue.message,
                    "frontend_file": issue.frontend_file,
                    "backend_file": issue.backend_file,
                    "line_number": issue.line_number
                }
                for issue in self.issues
            ]
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存到: {output_file}")


def main():
    """主函数"""
    if len(sys.argv) != 3:
        print("用法: python api_consistency_check.py <backend_path> <frontend_path>")
        print("示例: python api_consistency_check.py backend frontend")
        sys.exit(1)

    backend_path = sys.argv[1]
    frontend_path = sys.argv[2]

    checker = APIConsistencyChecker(backend_path, frontend_path)
    issues = checker.run_checks()

    checker.print_summary()
    checker.save_report("api_consistency_report.json")

    # 如果有严重问题，返回非零退出码
    critical_issues = [i for i in issues if i.severity == "critical"]
    if critical_issues:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()