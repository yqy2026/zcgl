#!/usr/bin/env python3
"""
智能项目清理脚本

使用模式匹配自动发现并清理临时文件、缓存文件和无效文件。
不需要手动维护文件列表，自动适应项目变化。

用法:
    python scripts/cleanup_project.py --dry-run    # 预览将删除的文件
    python scripts/cleanup_project.py --confirm    # 确认后执行清理
    python scripts/cleanup_project.py --backup     # 备份后清理

作者: Claude Code
日期: 2025-12-31
更新: 重构为智能模式匹配，无需手动维护文件列表
"""

import os
import sys
import shutil
import argparse
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Set

# ============== 智能清理配置 ==============

PROJECT_ROOT = Path(__file__).parent.parent

# 文件模式匹配规则
FILE_PATTERNS = {
    # 测试输出文件
    'test_outputs': [
        r'\.coverage$',
        r'coverage\.(json|xml)$',
        r'junit-report\.xml$',
        r'htmlcov$',  # 目录
        r'\.pytest_cache$',  # 目录
    ],

    # 临时数据库文件
    'temp_databases': [
        r'test.*\.db$',
        r'.*\.db-(shm|wal|journal)$',
        r'defect_tracking\.db$',
        r'database\.sqlite$',
    ],

    # 临时分析脚本（基于命名模式）
    'temp_scripts': [
        r'backend/(check|find|get|analyze)_.*\.py$',
        r'backend/.*_coverage\.py$',
        r'backend/.*_missing\.py$',
        r'backend/.*_quick_wins\.py$',
    ],

    # 缓存目录
    'cache_dirs': [
        r'\..*_cache$',  # .mypy_cache, .pytest_cache, .ruff_cache
        r'__pycache__$',
        r'node_modules/\.cache$',
    ],

    # 构建产物和报告
    'build_artifacts': [
        r'.*-report\.(json|xml)$',
        r'dist$',  # 目录
        r'coverage$',  # 目录
    ],

    # 调试产物
    'debug_artifacts': [
        r'\.playwright-mcp$',  # 目录
    ],

    # 日志文件
    'log_files': [
        r'.*\.log$',
        r'logs/.*$',
        r'backend/logs/.*$',
        r'frontend.*\.log$',
    ],

    # 临时报告和文档文件
    'temp_reports': [
        r'^TEST_.*\.md$',
        r'^FINAL_.*\.md$',
        r'^RALPH_.*\.md$',
        r'^PUSH_TO_.*\.md$',
        r'.*_ACHIEVEMENT\.md$',
        r'.*_ANALYSIS\.md$',
        r'.*_SUMMARY\.md$',
        r'.*_REPORT\.md$',
        r'.*_COMPLETE\.md$',
    ],

    # 旧会话文件（保留最近3天）
    'old_sessions': [
        r'^sessions/\d{6}-',  # sessions/YYMMDD-*
    ],

    # 临时上传文件
    'temp_uploads': [
        r'backend/temp_uploads$',
        r'temp_uploads$',
    ],

    # 备份和临时文件
    'backup_files': [
        r'.*\.bak$',
        r'.*\.backup$',
        r'.*\.old$',
        r'.*~$',
        r'.*\.tmp$',
        r'.*\.temp$',
    ],
}

# 目录扫描规则
SCAN_DIRECTORIES = [
    '.',  # 根目录
    'backend',
    'frontend',
    'docs',
    'scripts',
    'tools',
    'sessions',
]

# 排除的目录（不扫描）
EXCLUDE_DIRECTORIES = {
    '.git',
    '.vscode',
    '.idea',
    'node_modules',
    '.venv',
    'venv',
    '__pycache__',
}

# 保护的文件（永远不删除）
PROTECTED_FILES = {
    'scripts/cleanup_project.py',  # 自己
    '.gitignore',
    'README.md',
    'requirements.txt',
    'package.json',
    'pyproject.toml',
}

# 数据库备份保留数量
MAX_DB_BACKUPS = 10

# 空目录检查模式
EMPTY_DIR_PATTERNS = [
    r'.*/(test|tests)/.*',
    r'.*/docs/.*',
    r'.*/archive.*',
    r'.*/temp.*',
    r'.*/logs?$',
]

# ============== 日志设置 ==============

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


# ============== 智能文件发现 ==============

