import logging
import os
import subprocess
import sys
from pathlib import Path

# 添加 backend 目录到 path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_alembic_command(command, description):
    logger.info(f"开始执行: {description} ({command})")
    try:
        # 在 backend 目录下运行
        cwd = Path(__file__).parent.parent
        result = subprocess.run(
            command, cwd=cwd, shell=True, check=True, capture_output=True, text=True
        )
        logger.info(f"成功: {description}")
        logger.debug(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"失败: {description}")
        logger.error(f"错误输出:\n{e.stderr}")
        logger.error(f"标准输出:\n{e.stdout}")
        return False


def check_migrations():
    """
    验证数据库迁移的完整性：
    1. Upgrade Head (确保能升级到最新)
    2. Downgrade Base (确保能完全回滚)
    3. Upgrade Head (确保回滚后能再次升级)
    """
    logger.info("开始数据库迁移链路验证...")

    # 1. Upgrade to Head
    if not run_alembic_command("alembic upgrade head", "升级到最新版本 (Upgrade Head)"):
        sys.exit(1)

    # 2. Downgrade to Base
    if not run_alembic_command(
        "alembic downgrade base", "回滚到初始状态 (Downgrade Base)"
    ):
        sys.exit(1)

    # 3. Upgrade to Head Again
    if not run_alembic_command(
        "alembic upgrade head", "再次升级到最新版本 (Re-Upgrade Head)"
    ):
        sys.exit(1)

    logger.info("✅ 数据库迁移链路验证通过！(Upgrade -> Downgrade -> Upgrade)")


if __name__ == "__main__":
    check_migrations()
