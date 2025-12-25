#!/usr/bin/env python3
"""
质量监控系统安装脚本
Setup script for Quality Monitoring System

该脚本用于安装和配置持续质量监控系统的所有组件：
- 安装必要的依赖
- 创建配置文件
- 设置目录结构
- 创建Git hooks
- 配置定时任务
"""

import os
import platform
import subprocess
import sys
from pathlib import Path


class QualityMonitorSetup:
    """质量监控系统安装器"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.scripts_dir = Path(__file__).parent
        self.system = platform.system().lower()

    def run_setup(self):
        """执行完整安装流程"""
        print("[启动] 开始安装持续质量监控系统...")
        print(f"[信息] 安装目录: {self.base_dir}")
        print(f"[信息] 操作系统: {self.system}")
        print("=" * 60)

        try:
            # 1. 检查环境
            self._check_environment()

            # 2. 安装依赖
            self._install_dependencies()

            # 3. 创建目录结构
            self._create_directories()

            # 4. 创建Git hooks
            self._create_git_hooks()

            # 5. 配置定时任务
            self._setup_scheduled_tasks()

            # 6. 生成初始报告
            self._generate_initial_report()

            # 7. 创建启动脚本
            self._create_startup_scripts()

            print("=" * 60)
            print("✅ 持续质量监控系统安装完成!")
            print("\n📋 下一步操作:")
            print("1. 运行快速检查: python scripts/quality_monitor.py --mode quick")
            print("2. 运行全面检查: python scripts/quality_monitor.py --mode comprehensive")
            print("3. 查看监控配置: cat quality_monitor_config.yaml")
            print("4. 设置持续监控: 参考 scripts/schedule_monitoring.py")

        except Exception as e:
            print(f"❌ 安装失败: {e}")
            sys.exit(1)

    def _check_environment(self):
        """检查运行环境"""
        print("[检查] 检查运行环境...")

        # 检查Python版本
        python_version = sys.version_info
        if python_version.major < 3 or python_version.minor < 8:
            raise Exception(f"需要Python 3.8+，当前版本: {python_version}")
        print(f"  ✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")

        # 检查是否在项目根目录
        if not (self.base_dir / "pyproject.toml").exists():
            raise Exception("请在项目根目录运行此脚本")
        print("  ✅ 项目目录检查通过")

        # 检查必要的工具
        required_tools = ["git"]
        for tool in required_tools:
            try:
                subprocess.run([tool, "--version"],
                           capture_output=True, check=True)
                print(f"  ✅ {tool} 可用")
            except (subprocess.CalledProcessError, FileNotFoundError):
                raise Exception(f"需要安装 {tool} 工具")

    def _install_dependencies(self):
        """安装必要的依赖包"""
        print("\n📦 安装质量监控依赖...")

        # 质量监控相关依赖
        quality_dependencies = [
            "requests>=2.31.0",      # HTTP请求
            "psutil>=5.9.0",         # 系统监控
            "pyyaml>=6.0.1",         # YAML配置
            "radon>=6.0.1",          # 代码复杂度分析
            "bandit>=1.7.5",         # 安全检查
            "pytest>=7.4.0",          # 测试框架
            "pytest-cov>=4.1.0",      # 测试覆盖率
            "pytest-asyncio>=0.21.0", # 异步测试
        ]

        # 检查是否使用uv
        if self._check_uv_available():
            print("  🔄 使用 uv 安装依赖...")
            cmd = ["uv", "add"] + quality_dependencies
            working_dir = self.base_dir
        else:
            print("  🔄 使用 pip 安装依赖...")
            cmd = ["pip", "install"] + quality_dependencies
            working_dir = None

        try:
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                check=True
            )
            print("  ✅ 依赖安装完成")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ 依赖安装失败: {e}")
            print(f"  错误输出: {e.stderr}")
            raise

        # 安装开发工具（如果使用uv）
        if self._check_uv_available():
            dev_dependencies = [
                "ruff>=0.1.6",              # 代码检查和格式化
                "mypy>=1.7.0",              # 类型检查
            ]
            try:
                subprocess.run(
                    ["uv", "add", "--dev"] + dev_dependencies,
                    cwd=self.base_dir,
                    capture_output=True,
                    check=True
                )
                print("  ✅ 开发工具安装完成")
            except subprocess.CalledProcessError as e:
                print(f"  ⚠️  开发工具安装失败: {e}")

    def _check_uv_available(self) -> bool:
        """检查uv是否可用"""
        try:
            subprocess.run(
                ["uv", "--version"],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _create_directories(self):
        """创建必要的目录结构"""
        print("\n📁 创建目录结构...")

        directories = [
            "logs/quality",
            "reports/daily",
            "reports/weekly",
            "reports/metadata",
            "data/metrics",
            ".git/hooks",
            "scripts/monitoring"
        ]

        for dir_path in directories:
            full_path = self.base_dir / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ {dir_path}")

        # 创建.gitkeep文件保持空目录
        gitkeep_dirs = ["logs/quality", "reports/daily", "reports/weekly", "data/metrics"]
        for dir_path in gitkeep_dirs:
            (self.base_dir / dir_path / ".gitkeep").touch()

    def _create_git_hooks(self):
        """创建Git hooks"""
        print("\n🔗 创建Git hooks...")

        hooks_dir = self.base_dir / ".git" / "hooks"

        # Pre-commit hook
        pre_commit_content = f"""#!/bin/bash
