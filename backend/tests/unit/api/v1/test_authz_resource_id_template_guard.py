"""守卫测试：require_authz 的 resource_id 模板必须与路由路径参数一致。"""

import ast
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api

_ROUTE_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}
_READ_WITHOUT_RESOURCE_ID_ALLOWLIST: set[str] = set()


def _iter_api_modules() -> list[Path]:
    api_root = Path(__file__).resolve().parents[4] / "src" / "api" / "v1"
    return sorted(api_root.rglob("*.py"))


def _read_python_source(module_path: Path) -> str:
    # `utf-8-sig` removes BOM if present (e.g. U+FEFF), keeping AST parse stable.
    return module_path.read_text(encoding="utf-8-sig")


def _extract_route_paths(function_node: ast.AST) -> list[str]:
    if not isinstance(function_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return []
    paths: list[str] = []
    for decorator in function_node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        if not isinstance(decorator.func, ast.Attribute):
            continue
        if decorator.func.attr not in _ROUTE_METHODS:
            continue
        router_name = decorator.func.value
        if not isinstance(router_name, ast.Name) or router_name.id != "router":
            continue
        if not decorator.args:
            continue
        first_arg = decorator.args[0]
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            paths.append(first_arg.value)
    return paths


def _extract_template_resource_ids(function_node: ast.AST) -> list[str]:
    resource_ids: list[str] = []
    for sub_node in ast.walk(function_node):
        if not isinstance(sub_node, ast.Call):
            continue
        if not (
            isinstance(sub_node.func, ast.Name) and sub_node.func.id == "require_authz"
        ):
            continue
        for keyword in sub_node.keywords:
            if keyword.arg != "resource_id":
                continue
            if not (
                isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                continue
            resource_id = keyword.value.value
            if resource_id.startswith("{") and resource_id.endswith("}"):
                resource_ids.append(resource_id[1:-1])
    return resource_ids


def _extract_require_authz_calls(function_node: ast.AST) -> list[dict[str, ast.expr]]:
    calls: list[dict[str, ast.expr]] = []
    for sub_node in ast.walk(function_node):
        if not isinstance(sub_node, ast.Call):
            continue
        if not (
            isinstance(sub_node.func, ast.Name) and sub_node.func.id == "require_authz"
        ):
            continue
        calls.append(
            {
                keyword.arg: keyword.value
                for keyword in sub_node.keywords
                if keyword.arg is not None
            }
        )
    return calls


def _is_read_call(call_kwargs: dict[str, ast.expr]) -> bool:
    action_value = call_kwargs.get("action")
    return (
        isinstance(action_value, ast.Constant)
        and isinstance(action_value.value, str)
        and action_value.value == "read"
    )


def _has_any_resource_id(call_kwargs_list: list[dict[str, ast.expr]]) -> bool:
    return any("resource_id" in call_kwargs for call_kwargs in call_kwargs_list)


def test_require_authz_resource_id_templates_should_match_route_path_params() -> None:
    """路由函数里 require_authz 的模板型 resource_id 必须能在路径参数中找到。"""
    violations: list[str] = []

    for module_path in _iter_api_modules():
        module_source = _read_python_source(module_path)
        try:
            module_ast = ast.parse(module_source)
        except SyntaxError as exc:
            violations.append(f"{module_path}: 语法错误 {exc}")
            continue

        for node in module_ast.body:
            route_paths = _extract_route_paths(node)
            if not route_paths:
                continue

            template_resource_ids = _extract_template_resource_ids(node)
            if not template_resource_ids:
                continue

            for resource_param in template_resource_ids:
                if any(
                    re.search(r"\{" + re.escape(resource_param) + r"\}", route_path)
                    for route_path in route_paths
                ):
                    continue
                line_no = getattr(node, "lineno", 1)
                violations.append(
                    f"{module_path}:{line_no} function={getattr(node, 'name', '<unknown>')} "
                    f"resource_id='{{{resource_param}}}' routes={route_paths}"
                )

    assert not violations, (
        "发现 require_authz resource_id 模板与路由路径参数不一致：\n"
        + "\n".join(violations)
    )


def test_read_endpoints_with_id_path_should_not_omit_resource_id_unless_allowlisted() -> (
    None
):
    """
    read 端点若带 *_id 路径参数，默认应绑定 resource_id。

    仅允许明确列入 allowlist 的历史特例继续无 resource_id 运行。
    """

    offenders: set[str] = set()
    api_root = Path(__file__).resolve().parents[4] / "src" / "api" / "v1"

    for module_path in _iter_api_modules():
        module_source = _read_python_source(module_path)
        try:
            module_ast = ast.parse(module_source)
        except SyntaxError as exc:
            relative_module = module_path.relative_to(api_root).as_posix()
            offenders.add(f"{relative_module}:<syntax-error>:{exc.msg}")
            continue

        for node in module_ast.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            route_paths = _extract_route_paths(node)
            if not route_paths:
                continue

            route_params = {
                match.group(1)
                for route_path in route_paths
                for match in re.finditer(r"\{([^}]+)\}", route_path)
            }
            id_params = {param for param in route_params if param.endswith("_id")}
            if not id_params:
                continue

            require_authz_calls = _extract_require_authz_calls(node)
            read_calls = [
                call_kwargs
                for call_kwargs in require_authz_calls
                if _is_read_call(call_kwargs)
            ]
            if not read_calls:
                continue

            if _has_any_resource_id(read_calls):
                continue

            relative_module = module_path.relative_to(api_root).as_posix()
            offenders.add(f"{relative_module}:{node.name}")

    unexpected = sorted(offenders - _READ_WITHOUT_RESOURCE_ID_ALLOWLIST)
    assert not unexpected, (
        "以下 read 端点带 *_id 路径参数但未绑定 resource_id（且不在 allowlist）：\n"
        + "\n".join(unexpected)
    )


def test_read_without_resource_id_allowlist_should_be_empty_after_legacy_route_removal() -> (
    None
):
    """No current read route may omit a resource ID."""
    assert _READ_WITHOUT_RESOURCE_ID_ALLOWLIST == set()
