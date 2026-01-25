---
name: clean
description: "Project cleanup command - Updates and runs cleanup_project.py to remove invalid, expired, and temporary files from the project."
---

# Project Clean Command

智能项目清理命令。执行项目更新并运行清理脚本，自动删除临时文件、缓存文件和无效文件。

## When to Use

使用此命令当你需要：
- 清理项目中的临时文件和缓存
- 删除测试输出和构建产物
- 清理过期的数据库备份
- 更新并同步项目状态

## What This Command Does

1. **更新项目** - 执行 `git pull` 同步最新代码（如果可用）
2. **运行清理脚本** - 执行 `scripts/cleanup_project.py --confirm`
3. **智能清理** - 自动识别并清理：
   - 测试输出文件（.coverage, coverage.json, htmlcov/）
   - 临时数据库文件（test*.db, *.db-shm, *.db-wal）
   - 临时分析脚本（check_*, find_*, analyze_*.py）
   - 缓存目录（__pycache__, .pytest_cache, .mypy_cache）
   - 构建产物（dist/, coverage/, *-report.json）
   - 调试产物（.playwright-mcp/）

## How It Works

1. 检查 git 状态，如果是 git 仓库则执行 `git pull`
2. 运行清理脚本，使用智能模式匹配发现需要清理的文件
3. 显示清理摘要，包括删除的文件数量和释放的空间

## Safety Features

- ✅ 保护关键文件（cleanup_project.py 自身、.gitignore、README.md 等）
- ✅ 排除重要目录（.git, node_modules, .venv 等）
- ✅ 保留最新的数据库备份（最多保留 10 个）
- ✅ 显示详细的清理日志

## Examples

```bash
# 用户在 Claude Code 中输入：
/clean

# Claude Code 将执行：
# 1. git pull (如果可用)
# 2. python scripts/cleanup_project.py --confirm
```

## Related Files

- 清理脚本：`scripts/cleanup_project.py`
- Git 配置：`.gitignore`
- 备份目录：`backend/backups/`