# Pre-commit quality gate
echo "🔍 运行提交前质量检查..."

cd "{self.base_dir}"

# 快速语法检查
echo "  检查语法..."
python -m ruff check src/ --select=E,F --quiet
if [ $? -ne 0 ]; then
    echo "❌ 语法检查失败，请修复后重新提交"
    exit 1
fi

# 基本导入检查
echo "  检查模块导入..."
python -c "import src.main; import src.models.asset; print('✅ 导入检查通过')"
if [ $? -ne 0 ]; then
    echo "❌ 模块导入失败，请修复后重新提交"
    exit 1
fi

# 快速测试
echo "  运行快速测试..."
python -m pytest tests/test_main.py tests/test_quick_suite.py -q --tb=no
if [ $? -ne 0 ]; then
    echo "❌ 快速测试失败，请修复后重新提交"
    exit 1
fi

echo "✅ 提交前质量检查通过"
exit 0
"""

        # Pre-push hook
        pre_push_content = f"""#!/bin/bash
# Pre-push quality gate
echo "🔍 运行推送前质量检查..."

cd "{self.base_dir}"

# 代码质量检查
echo "  检查代码质量..."
python -m ruff check src/ --quiet
if [ $? -ne 0 ]; then
    echo "❌ 代码质量检查失败，请修复后重新推送"
    exit 1
fi

# 单元测试
echo "  运行单元测试..."
python -m pytest tests/test_main.py tests/test_quick_suite.py tests/test_api.py -q --tb=no
if [ $? -ne 0 ]; then
    echo "❌ 单元测试失败，请修复后重新推送"
    exit 1
fi

