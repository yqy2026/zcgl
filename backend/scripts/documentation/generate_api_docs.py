#!/usr/bin/env python3
"""
API文档自动生成脚本
生成FastAPI接口文档、OpenAPI规范和TypeScript类型定义
"""

import inspect
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

from main import app


class APIDocumentationGenerator:
    """API文档生成器"""

    def __init__(self):
        self.app = app
        self.output_dir = project_root / "docs" / "generated"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_openapi_schema(self) -> dict[str, Any]:
        """生成OpenAPI规范"""

        def custom_openapi():
            if app.openapi_schema:
                return app.openapi_schema

            openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                description=app.description,
                routes=app.routes,
            )

            # 添加自定义信息
            openapi_schema["info"]["x-generator"] = "Land Property Management System"
            openapi_schema["info"]["x-generated-at"] = datetime.utcnow().isoformat()

            # 添加安全方案
            openapi_schema["components"]["securitySchemes"] = {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            }

            # 添加全局安全要求（如果需要）
            # openapi_schema["security"] = [{"BearerAuth": []}]

            app.openapi_schema = openapi_schema
            return app.openapi_schema

        return custom_openapi()

    def generate_route_documentation(self) -> list[dict[str, Any]]:
        """生成路由文档"""
        routes = []

        for route in app.routes:
            if isinstance(route, APIRoute):
                route_info = {
                    "path": route.path,
                    "methods": list(route.methods),
                    "summary": route.summary or "",
                    "description": route.description or "",
                    "tags": route.tags or [],
                    "operation_id": route.operation_id,
                    "path_params": self._extract_params(route.path_params),
                    "query_params": self._extract_params(route.query_params),
                    "request_body": self._extract_request_body(route.body_field),
                    "responses": self._extract_responses(route.responses),
                    "dependencies": self._extract_dependencies(route.dependencies),
                }
                routes.append(route_info)

        return routes

    def _extract_params(self, params) -> list[dict[str, Any]]:
        """提取参数信息"""
        if not params:
            return []

        param_info = []
        for param in params:
            info = {
                "name": param.name,
                "type": param.type_.__name__
                if hasattr(param.type_, "__name__")
                else str(param.type_),
                "required": param.required,
                "default": param.default if param.default != ... else None,
                "description": param.description or "",
            }
            param_info.append(info)

        return param_info

    def _extract_request_body(self, body_field) -> dict[str, Any]:
        """提取请求体信息"""
        if not body_field:
            return {}

        return {
            "type": body_field.type_.__name__
            if hasattr(body_field.type_, "__name__")
            else str(body_field.type_),
            "required": body_field.required,
            "description": body_field.description or "",
        }

    def _extract_responses(self, responses) -> dict[str, Any]:
        """提取响应信息"""
        if not responses:
            return {}

        response_info = {}
        for status_code, response in responses.items():
            response_info[status_code] = {
                "description": response.description or "",
                "model": response.model.__name__ if response.model else None,
            }

        return response_info

    def _extract_dependencies(self, dependencies) -> list[str]:
        """提取依赖信息"""
        if not dependencies:
            return []

        dep_names = []
        for dep in dependencies:
            if hasattr(dep, "dependency") and hasattr(dep.dependency, "__name__"):
                dep_names.append(dep.dependency.__name__)
            elif hasattr(dep, "__name__"):
                dep_names.append(dep.__name__)

        return dep_names

    def generate_type_definitions(self) -> dict[str, Any]:
        """生成类型定义文档"""
        type_definitions = {}

        # 扫描schemas模块获取类型定义
        try:
            from models.ownership import Ownership
            from models.project import Project

            from models.asset import Asset
            from models.task import AsyncTask

            # 模型类型
            type_definitions["models"] = {
                "Asset": self._get_model_info(Asset),
                "Project": self._get_model_info(Project),
                "Ownership": self._get_model_info(Ownership),
                "AsyncTask": self._get_model_info(AsyncTask),
            }
        except ImportError as e:
            print(f"Warning: Could not import models: {e}")

        # 扫描schemas模块获取Pydantic模型
        schemas_dir = project_root / "src" / "schemas"
        if schemas_dir.exists():
            type_definitions["schemas"] = self._scan_schemas_directory(schemas_dir)

        return type_definitions

    def _get_model_info(self, model_class) -> dict[str, Any]:
        """获取模型信息"""
        if hasattr(model_class, "__annotations__"):
            return {
                "name": model_class.__name__,
                "fields": {
                    name: str(field_type)
                    for name, field_type in model_class.__annotations__.items()
                },
            }
        return {"name": model_class.__name__, "fields": {}}

    def _scan_schemas_directory(self, schemas_dir: Path) -> dict[str, Any]:
        """扫描schemas目录"""
        schemas = {}

        for schema_file in schemas_dir.glob("*.py"):
            if schema_file.name.startswith("__"):
                continue

            try:
                module_name = f"src.schemas.{schema_file.stem}"
                module = __import__(module_name, fromlist=[schema_file.stem])

                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and hasattr(obj, "__module__")
                        and obj.__module__ == module_name
                    ):
                        schemas[name] = self._get_model_info(obj)
            except Exception as e:
                print(f"Warning: Could not process schema file {schema_file}: {e}")

        return schemas

    def generate_markdown_documentation(self) -> str:
        """生成Markdown文档"""
        routes = self.generate_route_documentation()

        markdown = [
            "# API Documentation\n",
            f"Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n",
            "## Overview\n",
            f"- **Title**: {app.title}\n",
            f"- **Version**: {app.version}\n",
            f"- **Description**: {app.description}\n",
            "## Authentication\n",
            "Most endpoints require JWT authentication. Include the token in the Authorization header:\n",
            "```\n",
            "Authorization: Bearer <your-jwt-token>\n",
            "```\n",
            "## API Endpoints\n",
        ]

        # 按标签分组路由
        routes_by_tag = {}
        for route in routes:
            for tag in route["tags"]:
                if tag not in routes_by_tag:
                    routes_by_tag[tag] = []
                routes_by_tag[tag].append(route)

        # 生成每个标签的文档
        for tag, tag_routes in routes_by_tag.items():
            markdown.append(f"### {tag}\n")

            for route in tag_routes:
                methods_str = ", ".join(route["methods"])
                markdown.append(f"#### {methods_str} {route['path']}\n")

                if route["summary"]:
                    markdown.append(f"**Summary**: {route['summary']}\n")

                if route["description"]:
                    markdown.append(f"**Description**: {route['description']}\n")

                # 参数文档
                if route["path_params"]:
                    markdown.append("**Path Parameters**:\n")
                    for param in route["path_params"]:
                        required = " (required)" if param["required"] else ""
                        markdown.append(
                            f"- `{param['name']}` ({param['type']}){required}: {param['description']}\n"
                        )
                    markdown.append("")

                if route["query_params"]:
                    markdown.append("**Query Parameters**:\n")
                    for param in route["query_params"]:
                        required = " (required)" if param["required"] else ""
                        default = (
                            f" (default: {param['default']})"
                            if param["default"] is not None
                            else ""
                        )
                        markdown.append(
                            f"- `{param['name']}` ({param['type']}){required}{default}: {param['description']}\n"
                        )
                    markdown.append("")

                # 请求体文档
                if route["request_body"]:
                    body = route["request_body"]
                    required = " (required)" if body["required"] else ""
                    markdown.append(f"**Request Body**: {body['type']}{required}\n")
                    if body["description"]:
                        markdown.append(f"{body['description']}\n")
                    markdown.append("")

                # 响应文档
                if route["responses"]:
                    markdown.append("**Responses**:\n")
                    for status, response in route["responses"].items():
                        model_info = (
                            f" ({response['model']})" if response["model"] else ""
                        )
                        markdown.append(
                            f"- `{status}`: {response['description']}{model_info}\n"
                        )
                    markdown.append("")

                # 依赖文档
                if route["dependencies"]:
                    markdown.append(
                        f"**Dependencies**: {', '.join(route['dependencies'])}\n"
                    )

                markdown.append("---\n")

        return "\n".join(markdown)

    def save_documentation(self):
        """保存文档到文件"""
        # 生成OpenAPI规范
        openapi_schema = self.generate_openapi_schema()

        # 保存OpenAPI JSON
        with open(self.output_dir / "openapi.json", "w", encoding="utf-8") as f:
            json.dump(openapi_schema, f, indent=2, ensure_ascii=False)

        # 保存OpenAPI YAML
        try:
            import yaml

            with open(self.output_dir / "openapi.yaml", "w", encoding="utf-8") as f:
                yaml.dump(
                    openapi_schema, f, default_flow_style=False, allow_unicode=True
                )
        except ImportError:
            print("Warning: PyYAML not installed, skipping YAML export")

        # 生成路由文档
        routes = self.generate_route_documentation()
        with open(self.output_dir / "routes.json", "w", encoding="utf-8") as f:
            json.dump(routes, f, indent=2, ensure_ascii=False)

        # 生成类型定义
        type_definitions = self.generate_type_definitions()
        with open(self.output_dir / "types.json", "w", encoding="utf-8") as f:
            json.dump(type_definitions, f, indent=2, ensure_ascii=False)

        # 生成Markdown文档
        markdown_doc = self.generate_markdown_documentation()
        with open(self.output_dir / "api.md", "w", encoding="utf-8") as f:
            f.write(markdown_doc)

        # 复制到docs目录
        docs_dir = project_root / "docs"
        docs_dir.mkdir(exist_ok=True)

        import shutil

        shutil.copy2(self.output_dir / "api.md", docs_dir / "api.md")

        print("Documentation generated successfully!")
        print(f"Output directory: {self.output_dir}")
        print("Files generated:")
        print(f"  - OpenAPI JSON: {self.output_dir / 'openapi.json'}")
        print(f"  - OpenAPI YAML: {self.output_dir / 'openapi.yaml'}")
        print(f"  - Routes JSON: {self.output_dir / 'routes.json'}")
        print(f"  - Types JSON: {self.output_dir / 'types.json'}")
        print(f"  - Markdown: {self.output_dir / 'api.md'}")


def main():
    """主函数"""
    print("🚀 Generating API documentation...")

    try:
        generator = APIDocumentationGenerator()
        generator.save_documentation()
        print("✅ Documentation generation completed successfully!")
    except Exception as e:
        print(f"❌ Documentation generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
