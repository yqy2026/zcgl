#!/usr/bin/env python3
"""
系统文档自动生成脚本
生成系统架构、配置、部署和运维文档
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import subprocess
import platform

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


class SystemDocumentationGenerator:
    """系统文档生成器"""

    def __init__(self):
        self.project_root = project_root
        self.backend_dir = project_root / "backend"
        self.frontend_dir = project_root / "frontend"
        self.output_dir = project_root / "docs" / "generated" / "system"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "architecture": platform.architecture(),
            "processor": platform.processor(),
            "node": self._get_node_version(),
            "npm": self._get_npm_version()
        }

    def _get_node_version(self) -> str:
        """获取Node.js版本"""
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "Not installed"

    def _get_npm_version(self) -> str:
        """获取npm版本"""
        try:
            result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "Not installed"

    def get_project_structure(self) -> Dict[str, Any]:
        """获取项目结构"""
        structure = {
            "name": "land-property-management",
            "description": "土地物业资产管理系统",
            "directories": {},
            "total_files": 0,
            "total_lines": 0
        }

        # 扫描后端目录
        if self.backend_dir.exists():
            structure["directories"]["backend"] = self._scan_directory(
                self.backend_dir,
                exclude_patterns=["__pycache__", "*.pyc", ".pytest_cache", "site-packages"]
            )

        # 扫描前端目录
        if self.frontend_dir.exists():
            structure["directories"]["frontend"] = self._scan_directory(
                self.frontend_dir,
                exclude_patterns=["node_modules", "dist", ".next", ".nuxt"]
            )

        return structure

    def _scan_directory(self, directory: Path, exclude_patterns: List[str] = None) -> Dict[str, Any]:
        """扫描目录结构"""
        if exclude_patterns is None:
            exclude_patterns = []

        import fnmatch

        def should_exclude(path: Path) -> bool:
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(path.name, pattern) or pattern in str(path):
                    return True
            return False

        def scan_recursive(dir_path: Path) -> Dict[str, Any]:
            result = {
                "files": [],
                "subdirectories": {},
                "file_count": 0,
                "total_lines": 0
            }

            try:
                for item in dir_path.iterdir():
                    if should_exclude(item):
                        continue

                    if item.is_file():
                        file_info = {
                            "name": item.name,
                            "size": item.stat().st_size,
                            "extension": item.suffix,
                            "lines": self._count_lines(item)
                        }
                        result["files"].append(file_info)
                        result["file_count"] += 1
                        result["total_lines"] += file_info["lines"]

                    elif item.is_dir():
                        subdir_info = scan_recursive(item)
                        result["subdirectories"][item.name] = subdir_info
                        result["file_count"] += subdir_info["file_count"]
                        result["total_lines"] += subdir_info["total_lines"]

            except PermissionError:
                pass

            return result

        return scan_recursive(directory)

    def _count_lines(self, file_path: Path) -> int:
        """计算文件行数"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    def get_dependencies(self) -> Dict[str, Any]:
        """获取依赖信息"""
        dependencies = {
            "backend": {},
            "frontend": {}
        }

        # 后端依赖
        pyproject_path = self.backend_dir / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, 'r', encoding='utf-8') as f:
                    pyproject_data = tomllib.load(f)
                    dependencies["backend"] = {
                        "dependencies": pyproject_data.get("project", {}).get("dependencies", []),
                        "dev_dependencies": pyproject_data.get("project", {}).get("optional-dependencies", {}).get("dev", []),
                        "python_requires": pyproject_data.get("project", {}).get("requires-python", "Unknown")
                    }
            except Exception as e:
                dependencies["backend"]["error"] = str(e)

        # 前端依赖
        package_json_path = self.frontend_dir / "package.json"
        if package_json_path.exists():
            try:
                with open(package_json_path, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                    dependencies["frontend"] = {
                        "dependencies": dict(package_data.get("dependencies", {})),
                        "dev_dependencies": dict(package_data.get("devDependencies", {})),
                        "node_version": package_data.get("engines", {}).get("node", "Unknown"),
                        "npm_version": package_data.get("engines", {}).get("npm", "Unknown")
                    }
            except Exception as e:
                dependencies["frontend"]["error"] = str(e)

        return dependencies

    def get_configuration(self) -> Dict[str, Any]:
        """获取配置信息"""
        config = {
            "backend": {},
            "frontend": {},
            "environment": {}
        }

        # 后端配置
        config_files = [
            ".env",
            ".env.example",
            "config/settings.py",
            "config/config.py"
        ]

        for config_file in config_files:
            config_path = self.backend_dir / config_file
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 只读取非敏感配置
                        if not config_file.startswith('.env'):
                            config["backend"][config_file] = content[:1000] + "..." if len(content) > 1000 else content
                        else:
                            config["backend"][config_file] = "[Environment file - content hidden]"
                except Exception as e:
                    config["backend"][config_file] = f"Error reading: {e}"

        # 前端配置
        frontend_config_files = [
            ".env",
            ".env.example",
            "vite.config.ts",
            "tsconfig.json",
            "package.json"
        ]

        for config_file in frontend_config_files:
            config_path = self.frontend_dir / config_file
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if not config_file.startswith('.env'):
                            config["frontend"][config_file] = content[:1000] + "..." if len(content) > 1000 else content
                        else:
                            config["frontend"][config_file] = "[Environment file - content hidden]"
                except Exception as e:
                    config["frontend"][config_file] = f"Error reading: {e}"

        # 环境变量
        env_vars = [
            "DATABASE_URL",
            "DEV_MODE",
            "API_HOST",
            "API_PORT",
            "CORS_ORIGINS",
            "LOG_LEVEL"
        ]

        config["environment"] = {var: os.getenv(var, "Not set") for var in env_vars}

        return config

    def get_deployment_info(self) -> Dict[str, Any]:
        """获取部署信息"""
        deployment = {
            "development": {
                "backend": {
                    "command": "uv run python run_dev.py",
                    "port": 8002,
                    "health_check": "http://localhost:8002/health",
                    "docs": "http://localhost:8002/docs"
                },
                "frontend": {
                    "command": "npm run dev",
                    "port": 5173,
                    "health_check": "http://localhost:5173"
                }
            },
            "production": {
                "backend": {
                    "requirements": [
                        "Production database (MySQL/PostgreSQL)",
                        "Redis for caching",
                        "Load balancer",
                        "SSL certificate"
                    ],
                    "deployment_steps": [
                        "Configure environment variables",
                        "Install dependencies: uv sync",
                        "Run database migrations",
                        "Build frontend assets",
                        "Start application with Gunicorn",
                        "Configure reverse proxy (Nginx)"
                    ]
                },
                "frontend": {
                    "build_command": "npm run build",
                    "output_dir": "dist",
                    "deployment_steps": [
                        "Install dependencies: npm ci",
                        "Build application: npm run build",
                        "Configure web server",
                        "Enable gzip compression",
                        "Set up caching headers"
                    ]
                }
            }
        }

        return deployment

    def get_monitoring_info(self) -> Dict[str, Any]:
        """获取监控信息"""
        monitoring = {
            "logs": {
                "backend": {
                    "location": "logs/",
                    "format": "JSON structured logging",
                    "rotation": "Daily with 30-day retention"
                },
                "frontend": {
                    "location": "Browser console",
                    "format": "Console and Error tracking"
                }
            },
            "metrics": {
                "application": {
                    "response_time": "API response times",
                    "error_rate": "Failed request percentage",
                    "request_count": "Total API requests",
                    "active_users": "Concurrent users"
                },
                "infrastructure": {
                    "cpu_usage": "CPU utilization",
                    "memory_usage": "Memory consumption",
                    "disk_usage": "Storage utilization",
                    "network_io": "Network traffic"
                }
            },
            "alerts": [
                "High error rate (>5%)",
                "Slow response time (>2s)",
                "High memory usage (>80%)",
                "Database connection failures",
                "File upload failures"
            ]
        }

        return monitoring

    def generate_markdown_documentation(self) -> str:
        """生成Markdown文档"""
        system_info = self.get_system_info()
        project_structure = self.get_project_structure()
        dependencies = self.get_dependencies()
        configuration = self.get_configuration()
        deployment = self.get_deployment_info()
        monitoring = self.get_monitoring_info()

        markdown = [
            "# System Documentation\n",
            f"Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n",
            "## System Information\n",
            f"- **Platform**: {system_info['platform']}\n",
            f"- **Python Version**: {system_info['python_version']}\n",
            f"- **Node.js Version**: {system_info['node']}\n",
            f"- **NPM Version**: {system_info['npm']}\n",
            "## Project Structure\n",
            f"**Total Files**: {project_structure['total_files']}\n",
            f"**Total Lines**: {project_structure['total_lines']}\n"
        ]

        # 项目结构详情
        for dir_name, dir_info in project_structure["directories"].items():
            markdown.append(f"### {dir_name.title()}\n")
            markdown.append(f"- **Files**: {dir_info['file_count']}\n")
            markdown.append(f"- **Lines of Code**: {dir_info['total_lines']}\n")
            markdown.append("")

        # 依赖信息
        markdown.append("## Dependencies\n")
        markdown.append("### Backend\n")
        if dependencies.get("backend", {}).get("dependencies"):
            markdown.append("**Main Dependencies**:\n")
            for dep in dependencies["backend"]["dependencies"][:10]:  # 只显示前10个
                markdown.append(f"- {dep}\n")
            markdown.append("")

        markdown.append("### Frontend\n")
        if dependencies.get("frontend", {}).get("dependencies"):
            markdown.append("**Main Dependencies**:\n")
            for dep in list(dependencies["frontend"]["dependencies"].keys())[:10]:  # 只显示前10个
                markdown.append(f"- {dep}\n")
            markdown.append("")

        # 开发环境设置
        markdown.append("## Development Setup\n")
        markdown.append("### Backend\n")
        markdown.append("```bash\n")
        markdown.append("cd backend\n")
        markdown.append("uv sync\n")
        markdown.append("uv run python run_dev.py\n")
        markdown.append("```\n")
        markdown.append("### Frontend\n")
        markdown.append("```bash\n")
        markdown.append("cd frontend\n")
        markdown.append("npm install\n")
        markdown.append("npm run dev\n")
        markdown.append("```\n")

        # 部署信息
        markdown.append("## Deployment\n")
        markdown.append("### Development\n")
        markdown.append("- **Backend**: http://localhost:8002\n")
        markdown.append("- **Frontend**: http://localhost:5173\n")
        markdown.append("- **API Docs**: http://localhost:8002/docs\n")
        markdown.append("### Production\n")
        markdown.append("**Backend Requirements**:\n")
        for req in deployment["production"]["backend"]["requirements"]:
            markdown.append(f"- {req}\n")
        markdown.append("")

        # 监控信息
        markdown.append("## Monitoring\n")
        markdown.append("### Logs\n")
        markdown.append("- **Backend**: Structured JSON logs with rotation\n")
        markdown.append("- **Frontend**: Browser console with error tracking\n")
        markdown.append("### Metrics\n")
        for category, metrics in monitoring["metrics"].items():
            markdown.append(f"**{category.title()}**:\n")
            for metric, description in metrics.items():
                markdown.append(f"- {metric.replace('_', ' ').title()}: {description}\n")
            markdown.append("")

        # 故障排除
        markdown.append("## Troubleshooting\n")
        markdown.append("### Common Issues\n")
        markdown.append("1. **Database Connection Error**\n")
        markdown.append("   - Check database URL configuration\n")
        markdown.append("   - Verify database server is running\n")
        markdown.append("   - Check network connectivity\n")
        markdown.append("")
        markdown.append("2. **Port Conflicts**\n")
        markdown.append("   - Backend uses port 8002\n")
        markdown.append("   - Frontend uses port 5173\n")
        markdown.append("   - Kill processes using these ports if necessary\n")
        markdown.append("")
        markdown.append("3. **Dependency Issues**\n")
        markdown.append("   - Backend: Run `uv sync` to refresh dependencies\n")
        markdown.append("   - Frontend: Run `npm install` to refresh dependencies\n")
        markdown.append("")

        return "\n".join(markdown)

    def save_documentation(self):
        """保存文档到文件"""
        # 生成各种文档
        system_info = self.get_system_info()
        project_structure = self.get_project_structure()
        dependencies = self.get_dependencies()
        configuration = self.get_configuration()
        deployment = self.get_deployment_info()
        monitoring = self.get_monitoring_info()

        # 保存JSON格式文档
        with open(self.output_dir / "system_info.json", "w", encoding="utf-8") as f:
            json.dump(system_info, f, indent=2, ensure_ascii=False)

        with open(self.output_dir / "project_structure.json", "w", encoding="utf-8") as f:
            json.dump(project_structure, f, indent=2, ensure_ascii=False)

        with open(self.output_dir / "dependencies.json", "w", encoding="utf-8") as f:
            json.dump(dependencies, f, indent=2, ensure_ascii=False)

        with open(self.output_dir / "deployment.json", "w", encoding="utf-8") as f:
            json.dump(deployment, f, indent=2, ensure_ascii=False)

        with open(self.output_dir / "monitoring.json", "w", encoding="utf-8") as f:
            json.dump(monitoring, f, indent=2, ensure_ascii=False)

        # 生成Markdown文档
        markdown_doc = self.generate_markdown_documentation()
        with open(self.output_dir / "system.md", "w", encoding="utf-8") as f:
            f.write(markdown_doc)

        # 复制到docs目录
        docs_dir = self.project_root / "docs"
        docs_dir.mkdir(exist_ok=True)

        import shutil
        shutil.copy2(self.output_dir / "system.md", docs_dir / "system.md")

        print(f"System documentation generated successfully!")
        print(f"Output directory: {self.output_dir}")
        print(f"Files generated:")
        print(f"  - System Info: {self.output_dir / 'system_info.json'}")
        print(f"  - Project Structure: {self.output_dir / 'project_structure.json'}")
        print(f"  - Dependencies: {self.output_dir / 'dependencies.json'}")
        print(f"  - Deployment: {self.output_dir / 'deployment.json'}")
        print(f"  - Monitoring: {self.output_dir / 'monitoring.json'}")
        print(f"  - Markdown: {self.output_dir / 'system.md'}")


def main():
    """主函数"""
    print("🖥️  Generating system documentation...")

    try:
        generator = SystemDocumentationGenerator()
        generator.save_documentation()
        print("✅ System documentation generation completed successfully!")
    except Exception as e:
        print(f"❌ System documentation generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()