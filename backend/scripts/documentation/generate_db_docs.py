#!/usr/bin/env python3
"""
数据库文档自动生成脚本
生成数据库模型、表结构和关系文档
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, inspect

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from models.ownership import Ownership
from models.project import Project

from database import get_database_engine
from models.asset import Asset
from models.task import AsyncTask, ExcelTaskConfig, TaskHistory


class DatabaseDocumentationGenerator:
    """数据库文档生成器"""

    def __init__(self):
        self.engine = get_database_engine().sync_engine
        self.output_dir = project_root / "docs" / "generated" / "database"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata = MetaData()
        self.metadata.reflect(bind=self.engine)

    def get_table_info(self, table_name: str) -> dict[str, Any]:
        """获取表信息"""
        inspector = inspect(self.engine)

        # 获取表列信息
        columns = inspector.get_columns(table_name)

        # 获取主键信息
        primary_keys = inspector.get_pk_constraint(table_name)

        # 获取外键信息
        foreign_keys = inspector.get_foreign_keys(table_name)

        # 获取索引信息
        indexes = inspector.get_indexes(table_name)

        return {
            "name": table_name,
            "columns": columns,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
            "indexes": indexes,
        }

    def get_model_info(self, model_class) -> dict[str, Any]:
        """获取模型信息"""
        if not hasattr(model_class, "__table__"):
            return {}

        table = model_class.__table__

        columns_info = {}
        for column in table.columns:
            columns_info[column.name] = {
                "type": str(column.type),
                "nullable": column.nullable,
                "primary_key": column.primary_key,
                "foreign_key": str(column.foreign_key) if column.foreign_key else None,
                "default": str(column.default) if column.default else None,
                "unique": column.unique,
                "comment": column.comment,
            }

        relationships = {}
        if hasattr(model_class, "__relationships__"):
            for rel_name, rel in model_class.__relationships__.items():
                relationships[rel_name] = {
                    "direction": str(rel.direction),
                    "entity": str(rel.entity.class_.__name__)
                    if hasattr(rel.entity, "class_")
                    else str(rel.entity),
                    "foreign_keys": [str(fk) for fk in rel.local_columns],
                    "back_populates": getattr(rel, "back_populates", None),
                }

        return {
            "name": model_class.__name__,
            "table_name": table.name,
            "columns": columns_info,
            "relationships": relationships,
            "docstring": model_class.__doc__ or "",
        }

    def generate_er_diagram_data(self) -> dict[str, Any]:
        """生成ER图数据"""
        models = [Asset, Project, Ownership, AsyncTask, TaskHistory, ExcelTaskConfig]

        tables = []
        relationships = []

        for model in models:
            if hasattr(model, "__table__"):
                table_info = self.get_model_info(model)
                tables.append(table_info)

                # 提取关系信息
                for rel_name, rel_data in table_info.get("relationships", {}).items():
                    if rel_data["foreign_keys"]:
                        for fk in rel_data["foreign_keys"]:
                            relationships.append(
                                {
                                    "from_table": table_info["table_name"],
                                    "to_table": rel_data["entity"].lower()
                                    if rel_data["entity"]
                                    else "",
                                    "from_column": fk.split(".")[-1],
                                    "relationship_type": rel_data["direction"],
                                    "relationship_name": rel_name,
                                }
                            )

        return {"tables": tables, "relationships": relationships}

    def generate_schema_overview(self) -> dict[str, Any]:
        """生成数据库概览"""
        inspector = inspect(self.engine)
        table_names = inspector.get_table_names()

        overview = {
            "database_type": "PostgreSQL",
            "total_tables": len(table_names),
            "tables": {},
            "statistics": {
                "total_columns": 0,
                "tables_with_relationships": 0,
                "tables_with_indexes": 0,
            },
        }

        for table_name in table_names:
            table_info = self.get_table_info(table_name)
            overview["tables"][table_name] = {
                "column_count": len(table_info["columns"]),
                "has_primary_key": bool(
                    table_info["primary_keys"].get("constrained_columns")
                ),
                "has_foreign_keys": bool(table_info["foreign_keys"]),
                "has_indexes": bool(table_info["indexes"]),
                "foreign_key_count": len(table_info["foreign_keys"]),
                "index_count": len(table_info["indexes"]),
            }

            # 更新统计信息
            overview["statistics"]["total_columns"] += len(table_info["columns"])
            if table_info["foreign_keys"]:
                overview["statistics"]["tables_with_relationships"] += 1
            if table_info["indexes"]:
                overview["statistics"]["tables_with_indexes"] += 1

        return overview

    def generate_sample_queries(self) -> list[dict[str, Any]]:
        """生成示例查询"""
        queries = [
            {
                "category": "Basic Queries",
                "queries": [
                    {
                        "name": "Get all assets",
                        "description": "Retrieve all asset records",
                        "sql": "SELECT * FROM assets LIMIT 10;",
                        "python": "assets = session.query(Asset).limit(10).all()",
                    },
                    {
                        "name": "Get assets by ownership",
                        "description": "Filter assets by ownership entity",
                        "sql": "SELECT * FROM assets WHERE ownership_id = 'ownership-id';",
                        "python": "assets = session.query(Asset).filter(Asset.ownership_id == 'ownership-id').all()",
                    },
                    {
                        "name": "Count assets by project",
                        "description": "Count assets grouped by project",
                        "sql": "SELECT project_name, COUNT(*) as asset_count FROM assets GROUP BY project_name;",
                        "python": "from sqlalchemy import func\ncounts = session.query(Asset.project_name, func.count(Asset.id)).group_by(Asset.project_name).all()",
                    },
                ],
            },
            {
                "category": "Relationship Queries",
                "queries": [
                    {
                        "name": "Assets with projects",
                        "description": "Join assets with projects",
                        "sql": "SELECT a.property_name, p.name as project_name FROM assets a LEFT JOIN projects p ON a.project_name = p.name;",
                        "python": "results = session.query(Asset, Project).join(Project, Asset.project_name == Project.name).all()",
                    },
                    {
                        "name": "Active tasks",
                        "description": "Get currently running tasks",
                        "sql": "SELECT * FROM async_tasks WHERE status = 'RUNNING' ORDER BY created_at DESC;",
                        "python": "from enums.task import TaskStatus\ntasks = session.query(AsyncTask).filter(AsyncTask.status == TaskStatus.RUNNING).order_by(AsyncTask.created_at.desc()).all()",
                    },
                ],
            },
            {
                "category": "Analytics Queries",
                "queries": [
                    {
                        "name": "Occupancy rate calculation",
                        "description": "Calculate average occupancy rate",
                        "sql": "SELECT AVG(CASE WHEN rentable_area > 0 THEN (rented_area / rentable_area) * 100 ELSE 0 END) as avg_occupancy FROM assets WHERE rentable_area > 0;",
                        "python": "from sqlalchemy import func, case\navg_occupancy = session.query(\n    func.avg(\n        case((Asset.rentable_area > 0), (Asset.rented_area / Asset.rentable_area) * 100, else_=0)\n    )\n).filter(Asset.rentable_area > 0).scalar()",
                    },
                    {
                        "name": "Financial summary",
                        "description": "Get financial summary by ownership",
                        "sql": "SELECT o.name, SUM(a.annual_income) as total_income, SUM(a.annual_expense) as total_expense FROM assets a LEFT JOIN ownerships o ON a.ownership_id = o.id GROUP BY o.name;",
                        "python": "financial_summary = session.query(\n    Ownership.name,\n    func.sum(Asset.annual_income),\n    func.sum(Asset.annual_expense)\n).join(Ownership, Asset.ownership_id == Ownership.id, isouter=True).group_by(Ownership.name).all()",
                    },
                ],
            },
        ]

        return queries

    def generate_markdown_documentation(self) -> str:
        """生成Markdown文档"""
        overview = self.generate_schema_overview()
        er_data = self.generate_er_diagram_data()
        queries = self.generate_sample_queries()

        markdown = [
            "# Database Documentation\n",
            f"Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n",
            "## Overview\n",
            f"- **Database Type**: {overview['database_type']}\n",
            f"- **Total Tables**: {overview['total_tables']}\n",
            f"- **Total Columns**: {overview['statistics']['total_columns']}\n",
            f"- **Tables with Relationships**: {overview['statistics']['tables_with_relationships']}\n",
            f"- **Tables with Indexes**: {overview['statistics']['tables_with_indexes']}\n",
            "## Tables\n",
        ]

        # 表文档
        for table_name, table_info in overview["tables"].items():
            markdown.append(f"### {table_name}\n")
            markdown.append(f"- **Columns**: {table_info['column_count']}\n")
            markdown.append(
                f"- **Has Primary Key**: {'Yes' if table_info['has_primary_key'] else 'No'}\n"
            )
            markdown.append(f"- **Foreign Keys**: {table_info['foreign_key_count']}\n")
            markdown.append(f"- **Indexes**: {table_info['index_count']}\n")

            # 获取详细列信息
            detailed_table_info = self.get_table_info(table_name)
            if detailed_table_info["columns"]:
                markdown.append("\n**Columns**:\n")
                for column in detailed_table_info["columns"]:
                    nullable = "NULL" if column["nullable"] else "NOT NULL"
                    markdown.append(
                        f"- `{column['name']}` ({column['type']}) {nullable}"
                    )
                    if column.get("default"):
                        markdown.append(f" - Default: {column['default']}")
                    markdown.append("")

            markdown.append("---\n")

        # 关系文档
        if er_data["relationships"]:
            markdown.append("## Relationships\n")
            for rel in er_data["relationships"]:
                markdown.append(f"### {rel['relationship_name']}\n")
                markdown.append(
                    f"- **From**: {rel['from_table']}.{rel['from_column']}\n"
                )
                markdown.append(f"- **To**: {rel['to_table']}\n")
                markdown.append(f"- **Type**: {rel['relationship_type']}\n")
                markdown.append("")

        # 示例查询文档
        markdown.append("## Sample Queries\n")
        for category in queries:
            markdown.append(f"### {category['category']}\n")
            for query in category["queries"]:
                markdown.append(f"#### {query['name']}\n")
                markdown.append(f"{query['description']}\n")
                markdown.append("**SQL**:\n```sql\n{query['sql']}\n```\n")
                markdown.append("**Python**:\n```python\n{query['python']}\n```\n")
                markdown.append("")

        return "\n".join(markdown)

    def save_documentation(self):
        """保存文档到文件"""
        # 生成概览
        overview = self.generate_schema_overview()
        with open(self.output_dir / "overview.json", "w", encoding="utf-8") as f:
            json.dump(overview, f, indent=2, ensure_ascii=False)

        # 生成ER图数据
        er_data = self.generate_er_diagram_data()
        with open(self.output_dir / "er_diagram.json", "w", encoding="utf-8") as f:
            json.dump(er_data, f, indent=2, ensure_ascii=False)

        # 生成示例查询
        queries = self.generate_sample_queries()
        with open(self.output_dir / "sample_queries.json", "w", encoding="utf-8") as f:
            json.dump(queries, f, indent=2, ensure_ascii=False)

        # 生成Markdown文档
        markdown_doc = self.generate_markdown_documentation()
        with open(self.output_dir / "database.md", "w", encoding="utf-8") as f:
            f.write(markdown_doc)

        # 复制到docs目录
        docs_dir = project_root / "docs"
        docs_dir.mkdir(exist_ok=True)

        import shutil

        shutil.copy2(self.output_dir / "database.md", docs_dir / "database.md")

        print("Database documentation generated successfully!")
        print(f"Output directory: {self.output_dir}")
        print("Files generated:")
        print(f"  - Overview: {self.output_dir / 'overview.json'}")
        print(f"  - ER Diagram: {self.output_dir / 'er_diagram.json'}")
        print(f"  - Sample Queries: {self.output_dir / 'sample_queries.json'}")
        print(f"  - Markdown: {self.output_dir / 'database.md'}")


def main():
    """主函数"""
    print("🗄️  Generating database documentation...")

    try:
        generator = DatabaseDocumentationGenerator()
        generator.save_documentation()
        print("✅ Database documentation generation completed successfully!")
    except Exception as e:
        print(f"❌ Database documentation generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