# 类型检查
echo "  运行类型检查..."
python -m mypy src/ --no-error-summary
if [ $? -ne 0 ]; then
    echo "⚠️  类型检查发现问题，建议修复后推送"
    echo "  继续推送? (y/N)"
    read -r response
    if [[ ! $response =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✅ 推送前质量检查通过"
exit 0
"""

        # 写入hook文件
        hooks = {
            "pre-commit": pre_commit_content,
            "pre-push": pre_push_content
        }

        for hook_name, content in hooks.items():
            hook_file = hooks_dir / hook_name
            with open(hook_file, 'w', encoding='utf-8') as f:
                f.write(content)

            # 设置执行权限（Unix/Linux/macOS）
            if self.system != "windows":
                hook_file.chmod(0o755)

            print(f"  ✅ {hook_name}")

    def _setup_scheduled_tasks(self):
        """配置定时任务"""
        print("\n⏰ 配置定时任务...")

        # 创建调度脚本
        schedule_script = self.base_dir / "scripts" / "schedule_monitoring.py"
        schedule_content = f'''#!/usr/bin/env python3
"""
定时任务调度脚本
Scheduled task script for quality monitoring
"""

import subprocess
import time
import logging
from datetime import datetime
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('{self.base_dir}/logs/quality/schedule.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_quality_monitor(mode: str):
    """运行质量监控"""
    try:
        script_path = Path(__file__).parent / "quality_monitor.py"
        result = subprocess.run(
            ["python", str(script_path), "--mode", mode, "--format", "json"],
            capture_output=True,
            text=True,
            cwd="{self.base_dir}"
        )

        if result.returncode == 0:
            logger.info(f"质量监控成功 ({{mode}})")
        else:
            logger.error(f"质量监控失败 ({{mode}}): {{result.stderr}}")

    except Exception as e:
        logger.error(f"执行质量监控异常: {{e}}")

def main():
    """主调度循环"""
    logger.info("定时任务调度器启动")

    while True:
        try:
            current_time = datetime.now()

            # 每5分钟执行快速检查
            if current_time.minute % 5 == 0:
                logger.info("执行快速质量检查")
                run_quality_monitor("quick")

            # 每2小时执行中等检查
            if current_time.minute == 0 and current_time.hour % 2 == 0:
                logger.info("执行中等质量检查")
                run_quality_monitor("medium")

            # 每日执行全面检查
            if current_time.hour == 0 and current_time.minute == 0:
                logger.info("执行全面质量检查")
                run_quality_monitor("comprehensive")

            # 等待1分钟
            time.sleep(60)

        except KeyboardInterrupt:
            logger.info("定时任务调度器停止")
            break
        except Exception as e:
            logger.error(f"调度器异常: {{e}}")
            time.sleep(60)

if __name__ == "__main__":
    main()
'''

        with open(schedule_script, 'w', encoding='utf-8') as f:
            f.write(schedule_content)

        # 创建服务脚本
        if self.system == "linux":
            self._create_systemd_service()
        elif self.system == "darwin":  # macOS
            self._create_launchd_service()
        elif self.system == "windows":
            self._create_windows_service()

        print("  ✅ 定时任务脚本创建完成")

    def _create_systemd_service(self):
        """创建systemd服务文件（Linux）"""
        service_content = f"""[Unit]
Description=Quality Monitor Service
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'root')}
WorkingDirectory={self.base_dir}
ExecStart={sys.executable} {self.base_dir}/scripts/schedule_monitoring.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

        service_file = self.base_dir / "quality-monitor.service"
        with open(service_file, 'w', encoding='utf-8') as f:
            f.write(service_content)

        print(f"  📄 Systemd服务文件: {service_file}")
        print("  💡 启用服务: sudo cp quality-monitor.service /etc/systemd/system/")
        print("  💡 启动服务: sudo systemctl enable quality-monitor")
        print("  💡 开始服务: sudo systemctl start quality-monitor")

    def _create_launchd_service(self):
        """创建LaunchAgent服务文件（macOS）"""
        service_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.qualitymonitor</string>

    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{self.base_dir}/scripts/schedule_monitoring.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>{self.base_dir}</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>{self.base_dir}/logs/quality/monitor.log</string>

    <key>StandardErrorPath</key>
    <string>{self.base_dir}/logs/quality/monitor.error.log</string>
</dict>
</plist>
"""

        service_file = self.base_dir / "com.qualitymonitor.plist"
        with open(service_file, 'w', encoding='utf-8') as f:
            f.write(service_content)

        print(f"  📄 LaunchAgent文件: {service_file}")
        print("  💡 安装服务: cp com.qualitymonitor.plist ~/Library/LaunchAgents/")
        print("  💡 加载服务: launchctl load ~/Library/LaunchAgents/com.qualitymonitor.plist")

    def _create_windows_service(self):
        """创建Windows服务配置"""
        batch_content = f"""@echo off
