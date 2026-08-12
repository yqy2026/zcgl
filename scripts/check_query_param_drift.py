#!/usr/bin/env python3
"""Block drift between selected frontend query params and FastAPI query contracts.

The mappings below intentionally cover stable endpoint/service pairs only. They
are an auditable extension point, not a discovery mechanism for every query in
the application. Each mapping compares three independently maintained surfaces:

* FastAPI query-compatible endpoint/dependency parameters;
* the frontend ``*Params`` interface; and
* the parameters actually sent by the frontend service method.

Run from the repository root:
    python scripts/check_query_param_drift.py
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ContractMapping:
    """One explicit backend endpoint and frontend service query contract."""

    name: str
    backend_file: Path
    backend_symbol: str
    backend_route_symbol: str | None
    backend_route_path: str | None
    backend_route_dependency: str | None
    frontend_type_file: Path
    frontend_type: str
    service_file: Path
    service_method: str
    request_method: str
    request_path: str
    backend_registration_file: Path | None = None
    backend_registered_router: str | None = None


@dataclass(frozen=True)
class DriftIssue:
    """A source-located incompatibility in one mapped query contract."""

    contract: str
    kind: str
    field: str | None
    path: Path
    detail: str
    line: int | None = None
    compared_path: Path | None = None
    compared_line: int | None = None


@dataclass(frozen=True)
class RequestFieldSurface:
    """Fields and the outbound request line for one service method."""

    fields: dict[str, int]
    line: int


@dataclass(frozen=True)
class OutboundRequest:
    """The verified ``params`` value and endpoint of one apiClient call."""

    params_value: str
    params_index: int
    method: str
    path: str


@dataclass(frozen=True)
class MethodSurface:
    """The body and declared parameters of one mapped service method."""

    body: str
    body_offset: int
    parameters: str


CONTRACT_MAPPINGS: tuple[ContractMapping, ...] = (
    ContractMapping(
        name="parties",
        backend_file=ROOT / "backend/src/api/v1/party.py",
        backend_symbol="list_parties",
        backend_route_symbol="list_parties",
        backend_route_path="/parties",
        backend_route_dependency=None,
        frontend_type_file=ROOT / "frontend/src/types/party.ts",
        frontend_type="PartyListParams",
        service_file=ROOT / "frontend/src/services/partyService.ts",
        service_method="getParties",
        request_method="get",
        request_path="/parties",
    ),
    ContractMapping(
        name="contract_groups",
        backend_file=ROOT / "backend/src/api/v1/contracts/contract_groups.py",
        backend_symbol="list_contract_groups",
        backend_route_symbol="list_contract_groups",
        backend_route_path="/contract-groups",
        backend_route_dependency=None,
        frontend_type_file=ROOT / "frontend/src/types/contractGroup.ts",
        frontend_type="ContractGroupListParams",
        service_file=ROOT / "frontend/src/services/contractGroupService.ts",
        service_method="getContractGroups",
        request_method="get",
        request_path="/contract-groups",
    ),
    ContractMapping(
        name="ledger_entries",
        backend_file=ROOT / "backend/src/api/v1/contracts/ledger.py",
        backend_symbol="resolve_ledger_query_params",
        backend_route_symbol="get_ledger_entries",
        backend_route_path="/ledger/entries",
        backend_route_dependency="resolve_ledger_query_params",
        frontend_type_file=ROOT / "frontend/src/types/ledger.ts",
        frontend_type="LedgerListParams",
        service_file=ROOT / "frontend/src/services/ledgerService.ts",
        service_method="getLedgerEntries",
        request_method="get",
        request_path="/ledger/entries",
    ),
    ContractMapping(
        name="projects",
        backend_file=ROOT / "backend/src/api/v1/assets/project.py",
        backend_symbol="list_projects",
        backend_route_symbol="list_projects",
        backend_route_path="",
        backend_route_dependency=None,
        frontend_type_file=ROOT / "frontend/src/types/project.ts",
        frontend_type="ProjectSearchParams",
        service_file=ROOT / "frontend/src/services/projectService.ts",
        service_method="getProjects",
        request_method="get",
        request_path="/projects",
        backend_registration_file=ROOT / "backend/src/api/v1/__init__.py",
        backend_registered_router="project_router",
    ),
    ContractMapping(
        name="project_tenants",
        backend_file=ROOT / "backend/src/api/v1/assets/project.py",
        backend_symbol="get_project_tenants",
        backend_route_symbol="get_project_tenants",
        backend_route_path="/{project_id}/tenants",
        backend_route_dependency=None,
        frontend_type_file=ROOT / "frontend/src/types/project.ts",
        frontend_type="ProjectTenantParams",
        service_file=ROOT / "frontend/src/services/projectService.ts",
        service_method="getProjectTenants",
        request_method="get",
        request_path="/projects/{project_id}/tenants",
        backend_registration_file=ROOT / "backend/src/api/v1/__init__.py",
        backend_registered_router="project_router",
    ),
    ContractMapping(
        name="project_analytics",
        backend_file=ROOT / "backend/src/api/v1/assets/project.py",
        backend_symbol="get_project_analytics",
        backend_route_symbol="get_project_analytics",
        backend_route_path="/{project_id}/analytics",
        backend_route_dependency=None,
        frontend_type_file=ROOT / "frontend/src/types/project.ts",
        frontend_type="ProjectAnalyticsParams",
        service_file=ROOT / "frontend/src/services/projectService.ts",
        service_method="getProjectAnalytics",
        request_method="get",
        request_path="/projects/{project_id}/analytics",
        backend_registration_file=ROOT / "backend/src/api/v1/__init__.py",
        backend_registered_router="project_router",
    ),
    ContractMapping(
        name="property_certificates",
        backend_file=ROOT / "backend/src/api/v1/assets/property_certificate.py",
        backend_symbol="list_certificates",
        backend_route_symbol="list_certificates",
        backend_route_path="",
        backend_route_dependency=None,
        frontend_type_file=ROOT / "frontend/src/types/propertyCertificate.ts",
        frontend_type="PropertyCertificateListParams",
        service_file=ROOT / "frontend/src/services/propertyCertificateService.ts",
        service_method="listCertificates",
        request_method="get",
        request_path="/property-certificates",
    ),
)


class SourceParseError(ValueError):
    """Raised when a mapped source cannot be parsed deterministically."""

    def __init__(self, message: str, *, line: int | None = None) -> None:
        super().__init__(message)
        self.line = line


_IDENTIFIER_RE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
_INTERFACE_RE = re.compile(
    r"\bexport\s+interface\s+([A-Za-z_$][A-Za-z0-9_$]*)(?P<heritage>[^\{]*)\{"
)
_METHOD_RE_TEMPLATE = r"\basync\s+{name}\s*\("
_DYNAMIC_PARAMS_CALL_RE = re.compile(
    r"\A([A-Za-z_$][A-Za-z0-9_$]*)\s*\(\s*params\s*\)\Z"
)
_FASTAPI_PARAMETER_MARKERS = {
    "Body",
    "Cookie",
    "Depends",
    "File",
    "Form",
    "Header",
    "Path",
    "Query",
    "Security",
}


def _read_source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SourceParseError(f"cannot decode source as UTF-8: {exc}") from exc
    except OSError as exc:
        raise SourceParseError(f"cannot read source: {exc}") from exc


def _python_call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _python_target_binds_name(target: ast.expr | None, name: str) -> bool:
    if isinstance(target, ast.Name):
        return target.id == name
    if isinstance(target, ast.Starred):
        return _python_target_binds_name(target.value, name)
    if isinstance(target, (ast.List, ast.Tuple)):
        return any(_python_target_binds_name(element, name) for element in target.elts)
    return False


def _has_unrebound_fastapi_symbol(
    tree: ast.Module, name: str, modules: set[str]
) -> bool:
    imported = False
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            for imported_name in node.names:
                local_name = imported_name.asname or imported_name.name
                if local_name != name:
                    continue
                if (
                    node.module in modules
                    and imported_name.name == name
                    and imported_name.asname is None
                ):
                    imported = True
                    continue
                return False
        elif isinstance(node, ast.Import) and any(
            (alias.asname or alias.name.split(".")[0]) == name for alias in node.names
        ):
            return False

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == name:
                return False
        elif isinstance(node, ast.arg):
            if node.arg == name:
                return False
        elif isinstance(
            node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr)
        ):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(_python_target_binds_name(target, name) for target in targets):
                return False
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            if _python_target_binds_name(node.target, name):
                return False
        elif isinstance(node, ast.With):
            if any(
                _python_target_binds_name(item.optional_vars, name)
                for item in node.items
            ):
                return False
        elif isinstance(node, ast.ExceptHandler) and node.name == name:
            return False
    return imported


def _assert_no_fastapi_parameter_marker_aliases(tree: ast.Module) -> None:
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.module not in {
            "fastapi",
            "fastapi.params",
        }:
            continue
        for imported_name in node.names:
            if (
                imported_name.name in _FASTAPI_PARAMETER_MARKERS
                and imported_name.asname is not None
            ):
                raise SourceParseError(
                    "unsupported FastAPI parameter marker alias: "
                    f"{imported_name.name} as {imported_name.asname}",
                    line=node.lineno,
                )

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        target_names = [target.id for target in targets if isinstance(target, ast.Name)]
        source_marker = _python_call_name(value) if value is not None else None
        if source_marker in _FASTAPI_PARAMETER_MARKERS and target_names:
            raise SourceParseError(
                f"unsupported FastAPI parameter marker rebinding: {source_marker}",
                line=node.lineno,
            )
        if any(name in _FASTAPI_PARAMETER_MARKERS for name in target_names):
            raise SourceParseError(
                "unsupported FastAPI parameter marker rebinding",
                line=node.lineno,
            )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        marker = _python_call_name(node.func)
        if marker not in _FASTAPI_PARAMETER_MARKERS:
            continue
        if not isinstance(node.func, ast.Name) or not _has_unrebound_fastapi_symbol(
            tree, marker, {"fastapi", "fastapi.params"}
        ):
            raise SourceParseError(
                f"cannot verify FastAPI parameter marker provenance: {marker}",
                line=node.lineno,
            )


def _is_fastapi_parameter_default(default: ast.expr | None, names: set[str]) -> bool:
    return isinstance(default, ast.Call) and _python_call_name(default.func) in names


def _is_dependency_default(default: ast.expr | None) -> bool:
    return _is_fastapi_parameter_default(default, {"Depends", "Security"})


def _is_expected_dependency(default: ast.expr | None, dependency: str) -> bool:
    return (
        isinstance(default, ast.Call)
        and _python_call_name(default.func) == "Depends"
        and len(default.args) == 1
        and not default.keywords
        and isinstance(default.args[0], ast.Name)
        and default.args[0].id == dependency
    )


def _is_non_query_default(default: ast.expr | None) -> bool:
    return _is_fastapi_parameter_default(
        default, {"Body", "Cookie", "File", "Form", "Header", "Path"}
    )


def _annotation_contains_marker(annotation: ast.expr | None, names: set[str]) -> bool:
    if annotation is None:
        return False
    return any(
        isinstance(node, ast.Call) and _python_call_name(node.func) in names
        for node in ast.walk(annotation)
    )


def _is_dependency_annotation(annotation: ast.expr | None) -> bool:
    return _annotation_contains_marker(annotation, {"Depends", "Security"})


def _is_query_annotation(annotation: ast.expr | None) -> bool:
    return _annotation_contains_marker(annotation, {"Query"})


def _is_non_query_annotation(annotation: ast.expr | None) -> bool:
    return _annotation_contains_marker(
        annotation, {"Body", "Cookie", "File", "Form", "Header", "Path"}
    )


def _is_proven_scalar_annotation(annotation: ast.expr | None) -> bool:
    if isinstance(annotation, ast.Name):
        return annotation.id in {"bool", "float", "int", "str"}
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return _is_proven_scalar_annotation(
            annotation.left
        ) and _is_proven_scalar_annotation(annotation.right)
    if isinstance(annotation, ast.Constant):
        return annotation.value is None
    if isinstance(annotation, ast.Subscript) and _python_call_name(
        annotation.value
    ) in {
        "Literal",
    }:
        return True
    return False


def _is_query_default(default: ast.expr | None, annotation: ast.expr | None) -> bool:
    if _is_dependency_annotation(annotation) or _is_non_query_annotation(annotation):
        return False
    if _is_query_annotation(annotation):
        return True
    if _is_fastapi_parameter_default(default, {"Query"}):
        return True
    if default is None:
        return False
    if _is_dependency_default(default) or _is_non_query_default(default):
        return False
    return _is_proven_scalar_annotation(annotation)


def _line_number(source: str, index: int) -> int:
    return source.count("\n", 0, index) + 1


def _query_marker_calls(
    default: ast.expr | None, annotation: ast.expr | None
) -> list[ast.Call]:
    nodes = [node for node in (default, annotation) if node is not None]
    return [
        node
        for root in nodes
        for node in ast.walk(root)
        if isinstance(node, ast.Call) and _python_call_name(node.func) == "Query"
    ]


def _query_wire_name(argument: ast.arg, default: ast.expr | None) -> str:
    query_calls = _query_marker_calls(default, argument.annotation)
    for query_call in query_calls:
        if any(keyword.arg is None for keyword in query_call.keywords):
            raise SourceParseError(
                f"unsupported Query keyword expansion for mapped contract field: {argument.arg}",
                line=query_call.lineno,
            )
        if any(keyword.arg == "alias" for keyword in query_call.keywords):
            raise SourceParseError(
                f"unsupported Query alias for mapped contract field: {argument.arg}",
                line=query_call.lineno,
            )
    return argument.arg


def _has_unproven_required_parameter(
    default: ast.expr | None, annotation: ast.expr | None
) -> bool:
    return (
        default is None
        and not _is_dependency_annotation(annotation)
        and not _is_non_query_annotation(annotation)
    )


def _has_unproven_optional_parameter(
    default: ast.expr | None, annotation: ast.expr | None
) -> bool:
    return (
        default is not None
        and not _is_dependency_default(default)
        and not _is_non_query_default(default)
        and not _is_dependency_annotation(annotation)
        and not _is_non_query_annotation(annotation)
        and not _is_fastapi_parameter_default(default, {"Query"})
        and not _is_proven_scalar_annotation(annotation)
    )


def parse_backend_query_params(path: Path, symbol: str) -> dict[str, int]:
    """Extract FastAPI query-compatible parameters from a named function.

    Explicit ``Query`` declarations and ordinary optional scalar parameters are
    query-compatible. A mapped required parameter without a FastAPI marker is
    ambiguous without route-path analysis, so it blocks rather than being
    silently omitted. Query aliases are also rejected until wire-name parsing is
    implemented for an explicit mapped contract. Aliased FastAPI parameter-marker
    imports are rejected because their request location and wire-name semantics
    cannot be determined by this conservative parser.
    """

    source = _read_source(path)
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise SourceParseError(
            f"Python syntax error: {exc.msg}", line=exc.lineno
        ) from exc

    _assert_no_fastapi_parameter_marker_aliases(tree)

    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == symbol
    ]
    if len(functions) != 1:
        raise SourceParseError(f"cannot determine unique top-level function: {symbol}")
    function = functions[0]

    positional_args = [*function.args.posonlyargs, *function.args.args]
    positional_defaults = [None] * (len(positional_args) - len(function.args.defaults))
    positional_defaults.extend(function.args.defaults)
    query_args = [
        *zip(positional_args, positional_defaults, strict=True),
        *zip(function.args.kwonlyargs, function.args.kw_defaults, strict=True),
    ]

    fields: dict[str, int] = {}
    for argument, default in query_args:
        if _is_query_default(default, argument.annotation):
            fields[_query_wire_name(argument, default)] = argument.lineno
            continue
        if _has_unproven_optional_parameter(default, argument.annotation):
            raise SourceParseError(
                f"cannot determine optional parameter location: {argument.arg}",
                line=argument.lineno,
            )
        if _has_unproven_required_parameter(default, argument.annotation):
            raise SourceParseError(
                f"cannot determine required parameter location: {argument.arg}",
                line=argument.lineno,
            )
    if not fields:
        raise SourceParseError(f"no query-compatible parameters found for: {symbol}")
    return fields


def _is_proven_fastapi_router_binding(tree: ast.Module, name: str) -> bool:
    if not _has_unrebound_fastapi_symbol(tree, "APIRouter", {"fastapi"}):
        return False

    bindings = [
        node
        for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        and any(
            isinstance(target, ast.Name) and target.id == name
            for target in (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
        )
    ]
    if len(bindings) != 1:
        return False
    value = bindings[0].value
    return isinstance(value, ast.Call) and _python_call_name(value.func) == "APIRouter"


def _parse_backend_route_path(
    path: Path,
    symbol: str,
    expected_method: str,
    expected_path: str,
    expected_dependency: str | None,
) -> None:
    """Prove a unique named FastAPI handler exposes the registered route path."""

    source = _read_source(path)
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise SourceParseError(
            f"Python syntax error: {exc.msg}", line=exc.lineno
        ) from exc

    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == symbol
    ]
    if len(functions) != 1:
        raise SourceParseError(f"cannot determine unique top-level function: {symbol}")
    function = functions[0]

    if expected_dependency is not None:
        defaults = [
            *function.args.defaults,
            *function.args.kw_defaults,
        ]
        if not any(
            _is_expected_dependency(default, expected_dependency)
            for default in defaults
        ):
            raise SourceParseError(
                f"cannot verify mapped backend route dependency: {expected_dependency}",
                line=function.lineno,
            )

    routes: list[tuple[str, int]] = []
    for decorator in function.decorator_list:
        if not isinstance(decorator, ast.Call) or not isinstance(
            decorator.func, ast.Attribute
        ):
            continue
        if decorator.func.attr != expected_method:
            continue
        if not isinstance(
            decorator.func.value, ast.Name
        ) or not _is_proven_fastapi_router_binding(tree, decorator.func.value.id):
            raise SourceParseError(
                f"cannot verify FastAPI APIRouter binding: {symbol}",
                line=decorator.lineno,
            )
        if not decorator.args:
            raise SourceParseError(
                f"unsupported FastAPI route decorator: {symbol}", line=decorator.lineno
            )
        route_path = decorator.args[0]
        if not isinstance(route_path, ast.Constant) or not isinstance(
            route_path.value, str
        ):
            raise SourceParseError(
                f"unsupported FastAPI route path: {symbol}", line=decorator.lineno
            )
        routes.append((route_path.value, decorator.lineno))

    if expected_path == "":
        if not any(route_path == "" for route_path, _ in routes):
            raise SourceParseError(
                f"cannot verify mapped backend route path: {symbol}",
                line=function.lineno,
            )
        return
    if len(routes) != 1 or routes[0][0] != expected_path:
        line = routes[0][1] if len(routes) == 1 else function.lineno
        raise SourceParseError(
            f"cannot verify mapped backend route path: {symbol}", line=line
        )


def _parse_backend_registered_route_path(
    registration_path: Path,
    backend_path: Path,
    registered_router: str,
    local_path: str,
    expected_complete_path: str,
) -> None:
    """Prove an aggregated router prefix completes the backend route path."""

    source = _read_source(registration_path)
    try:
        tree = ast.parse(source, filename=str(registration_path))
    except SyntaxError as exc:
        raise SourceParseError(
            f"Python syntax error: {exc.msg}", line=exc.lineno
        ) from exc

    matching_imports: list[ast.ImportFrom] = []
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.level < 1:
            continue
        if not any(
            alias.name == "router" and alias.asname == registered_router
            for alias in node.names
        ):
            continue
        module_base = registration_path.parent
        for _ in range(node.level - 1):
            module_base = module_base.parent
        module_parts = [] if node.module is None else node.module.split(".")
        imported_path = module_base.joinpath(*module_parts).with_suffix(".py")
        if imported_path.resolve() == backend_path.resolve():
            matching_imports.append(node)
    if len(matching_imports) != 1 or any(
        _python_target_binds_name(target, registered_router)
        for node in ast.walk(tree)
        for target in (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
            if isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr))
            else []
        )
    ):
        raise SourceParseError(
            f"cannot verify registered backend router import: {registered_router}"
        )
    if not _is_proven_fastapi_router_binding(tree, "api_router"):
        raise SourceParseError("cannot verify backend aggregation APIRouter binding")

    registrations: list[tuple[str, int]] = []
    for node in tree.body:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if (
            not isinstance(call.func, ast.Attribute)
            or call.func.attr != "include_router"
        ):
            continue
        if (
            not isinstance(call.func.value, ast.Name)
            or call.func.value.id != "api_router"
        ):
            continue
        if (
            not call.args
            or not isinstance(call.args[0], ast.Name)
            or call.args[0].id != registered_router
        ):
            continue
        prefix_keywords = [
            keyword for keyword in call.keywords if keyword.arg == "prefix"
        ]
        if len(prefix_keywords) != 1:
            raise SourceParseError(
                f"cannot verify static backend router prefix: {registered_router}",
                line=node.lineno,
            )
        prefix_value = prefix_keywords[0].value
        if not isinstance(prefix_value, ast.Constant) or not isinstance(
            prefix_value.value, str
        ):
            raise SourceParseError(
                f"cannot verify static backend router prefix: {registered_router}",
                line=node.lineno,
            )
        registrations.append((prefix_value.value, node.lineno))

    if len(registrations) != 1:
        raise SourceParseError(
            f"cannot verify unique backend router registration: {registered_router}"
        )
    prefix, line = registrations[0]
    complete_path = f"{prefix.rstrip('/')}/{local_path.lstrip('/')}"
    if local_path == "":
        complete_path = prefix.rstrip("/") or "/"
    if not _request_paths_match(complete_path, expected_complete_path):
        raise SourceParseError(
            f"cannot verify complete backend route path: {expected_complete_path}",
            line=line,
        )


def _skip_typescript_quoted(text: str, index: int) -> int:
    quote = text[index]
    opening_line = _line_number(text, index)
    index += 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == quote:
            return index + 1
        index += 1
    raise SourceParseError("unterminated string literal", line=opening_line)


def _skip_typescript_comment(text: str, index: int) -> int:
    if text.startswith("//", index):
        newline = text.find("\n", index + 2)
        return len(text) if newline == -1 else newline + 1
    if text.startswith("/*", index):
        end = text.find("*/", index + 2)
        if end == -1:
            raise SourceParseError(
                "unterminated block comment", line=_line_number(text, index)
            )
        return end + 2
    return index


def _find_matching_brace(text: str, opening_index: int) -> int:
    """Return the matching brace while ignoring TypeScript strings/comments."""

    if opening_index >= len(text) or text[opening_index] != "{":
        raise SourceParseError("expected opening brace")

    depth = 0
    index = opening_index
    while index < len(text):
        if text.startswith("//", index) or text.startswith("/*", index):
            index = _skip_typescript_comment(text, index)
            continue
        if text[index] in {"'", '"', "`"}:
            index = _skip_typescript_quoted(text, index)
            continue
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise SourceParseError(
        "unmatched opening brace", line=_line_number(text, opening_index)
    )


def _find_matching_parenthesis(text: str, opening_index: int) -> int:
    if opening_index >= len(text) or text[opening_index] != "(":
        raise SourceParseError("expected opening parenthesis")

    depth = 0
    index = opening_index
    while index < len(text):
        if text.startswith("//", index) or text.startswith("/*", index):
            index = _skip_typescript_comment(text, index)
            continue
        if text[index] in {"'", '"', "`"}:
            index = _skip_typescript_quoted(text, index)
            continue
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise SourceParseError(
        "unmatched opening parenthesis", line=_line_number(text, opening_index)
    )


def _find_interface_body(source: str, interface_name: str) -> tuple[str, int]:
    matches = [
        match
        for match in _INTERFACE_RE.finditer(source)
        if match.group(1) == interface_name
    ]
    if len(matches) != 1:
        raise SourceParseError(
            f"cannot determine unique interface declaration: {interface_name}"
        )
    match = matches[0]
    if match.group("heritage").strip() != "":
        raise SourceParseError(
            f"unsupported interface heritage: {interface_name}",
            line=_line_number(source, match.start()),
        )
    opening_index = match.end() - 1
    closing_index = _find_matching_brace(source, opening_index)
    return source[opening_index + 1 : closing_index], opening_index + 1


def _top_level_typescript_segments(text: str) -> list[tuple[str, int]]:
    segments: list[tuple[str, int]] = []
    start = 0
    depth = 0
    index = 0
    while index < len(text):
        if text.startswith("//", index) or text.startswith("/*", index):
            comment_end = _skip_typescript_comment(text, index)
            segments.append((text[start:index], start))
            start = comment_end
            index = comment_end
            continue
        if text[index] in {"'", '"', "`"}:
            index = _skip_typescript_quoted(text, index)
            continue
        if text[index] in "{([<":
            depth += 1
        elif text[index] in "})]>" and depth > 0:
            depth -= 1
        elif text[index] in ";," and depth == 0:
            segments.append((text[start:index], start))
            start = index + 1
        index += 1
    segments.append((text[start:], start))
    return [(segment, offset) for segment, offset in segments if segment.strip() != ""]


def parse_typescript_interface_fields(
    path: Path, interface_name: str
) -> dict[str, int]:
    """Extract top-level property names from a single non-inherited interface."""

    source = _read_source(path)
    body, body_offset = _find_interface_body(source, interface_name)
    fields: dict[str, int] = {}
    for segment, segment_offset in _top_level_typescript_segments(body):
        property_match = re.fullmatch(
            r"\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*\??\s*:\s*.+", segment, re.DOTALL
        )
        if property_match is None:
            raise SourceParseError(
                "unsupported TypeScript interface property shape",
                line=_line_number(source, body_offset + segment_offset),
            )
        field = property_match.group(1)
        if field in fields:
            raise SourceParseError(
                f"duplicate TypeScript interface property: {field}",
                line=_line_number(source, body_offset + segment_offset),
            )
        fields[field] = _line_number(
            source, body_offset + segment_offset + property_match.start(1)
        )
    if not fields:
        raise SourceParseError(f"interface has no fields: {interface_name}")
    return fields


def _find_method_surface(source: str, method_name: str) -> MethodSurface:
    pattern = re.compile(_METHOD_RE_TEMPLATE.format(name=re.escape(method_name)))
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise SourceParseError(f"cannot determine unique service method: {method_name}")

    match = matches[0]
    opening_parenthesis = source.find("(", match.start(), match.end())
    closing_parenthesis = _find_matching_parenthesis(source, opening_parenthesis)
    opening_brace = source.find("{", closing_parenthesis)
    if opening_brace == -1:
        raise SourceParseError(
            f"service method has no body: {method_name}",
            line=_line_number(source, match.start()),
        )
    closing_brace = _find_matching_brace(source, opening_brace)
    return MethodSurface(
        body=source[opening_brace + 1 : closing_brace],
        body_offset=opening_brace + 1,
        parameters=source[opening_parenthesis + 1 : closing_parenthesis],
    )


def _declares_method_parameter(parameters: str, name: str) -> bool:
    return bool(re.search(rf"(?:^|,)\s*{re.escape(name)}\s*(?:\?|:|=|,)", parameters))


def _declares_mapped_params_type(parameters: str, params_type: str) -> bool:
    code = _typescripts_comments_only(parameters)
    return bool(
        re.search(
            rf"(?:^|,)\s*params\s*\??\s*:\s*{re.escape(params_type)}\s*(?==|,|$)",
            code,
        )
    )


def _method_rebinds_identifier(method_body: str, name: str) -> bool:
    escaped_name = re.escape(name)
    return bool(
        re.search(rf"\b(?:const|let|var|function)\s+{escaped_name}\b", method_body)
        or re.search(
            rf"(?<![.$\w]){escaped_name}\s*(?:=(?!=|>)|&&=|\|\|=|\?\?=)",
            method_body,
        )
    )


def _method_mutates_identifier(method_body: str, name: str) -> bool:
    code = _typescripts_code_only(method_body)
    escaped_name = re.escape(name)
    property_target = rf"{escaped_name}\s*(?:\.\s*[A-Za-z_$][A-Za-z0-9_$]*|\[[^\]]+\])"
    object_or_reflect_call = (
        r"\b(?:Object|Reflect)\s*(?:\?\.|\.)?\s*"
        r"(?:[A-Za-z_$][A-Za-z0-9_$]*|\[[^\]]+\])\s*(?:\?\.)?\s*\("
    )
    return bool(
        re.search(rf"\bdelete\s+{property_target}", code)
        or re.search(rf"{property_target}\s*(?:=(?!=|>)|&&=|\|\|=|\?\?=|\+\+|--)", code)
        or re.search(rf"{object_or_reflect_call}\s*{escaped_name}\b", code)
    )


def _typescript_brace_depth(text: str, target_index: int) -> int:
    depth = 0
    index = 0
    while index < target_index:
        if text.startswith("//", index) or text.startswith("/*", index):
            index = _skip_typescript_comment(text, index)
            continue
        if text[index] in {"'", '"', "`"}:
            index = _skip_typescript_quoted(text, index)
            continue
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
        index += 1
    return depth


def _find_named_helper_body(source: str, helper_name: str) -> str | None:
    helper_pattern = re.compile(
        rf"\bconst\s+{re.escape(helper_name)}\s*=\s*\(\s*params\s*:"
    )
    helper_matches = [
        match
        for match in helper_pattern.finditer(source)
        if _typescript_brace_depth(source, match.start()) == 0
    ]
    if len(helper_matches) != 1:
        return None
    helper_match = helper_matches[0]
    arrow_index = source.find("=>", helper_match.end())
    if arrow_index == -1:
        return None
    opening_brace = source.find("{", arrow_index)
    if opening_brace == -1:
        return None
    closing_brace = _find_matching_brace(source, opening_brace)
    return source[opening_brace + 1 : closing_brace]


def _is_complete_dynamic_forwarder(helper_body: str) -> bool:
    normalized = re.sub(r"\s+", " ", helper_body).strip()
    return bool(
        re.fullmatch(
            r"const normalized: Record<string, [^>]+> = \{\}; "
            r"Object\.entries\(params\)\.forEach\(\(\[key, value\]\) => \{ "
            r"if \(value == null \|\| value === ''\) \{ return; \} "
            r"normalized\[key\] = value; \}\); return normalized;",
            normalized,
        )
    )


def _typescripts_code_only(source: str) -> str:
    """Mask comments and strings without changing source positions."""

    characters = list(source)
    index = 0
    while index < len(source):
        if source.startswith("//", index) or source.startswith("/*", index):
            end = _skip_typescript_comment(source, index)
        elif source[index] in {"'", '"', "`"}:
            end = _skip_typescript_quoted(source, index)
        else:
            index += 1
            continue
        for offset in range(index, end):
            if characters[offset] != "\n":
                characters[offset] = " "
        index = end
    return "".join(characters)


def _typescripts_comments_only(source: str) -> str:
    """Mask comments without changing source positions or string literals."""

    characters = list(source)
    index = 0
    while index < len(source):
        if source.startswith("//", index) or source.startswith("/*", index):
            end = _skip_typescript_comment(source, index)
            for offset in range(index, end):
                if characters[offset] != "\n":
                    characters[offset] = " "
            index = end
            continue
        if source[index] in {"'", '"', "`"}:
            index = _skip_typescript_quoted(source, index)
            continue
        index += 1
    return "".join(characters)


def _method_has_unsupported_container_reference(
    method_body: str, name: str, ignored_identifier_index: int | None
) -> bool:
    code = _typescripts_code_only(method_body)
    escaped_name = re.escape(name)
    reference = rf"(?:\(\s*)?{escaped_name}\b(?:\s*\))?(?!\s*(?:\.|\?\.|\[))"
    property_references = re.finditer(
        rf"\b[A-Za-z_$][A-Za-z0-9_$]*\s*:\s*(?P<value>{reference})", code
    )
    for match in property_references:
        value_index = match.start("value")
        if ignored_identifier_index is None or value_index != ignored_identifier_index:
            return True
    return bool(re.search(rf"\[\s*{reference}", code))


def _has_unrebound_api_client_import(source: str, method: MethodSurface) -> bool:
    code = _typescripts_comments_only(source)
    imports = re.findall(
        r"^\s*import\s*\{\s*apiClient\s*\}\s*from\s*['\"]@/api/client['\"]\s*;",
        code,
        re.MULTILINE,
    )
    if len(imports) != 1 or _declares_method_parameter(method.parameters, "apiClient"):
        return False
    return not bool(
        re.search(r"\b(?:const|let|var|function|class)\s+apiClient\b", code)
        or re.search(r"(?<![.$\w])apiClient\s*(?:=(?!=|>)|&&=|\|\|=|\?\?=)", code)
    )


def _typescript_import_path(path: Path, module_path: str) -> Path | None:
    if module_path.startswith("@/"):
        candidate = ROOT / "frontend/src" / module_path.removeprefix("@/")
    elif module_path.startswith("."):
        candidate = path.parent / module_path
    else:
        return None
    return candidate.with_suffix(".ts").resolve()


def _has_mapped_params_type_binding(source: str, mapping: ContractMapping) -> bool:
    code = _typescripts_comments_only(source)
    imports = re.finditer(
        r"^\s*import\s+type\s*\{(?P<names>[^}]+)\}\s*from\s*['\"](?P<module>[^'\"]+)['\"]\s*;",
        code,
        re.MULTILINE,
    )
    matching_imports = [
        match
        for match in imports
        if any(
            re.fullmatch(rf"\s*{re.escape(mapping.frontend_type)}\s*", name)
            for name in match.group("names").split(",")
        )
        and _typescript_import_path(mapping.service_file, match.group("module"))
        == mapping.frontend_type_file.resolve()
    ]
    if len(matching_imports) != 1:
        return False
    return not bool(
        re.search(
            rf"\b(?:type|interface|class|enum|namespace)\s+{re.escape(mapping.frontend_type)}\b",
            code,
        )
    )


def _method_has_unsupported_destructuring_binding(method_body: str) -> bool:
    code = _typescripts_code_only(method_body)
    return bool(re.search(r"\b(?:const|let|var)\s*(?:\{|\[)", code))


def _is_typescript_regex_literal_start(text: str, index: int) -> bool:
    if (
        text[index] != "/"
        or text.startswith("//", index)
        or text.startswith("/*", index)
    ):
        return False
    previous_index = index - 1
    while previous_index >= 0 and text[previous_index].isspace():
        previous_index -= 1
    if previous_index < 0 or text[previous_index] in "=(:,[!&|?{};":
        return True
    return bool(
        re.search(
            r"\b(?:return|case|throw|yield|await)\s*$", text[: previous_index + 1]
        )
    )


def _method_has_unsupported_regex_literal(method_body: str) -> bool:
    index = 0
    while index < len(method_body):
        if method_body.startswith("//", index) or method_body.startswith("/*", index):
            index = _skip_typescript_comment(method_body, index)
            continue
        if method_body[index] in {"'", '"', "`"}:
            index = _skip_typescript_quoted(method_body, index)
            continue
        if _is_typescript_regex_literal_start(method_body, index):
            return True
        index += 1
    return False


def _method_interpolates_identifier(method_body: str, name: str) -> bool:
    escaped_name = re.escape(name)
    index = 0
    while index < len(method_body):
        if method_body.startswith("//", index) or method_body.startswith("/*", index):
            index = _skip_typescript_comment(method_body, index)
            continue
        if method_body[index] != "`":
            if method_body[index] in {"'", '"'}:
                index = _skip_typescript_quoted(method_body, index)
                continue
            index += 1
            continue
        template_end = _skip_typescript_quoted(method_body, index)
        if re.search(
            rf"\$\{{[^}}]*\b{escaped_name}\b", method_body[index:template_end]
        ):
            return True
        index = template_end
    return False


def _assert_supported_service_method_source(
    method: MethodSurface,
    identifiers: tuple[str, ...],
    line: int,
    ignored_identifier_index: int | None = None,
) -> None:
    if _method_has_unsupported_destructuring_binding(method.body):
        raise SourceParseError(
            "cannot verify service method source: destructuring binding", line=line
        )
    if _method_has_unsupported_regex_literal(method.body):
        raise SourceParseError(
            "cannot verify service method source: regular expression literal", line=line
        )
    for identifier in identifiers:
        if _method_has_unsupported_container_reference(
            method.body, identifier, ignored_identifier_index
        ):
            raise SourceParseError(
                "cannot verify service method source: container reference to "
                f"{identifier}",
                line=line,
            )
        if _method_interpolates_identifier(method.body, identifier):
            raise SourceParseError(
                "cannot verify service method source: template interpolation of "
                f"{identifier}",
                line=line,
            )


def _method_aliases_identifier(method_body: str, name: str) -> bool:
    code = _typescripts_code_only(method_body)
    escaped_name = re.escape(name)
    aliases = re.finditer(
        rf"(?<![.$\w])(?:const\s+|let\s+|var\s+)?"
        rf"(?P<alias>[A-Za-z_$][A-Za-z0-9_$]*)(?:\s*:\s*[^=;]+)?"
        rf"\s*=\s*(?:\(\s*)?{escaped_name}\b(?:\s*\))?",
        code,
    )
    return any(alias.group("alias") != name for alias in aliases)


def _resolve_dynamic_endpoint_path(
    group_body: str,
    key: str,
    call_arguments: str,
) -> str | None:
    arguments = [
        argument.strip()
        for argument, _ in _split_top_level_object_entries(call_arguments)
    ]
    if any(_IDENTIFIER_RE.fullmatch(argument) is None for argument in arguments):
        return None

    value_matches = list(
        re.finditer(
            rf"\b{re.escape(key)}\s*:\s*\((?P<parameters>[^)]*)\)\s*=>\s*"
            r"`(?P<template>[^`]*)`",
            group_body,
        )
    )
    if len(value_matches) != 1:
        return None

    parameters = []
    for parameter, _ in _split_top_level_object_entries(
        value_matches[0].group("parameters")
    ):
        parameter_match = re.fullmatch(
            r"\s*(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*:\s*[^,]+\s*",
            parameter,
        )
        if parameter_match is None:
            return None
        parameters.append(parameter_match.group("name"))
    if len(arguments) != len(parameters):
        return None

    template = value_matches[0].group("template")
    interpolations = re.findall(r"\$\{\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*\}", template)
    if len(interpolations) != len(parameters) or set(interpolations) != set(parameters):
        return None
    resolved = re.sub(
        r"\$\{\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*\}",
        lambda match: "{" + match.group(1) + "}",
        template,
    )
    return None if "${" in resolved else resolved


def _resolve_request_path(source: str, target: str) -> str | None:
    target = re.sub(r"\s+", "", target)
    literal = re.fullmatch(r"(['\"])(?P<path>[^'\"]*)\1", target)
    if literal is not None:
        return literal.group("path")

    if target.startswith("this."):
        property_name = target.removeprefix("this.")
        assignment = re.findall(
            rf"\b(?:private\s+|public\s+|protected\s+)?(?:readonly\s+)?"
            rf"{re.escape(property_name)}\s*=\s*(?P<value>[^;\n]+)",
            _typescripts_comments_only(source),
        )
        if len(assignment) != 1:
            return None
        return _resolve_request_path(source, assignment[0])

    identifier = re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", target)
    if identifier is not None:
        assignment = re.findall(
            rf"\bconst\s+{re.escape(target)}\s*=\s*(['\"])(?P<path>[^'\"]*)\1",
            _typescripts_comments_only(source),
        )
        if len(assignment) != 1:
            return None
        return assignment[0][1]

    if target.startswith("API_ENDPOINTS."):
        target = target.removeprefix("API_ENDPOINTS.")
    endpoint = re.fullmatch(
        r"(?P<group>[A-Z_]+)\.(?P<key>[A-Z_]+)"
        r"(?:\((?P<arguments>.*)\))?",
        target,
    )
    if endpoint is None:
        return None
    group = endpoint.group("group")
    key = endpoint.group("key")
    constants_source = _read_source(ROOT / "frontend/src/constants/api.ts")
    group_match = re.search(
        rf"export\s+const\s+{re.escape(group)}_API\s*=\s*\{{(?P<body>.*?)\}}\s*as\s+const;",
        _typescripts_comments_only(constants_source),
        re.DOTALL,
    )
    if group_match is None:
        return None
    group_body = group_match.group("body")
    call_arguments = endpoint.group("arguments")
    if call_arguments is not None:
        return _resolve_dynamic_endpoint_path(group_body, key, call_arguments)

    value_match = re.search(
        rf"\b{re.escape(key)}\s*:\s*(['\"])(?P<path>[^'\"]*)\1",
        group_body,
    )
    return None if value_match is None else value_match.group("path")


def _request_paths_match(actual: str | None, expected: str) -> bool:
    if actual is None:
        return False
    dynamic_segment = re.compile(r"\{[A-Za-z_$][A-Za-z0-9_$]*\}")
    normalized_actual = dynamic_segment.sub("{}", actual)
    normalized_expected = dynamic_segment.sub("{}", expected)
    if "{" in normalized_actual.replace("{}", "") or "}" in normalized_actual.replace(
        "{}", ""
    ):
        return False
    if "{" in normalized_expected.replace(
        "{}", ""
    ) or "}" in normalized_expected.replace("{}", ""):
        return False
    return normalized_actual == normalized_expected


def _is_within_expression_arrow_body(code: str, index: int) -> bool:
    for arrow_match in re.finditer(r"=>", code[:index]):
        body_start = arrow_match.end()
        while body_start < len(code) and code[body_start].isspace():
            body_start += 1
        if body_start > index or code[body_start] == "{":
            continue

        parenthesis_depth = 0
        bracket_depth = 0
        brace_depth = 0
        body_end = body_start
        while body_end < index:
            character = code[body_end]
            if character == "(":
                parenthesis_depth += 1
            elif character == ")":
                if parenthesis_depth == 0:
                    break
                parenthesis_depth -= 1
            elif character == "[":
                bracket_depth += 1
            elif character == "]":
                if bracket_depth == 0:
                    break
                bracket_depth -= 1
            elif character == "{":
                brace_depth += 1
            elif character == "}":
                if brace_depth == 0:
                    break
                brace_depth -= 1
            elif (
                character == ";"
                and parenthesis_depth == 0
                and bracket_depth == 0
                and brace_depth == 0
            ):
                break
            body_end += 1
        if body_end == index:
            return True
    return False


def _is_supported_outbound_request_scope(method_body: str, index: int) -> bool:
    code = _typescripts_code_only(method_body)
    if _is_within_expression_arrow_body(code, index):
        return False
    if _typescript_brace_depth(code, index) == 0:
        return True

    for try_match in re.finditer(r"\btry\s*\{", code):
        if _typescript_brace_depth(code, try_match.start()) != 0:
            continue
        opening_brace = code.find("{", try_match.start(), try_match.end())
        closing_brace = _find_matching_brace(code, opening_brace)
        if (
            opening_brace < index < closing_brace
            and _typescript_brace_depth(code, index) == 1
        ):
            return True
    return False


def _find_outbound_params(
    source: str, method_body: str, mapping: ContractMapping
) -> OutboundRequest:
    matches: list[OutboundRequest] = []
    index = 0
    while index < len(method_body):
        if method_body.startswith("//", index) or method_body.startswith("/*", index):
            index = _skip_typescript_comment(method_body, index)
            continue
        if method_body[index] in {"'", '"', "`"}:
            index = _skip_typescript_quoted(method_body, index)
            continue
        client_match = re.match(
            r"apiClient\.(?P<method>[A-Za-z_$][A-Za-z0-9_$]*)\s*(?:<[^>]+>)?\s*\(",
            method_body[index:],
        )
        if client_match is None:
            index += 1
            continue
        if not _is_supported_outbound_request_scope(method_body, index):
            raise SourceParseError(
                "cannot verify nested outbound request scope: "
                f"{mapping.service_method}",
                line=_line_number(method_body, index),
            )
        opening_parenthesis = index + client_match.end() - 1
        closing_parenthesis = _find_matching_parenthesis(
            method_body, opening_parenthesis
        )
        call_arguments = method_body[opening_parenthesis + 1 : closing_parenthesis]
        arguments = _split_top_level_object_entries(call_arguments)
        if len(arguments) < 2:
            index = closing_parenthesis + 1
            continue
        target, _ = arguments[0]
        request_method = client_match.group("method")
        request_path = _resolve_request_path(source, target)
        if request_method != mapping.request_method or not _request_paths_match(
            request_path, mapping.request_path
        ):
            raise SourceParseError(
                f"cannot verify mapped outbound request: expected "
                f"{mapping.request_method.upper()} {mapping.request_path}",
                line=_line_number(method_body, index),
            )
        config, config_offset = arguments[1]
        stripped_config = config.strip()
        config_leading = len(config) - len(config.lstrip())
        if not stripped_config.startswith("{"):
            raise SourceParseError(
                f"unsupported outbound request config shape: {mapping.service_method}",
                line=_line_number(method_body, opening_parenthesis + 1 + config_offset),
            )
        config_opening = opening_parenthesis + 1 + config_offset + config_leading
        config_closing = _find_matching_brace(method_body, config_opening)
        if method_body[config_closing + 1 : closing_parenthesis].strip() != "":
            raise SourceParseError(
                f"unsupported outbound request config shape: {mapping.service_method}",
                line=_line_number(method_body, config_opening),
            )
        config_body = method_body[config_opening + 1 : config_closing]
        params_entries: list[tuple[str, int]] = []
        for entry, entry_offset in _split_top_level_object_entries(config_body):
            property_match = re.fullmatch(
                r"\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*:\s*(?P<value>.+?)\s*",
                entry,
                re.DOTALL,
            )
            if property_match is None:
                raise SourceParseError(
                    "cannot verify explicit outbound request config property: "
                    f"{mapping.service_method}",
                    line=_line_number(method_body, config_opening + 1 + entry_offset),
                )
            if property_match.group(1) != "params":
                continue
            params_value = property_match.group("value")
            if not re.fullmatch(
                r"[A-Za-z_$][A-Za-z0-9_$]*(?:\s*\(\s*params\s*\))?",
                params_value,
            ):
                raise SourceParseError(
                    "cannot verify explicit outbound request params value: "
                    f"{mapping.service_method}",
                    line=_line_number(
                        method_body,
                        config_opening
                        + 1
                        + entry_offset
                        + property_match.start("value"),
                    ),
                )
            params_entries.append(
                (
                    params_value,
                    config_opening + 1 + entry_offset + property_match.start("value"),
                )
            )
        if len(params_entries) != 1:
            raise SourceParseError(
                "cannot determine exactly one top-level outbound request params value: "
                f"{mapping.service_method}",
                line=_line_number(method_body, config_opening),
            )
        params_value, params_index = params_entries[0]
        matches.append(
            OutboundRequest(
                params_value=params_value,
                params_index=params_index,
                method=request_method,
                path=request_path,
            )
        )
        index = closing_parenthesis + 1
    if len(matches) != 1:
        raise SourceParseError(
            "cannot determine exactly one mapped outbound request params value: "
            f"{mapping.service_method}"
        )
    return matches[0]


def _split_top_level_object_entries(object_body: str) -> list[tuple[str, int]]:
    entries: list[tuple[str, int]] = []
    start = 0
    parentheses = 0
    braces = 0
    brackets = 0
    index = 0
    while index < len(object_body):
        if object_body.startswith("//", index) or object_body.startswith("/*", index):
            index = _skip_typescript_comment(object_body, index)
            continue
        if object_body[index] in {"'", '"', "`"}:
            index = _skip_typescript_quoted(object_body, index)
            continue
        if object_body[index] == "(":
            parentheses += 1
        elif object_body[index] == ")":
            parentheses -= 1
        elif object_body[index] == "{":
            braces += 1
        elif object_body[index] == "}":
            braces -= 1
        elif object_body[index] == "[":
            brackets += 1
        elif object_body[index] == "]":
            brackets -= 1
        elif (
            object_body[index] == ","
            and parentheses == 0
            and braces == 0
            and brackets == 0
        ):
            entries.append((object_body[start:index], start))
            start = index + 1
        index += 1
    entries.append((object_body[start:], start))
    return [(entry, offset) for entry, offset in entries if entry.strip() != ""]


def _is_verified_param_value(value: str, field: str) -> bool:
    parameter_access = rf"params(?:\.|\?\.){re.escape(field)}\b"
    return bool(
        re.fullmatch(
            rf"\s*{parameter_access}(?:\s*\?\?\s*(?:[A-Za-z_$][A-Za-z0-9_$]*|\d+(?:\.\d+)?|'[^']*'|\"[^\"]*\"|true|false|null))?\s*",
            value,
            re.DOTALL,
        )
    )


def _is_verified_field_condition(condition: str, field: str) -> bool:
    parameter_access = rf"params(?:\.|\?\.){re.escape(field)}\b"
    presence = rf"{parameter_access}\s*!=\s*null"
    non_empty = rf"{parameter_access}\.trim\(\)\s*!==\s*''"
    return bool(
        re.fullmatch(
            rf"\s*{presence}(?:\s*&&\s*{non_empty})?\s*",
            condition,
            re.DOTALL,
        )
    )


def _parse_request_object_entry(entry: str) -> tuple[str, int]:
    conditional_spread = re.fullmatch(
        r"\s*\.\.\.\(\s*(?P<condition>.+?)\s*\?\s*\{(?P<body>[^{}]*)\}\s*:\s*\{\s*\}\s*\)\s*",
        entry,
        re.DOTALL,
    )
    if conditional_spread is not None:
        nested_entries = _split_top_level_object_entries(
            conditional_spread.group("body")
        )
        if len(nested_entries) != 1:
            raise SourceParseError("unsupported outbound request params property shape")
        nested_entry, nested_offset = nested_entries[0]
        nested_property = re.fullmatch(
            r"\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*:\s*(?P<value>.+?)\s*",
            nested_entry,
            re.DOTALL,
        )
        if (
            nested_property is not None
            and _is_verified_field_condition(
                conditional_spread.group("condition"), nested_property.group(1)
            )
            and _is_verified_param_value(
                nested_property.group("value"), nested_property.group(1)
            )
        ):
            return (
                nested_property.group(1),
                conditional_spread.start("body")
                + nested_offset
                + nested_property.start(1),
            )
        raise SourceParseError("unsupported outbound request params property shape")

    property_match = re.fullmatch(
        r"\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*:\s*(?P<value>.+?)\s*", entry, re.DOTALL
    )
    if property_match is not None and _is_verified_param_value(
        property_match.group("value"), property_match.group(1)
    ):
        return property_match.group(1), property_match.start(1)

    raise SourceParseError("unsupported outbound request params property shape")


def _identifier_mutated_before(
    method_body: str, name: str, start: int, end: int
) -> bool:
    return _method_mutates_identifier(method_body[start:end], name)


def _find_named_object_fields(
    method_body: str, variable_name: str, method_name: str, outbound_index: int
) -> dict[str, int]:
    declarations = list(
        re.finditer(
            rf"\bconst\s+{re.escape(variable_name)}\s*=\s*\{{",
            method_body,
        )
    )
    if len(declarations) != 1:
        raise SourceParseError(
            f"cannot determine unique outbound request params object: {variable_name}"
        )
    declaration = declarations[0]
    opening_brace = method_body.find("{", declaration.start())
    closing_brace = _find_matching_brace(method_body, opening_brace)
    request_params_segment = method_body[closing_brace + 1 : outbound_index]
    if (
        _identifier_mutated_before(
            method_body, variable_name, closing_brace + 1, outbound_index
        )
        or _method_aliases_identifier(request_params_segment, variable_name)
        or _method_passes_identifier_to_helper(request_params_segment, variable_name)
    ):
        raise SourceParseError(
            f"cannot verify unchanged outbound request params object: {variable_name}",
            line=_line_number(method_body, closing_brace + 1),
        )
    object_body = method_body[opening_brace + 1 : closing_brace]
    fields: dict[str, int] = {}
    for entry, entry_offset in _split_top_level_object_entries(object_body):
        field, field_offset = _parse_request_object_entry(entry)
        if field in fields:
            raise SourceParseError(
                f"duplicate outbound request params field: {field} in {method_name}"
            )
        fields[field] = _line_number(
            method_body, opening_brace + 1 + entry_offset + field_offset
        )
    if not fields:
        raise SourceParseError(
            f"outbound request params has no properties: {method_name}"
        )
    return fields


def _typescripts_call_callee(text: str, opening_index: int) -> tuple[str | None, bool]:
    """Return the direct callee name and whether it has no member/wrapper shape."""

    prefix = text[:opening_index].rstrip()
    if prefix == "":
        return None, False
    if prefix.endswith("?."):
        member_prefix = prefix[:-2].rstrip()
        member_match = re.search(
            r"(?P<callee>[A-Za-z_$][A-Za-z0-9_$]*)$", member_prefix
        )
        if member_match is None:
            return None, False
        return member_match.group("callee"), False
    if prefix.endswith("."):
        member_prefix = prefix[:-1].rstrip()
        member_match = re.search(
            r"(?P<callee>[A-Za-z_$][A-Za-z0-9_$]*)$", member_prefix
        )
        if member_match is None:
            return None, False
        return member_match.group("callee"), False
    if prefix[-1] in ")]>":
        return "", False
    match = re.search(r"(?P<callee>[A-Za-z_$][A-Za-z0-9_$]*)$", prefix)
    if match is None:
        return None, False
    callee = match.group("callee")
    before_callee = prefix[: match.start()].rstrip()
    if callee in {"catch", "for", "if", "switch", "while", "with"}:
        return None, False
    if re.search(r"(?:^|\s)(?:async\s+)?function$", before_callee):
        return None, False
    return callee, not before_callee.endswith((".", "?.", "]"))


def _method_passes_identifier_to_helper(
    method_body: str,
    name: str,
    allowed_helper: str | None = None,
    ignored_argument_index: int | None = None,
) -> bool:
    code = _typescripts_code_only(method_body)
    protected_identifier = re.compile(rf"\b{re.escape(name)}\b")
    index = 0
    while index < len(code):
        if code[index] != "(":
            index += 1
            continue
        try:
            closing_index = _find_matching_parenthesis(code, index)
        except SourceParseError:
            index += 1
            continue
        if (
            ignored_argument_index is not None
            and index < ignored_argument_index < closing_index
        ):
            index += 1
            continue
        callee, is_direct = _typescripts_call_callee(code, index)
        if callee is None:
            index += 1
            continue
        arguments = code[index + 1 : closing_index]
        if protected_identifier.search(arguments) is not None and not (
            is_direct and callee == allowed_helper
        ):
            return True
        index += 1
    return False


def _method_params_input_is_unchanged(
    method: MethodSurface,
    allowed_helper: str | None = None,
    ignored_argument_index: int | None = None,
) -> bool:
    return not (
        _method_rebinds_identifier(method.body, "params")
        or _method_mutates_identifier(method.body, "params")
        or _method_aliases_identifier(method.body, "params")
        or _method_passes_identifier_to_helper(
            method.body, "params", allowed_helper, ignored_argument_index
        )
    )


def _assert_method_params_input_is_unchanged(
    method: MethodSurface,
    *,
    context: str,
    line: int,
    allowed_helper: str | None = None,
    ignored_argument_index: int | None = None,
) -> None:
    if _method_passes_identifier_to_helper(
        method.body, "params", allowed_helper, ignored_argument_index
    ):
        raise SourceParseError(
            f"cannot verify {context}: unproven params helper",
            line=line,
        )
    if not _method_params_input_is_unchanged(
        method, allowed_helper, ignored_argument_index
    ):
        raise SourceParseError(
            f"cannot verify {context}: params is not the unchanged method input",
            line=line,
        )


def parse_service_request_fields(
    path: Path, mapping: ContractMapping
) -> RequestFieldSurface | None:
    """Extract outbound whitelist fields or prove full dynamic forwarding.

    The checker reads the ``params`` value from the mapped service method's one
    outbound request. A dynamic helper is accepted only when its entire body
    matches the ledger's complete normalizer form. Other dynamic or inline
    request shapes fail loudly until the parser supports them.
    """

    source = _read_source(path)
    method = _find_method_surface(source, mapping.service_method)
    if not _has_unrebound_api_client_import(source, method):
        raise SourceParseError(
            "cannot verify outbound apiClient binding: expected unrebound import from @/api/client"
        )
    if not _has_mapped_params_type_binding(source, mapping):
        raise SourceParseError(
            f"cannot verify mapped Params type binding: {mapping.frontend_type}"
        )
    outbound = _find_outbound_params(source, method.body, mapping)
    outbound_value = outbound.params_value
    outbound_index = outbound.params_index
    absolute_outbound_line = _line_number(source, method.body_offset + outbound_index)
    if not _declares_mapped_params_type(method.parameters, mapping.frontend_type):
        raise SourceParseError(
            f"cannot verify mapped Params type: {mapping.frontend_type}",
            line=absolute_outbound_line,
        )

    if outbound_value == "params":
        _assert_supported_service_method_source(
            method,
            ("params",),
            absolute_outbound_line,
            ignored_identifier_index=outbound_index,
        )
        if not _declares_method_parameter(method.parameters, "params"):
            raise SourceParseError(
                "cannot verify direct params forwarding: params is not the mapped method input",
                line=absolute_outbound_line,
            )
        _assert_method_params_input_is_unchanged(
            method,
            context="direct params forwarding",
            line=absolute_outbound_line,
            ignored_argument_index=outbound_index,
        )
        return None

    dynamic_match = _DYNAMIC_PARAMS_CALL_RE.fullmatch(outbound_value)
    if dynamic_match is not None:
        _assert_supported_service_method_source(
            method,
            ("params", dynamic_match.group(1)),
            absolute_outbound_line,
            ignored_identifier_index=outbound_index,
        )
        helper_name = dynamic_match.group(1)
        if not _declares_method_parameter(method.parameters, "params"):
            raise SourceParseError(
                "cannot verify complete dynamic forwarding: params is not the mapped method input",
                line=absolute_outbound_line,
            )
        _assert_method_params_input_is_unchanged(
            method,
            context="complete dynamic forwarding",
            line=absolute_outbound_line,
            allowed_helper=helper_name,
            ignored_argument_index=outbound_index,
        )
        if _declares_method_parameter(
            method.parameters, helper_name
        ) or _method_rebinds_identifier(method.body, helper_name):
            raise SourceParseError(
                f"cannot verify complete dynamic forwarding: {helper_name}",
                line=absolute_outbound_line,
            )
        helper_body = _find_named_helper_body(source, helper_name)
        if helper_body is not None and _is_complete_dynamic_forwarder(helper_body):
            return None
        raise SourceParseError(
            f"cannot verify complete dynamic forwarding: {helper_name}",
            line=absolute_outbound_line,
        )

    _assert_supported_service_method_source(
        method,
        ("params", outbound_value),
        absolute_outbound_line,
        ignored_identifier_index=outbound_index,
    )
    if not _declares_method_parameter(method.parameters, "params"):
        raise SourceParseError(
            "cannot verify outbound request whitelist: params is not the mapped method input",
            line=absolute_outbound_line,
        )
    _assert_method_params_input_is_unchanged(
        method,
        context="outbound request whitelist",
        line=absolute_outbound_line,
        ignored_argument_index=outbound_index,
    )

    return RequestFieldSurface(
        fields={
            field: _line_number(source, method.body_offset) + line - 1
            for field, line in _find_named_object_fields(
                method.body, outbound_value, mapping.service_method, outbound_index
            ).items()
        },
        line=absolute_outbound_line,
    )


def _parse_or_issue(
    *,
    contract: ContractMapping,
    kind: str,
    path: Path,
    parse: Callable[[], dict[str, int] | RequestFieldSurface | None],
) -> tuple[dict[str, int] | RequestFieldSurface | None, DriftIssue | None]:
    try:
        return parse(), None
    except SourceParseError as exc:
        return None, DriftIssue(
            contract=contract.name,
            kind=kind,
            field=None,
            path=path,
            line=exc.line,
            detail=str(exc),
        )


def check_mapping(mapping: ContractMapping) -> list[DriftIssue]:
    """Return all drift findings for one explicit contract mapping."""

    backend_fields, backend_error = _parse_or_issue(
        contract=mapping,
        kind="parse_error",
        path=mapping.backend_file,
        parse=lambda: parse_backend_query_params(
            mapping.backend_file, mapping.backend_symbol
        ),
    )
    frontend_fields, frontend_error = _parse_or_issue(
        contract=mapping,
        kind="parse_error",
        path=mapping.frontend_type_file,
        parse=lambda: parse_typescript_interface_fields(
            mapping.frontend_type_file, mapping.frontend_type
        ),
    )
    backend_route_error: DriftIssue | None = None
    backend_registration_error: DriftIssue | None = None
    if (
        mapping.backend_route_symbol is not None
        and mapping.backend_route_path is not None
    ):
        _, backend_route_error = _parse_or_issue(
            contract=mapping,
            kind="parse_error",
            path=mapping.backend_file,
            parse=lambda: _parse_backend_route_path(
                mapping.backend_file,
                mapping.backend_route_symbol,
                mapping.request_method,
                mapping.backend_route_path,
                mapping.backend_route_dependency,
            ),
        )
    if (mapping.backend_registration_file is None) != (
        mapping.backend_registered_router is None
    ):
        backend_registration_error = DriftIssue(
            contract=mapping.name,
            kind="parse_error",
            field=None,
            path=mapping.backend_registration_file or mapping.backend_file,
            detail="backend router registration metadata must be configured together",
        )
    elif (
        mapping.backend_registration_file is not None
        and mapping.backend_registered_router is not None
        and mapping.backend_route_path is not None
    ):
        _, backend_registration_error = _parse_or_issue(
            contract=mapping,
            kind="parse_error",
            path=mapping.backend_registration_file,
            parse=lambda: _parse_backend_registered_route_path(
                mapping.backend_registration_file,
                mapping.backend_file,
                mapping.backend_registered_router,
                mapping.backend_route_path,
                mapping.request_path,
            ),
        )
    request_fields, request_error = _parse_or_issue(
        contract=mapping,
        kind="parse_error",
        path=mapping.service_file,
        parse=lambda: parse_service_request_fields(mapping.service_file, mapping),
    )

    issues = [
        issue
        for issue in (
            backend_error,
            frontend_error,
            backend_route_error,
            backend_registration_error,
            request_error,
        )
        if issue is not None
    ]
    if issues:
        return issues

    assert isinstance(backend_fields, dict)
    assert isinstance(frontend_fields, dict)

    for field in sorted(backend_fields.keys() - frontend_fields.keys()):
        issues.append(
            DriftIssue(
                contract=mapping.name,
                kind="backend_only",
                field=field,
                path=mapping.backend_file,
                line=backend_fields[field],
                compared_path=mapping.frontend_type_file,
                detail="backend query parameter is missing from the frontend Params interface",
            )
        )
    for field in sorted(frontend_fields.keys() - backend_fields.keys()):
        issues.append(
            DriftIssue(
                contract=mapping.name,
                kind="frontend_only",
                field=field,
                path=mapping.frontend_type_file,
                line=frontend_fields[field],
                compared_path=mapping.backend_file,
                detail="frontend Params field is missing from the backend query contract",
            )
        )

    if request_fields is None:
        return issues

    request_surface = request_fields
    for field in sorted(frontend_fields.keys() - request_surface.fields.keys()):
        issues.append(
            DriftIssue(
                contract=mapping.name,
                kind="request_whitelist_missing",
                field=field,
                path=mapping.service_file,
                line=request_surface.line,
                compared_path=mapping.frontend_type_file,
                compared_line=frontend_fields[field],
                detail="frontend Params field is not forwarded by the service request whitelist",
            )
        )
    for field in sorted(request_surface.fields.keys() - frontend_fields.keys()):
        issues.append(
            DriftIssue(
                contract=mapping.name,
                kind="request_whitelist_only",
                field=field,
                path=mapping.service_file,
                line=request_surface.fields[field],
                compared_path=mapping.frontend_type_file,
                detail="service request whitelist field is absent from the frontend Params interface",
            )
        )
    return issues


def check_all_contracts(
    mappings: Sequence[ContractMapping] = CONTRACT_MAPPINGS,
) -> list[DriftIssue]:
    return [issue for mapping in mappings for issue in check_mapping(mapping)]


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _display_location(path: Path, line: int | None) -> str:
    location = _display_path(path)
    return f"{location}:{line}" if line is not None else location


def format_issues(issues: Iterable[DriftIssue]) -> str:
    lines = []
    for issue in issues:
        subject = issue.field if issue.field is not None else "source"
        location = _display_location(issue.path, issue.line)
        if issue.compared_path is not None:
            compared = _display_location(issue.compared_path, issue.compared_line)
            location = f"{location}; compared with {compared}"
        lines.append(
            f"[DRIFT] {issue.contract} {issue.kind}: {subject} "
            f"({location}) - {issue.detail}"
        )
    return "\n".join(lines)


def run(mappings: Sequence[ContractMapping] = CONTRACT_MAPPINGS) -> int:
    issues = check_all_contracts(mappings)
    if issues:
        print("=== Query Parameter Drift Check ===")
        print(format_issues(issues))
        print(f"\nFAILED: {len(issues)} query parameter drift issue(s).")
        return 1

    print(
        "Query Parameter Drift Check: OK "
        f"({len(mappings)} explicit contracts, zero drift)."
    )
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
