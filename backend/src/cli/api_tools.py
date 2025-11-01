"""
API工具命令行接口
提供API文档生成、一致性检查等功能
"""

import os
import sys
from pathlib import Path

import click

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@click.group()
@click.version_option(version="2.0.0")
def cli():
    """API工具集 - 用于管理API文档和一致性检查"""
    pass


@cli.command()
@click.option(
    "--app-path",
    "-a",
    default="src.main:app",
    help="FastAPI应用路径，格式: module.file:app",
)
@click.option("--output-dir", "-o", default="docs/api", help="文档输出目录")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "markdown", "all"]),
    default="all",
    help="输出格式",
)
def docs(app_path: str, output_dir: str, format: str):
    """生成API文档"""
    click.echo("🚀 开始生成API文档...")

    try:
        # 动态导入FastAPI应用
        module_path, app_name = app_path.split(":")
        module = __import__(module_path, fromlist=[app_name])
        app = getattr(module, app_name)

        # 动态导入生成API文档函数
        try:
            from src.utils.api_doc_generator import generate_api_docs
        except ImportError as e:
            click.echo(f"❌ 无法导入API文档生成器: {e}", err=True)
            sys.exit(1)

        # 生成文档
        docs_data = generate_api_docs(app, output_dir)

        click.echo("✅ API文档生成成功!")
        click.echo(f"📁 输出目录: {output_dir}")
        click.echo(f"📊 发现 {len(docs_data.get('paths', {}))} 个API端点")

    except Exception as e:
        click.echo(f"❌ 生成文档失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--frontend-dir", "-f", default="frontend", help="前端代码目录")
@click.option("--backend-dir", "-b", default="backend", help="后端代码目录")
@click.option("--output-dir", "-o", default="reports", help="报告输出目录")
@click.option(
    "--severity",
    "-s",
    type=click.Choice(["high", "medium", "low", "all"]),
    default="all",
    help="只显示指定严重程度的问题",
)
def check(frontend_dir: str, backend_dir: str, output_dir: str, severity: str):
    """检查API一致性"""
    click.echo("🔍 开始API一致性检查...")

    try:
        # 动态导入一致性检查函数
        from src.utils.api_consistency_checker import check_api_consistency

        # 执行检查
        report = check_api_consistency(frontend_dir, backend_dir, output_dir)

        # 显示结果摘要
        summary = report["summary"]
        click.echo("📊 检查完成!")
        click.echo(f"   总问题数: {summary['total_issues']}")
        click.echo(f"   🔴 高严重性: {summary['high_severity']}")
        click.echo(f"   🟡 中等严重性: {summary['medium_severity']}")
        click.echo(f"   🟢 低严重性: {summary['low_severity']}")

        # 显示高优先级问题
        high_issues = report.get("high_priority_issues", [])
        if high_issues:
            click.echo("\n🚨 高优先级问题:")
            for i, issue in enumerate(high_issues[:5], 1):  # 只显示前5个
                click.echo(f"   {i}. {issue['description']}")
                if i >= 5 and len(high_issues) > 5:
                    click.echo(f"   ... 还有 {len(high_issues) - 5} 个问题")
                    break

        # 根据严重程度决定退出码
        if severity == "high" and summary["high_severity"] > 0:
            click.echo("\n❌ 发现高严重性问题，请及时修复", err=True)
            sys.exit(1)
        elif (
            severity == "medium"
            and (summary["high_severity"] + summary["medium_severity"]) > 0
        ):
            click.echo("\n⚠️ 发现中高严重性问题", err=True)
            sys.exit(1)
        elif summary["total_issues"] > 0:
            click.echo(
                f"\n📄 详细报告: {os.path.join(output_dir, 'api_consistency_report.md')}"
            )

    except Exception as e:
        click.echo(f"❌ 检查失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--output-dir", "-o", default="analysis", help="分析输出目录")
def analyze(output_dir: str):
    """分析API质量指标"""
    click.echo("📊 开始API质量分析...")

    try:
        os.makedirs(output_dir, exist_ok=True)

        # 生成API文档
        click.echo("🔍 扫描API端点...")
        try:
            # 尝试导入应用
            from src.main import app

            # 尝试导入API文档生成器
            from src.utils.api_doc_generator import generate_api_docs

            docs_data = generate_api_docs(app, output_dir)

            # 分析API质量
            analysis = _analyze_api_quality(docs_data)
            _save_analysis_report(analysis, output_dir)

            # 显示分析结果
            click.echo("✅ 分析完成!")
            click.echo(f"   📈 API质量得分: {analysis['quality_score']}/100")
            click.echo(f"   📋 总端点数: {analysis['total_endpoints']}")
            click.echo(f"   🏷️ 标签覆盖率: {analysis['tag_coverage']:.1f}%")
            click.echo(f"   📝 文档覆盖率: {analysis['documentation_coverage']:.1f}%")

            if analysis["recommendations"]:
                click.echo("\n💡 改进建议:")
                for rec in analysis["recommendations"][:3]:
                    click.echo(f"   • {rec}")

        except ImportError:
            click.echo("⚠️ 无法导入FastAPI应用，跳过详细分析", err=True)

    except Exception as e:
        click.echo(f"❌ 分析失败: {e}", err=True)
        sys.exit(1)


