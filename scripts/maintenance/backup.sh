#!/bin/bash

# 项目备份脚本
# 备份数据库、配置文件和重要文档

set -e

# 获取当前日期时间
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="database/backups"
PROJECT_ROOT=$(pwd)

echo "💾 开始项目备份 - $TIMESTAMP"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 备份数据库
echo "📊 备份数据库..."
if [ -f "database/data/land_property.db" ]; then
    cp database/data/land_property.db "$BACKUP_DIR/land_property_$TIMESTAMP.db"
    echo "✅ 数据库备份完成: land_property_$TIMESTAMP.db"
else
    echo "⚠️ 数据库文件不存在，跳过数据库备份"
fi

# 备份配置文件
echo "⚙️ 备份配置文件..."
CONFIG_BACKUP_DIR="$BACKUP_DIR/config_$TIMESTAMP"
mkdir -p "$CONFIG_BACKUP_DIR"

if [ -d "config" ]; then
    cp -r config/* "$CONFIG_BACKUP_DIR/"
    echo "✅ 配置文件备份完成"
fi

# 备份环境文件
echo "📝 备份环境文件..."
find . -maxdepth 2 -name "*.env*" -not -path "./.venv/*" -not -path "./node_modules/*" | while read env_file; do
    rel_path=$(realpath --relative-to="$PROJECT_ROOT" "$env_file")
    mkdir -p "$CONFIG_BACKUP_DIR/$(dirname "$rel_path")"
    cp "$env_file" "$CONFIG_BACKUP_DIR/$rel_path"
    echo "  📄 $rel_path"
done

# 备份重要文档
echo "📚 备份重要文档..."
DOC_BACKUP_DIR="$BACKUP_DIR/docs_$TIMESTAMP"
mkdir -p "$DOC_BACKUP_DIR"

important_docs=(
    "README.md"
    "CLAUDE.md"
    "docs/dev"
    "docs/api"
    "docs/deployment"
)

for doc in "${important_docs[@]}"; do
    if [ -e "$doc" ]; then
        cp -r "$doc" "$DOC_BACKUP_DIR/"
        echo "  📄 $doc"
    fi
done

# 创建备份信息文件
echo "📋 创建备份信息..."
cat > "$BACKUP_DIR/backup_info_$TIMESTAMP.txt" << EOF
备份时间: $(date)
备份类型: 完整项目备份
项目版本: $(git describe --tags --always 2>/dev/null || echo "unknown")
Git分支: $(git branch --show-current 2>/dev/null || echo "unknown")
Git提交: $(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

备份内容:
- 数据库文件
- 配置文件
- 环境文件
- 重要文档

备份命令: ./scripts/maintenance/backup.sh
恢复命令: ./scripts/maintenance/restore.sh $TIMESTAMP
EOF

# 压缩备份
echo "🗜️ 压缩备份文件..."
cd "$BACKUP_DIR"
tar -czf "project_backup_$TIMESTAMP.tar.gz" \
    "land_property_$TIMESTAMP.db" \
    "config_$TIMESTAMP" \
    "docs_$TIMESTAMP" \
    "backup_info_$TIMESTAMP.txt" 2>/dev/null || true

# 清理未压缩的备份文件（可选）
read -p "是否删除未压缩的备份文件？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "land_property_$TIMESTAMP.db" \
           "config_$TIMESTAMP" \
           "docs_$TIMESTAMP" \
           "backup_info_$TIMESTAMP.txt" 2>/dev/null || true
    echo "✅ 未压缩文件已清理"
fi

cd "$PROJECT_ROOT"

# 清理旧备份（保留最新的10个）
echo "🧹 清理旧备份..."
cd "$BACKUP_DIR"
ls -t project_backup_*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm -f
cd "$PROJECT_ROOT"

echo ""
echo "🎉 备份完成！"
echo "📁 备份位置: $BACKUP_DIR/project_backup_$TIMESTAMP.tar.gz"
echo "📊 备份大小: $(du -h "$BACKUP_DIR/project_backup_$TIMESTAMP.tar.gz" 2>/dev/null | cut -f1 || echo "unknown")"
echo ""
echo "💡 提示："
echo "   - 恢复备份: ./scripts/maintenance/restore.sh $TIMESTAMP"
echo "   - 查看备份信息: $BACKUP_DIR/backup_info_$TIMESTAMP.txt"
echo "   - 保留最新10个备份文件"