"""
API文档生成工具
自动扫描FastAPI应用并生成标准化的API文档
"""

import inspect
import json
import os
from datetime import datetime
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute


class APIDocGenerator:
    """API文档生成器"""

    def __init__(self, app: FastAPI):
        self.app = app
        self.docs_data = {
            "info": {
                "title": "Land Property Asset Management API",
                "description": "土地物业管理资产系统 API 文档",
                "version": "2.0.0",
                "generated_at": datetime.now().isoformat(),
            },
            "servers": [
                {"url": "http://localhost:8002", "description": "开发环境"},
                {"url": "https://api.zcgl.com", "description": "生产环境"},
            ],
            "tags": [],
            "paths": {},
            "schemas": {},
            "examples": {},
        }

    def generate_docs(self) -> dict[str, Any]:
        """生成完整的API文档"""
        print("🔍 扫描API路由...")

        # 扫描所有路由
        for route in self.app.routes:
            if isinstance(route, APIRoute):
                self._process_route(route)

        # 生成标签信息
        self._generate_tags_info()

        # 生成数据模型
        self._generate_schemas()

        # 生成示例数据
        self._generate_examples()

        return self.docs_data

    def _process_route(self, route: APIRoute):
        """处理单个路由"""
        path = route.path
        methods = list(route.methods)

        # 获取路由信息
        endpoint = route.endpoint
        path_params = route.path_params
        query_params = [param for param in route.dependant.call_params.values()]

        # 解析端点函数
        inspect.signature(endpoint)  # 预留字段，当前未使用
        docstring = inspect.getdoc(endpoint) or ""

        # 提取标签
        tags = getattr(route, "tags", ["default"])
        for tag in tags:
            if tag not in self.docs_data["tags"]:
                self.docs_data["tags"].append({"name": tag})

        # 处理每个HTTP方法
        for method in methods:
            if method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                self._add_method_to_docs(
                    path=path,
                    method=method,
                    endpoint=endpoint,
                    docstring=docstring,
                    path_params=path_params,
                    query_params=query_params,
                    tags=tags,
                )

    def _add_method_to_docs(
        self,
        path: str,
        method: str,
        endpoint,
        docstring: str,
        path_params: list,
        query_params: list,
        tags: list[str],
    ):
        """添加HTTP方法到文档"""
        if path not in self.docs_data["paths"]:
            self.docs_data["paths"][path] = {}

        # 解析文档字符串
        summary, description, parameters = self._parse_docstring(docstring)

        # 构建操作对象
        operation = {
            "summary": summary or f"{method} {path}",
            "description": description or "",
            "tags": tags,
            "responses": {
                "200": {
                    "description": "成功响应",
                    "content": {"application/json": {"schema": {"type": "object"}}},
                },
                "400": {"description": "请求参数错误"},
                "401": {"description": "未授权访问"},
                "404": {"description": "资源不存在"},
                "500": {"description": "服务器内部错误"},
            },
        }

        # 添加参数
        if parameters or path_params or query_params:
            operation["parameters"] = []

            # 路径参数
            for param in path_params:
                operation["parameters"].append(
                    {
                        "name": param,
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                )

            # 查询参数（简化处理）
            for param in query_params:
                if hasattr(param, "name") and hasattr(param, "type_"):
                    operation["parameters"].append(
                        {
                            "name": param.name,
                            "in": "query",
                            "required": param.default == inspect.Parameter.empty,
                            "schema": {"type": "string"},
                        }
                    )

        # 特殊处理不同方法
        if method in ["POST", "PUT", "PATCH"]:
            operation["requestBody"] = {
                "description": "请求体",
                "required": True,
                "content": {"application/json": {"schema": {"type": "object"}}},
            }

        self.docs_data["paths"][path][method.lower()] = operation

    def _parse_docstring(self, docstring: str) -> tuple[str, str, list[dict]]:
        """解析文档字符串"""
        lines = docstring.split("\n")
        summary = ""
        description = ""
        parameters = []

        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("- **"):
                # 参数描述
                if ":" in line:
                    param_name = line[4:].split(":")[0]
                    param_desc = line[4:].split(":", 1)[1].strip()
                    parameters.append({"name": param_name, "description": param_desc})
            elif not summary:
                summary = line
            elif current_section != "description":
                description += line + "\n"

        return summary, description.strip(), parameters

    def _generate_tags_info(self):
        """生成标签详细信息"""
        tag_details = {
            "资产": {
                "description": "资产信息管理相关接口，包括资产的增删改查、批量操作等功能"
            },
            "项目": {
                "description": "项目管理相关接口，包括项目的创建、查询、更新等操作"
            },
            "权属方": {"description": "权属方管理相关接口，包括权属方信息的维护和查询"},
            "统计": {
                "description": "数据统计分析接口，提供各种维度的数据统计和报表功能"
            },
            "Excel": {"description": "Excel导入导出功能，支持异步处理和任务跟踪"},
            "PDF": {"description": "PDF文件处理功能，支持智能提取和批量导入"},
            "任务管理": {"description": "异步任务管理，提供任务状态跟踪和历史记录查询"},
            "系统管理": {"description": "系统配置和字典管理功能"},
        }

        # 更新标签信息
        for tag in self.docs_data["tags"]:
            tag_name = tag.get("name", "")
            if tag_name in tag_details:
                tag["description"] = tag_details[tag_name]["description"]

    def _generate_schemas(self):
        """生成数据模型文档"""
        # 常用数据模型
        common_schemas = {
            "Asset": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "资产ID"},
                    "property_name": {"type": "string", "description": "物业名称"},
                    "address": {"type": "string", "description": "物业地址"},
                    "ownership_status": {"type": "string", "description": "确权状态"},
                    "property_nature": {"type": "string", "description": "物业性质"},
                    "usage_status": {"type": "string", "description": "使用状态"},
                    "ownership_entity": {"type": "string", "description": "权属方"},
                    "land_area": {"type": "number", "description": "土地面积"},
                    "actual_property_area": {
                        "type": "number",
                        "description": "实际房产面积",
                    },
                    "rentable_area": {"type": "number", "description": "可出租面积"},
                    "rented_area": {"type": "number", "description": "已出租面积"},
                    "created_at": {
                        "type": "string",
                        "format": "date-time",
                        "description": "创建时间",
                    },
                    "updated_at": {
                        "type": "string",
                        "format": "date-time",
                        "description": "更新时间",
                    },
                },
            },
            "ApiResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "description": "操作是否成功"},
                    "message": {"type": "string", "description": "响应消息"},
                    "data": {"type": "object", "description": "响应数据"},
                },
            },
            "PaginatedResponse": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "数据列表",
                    },
                    "total": {"type": "integer", "description": "总数量"},
                    "page": {"type": "integer", "description": "当前页码"},
                    "limit": {"type": "integer", "description": "每页数量"},
                    "pages": {"type": "integer", "description": "总页数"},
                },
            },
            "Task": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "任务ID"},
                    "task_type": {"type": "string", "description": "任务类型"},
                    "status": {"type": "string", "description": "任务状态"},
                    "title": {"type": "string", "description": "任务标题"},
                    "progress": {"type": "integer", "description": "进度百分比"},
                    "created_at": {
                        "type": "string",
                        "format": "date-time",
                        "description": "创建时间",
                    },
                    "started_at": {
                        "type": "string",
                        "format": "date-time",
                        "description": "开始时间",
                    },
                    "completed_at": {
                        "type": "string",
                        "format": "date-time",
                        "description": "完成时间",
                    },
                },
            },
        }

        self.docs_data["schemas"] = common_schemas

    def _generate_examples(self):
        """生成示例数据"""
        examples = {
            "AssetExample": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "property_name": "示例物业",
                "address": "示例地址",
                "ownership_status": "已确权",
                "property_nature": "经营性",
                "usage_status": "出租",
                "ownership_entity": "示例权属方",
                "land_area": 1000.0,
                "actual_property_area": 800.0,
                "rentable_area": 600.0,
                "rented_area": 400.0,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
            "SuccessResponse": {"success": True, "message": "操作成功", "data": {}},
            "ErrorResponse": {
                "success": False,
                "message": "操作失败",
                "error": "详细错误信息",
            },
        }

        self.docs_data["examples"] = examples

    def save_docs(self, output_dir: str = "docs/api"):
        """保存文档到文件"""
        os.makedirs(output_dir, exist_ok=True)

        # 生成JSON格式文档
        json_path = os.path.join(output_dir, "api-docs.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.docs_data, f, ensure_ascii=False, indent=2)

        # 生成Markdown格式文档
        self._generate_markdown_docs(output_dir)

        print("✅ API文档已生成:")
        print(f"   📄 JSON文档: {json_path}")
        print(f"   📖 Markdown文档: {os.path.join(output_dir, 'README.md')}")

    def _generate_markdown_docs(self, output_dir: str):
        """生成Markdown格式文档"""
        md_content = f"""# {self.docs_data["info"]["title"]}

{self.docs_data["info"]["description"]}

**版本:** {self.docs_data["info"]["version"]}
**生成时间:** {self.docs_data["info"]["generated_at"]}

## 目录

"""

        # 生成目录
        for tag in self.docs_data["tags"]:
            tag_name = tag.get("name", "")
            md_content += f"- [{tag_name}](#{tag_name})\n"

        md_content += "\n---\n\n"

        # 生成各标签的API文档
        for tag in self.docs_data["tags"]:
            tag_name = tag.get("name", "")
            tag_desc = tag.get("description", "")

            md_content += f"## {tag_name}\n\n"
            if tag_desc:
                md_content += f"{tag_desc}\n\n"

            # 查找该标签的所有API
            for path, methods in self.docs_data["paths"].items():
                for method, operation in methods.items():
                    if tag_name in operation.get("tags", []):
                        md_content += self._generate_api_md(path, method, operation)

            md_content += "\n---\n\n"

        # 保存Markdown文档
        md_path = os.path.join(output_dir, "README.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

    def _generate_api_md(self, path: str, method: str, operation: dict) -> str:
        """生成单个API的Markdown文档"""
        summary = operation.get("summary", f"{method.upper()} {path}")
        description = operation.get("description", "")

        md = f"### {method.upper()} {path}\n\n"
        md += f"**摘要:** {summary}\n\n"

        if description:
            md += f"**描述:** {description}\n\n"

        # 参数
        parameters = operation.get("parameters", [])
        if parameters:
            md += "**参数:**\n\n"
            md += "| 参数名 | 位置 | 类型 | 必填 | 描述 |\n"
            md += "|--------|------|------|------|------|\n"

            for param in parameters:
                param_name = param.get("name", "")
                param_in = param.get("in", "")
                param_required = param.get("required", False)
                param_schema = param.get("schema", {})
                param_type = param_schema.get("type", "string")
                param_desc = param.get("description", "")

                md += f"| {param_name} | {param_in} | {param_type} | {'是' if param_required else '否'} | {param_desc} |\n"

            md += "\n"

        # 响应示例
        responses = operation.get("responses", {})
        if "200" in responses:
            md += "**响应示例:**\n\n"
            md += "```json\n"
            md += '{\n  "success": true,\n  "message": "操作成功",\n  "data": {}\n}'
            md += "\n```\n\n"

        md += "---\n\n"
        return md


def generate_api_docs(app: FastAPI, output_dir: str = "docs/api"):
    """
    生成API文档的便捷函数

    Args:
        app: FastAPI应用实例
        output_dir: 输出目录
    """
    generator = APIDocGenerator(app)
    docs = generator.generate_docs()
    generator.save_docs(output_dir)
    return docs


if __name__ == "__main__":
    # 示例用法
    print("🚀 API文档生成工具")
    print("请在FastAPI应用中调用 generate_api_docs(app) 函数")