echo Starting Quality Monitor Service...
cd /d "{self.base_dir}"
python scripts/schedule_monitoring.py
pause
"""

        batch_file = self.base_dir / "start_quality_monitor.bat"
        with open(batch_file, 'w', encoding='utf-8') as f:
            f.write(batch_content)

        # 创建PowerShell服务脚本
        ps_content = f"""# Quality Monitor Service for Windows
# 使用NSSM (Non-Sucking Service Manager) 安装为Windows服务

# 安装服务的PowerShell脚本
$nssmPath = "nssm.exe"  # 需要下载NSSM
$serviceName = "QualityMonitor"
$executable = "{sys.executable}"
$arguments = "{self.base_dir}\\scripts\\schedule_monitoring.py"
$workingDirectory = "{self.base_dir}"

Write-Host "安装质量监控Windows服务..."
Write-Host "需要先下载安装NSSM: https://nssm.cc/download"

if (Test-Path $nssmPath) {{
    & $nssmPath install $serviceName $executable $arguments
    & $nssmPath set $serviceName AppDirectory $workingDirectory
    & $nssmPath set $serviceName DisplayName "Quality Monitor Service"
    & $nssmPath set $serviceName Description "Continuous quality monitoring service"

    Write-Host "服务安装完成!"
    Write-Host "启动服务: nssm start $serviceName"
    Write-Host "停止服务: nssm stop $serviceName"
}} else {{
    Write-Host "NSSM未找到，请先安装NSSM"
    Write-Host "或者直接运行: start_quality_monitor.bat"
}}
"""

        ps_file = self.base_dir / "install_service.ps1"
        with open(ps_file, 'w', encoding='utf-8') as f:
            f.write(ps_content)

        print(f"  📄 批处理文件: {batch_file}")
        print(f"  📄 PowerShell脚本: {ps_file}")
        print("  💡 启动服务: 双击 start_quality_monitor.bat")
        print("  💡 安装系统服务: PowerShell运行 install_service.ps1 (需要NSSM)")

    def _generate_initial_report(self):
        """生成初始质量报告"""
        print("\n📊 生成初始质量报告...")

        try:
            # 运行质量监控脚本
            script_path = self.scripts_dir / "quality_monitor.py"
            result = subprocess.run(
                ["python", str(script_path), "--mode", "quick", "--format", "console"],
                capture_output=True,
                text=True,
                cwd=self.base_dir
            )

            if result.returncode == 0:
                print("  ✅ 初始报告生成成功")
                print(result.stdout)
            else:
                print("  ⚠️  初始报告生成遇到问题")
                print(result.stderr)

        except Exception as e:
            print(f"  ❌ 初始报告生成失败: {e}")

    def _create_startup_scripts(self):
        """创建启动脚本"""
        print("\n🚀 创建启动脚本...")

        # 快速检查脚本
        quick_check_script = self.base_dir / "quick_quality_check.py"
        quick_content = '''#!/usr/bin/env python3
"""快速质量检查快捷脚本"""

import subprocess
import sys
from pathlib import Path

script_path = Path(__file__).parent / "scripts" / "quality_monitor.py"
subprocess.run([sys.executable, str(script_path), "--mode", "quick", "--format", "console"])
'''

        with open(quick_check_script, 'w', encoding='utf-8') as f:
            f.write(quick_content)

        # 全面检查脚本
        full_check_script = self.base_dir / "full_quality_check.py"
        full_content = '''#!/usr/bin/env python3
"""全面质量检查快捷脚本"""

import subprocess
import sys
from pathlib import Path

script_path = Path(__file__).parent / "scripts" / "quality_monitor.py"
subprocess.run([sys.executable, str(script_path), "--mode", "comprehensive", "--format", "console"])
'''

        with open(full_check_script, 'w', encoding='utf-8') as f:
            f.write(full_content)

        print("  ✅ 快速检查脚本: quick_quality_check.py")
        print("  ✅ 全面检查脚本: full_quality_check.py")


def main():
    """主函数"""
    setup = QualityMonitorSetup()
    setup.run_setup()


if __name__ == "__main__":
    main()