class SmartFileFinder:
    """智能文件发现器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.found_files: Dict[str, Set[Path]] = {}
        self.all_found_files: Set[Path] = set()  # 跟踪所有已找到的文件

    def scan_project(self) -> Dict[str, List[Path]]:
        """扫描项目，按类别分类文件"""
        self.found_files = {category: set() for category in FILE_PATTERNS.keys()}
        self.all_found_files = set()

        for scan_dir in SCAN_DIRECTORIES:
            dir_path = self.project_root / scan_dir
            if dir_path.exists():
                self._scan_directory(dir_path)

        # 转换为列表返回
        return {category: list(files) for category, files in self.found_files.items()}

    def _scan_directory(self, directory: Path, max_depth: int = 5):
        """递归扫描目录"""
        if max_depth <= 0:
            return

        try:
            for item in directory.iterdir():
                # 跳过排除的目录
                if item.is_dir() and item.name in EXCLUDE_DIRECTORIES:
                    continue

                # 检查是否为保护文件
                relative_path = item.relative_to(self.project_root)
                if str(relative_path) in PROTECTED_FILES:
                    continue

                # 匹配文件模式
                self._match_file_patterns(item, relative_path)

                # 递归扫描子目录
                if item.is_dir():
                    self._scan_directory(item, max_depth - 1)

        except (PermissionError, OSError):
            # 跳过无法访问的目录
            pass

    def _match_file_patterns(self, file_path: Path, relative_path: Path):
        """匹配文件模式"""
        # 避免重复处理同一个文件
        if file_path in self.all_found_files:
            return

        path_str = str(relative_path).replace('\\', '/')

        for category, patterns in FILE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, path_str):
                    self.found_files[category].add(file_path)
                    self.all_found_files.add(file_path)
                    return  # 找到匹配后立即返回，避免重复分类

    def find_empty_directories(self) -> List[Path]:
        """查找空目录"""
        empty_dirs = set()  # 使用集合避免重复

        for scan_dir in SCAN_DIRECTORIES:
            dir_path = self.project_root / scan_dir
            if dir_path.exists():
                empty_dirs.update(self._find_empty_dirs_recursive(dir_path))

        return list(empty_dirs)

    def _find_empty_dirs_recursive(self, directory: Path, max_depth: int = 5) -> List[Path]:
        """递归查找空目录"""
        if max_depth <= 0:
            return []

        empty_dirs = []

        try:
            for item in directory.iterdir():
                if item.is_dir() and item.name not in EXCLUDE_DIRECTORIES:
                    # 检查是否匹配空目录模式
                    relative_path = item.relative_to(self.project_root)
                    path_str = str(relative_path).replace('\\', '/')

                    matches_pattern = any(re.search(pattern, path_str) for pattern in EMPTY_DIR_PATTERNS)

                    if matches_pattern and self._is_directory_empty(item):
                        empty_dirs.append(item)
                    else:
                        # 递归检查子目录
                        empty_dirs.extend(self._find_empty_dirs_recursive(item, max_depth - 1))

        except (PermissionError, OSError):
            pass

        return empty_dirs

    def _is_directory_empty(self, path: Path) -> bool:
        """检查目录是否为空"""
        try:
            return not any(path.iterdir())
        except (PermissionError, OSError):
            return False

# ============== 工具函数 ==============

def get_file_size(path: Path) -> str:
    """获取文件大小的可读字符串"""
    if path.is_file():
        size = path.stat().st_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    return "0 B"


def format_size(size_bytes: int) -> str:
    """格式化字节大小为可读字符串"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def is_directory_empty(path: Path) -> bool:
    """检查目录是否为空"""
    if not path.exists():
        return True
    return not any(path.iterdir())


def count_files(path: Path) -> int:
    """递归计算目录中的文件数"""
    if not path.exists() or path.is_file():
        return 0
    return sum(1 for _ in path.rglob('*') if _.is_file())


# ============== 清理操作 ==============

class CleanupOperation:
    """清理操作基类"""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.deleted_files: List[Path] = []
        self.deleted_dirs: List[Path] = []
        self.moved_files: Dict[Path, Path] = {}
        self.total_size = 0

    def log(self, message: str):
        """日志输出"""
        logger.info(message)

    def delete_file(self, path: Path) -> bool:
        """删除文件"""
        if not path.exists():
            return False

        size = path.stat().st_size if path.is_file() else 0
        self.total_size += size

        if self.dry_run:
            self.log(f"  [DRY RUN] 将删除: {path} ({get_file_size(path)})")
            self.deleted_files.append(path)
            return True

        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            self.log(f"  + 已删除: {path} ({get_file_size(path)})")
            self.deleted_files.append(path)
            return True
        except Exception as e:
            self.log(f"  x 删除失败: {path} - {e}")
            return False

    def move_file(self, src: Path, dst: Path) -> bool:
        """移动文件"""
        if not src.exists():
            return False

        # 确保目标目录存在
        dst.parent.mkdir(parents=True, exist_ok=True)

        if self.dry_run:
            self.log(f"  [DRY RUN] 将移动: {src} -> {dst}")
            self.moved_files[src] = dst
            return True

        try:
            shutil.move(str(src), str(dst))
            self.log(f"  ✓ 已移动: {src} -> {dst}")
            self.moved_files[src] = dst
            return True
        except Exception as e:
            self.log(f"  ✗ 移动失败: {src} -> {dst} - {e}")
            return False


