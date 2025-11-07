"""数据备份和恢复服�?
使用SQLite数据库的备份和恢复功�?
"""

import logging

logger = logging.getLogger(__name__)


class BackupError(Exception):
    """备份操作异常"""

    pass


class RestoreError(Exception):
    """恢复操作异常"""

    pass


class BackupConfig:
    """备份配置"""

    def __init__(self):
        pass
