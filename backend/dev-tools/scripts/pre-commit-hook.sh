#!/bin/bash
# Git pre-commit hook 替代脚本
# 在提交前运行代码质量检查

echo "=== Git Pre-commit 代码质量检查 ==="

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 运行本地代码质量检查
python local_code_quality_check.py

# 获取退出码
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 代码质量检查通过，可以提交"
    exit 0
else
    echo "❌ 代码质量检查失败，请修复问题后再提交"
    echo ""
    echo "建议运行以下命令修复问题："
    echo "  1. 修复格式问题: uv run ruff format src/"
    echo "  2. 检查其他问题: uv run ruff check src/"
    echo "  3. 重新运行检查: python local_code_quality_check.py"
    exit 1
fi
