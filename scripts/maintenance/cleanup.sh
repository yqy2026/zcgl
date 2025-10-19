#!/bin/bash

# 项目清理脚本
# 清理临时文件、日志文件、缓存文件

set -e

echo "🧹 开始清理项目..."

# 清理后端临时文件
echo "📁 清理后端临时文件..."
if [ -d "backend/workspace/temp" ]; then
    find backend/workspace/temp -type f -name "*.py" -mtime +7 -delete 2>/dev/null || true
    echo "✅ 清理7天前的临时Python文件"
fi

# 清理日志文件
echo "📋 清理日志文件..."
if [ -d "logs" ]; then
    find logs -name "*.log" -mtime +30 -delete 2>/dev/null || true
    find logs -name "*.log.*" -mtime +30 -delete 2>/dev/null || true
    echo "✅ 清理30天前的日志文件"
fi

# 清理前端构建文件
echo "🏗️ 清理前端构建文件..."
if [ -d "frontend/dist" ]; then
    rm -rf frontend/dist/*
    echo "✅ 清理前端dist目录"
fi

if [ -d "frontend/node_modules/.cache" ]; then
    rm -rf frontend/node_modules/.cache
    echo "✅ 清理前端缓存"
fi

# 清理Python缓存
echo "🐍 清理Python缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
echo "✅ 清理Python缓存文件"

# 清理测试覆盖率文件
echo "🧪 清理测试文件..."
find . -name ".coverage" -delete 2>/dev/null || true
find . -name "htmlcov" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
echo "✅ 清理测试覆盖率文件"

# 清理临时下载文件
echo "⬇️ 清理下载文件..."
if [ -d "downloads" ]; then
    find downloads -type f -mtime +7 -delete 2>/dev/null || true
    echo "✅ 清理7天前的下载文件"
fi

# 清理IDE文件
echo "💻 清理IDE文件..."
find . -name ".vscode" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.swp" -delete 2>/dev/null || true
find . -name "*.swo" -delete 2>/dev/null || true
find . -name ".DS_Store" -delete 2>/dev/null || true
echo "✅ 清理IDE临时文件"

# 清理数据库备份文件（保留最新的5个）
echo "💾 清理旧备份文件..."
if [ -d "database/backups" ]; then
    cd database/backups
    ls -t *.db *.sql 2>/dev/null | tail -n +6 | xargs -r rm -f
    cd ../..
    echo "✅ 保留最新的5个备份文件"
fi

echo "🎉 项目清理完成！"
echo ""
echo "📊 清理统计："
echo "   - 临时文件: 已清理"
echo "   - 日志文件: 已清理"
echo "   - 缓存文件: 已清理"
echo "   - 备份文件: 已保留最新版本"