def _analyze_api_quality(docs_data: dict) -> dict:
    """分析API质量"""
    paths = docs_data.get("paths", {})
    total_endpoints = sum(len(methods) for methods in paths.values())

    # 计算文档覆盖率
    documented_endpoints = 0
    tagged_endpoints = 0

    for path, methods in paths.items():
        for method, operation in methods.items():
            # 检查是否有文档
            if operation.get("summary") or operation.get("description"):
                documented_endpoints += 1

            # 检查是否有标签
            if operation.get("tags"):
                tagged_endpoints += 1

    doc_coverage = (
        (documented_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0
    )
    tag_coverage = (
        (tagged_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0
    )

    # 计算质量得分
    quality_score = int((doc_coverage + tag_coverage) / 2)

    # 生成改进建议
    recommendations = []
    if doc_coverage < 80:
        recommendations.append("增加API文档覆盖率，为所有端点添加描述")
    if tag_coverage < 80:
        recommendations.append("为API端点添加标签以便分类管理")
    if total_endpoints < 10:
        recommendations.append("考虑添加更多功能端点")
    if total_endpoints > 100:
        recommendations.append("考虑将API进行模块化拆分")

    return {
        "quality_score": quality_score,
        "total_endpoints": total_endpoints,
        "documented_endpoints": documented_endpoints,
        "tagged_endpoints": tagged_endpoints,
        "documentation_coverage": doc_coverage,
        "tag_coverage": tag_coverage,
        "recommendations": recommendations,
    }


def _save_analysis_report(analysis: dict, output_dir: str):
    """保存分析报告"""
    import json
    from datetime import datetime

    analysis["timestamp"] = datetime.now().isoformat()

    # JSON报告
    json_path = os.path.join(output_dir, "api_quality_analysis.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    # Markdown报告
    md_content = f"""# API质量分析报告

## 质量概览

- **质量得分**: {analysis["quality_score"]}/100
- **总端点数**: {analysis["total_endpoints"]}
- **已文档化端点**: {analysis["documented_endpoints"]}
- **已标签端点**: {analysis["tagged_endpoints"]}
- **文档覆盖率**: {analysis["documentation_coverage"]:.1f}%
- **标签覆盖率**: {analysis["tag_coverage"]:.1f}%

## 改进建议

"""
    for rec in analysis["recommendations"]:
        md_content += f"- {rec}\n"

    md_path = os.path.join(output_dir, "api_quality_analysis.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)


@cli.command()
def setup():
    """初始化API工具配置"""
    click.echo("🔧 初始化API工具配置...")

    # 创建必要的目录
    directories = ["docs/api", "reports", "analysis", ".github/workflows"]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        click.echo(f"📁 创建目录: {directory}")

    # 创建GitHub Actions工作流
    workflow_content = """name: API Checks

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  api-docs:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt

    - name: Generate API docs
      run: |
        cd backend
        python -m src.cli.api_tools docs

    - name: Check API consistency
      run: |
        cd backend
        python -m src.cli.api_tools check --severity high

  deploy-docs:
    needs: api-docs
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - name: Deploy to GitHub Pages
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./backend/docs/api
"""

    workflow_path = ".github/workflows/api-checks.yml"
    with open(workflow_path, "w") as f:
        f.write(workflow_content)

    click.echo(f"📄 创建工作流: {workflow_path}")

    # 创建配置文件
    config_content = """{
  "api_tools": {
    "default_output_dir": "docs/api",
    "default_report_dir": "reports",
    "quality_threshold": 80,
    "ignore_patterns": [
      "*/node_modules/*",
      "*/__pycache__/*",
      "*/migrations/*"
    ]
  }
}
"""

    config_path = "api-tools.config.json"
    with open(config_path, "w") as f:
        f.write(config_content)

    click.echo(f"⚙️ 创建配置: {config_path}")
    click.echo("✅ 初始化完成!")


if __name__ == "__main__":
    cli()
