#!/usr/bin/env python3
"""
系统健康监控脚本
定期检查系统状态并发送告警
"""

import json
import os
import smtplib
import sqlite3
import sys
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))


class HealthMonitor:
    def __init__(self, config_file="monitor_config.json"):
        self.config = self.load_config(config_file)
        self.alerts = []

    def load_config(self, config_file):
        """加载监控配置"""
        default_config = {
            "api_url": "http://localhost:8002",
            "db_path": "../land_property.db",
            "check_interval": 300,  # 5分钟
            "alert_email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "to_email": "",
            },
            "thresholds": {
                "response_time": 5.0,  # 秒
                "db_size_mb": 1000,  # MB
                "error_rate": 0.1,  # 10%
            },
        }

        try:
            with open(config_file) as f:
                config = json.load(f)
                # 合并默认配置
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except FileNotFoundError:
            print(f"配置文件 {config_file} 不存在，使用默认配置")
            return default_config

    def check_api_health(self):
        """检查API服务健康状态"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.config['api_url']}/health", timeout=10)
            response_time = time.time() - start_time

            if response.status_code == 200:
                if response_time > self.config["thresholds"]["response_time"]:
                    self.alerts.append(
                        {
                            "type": "warning",
                            "message": f"API响应时间过长: {response_time:.2f}秒",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                return True, response_time
            else:
                self.alerts.append(
                    {
                        "type": "error",
                        "message": f"API服务异常: HTTP {response.status_code}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                return False, response_time

        except requests.exceptions.RequestException as e:
            self.alerts.append(
                {
                    "type": "critical",
                    "message": f"API服务无法访问: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return False, 0

    def check_database_health(self):
        """检查数据库健康状态"""
        db_path = self.config["db_path"]

        try:
            # 检查数据库文件是否存在
            if not os.path.exists(db_path):
                self.alerts.append(
                    {
                        "type": "critical",
                        "message": f"数据库文件不存在: {db_path}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                return False

            # 检查数据库大小
            db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
            if db_size_mb > self.config["thresholds"]["db_size_mb"]:
                self.alerts.append(
                    {
                        "type": "warning",
                        "message": f"数据库文件过大: {db_size_mb:.2f}MB",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # 检查数据库完整性
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()

            if result[0] != "ok":
                self.alerts.append(
                    {
                        "type": "critical",
                        "message": f"数据库完整性检查失败: {result[0]}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                conn.close()
                return False

            # 检查数据库连接
            cursor.execute("SELECT COUNT(*) FROM assets")
            asset_count = cursor.fetchone()[0]

            conn.close()
            return True, {"size_mb": db_size_mb, "asset_count": asset_count}

        except Exception as e:
            self.alerts.append(
                {
                    "type": "error",
                    "message": f"数据库检查失败: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return False, None

    def check_system_resources(self):
        """检查系统资源使用情况"""
        try:
            import psutil

            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 80:
                self.alerts.append(
                    {
                        "type": "warning",
                        "message": f"CPU使用率过高: {cpu_percent}%",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # 内存使用率
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                self.alerts.append(
                    {
                        "type": "warning",
                        "message": f"内存使用率过高: {memory.percent}%",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # 磁盘使用率
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent > 90:
                self.alerts.append(
                    {
                        "type": "warning",
                        "message": f"磁盘使用率过高: {disk_percent:.1f}%",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk_percent,
            }

        except ImportError:
            print("psutil未安装，跳过系统资源检查")
            return None
        except Exception as e:
            self.alerts.append(
                {
                    "type": "error",
                    "message": f"系统资源检查失败: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return None

    def send_alert_email(self):
        """发送告警邮件"""
        if not self.config["alert_email"]["enabled"] or not self.alerts:
            return

        try:
            msg = MIMEMultipart()
            msg["From"] = self.config["alert_email"]["username"]
            msg["To"] = self.config["alert_email"]["to_email"]
            msg["Subject"] = (
                f"土地物业系统告警 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # 构建邮件内容
            body = "系统监控发现以下问题：\n\n"
            for alert in self.alerts:
                body += f"[{alert['type'].upper()}] {alert['timestamp']}\n"
                body += f"  {alert['message']}\n\n"

            msg.attach(MIMEText(body, "plain", "utf-8"))

            # 发送邮件
            server = smtplib.SMTP(
                self.config["alert_email"]["smtp_server"],
                self.config["alert_email"]["smtp_port"],
            )
            server.starttls()
            server.login(
                self.config["alert_email"]["username"],
                self.config["alert_email"]["password"],
            )

            text = msg.as_string()
            server.sendmail(
                self.config["alert_email"]["username"],
                self.config["alert_email"]["to_email"],
                text,
            )
            server.quit()

            print(f"告警邮件已发送到 {self.config['alert_email']['to_email']}")

        except Exception as e:
            print(f"发送告警邮件失败: {str(e)}")

    def run_health_check(self):
        """执行完整的健康检查"""
        print(f"开始健康检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 清空之前的告警
        self.alerts = []

        # 检查API服务
        api_ok, response_time = self.check_api_health()
        print(f"API服务: {'✓' if api_ok else '✗'} (响应时间: {response_time:.2f}s)")

        # 检查数据库
        db_result = self.check_database_health()
        if isinstance(db_result, tuple):
            db_ok, db_info = db_result
            print(f"数据库: {'✓' if db_ok else '✗'}")
            if db_ok and db_info:
                print(
                    f"  大小: {db_info['size_mb']:.2f}MB, 资产数: {db_info['asset_count']}"
                )
        else:
            print("数据库: ✗")

        # 检查系统资源
        resources = self.check_system_resources()
        if resources:
            print(
                f"系统资源: CPU {resources['cpu_percent']}%, "
                f"内存 {resources['memory_percent']}%, "
                f"磁盘 {resources['disk_percent']:.1f}%"
            )

        # 显示告警
        if self.alerts:
            print(f"\n发现 {len(self.alerts)} 个问题:")
            for alert in self.alerts:
                print(f"  [{alert['type'].upper()}] {alert['message']}")

            # 发送告警邮件
            self.send_alert_email()
        else:
            print("✓ 系统运行正常")

        return len(self.alerts) == 0

    def run_continuous_monitor(self):
        """持续监控模式"""
        print("启动持续监控模式...")
        print(f"检查间隔: {self.config['check_interval']}秒")

        try:
            while True:
                self.run_health_check()
                print(f"下次检查时间: {datetime.now().strftime('%H:%M:%S')}")
                print("-" * 50)
                time.sleep(self.config["check_interval"])

        except KeyboardInterrupt:
            print("\n监控已停止")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="系统健康监控")
    parser.add_argument("--config", default="monitor_config.json", help="配置文件路径")
    parser.add_argument("--continuous", action="store_true", help="持续监控模式")

    args = parser.parse_args()

    monitor = HealthMonitor(args.config)

    if args.continuous:
        monitor.run_continuous_monitor()
    else:
        success = monitor.run_health_check()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
