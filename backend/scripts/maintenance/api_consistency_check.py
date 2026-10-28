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
from dataclasses import dataclass
from pathlib import Path


@dataclass
class APIEndpoint:
    """API端点信息"""

    path: str
    method: str
    response_model: str = None
    parameters: list[str] = None
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
        self.issues: list[ConsistencyIssue] = []

    def run_checks(self) -> list[ConsistencyIssue]:
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

    def extract_backend_endpoints(self) -> dict[str, APIEndpoint]:
        """静态解析已挂载的路由图，组合模块、路由器和挂载前缀。"""
        modules = {}
        for source in self.backend_path.glob("src/api/v1/**/*.py"):
            parts = source.relative_to(self.backend_path).with_suffix("").parts
            module = ".".join(parts[:-1] if parts[-1] == "__init__" else parts)
            try:
                modules[module] = (
                    source,
                    ast.parse(source.read_text(encoding="utf-8")),
                )
            except (OSError, UnicodeError, SyntaxError) as exc:
                self.issues.append(
                    ConsistencyIssue(
                        "extraction_error",
                        "critical",
                        f"无法解析路由模块 {source}: {exc}",
                        backend_file=str(source),
                    )
                )

        bindings = {}
        imports = {}
        prefixes = {}
        routes = {}
        includes = {}
        registrations = []

        def reference(module, expression):
            if isinstance(expression, ast.Name):
                return bindings.get((module, expression.id), (module, expression.id))
            if isinstance(expression, ast.Attribute):
                parent = reference(module, expression.value)
                if parent is not None and parent[1] == "":
                    return (parent[0], expression.attr)
            return None

        def keyword(call, name, default=""):
            for item in call.keywords:
                if item.arg == name:
                    if not isinstance(item.value, ast.Constant) or not isinstance(
                        item.value.value, str
                    ):
                        raise ValueError(f"无法静态解析路由参数 {name}")
                    return item.value.value
            return default

        for module, (source, tree) in modules.items():
            imports[module] = set()
            package = (
                module if source.name == "__init__.py" else module.rsplit(".", 1)[0]
            )
            for node in tree.body:
                if isinstance(node, ast.ImportFrom):
                    base = node.module or ""
                    if node.level:
                        base = ".".join(
                            package.split(".")[
                                : len(package.split(".")) - node.level + 1
                            ]
                        ) + ("." + base if base else "")
                    for alias in node.names:
                        candidate = f"{base}.{alias.name}"
                        target = (
                            (candidate, "")
                            if candidate in modules
                            else (base, alias.name)
                        )
                        bindings[(module, alias.asname or alias.name)] = target
                        imports[module].add(target[0])

        for module, (source, tree) in modules.items():
            for node in tree.body:
                if (
                    isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                ):
                    key = (module, node.targets[0].id)
                    if isinstance(node.value, ast.Call) and reference(
                        module, node.value.func
                    ) == ("fastapi", "APIRouter"):
                        prefixes[key] = keyword(node.value, "prefix")
                    elif isinstance(node.value, (ast.Name, ast.Attribute)):
                        target = reference(module, node.value)
                        if target is not None:
                            bindings[key] = target
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for decorator in node.decorator_list:
                        if not isinstance(decorator, ast.Call) or not isinstance(
                            decorator.func, ast.Attribute
                        ):
                            continue
                        method = decorator.func.attr.upper()
                        if method not in {
                            "GET",
                            "POST",
                            "PUT",
                            "DELETE",
                            "PATCH",
                            "HEAD",
                            "OPTIONS",
                        }:
                            continue
                        if not decorator.args or not isinstance(
                            decorator.args[0], ast.Constant
                        ):
                            raise ValueError(
                                f"无法静态解析路由路径: {source}:{node.lineno}"
                            )
                        path = decorator.args[0].value
                        if not isinstance(path, str):
                            raise ValueError(
                                f"路由路径不是字符串: {source}:{node.lineno}"
                            )
                        model = next(
                            (
                                ast.unparse(k.value)
                                for k in decorator.keywords
                                if k.arg == "response_model"
                            ),
                            None,
                        )
                        owner = reference(module, decorator.func.value)
                        routes.setdefault(owner, []).append(
                            APIEndpoint(path, method, model)
                        )
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                    call = node.value
                    if not isinstance(call.func, ast.Attribute) or not call.args:
                        continue
                    if call.func.attr == "include_router":
                        parent = reference(module, call.func.value)
                        includes.setdefault(parent, []).append(
                            (reference(module, call.args[0]), keyword(call, "prefix"))
                        )
                    elif call.func.attr == "register_router":
                        registrations.append(
                            (
                                module,
                                reference(module, call.args[0]),
                                keyword(call, "prefix"),
                            )
                        )

        reachable = set()

        def visit(module):
            if module in reachable:
                return
            reachable.add(module)
            for child in imports.get(module, ()):
                visit(child)

        visit("src.api.v1")
        endpoints = {}

        def collect(key, prefix, ancestors):
            if key in ancestors:
                raise ValueError(f"循环路由挂载: {key}")
            ancestors = ancestors | {key}
            alias = bindings.get(key)
            if alias is not None and alias != key:
                collect(alias, prefix, ancestors)
                return
            if key not in prefixes:
                raise ValueError(f"无法解析已挂载的路由器: {key}")
            prefix += prefixes.get(key, "")
            for route in routes.get(key, ()):
                path = prefix + route.path
                if path == "/api/v1" or path.startswith("/api/v1/"):
                    path = path[len("/api/v1") :]
                endpoints[f"{route.method}:{path}"] = APIEndpoint(
                    path, route.method, route.response_model
                )
            for child, mount_prefix in includes.get(key, ()):
                collect(child, prefix + mount_prefix, ancestors)

        collect(("src.api.v1", "api_router"), "", set())
        for module, router, prefix in registrations:
            if module in reachable:
                collect(router, prefix, set())
        return endpoints

    def extract_frontend_api_calls(self) -> dict[str, APIEndpoint]:
        """提取前端API调用"""
        calls = {}

        # 查找所有服务文件
        service_files = list(self.frontend_path.glob("src/services/*.ts"))

        for service_file in service_files:
            try:
                with open(service_file, encoding="utf-8") as f:
                    content = f.read()

                # 使用正则表达式提取API调用
                api_call_pattern = (
                    r'apiClient\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
                )
                matches = re.finditer(api_call_pattern, content)

                for match in matches:
                    method = match.group(1).upper()
                    path = match.group(2)

                    endpoint_key = f"{method}:{path}"
                    calls[endpoint_key] = APIEndpoint(path=path, method=method)

            except Exception as e:
                self.issues.append(
                    ConsistencyIssue(
                        issue_type="extraction_error",
                        severity="warning",
                        message=f"无法解析前端服务文件 {service_file}: {str(e)}",
                        frontend_file=str(service_file),
                    )
                )

        return calls

    def check_path_consistency(
        self,
        backend_endpoints: dict[str, APIEndpoint],
        frontend_calls: dict[str, APIEndpoint],
    ):
        """检查路径一致性"""
        print("\n* 检查API路径一致性...")

        # 找出前端调用但后端不存在的API
        missing_endpoints = []
        for key, frontend_call in frontend_calls.items():
            if key not in backend_endpoints:
                missing_endpoints.append(key)
                self.issues.append(
                    ConsistencyIssue(
                        issue_type="missing_endpoint",
                        severity="critical",
                        message=f"前端调用但后端不存在的API: {frontend_call.method} {frontend_call.path}",
                        frontend_file="前端服务文件",
                    )
                )

        # 找出后端存在但前端未使用的API（信息性）
        unused_endpoints = []
        for key, backend_endpoint in backend_endpoints.items():
            if key not in frontend_calls:
                unused_endpoints.append(key)
                self.issues.append(
                    ConsistencyIssue(
                        issue_type="unused_endpoint",
                        severity="info",
                        message=f"后端存在但前端未使用的API: {backend_endpoint.method} {backend_endpoint.path}",
                        backend_file="后端API文件",
                    )
                )

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
                self.issues.append(
                    ConsistencyIssue(
                        issue_type="missing_field",
                        severity="warning",
                        message=f"前端类型定义中存在但后端模型中缺失的字段: {field}",
                        frontend_file=str(asset_types_file),
                    )
                )

            # 找出后端有但前端没有的字段
            missing_in_frontend = set(backend_fields) - set(frontend_fields)
            for field in missing_in_frontend:
                self.issues.append(
                    ConsistencyIssue(
                        issue_type="missing_field",
                        severity="warning",
                        message=f"后端模型中存在但前端类型定义中缺失的字段: {field}",
                        backend_file=str(backend_model_file),
                    )
                )

            print(f"  *  前端缺失字段: {len(missing_in_frontend)}")
            print(f"  *  后端缺失字段: {len(missing_in_backend)}")

    def check_response_format_consistency(
        self, backend_endpoints: dict[str, APIEndpoint]
    ):
        """检查响应格式一致性"""
        print("\n* 检查响应格式一致性...")

        # 检查是否有统一的响应模型
        response_models = {}
        for endpoint in backend_endpoints.values():
            if endpoint.response_model:
                response_models[endpoint.response_model] = (
                    response_models.get(endpoint.response_model, 0) + 1
                )

        # 检查响应模型命名规范
        for model_name in response_models:
            if not model_name.endswith("Response"):
                self.issues.append(
                    ConsistencyIssue(
                        issue_type="response_format",
                        severity="warning",
                        message=f"响应模型命名不规范，建议以'Response'结尾: {model_name}",
                        backend_file="后端API文件",
                    )
                )

        print(f"  * 响应模型数量: {len(response_models)}")

    def check_parameter_consistency(
        self,
        backend_endpoints: dict[str, APIEndpoint],
        frontend_calls: dict[str, APIEndpoint],
    ):
        """检查参数一致性"""
        print("\n* 检查参数一致性...")

        # 这里可以扩展更复杂的参数检查逻辑
        # 目前只做基本的路径参数检查

        inconsistent_params = 0
        for key in set(backend_endpoints.keys()) & set(frontend_calls.keys()):
            backend_path = backend_endpoints[key].path
            frontend_path = frontend_calls[key].path

            # 检查路径参数是否一致
            backend_params = re.findall(r"\{([^}]+)\}", backend_path)
            frontend_params = re.findall(r"\{([^}]+)\}", frontend_path) or []

            if set(backend_params) != set(frontend_params):
                inconsistent_params += 1
                self.issues.append(
                    ConsistencyIssue(
                        issue_type="parameter_mismatch",
                        severity="critical",
                        message=f"路径参数不匹配: 后端={backend_params}, 前端={frontend_params}",
                        backend_file="后端API文件",
                        frontend_file="前端服务文件",
                    )
                )

        print(f"  *  参数不匹配的端点: {inconsistent_params}")

    def extract_type_fields(self, types_file: Path) -> set[str]:
        """从类型文件中提取字段名"""
        fields = set()
        try:
            with open(types_file, encoding="utf-8") as f:
                content = f.read()

            # 使用正则表达式提取接口字段
            interface_pattern = r"interface\s+\w+\s*\{([^}]+)\}"
            matches = re.finditer(interface_pattern, content, re.DOTALL)

            for match in matches:
                interface_content = match.group(1)
                field_pattern = r"(\w+)(?:\?)?\s*:"
                field_matches = re.findall(field_pattern, interface_content)
                fields.update(field_matches)

        except Exception as e:
            print(f"无法提取类型字段: {e}")

        return fields

    def extract_model_fields(self, model_file: Path) -> set[str]:
        """从模型文件中提取字段名"""
        fields = set()
        try:
            with open(model_file, encoding="utf-8") as f:
                content = f.read()

            # 使用正则表达式提取模型字段
            field_pattern = r"(\w+)\s*=\s*Column\s*\("
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
                    "line_number": issue.line_number,
                }
                for issue in self.issues
            ],
        }

        with open(output_file, "w", encoding="utf-8") as f:
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
