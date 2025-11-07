#!/usr/bin/env python3
"""
配置管理迁移脚本
将分散的配置文件迁移到统一配置管理系统
"""

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional

import yaml

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# 先验证统一配置文件是否存在
config_file = project_root / "src" / "core" / "unified_config.py"
if not config_file.exists():
    print("⚠️ 统一配置文件还未创建，将跳过配置迁移")
    print("📝 请先完成统一错误处理和配置管理的实现")
    sys.exit(0)

# 现在导入统一配置
from core.unified_config import ConfigManager, UnifiedConfig


class ConfigMigrator:
    """配置迁移器"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.backup_dir = project_root / "config" / "backups"
        self.migration_log = []

    def migrate_all(self) -> bool:
        """执行所有迁移"""
        print("🚀 开始配置迁移...")

        try:
            # 创建备份目录
            self.create_backup_directory()

            # 识别现有配置文件
            config_files = self.identify_config_files()
            print(f"📁 发现 {len(config_files)} 个配置文件")

            # 备份现有配置
            self.backup_existing_configs(config_files)

            # 迁移配置
            migration_results = self.migrate_configs(config_files)

            # 生成新的统一配置文件
            self.generate_unified_config(migration_results)

            # 验证新配置
            if self.validate_new_config():
                print("✅ 配置迁移成功！")
                self.print_migration_summary()
                return True
            else:
                print("❌ 配置验证失败，正在回滚...")
                self.rollback_migration()
                return False

        except Exception as e:
            print(f"❌ 迁移过程中发生错误: {e}")
            self.rollback_migration()
            return False

    def create_backup_directory(self):
        """创建备份目录"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.backup_dir / f"migration_{timestamp}"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        print(f"📦 备份目录: {self.backup_dir}")

    def identify_config_files(self) -> List[Path]:
        """识别现有配置文件"""
        config_files = []

        # 搜索配置文件
        patterns = ["*.env*", "*.yaml", "*.yml", "config.json", "settings.py", "*.toml"]

        for pattern in patterns:
            for config_file in project_root.rglob(pattern):
                # 跳过某些目录
                if any(
                    skip in str(config_file)
                    for skip in [
                        "node_modules",
                        ".git",
                        "__pycache__",
                        "venv",
                        ".venv",
                        "build",
                        "dist",
                    ]
                ):
                    continue

                # 检查是否为配置相关文件
                if self.is_config_file(config_file):
                    config_files.append(config_file)

        return sorted(config_files)

    def is_config_file(self, file_path: Path) -> bool:
        """判断是否为配置文件"""
        # 检查文件名
        config_names = [
            "config",
            "settings",
            "env",
            "application",
            "app",
            "database",
            "cache",
            "security",
        ]

        file_name_lower = file_path.name.lower()
        return any(name in file_name_lower for name in config_names)

    def backup_existing_configs(self, config_files: List[Path]):
        """备份现有配置文件"""
        print("💾 备份现有配置文件...")

        for config_file in config_files:
            try:
                # 保持相对路径结构
                relative_path = config_file.relative_to(project_root)
                backup_path = self.backup_dir / relative_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(config_file, backup_path)
                self.migration_log.append(f"备份: {config_file} -> {backup_path}")

            except Exception as e:
                print(f"⚠️ 备份失败 {config_file}: {e}")

    def migrate_configs(self, config_files: List[Path]) -> Dict[str, Dict]:
        """迁移配置文件"""
        print("🔄 迁移配置文件...")

        migration_results = {
            "environment_variables": {},
            "yaml_configs": {},
            "python_configs": {},
            "json_configs": {},
        }

        for config_file in config_files:
            try:
                if config_file.suffix in [".yaml", ".yml"]:
                    result = self.migrate_yaml_config(config_file)
                    migration_results["yaml_configs"][str(config_file)] = result

                elif config_file.suffix == ".json":
                    result = self.migrate_json_config(config_file)
                    migration_results["json_configs"][str(config_file)] = result

                elif config_file.name.startswith(".env"):
                    result = self.migrate_env_config(config_file)
                    migration_results["environment_variables"].update(result)

                elif config_file.suffix == ".py" and "config" in config_file.name:
                    result = self.migrate_python_config(config_file)
                    migration_results["python_configs"][str(config_file)] = result

                self.migration_log.append(f"迁移: {config_file}")

            except Exception as e:
                print(f"⚠️ 迁移失败 {config_file}: {e}")
                self.migration_log.append(f"迁移失败: {config_file} - {e}")

        return migration_results

    def migrate_yaml_config(self, config_file: Path) -> Dict:
        """迁移YAML配置"""
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

        # 映射配置到新的结构
        mapped_config = self.map_config_structure(config_data, str(config_file))

        return {"original": config_data, "mapped": mapped_config, "type": "yaml"}

    def migrate_json_config(self, config_file: Path) -> Dict:
        """迁移JSON配置"""
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        mapped_config = self.map_config_structure(config_data, str(config_file))

        return {"original": config_data, "mapped": mapped_config, "type": "json"}

    def migrate_env_config(self, config_file: Path) -> Dict:
        """迁移环境变量配置"""
        env_vars = {}

        with open(config_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()

        # 移除不安全的配置
        secure_keys = ["SECRET_KEY", "DATABASE_URL", "REDIS_URL"]
        for key in secure_keys:
            if key in env_vars:
                print(f"🔒 发现敏感配置 {key}，建议使用环境变量")

        return env_vars

    def migrate_python_config(self, config_file: Path) -> Dict:
        """迁移Python配置文件"""
        # 这里可以添加解析Python配置文件的逻辑
        # 由于Python配置文件格式多样，这里简单返回文件信息
        return {
            "file_path": str(config_file),
            "type": "python",
            "note": "Python配置文件需要手动迁移",
        }

    def map_config_structure(self, config_data: Dict, source_file: str) -> Dict:
        """映射配置到新的统一结构"""
        mapped = {}

        # 数据库配置映射
        if "database" in config_data or "db" in config_data:
            db_config = config_data.get("database") or config_data.get("db", {})
            mapped["database"] = {
                "url": db_config.get("url", ""),
                "echo": db_config.get("echo", False),
                "pool_size": db_config.get("pool_size", 10),
                "max_overflow": db_config.get("max_overflow", 20),
            }

        # API配置映射
        if "api" in config_data or "server" in config_data:
            api_config = config_data.get("api") or config_data.get("server", {})
            mapped["api"] = {
                "host": api_config.get("host", "0.0.0.0"),
                "port": api_config.get("port", 8002),
                "debug": api_config.get("debug", False),
                "title": api_config.get("title", "API"),
                "version": api_config.get("version", "1.0.0"),
            }

        # 安全配置映射
        if "security" in config_data:
            security_config = config_data["security"]
            mapped["security"] = {
                "secret_key": security_config.get("secret_key", ""),
                "allowed_origins": security_config.get("allowed_origins", ["*"]),
                "allowed_methods": security_config.get("allowed_methods", ["*"]),
                "allowed_headers": security_config.get("allowed_headers", ["*"]),
            }

        # 日志配置映射
        if "logging" in config_data or "log" in config_data:
            log_config = config_data.get("logging") or config_data.get("log", {})
            mapped["logging"] = {
                "level": log_config.get("level", "INFO"),
                "format": log_config.get("format", ""),
                "file_enabled": log_config.get("file_enabled", True),
                "console_enabled": log_config.get("console_enabled", True),
            }

        return mapped

    def generate_unified_config(self, migration_results: Dict) -> bool:
        """生成统一的配置文件"""
        print("📝 生成统一配置文件...")

        try:
            # 合并所有配置
            unified_config_data = self.merge_configs(migration_results)

            # 生成新的环境配置文件
            self.generate_env_file(unified_config_data)

            # 生成新的YAML配置文件
            self.generate_yaml_file(unified_config_data)

            # 生成配置文档
            self.generate_config_documentation(unified_config_data, migration_results)

            return True

        except Exception as e:
            print(f"❌ 生成统一配置失败: {e}")
            return False

    def merge_configs(self, migration_results: Dict) -> Dict:
        """合并所有配置数据"""
        unified_config = {
            "environment": "development",
            "debug": False,
            "database": {},
            "api": {},
            "security": {},
            "logging": {},
            "file_upload": {},
            "cache": {},
            "monitoring": {},
        }

        # 合并YAML配置
        for file_path, config_data in migration_results["yaml_configs"].items():
            mapped = config_data["mapped"]
            for section, values in mapped.items():
                if section in unified_config:
                    unified_config[section].update(values)

        # 合并JSON配置
        for file_path, config_data in migration_results["json_configs"].items():
            mapped = config_data["mapped"]
            for section, values in mapped.items():
                if section in unified_config:
                    unified_config[section].update(values)

        return unified_config

    def generate_env_file(self, config_data: Dict):
        """生成环境配置文件"""
        env_file = project_root / ".env"

        env_content = f"""# 环境配置
ENVIRONMENT={config_data.get("environment", "development")}
DEBUG={str(config_data.get("debug", False)).lower()}

# API配置
API_HOST={config_data.get("api", {}).get("host", "0.0.0.0")}
API_PORT={config_data.get("api", {}).get("port", 8002)}
API_DEBUG={str(config_data.get("api", {}).get("debug", False)).lower()}

# 数据库配置
DATABASE_URL={config_data.get("database", {}).get("url", "sqlite:///./app.db")}
DATABASE_ECHO={str(config_data.get("database", {}).get("echo", False)).lower()}

# 安全配置
SECRET_KEY={config_data.get("security", {}).get("secret_key", "your-secret-key-change-in-production")}
ALLOWED_ORIGINS={",".join(config_data.get("security", {}).get("allowed_origins", ["*"]))}

# 日志配置
LOG_LEVEL={config_data.get("logging", {}).get("level", "INFO")}
LOG_FILE_ENABLED={str(config_data.get("logging", {}).get("file_enabled", True)).lower()}
"""

        with open(env_file, "w", encoding="utf-8") as f:
            f.write(env_content)

        self.migration_log.append(f"生成环境配置: {env_file}")

    def generate_yaml_file(self, config_data: Dict):
        """生成YAML配置文件"""
        yaml_file = project_root / "config.yaml"

        with open(yaml_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        self.migration_log.append(f"生成YAML配置: {yaml_file}")

    def generate_config_documentation(self, config_data: Dict, migration_results: Dict):
        """生成配置文档"""
        doc_file = project_root / "CONFIG_MIGRATION_REPORT.md"

        doc_content = f"""# 配置迁移报告

**迁移时间**: {datetime.now().isoformat()}
**迁移文件数**: {len(self.migration_log)}

## 迁移详情

### 迁移的配置文件
"""

        for log_entry in self.migration_log:
            doc_content += f"- {log_entry}\n"

        doc_content += f"""

## 新的配置结构

### 环境变量 (.env)
主要包含运行时配置和敏感信息。

### YAML配置 (config.yaml)
包含应用的结构化配置。

## 配置项说明

### 数据库配置
- `DATABASE_URL`: 数据库连接URL
- `DATABASE_ECHO`: 是否打印SQL语句

### API配置
- `API_HOST`: API服务器主机
- `API_PORT`: API服务器端口
- `API_DEBUG`: 调试模式

### 安全配置
- `SECRET_KEY`: JWT密钥（生产环境必须更改）
- `ALLOWED_ORIGINS`: 允许的跨域源

## 后续步骤

1. 检查生成的配置文件
2. 更新敏感配置信息
3. 测试应用启动
4. 删除旧的配置文件（可选）
"""

        with open(doc_file, "w", encoding="utf-8") as f:
            f.write(doc_content)

        self.migration_log.append(f"生成配置文档: {doc_file}")

    def validate_new_config(self) -> bool:
        """验证新配置"""
        print("✅ 验证新配置...")

        try:
            # 尝试加载新配置
            config = self.config_manager.load_config()

            # 基本验证
            assert config.database.url, "数据库URL不能为空"
            assert config.api.port > 0, "API端口必须大于0"
            assert len(config.security.secret_key) >= 32, "密钥长度必须至少32字符"

            print("✅ 配置验证通过")
            return True

        except Exception as e:
            print(f"❌ 配置验证失败: {e}")
            return False

    def rollback_migration(self):
        """回滚迁移"""
        print("🔄 回滚迁移...")

        if not self.backup_dir.exists():
            print("❌ 备份目录不存在，无法回滚")
            return

        try:
            # 恢复备份的配置文件
            for backup_file in self.backup_dir.rglob("*"):
                if backup_file.is_file():
                    relative_path = backup_file.relative_to(self.backup_dir)
                    original_path = project_root / relative_path
                    original_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_file, original_path)

            # 删除生成的新配置文件
            new_files = [
                project_root / ".env",
                project_root / "config.yaml",
                project_root / "CONFIG_MIGRATION_REPORT.md",
            ]

            for file_path in new_files:
                if file_path.exists():
                    file_path.unlink()

            print("✅ 迁移已回滚")

        except Exception as e:
            print(f"❌ 回滚失败: {e}")

    def print_migration_summary(self):
        """打印迁移摘要"""
        print("\n" + "=" * 60)
        print("🎉 配置迁移完成摘要")
        print("=" * 60)
        print(f"📁 备份位置: {self.backup_dir}")
        print(f"📋 操作日志: {len(self.migration_log)} 个操作")
        print("\n📝 生成的文件:")
        print("  - .env (环境配置)")
        print("  - config.yaml (YAML配置)")
        print("  - CONFIG_MIGRATION_REPORT.md (迁移报告)")
        print("\n🔧 后续步骤:")
        print("  1. 检查 .env 文件中的敏感配置")
        print("  2. 根据需要调整配置参数")
        print("  3. 测试应用启动: python src/main_unified.py")
        print("  4. 确认无问题后可删除旧配置文件")
        print("=" * 60)


def main():
    """主函数"""
    migrator = ConfigMigrator()

    print("🚀 地产资产管理系统 - 配置迁移工具")
    print("⚠️ 此工具将迁移现有配置到统一配置管理系统")
    print()

    # 确认执行
    response = input("是否继续执行配置迁移? (y/N): ").strip().lower()
    if response not in ["y", "yes"]:
        print("❌ 取消配置迁移")
        return

    # 执行迁移
    success = migrator.migrate_all()

    if success:
        print("\n🎉 配置迁移成功完成!")
        print("请检查生成的配置文件并根据需要进行调整。")
    else:
        print("\n❌ 配置迁移失败!")
        print("请检查错误信息并手动处理。")
        sys.exit(1)


if __name__ == "__main__":
    from datetime import datetime

    main()
