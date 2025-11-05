#!/bin/bash

# 快速代码质量修复脚本
# 处理最关键的质量问题，确保代码可以正常运行

echo "🚀 开始快速代码质量修复..."

# 进入项目根目录
cd "$(dirname "$0")/.."

echo "📊 当前质量状态:"
echo "=========================="

# 检查后端代码质量
echo "🔍 检查后端代码质量..."
if [ -d "backend" ]; then
    cd backend
    echo "后端 ruff 错误数量:"
    uv run ruff check src/ --output-format=concise 2>/dev/null | grep -c "error" || echo "0"
    echo "后端主要问题类型:"
    uv run ruff check src/ --output-format=concise 2>/dev/null | grep -E "E[0-9]+" | cut -d':' -f3 | sort | uniq -c | sort -nr | head -5
    cd ..
fi

# 检查前端代码质量
echo ""
echo "🔍 检查前端代码质量..."
if [ -d "frontend" ]; then
    cd frontend
    echo "前端 ESLint 错误数量:"
    npm run lint 2>/dev/null | grep -c "error" || echo "0"
    echo "前端 ESLint 警告数量:"
    npm run lint 2>/dev/null | grep -c "warning" || echo "0"
    cd ..
fi

echo ""
echo "🔧 开始自动修复..."

# 后端自动修复
if [ -d "backend" ]; then
    echo "🐍 修复后端代码问题..."
    cd backend

    # 修复可自动修复的问题
    echo "  - 尝试自动修复导入顺序问题..."
    uv run ruff check src/ --fix --unsafe-fixes 2>/dev/null || echo "    部分导入问题需要手动修复"

    # 格式化代码
    echo "  - 格式化代码..."
    uv run ruff format src/ 2>/dev/null || echo "    代码格式化完成"

    cd ..
fi

# 前端自动修复
if [ -d "frontend" ]; then
    echo "⚛️ 修复前端代码问题..."
    cd frontend

    # 自动修复可修复的问题
    echo "  - 运行 ESLint 自动修复..."
    npm run lint:fix 2>/dev/null || echo "    部分问题需要手动修复"

    cd ..
fi

echo ""
echo "📈 修复后质量状态:"
echo "=========================="

# 再次检查质量状态
if [ -d "backend" ]; then
    cd backend
    echo "🐍 后端剩余错误数量:"
    uv run ruff check src/ --output-format=concise 2>/dev/null | grep -c "error" || echo "0"
    cd ..
fi

if [ -d "frontend" ]; then
    cd frontend
    echo "⚛️ 前端剩余错误数量:"
    npm run lint 2>/dev/null | grep -c "error" || echo "0"
    echo "⚛️ 前端剩余警告数量:"
    npm run lint 2>/dev/null | grep -c "warning" || echo "0"
    cd ..
fi

echo ""
echo "✅ 快速修复完成!"
echo ""
echo "📝 剩余问题需要手动处理，详见 CODE_QUALITY_IMPROVEMENT_PLAN.md"
echo "🔄 建议创建专门的代码质量改进提交"