class SmartCleanupScript:
    """智能清理脚本主类"""

    def __init__(self, dry_run: bool = True, backup: bool = False):
        self.dry_run = dry_run
        self.backup = backup
        self.op = CleanupOperation(dry_run)
        self.finder = SmartFileFinder(PROJECT_ROOT)

    def run(self):
        """执行所有清理操作"""
        self.op.log("=" * 60)
        self.op.log("智能项目清理脚本")
        self.op.log(f"模式: {'DRY RUN (预览)' if self.dry_run else '执行清理'}")
        self.op.log("=" * 60)
        self.op.log("")

        # 扫描项目文件
        self.op.log("[扫描] 智能扫描项目文件...")
        found_files = self.finder.scan_project()

        total_found = sum(len(files) for files in found_files.values())
        self.op.log(f"  发现 {total_found} 个可清理文件")
        self.op.log("")

        # 按类别清理文件
        self.clean_by_category(found_files)

        # 清理数据库备份
        self.clean_old_backups()

        # 检查空目录
        self.check_empty_dirs()

        # 更新 .gitignore
        self.update_gitignore()

        # 打印摘要
        self.print_summary()

    def clean_by_category(self, found_files: Dict[str, List[Path]]):
        """按类别清理文件"""
        category_names = {
            'test_outputs': '测试输出',
            'temp_databases': '临时数据库',
            'temp_scripts': '临时脚本',
            'cache_dirs': '缓存目录',
            'build_artifacts': '构建产物',
            'debug_artifacts': '调试产物',
            'log_files': '日志文件',
            'temp_reports': '临时报告',
            'old_sessions': '旧会话',
            'temp_uploads': '临时上传',
            'backup_files': '备份文件',
        }

        for category, files in found_files.items():
            if not files:
                continue

            name = category_names.get(category, category)
            self.op.log(f"[{name}] 清理 {len(files)} 个文件/目录...")

            for file_path in files:
                if file_path.is_dir():
                    file_count = count_files(file_path)
                    self.op.log(f"  发现目录 {file_path.name} ({file_count} 文件)")

                self.op.delete_file(file_path)

            self.op.log("")

    def clean_old_backups(self):
        """清理旧的数据库备份"""
        self.op.log("[备份清理] 清理旧数据库备份...")

        backup_dir = PROJECT_ROOT / "backend/backups"
        if not backup_dir.exists():
            self.op.log("  备份目录不存在，跳过")
            self.op.log("")
            return

        # 获取所有数据库备份文件，按修改时间排序
        backups = sorted(
            backup_dir.glob("*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if len(backups) <= MAX_DB_BACKUPS:
            self.op.log(f"  备份数量 ({len(backups)}) 未超过限制 ({MAX_DB_BACKUPS})")
            self.op.log("")
            return

        # 删除超出限制的旧备份
        old_backups = backups[MAX_DB_BACKUPS:]
        self.op.log(f"  发现 {len(old_backups)} 个旧备份需要清理:")

        for backup in old_backups:
            self.op.delete_file(backup)

        self.op.log("")

    def check_empty_dirs(self):
        """检查空目录"""
        self.op.log("[空目录] 智能检查空目录...")

        empty_dirs = self.finder.find_empty_directories()

        if not empty_dirs:
            self.op.log("  未发现空目录")
            self.op.log("")
            return

        self.op.log(f"  发现 {len(empty_dirs)} 个空目录:")
        for dir_path in empty_dirs:
            relative_path = dir_path.relative_to(PROJECT_ROOT)
            self.op.log(f"    {relative_path}")

        if not self.dry_run:
            self.op.log("")
            try:
                response = input("  是否删除这些空目录? (y/N): ")
                if response.lower() == 'y':
                    for dir_path in empty_dirs:
                        if dir_path.exists():
                            try:
                                dir_path.rmdir()
                                self.op.log(f"  + 已删除: {dir_path}")
                            except Exception as e:
                                self.op.log(f"  x 删除失败: {dir_path} - {e}")
            except (EOFError, OSError):
                # 非交互式环境，跳过空目录删除
                self.op.log("  (非交互式环境，跳过空目录删除)")

        self.op.log("")

    def update_gitignore(self):
        """智能更新 .gitignore 文件"""
        self.op.log("[.gitignore] 智能更新 .gitignore...")

        gitignore_path = PROJECT_ROOT / ".gitignore"
        if not gitignore_path.exists():
            self.op.log("  .gitignore 不存在，跳过")
            self.op.log("")
            return

        # 基于发现的文件类型生成 gitignore 规则
        gitignore_rules = self._generate_gitignore_rules()

        if not gitignore_rules:
            self.op.log("  .gitignore 已包含所需规则")
            self.op.log("")
            return

        current_content = gitignore_path.read_text(encoding='utf-8')
        missing_rules = [rule for rule in gitignore_rules if rule not in current_content]

        if not missing_rules:
            self.op.log("  .gitignore 已是最新的")
            self.op.log("")
            return

        self.op.log(f"  建议添加 {len(missing_rules)} 个规则到 .gitignore:")
        for rule in missing_rules:
            self.op.log(f"    {rule}")

        if not self.dry_run:
            try:
                response = input("  是否更新 .gitignore? (y/N): ")
                if response.lower() == 'y':
                    with open(gitignore_path, 'a', encoding='utf-8') as f:
                        f.write('\n\n# 智能清理脚本建议的规则\n')
                        f.write('\n'.join(missing_rules))
                        f.write('\n')
                    self.op.log("  + .gitignore 已更新")
            except (EOFError, OSError):
                # 非交互式环境，自动更新
                self.op.log("  (非交互式环境，自动更新 .gitignore)")
                with open(gitignore_path, 'a', encoding='utf-8') as f:
                    f.write('\n\n# 智能清理脚本建议的规则\n')
                    f.write('\n'.join(missing_rules))
                    f.write('\n')
                self.op.log("  + .gitignore 已更新")

        self.op.log("")

    def _generate_gitignore_rules(self) -> List[str]:
        """基于发现的文件生成 gitignore 规则"""
        rules = [
            "# 测试和覆盖率文件",
            ".coverage",
            "coverage.json",
            "coverage.xml",
            "junit-report.xml",
            "htmlcov/",
            ".pytest_cache/",
            "",
            "# 临时数据库文件",
            "*.db-shm",
            "*.db-wal",
            "*.db-journal",
            "test*.db",
            "",
            "# 缓存目录",
            "__pycache__/",
            ".mypy_cache/",
            ".ruff_cache/",
            "",
            "# 构建产物",
            "*-report.json",
            "*-report.xml",
            "",
            "# 日志文件",
            "*.log",
            "logs/",
            "backend/logs/",
            "frontend/*.log",
            "",
            "# 临时和备份文件",
            "*.bak",
            "*.backup",
            "*.old",
            "*~",
            "*.tmp",
            "*.temp",
            "",
            "# 临时上传目录",
            "temp_uploads/",
            "backend/temp_uploads/",
            "",
            "# 临时报告文件",
            "TEST_*.md",
            "FINAL_*.md",
            "RALPH_*.md",
            "*_ACHIEVEMENT.md",
            "*_ANALYSIS.md",
            "*_SUMMARY.md",
            "*_REPORT.md",
            "",
            "# 旧会话文件（保留最近）",
            "sessions/[0-9][0-9][0-9][0-9][0-9][0-9]-*",
        ]
        return rules

    def print_summary(self):
        """打印清理摘要"""
        self.op.log("=" * 60)
        self.op.log("清理摘要")
        self.op.log("=" * 60)

        file_count = len(self.op.deleted_files)
        dir_count = len(self.op.deleted_dirs)
        move_count = len(self.op.moved_files)

        self.op.log(f"删除的文件: {file_count}")
        self.op.log(f"删除的目录: {dir_count}")
        self.op.log(f"移动的文件: {move_count}")
        self.op.log(f"释放空间: {format_size(self.op.total_size) if self.op.total_size > 0 else '0 B'}")

        if self.dry_run:
            self.op.log("")
            self.op.log("! 这是 DRY RUN 模式，没有实际删除任何文件")
            self.op.log("  使用 --confirm 参数执行实际清理")
        else:
            self.op.log("")
            self.op.log("+ 清理完成！")


# ============== 主函数 ==============

def main():
    parser = argparse.ArgumentParser(
        description="项目清理脚本 - 安全删除临时文件和无效文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --dry-run     # 预览将删除的文件
  %(prog)s --confirm     # 确认后执行清理
  %(prog)s --backup      # 备份后清理
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='预览模式（默认），不实际删除文件'
    )

    parser.add_argument(
        '--confirm',
        action='store_true',
        help='执行模式，实际删除文件'
    )

    parser.add_argument(
        '--backup',
        action='store_true',
        help='在删除前创建备份'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='详细输出'
    )

    args = parser.parse_args()

    # 确定是否为干运行模式
    dry_run = not args.confirm

    # 创建备份
    if args.backup and not dry_run:
        backup_dir = PROJECT_ROOT / f".cleanup_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"创建备份: {backup_dir}")
        # 这里可以添加备份逻辑
        # shutil.copytree(PROJECT_ROOT, backup_dir, ignore=...)

    # 执行清理
    cleaner = SmartCleanupScript(dry_run=dry_run)
    cleaner.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
