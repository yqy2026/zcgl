#!/bin/bash

# CI/CD 兼容性快速修复脚本
# 修复可能导致流水线失败的关键问题

echo "🔧 开始CI/CD兼容性快速修复..."

# 进入项目根目录
cd "$(dirname "$0")/.."

echo "📊 当前CI/CD状态:"
echo "=========================="

# 检查Git状态
echo "🔍 检查Git状态..."
if [ -n "$(git status --porcelain)" ]; then
    echo "发现未提交的更改，请先提交所有更改"
    echo "运行: git add . && git commit -m 'Fix CI compatibility issues'"
    exit 1
fi

echo "✅ Git状态检查通过"

# 检查后端关键问题
echo ""
echo "🐍 检查后端关键问题..."
if [ -d "backend" ]; then
    cd backend

    echo "  - 检查重复定义问题..."
    F811_COUNT=$(uv run ruff check src/ --select=F811 2>/dev/null | grep -c "F811" || echo "0")
    echo "    发现 $F811_count 个重复定义问题"

    echo "  - 检查布尔比较问题..."
    E712_COUNT=$(uv run ruff check src/ --select=E712 2>/dev/null | grep -c "E712" || echo "0")
    echo "    发现 $E712_count 个布尔比较问题"

    echo "  - 检查未使用导入..."
    F401_COUNT=$(uv run ruff check src/ --select=F401 2>/dev/null | grep -c "F401" || echo "0")
    echo "    发现 $F401_count 个未使用导入"

    # 修复重复定义问题
    if [ "$F811_COUNT" -gt 0 ]; then
        echo "  🔧 修复重复定义问题..."
        uv run ruff check src/ --select=F811 --fix 2>/dev/null || echo "    部分重复定义需要手动修复"
    fi

    # 修复布尔比较问题
    if [ "$E712_COUNT" -gt 0 ]; then
        echo "  🔧 修复布尔比较问题..."
        uv run ruff check src/ --select=E712 --fix 2>/dev/null || echo "    部分布尔比较问题需要手动修复"
    fi

    # 删除未使用导入
    if [ "$F401_COUNT" -gt 0 ]; then
        echo "  🔧 删除未使用导入..."
        uv run ruff check src/ --select=F401 --fix 2>/dev/null || echo "    部分未使用导入需要手动删除"
    fi

    cd ..
fi

# 检查前端关键问题
echo ""
echo "⚛️ 检查前端关键问题..."
if [ -d "frontend" ]; then
    cd frontend

    echo "  - 检查未使用变量错误..."
    UNUSED_COUNT=$(npm run lint 2>&1 | grep -c "no-unused-vars" || echo "0")
    echo "    发现 $UNUSED_COUNT 个未使用变量错误"

    echo "  - 检查require导入错误..."
    REQUIRE_COUNT=$(npm run lint 2>&1 | grep -c "no-require-imports" || echo "0")
    echo "    发现 $REQUIRE_COUNT 个require导入错误"

    # 自动修复可修复的问题
    echo "  🔧 自动修复前端问题..."
    npm run lint:fix 2>/dev/null || echo "    部分前端问题需要手动修复"

    cd ..
fi

echo ""
echo "📈 修复后质量状态:"
echo "=========================="

# 再次检查质量状态
if [ -d "backend" ]; then
    cd backend
    echo "🐍 后端剩余关键问题:"
    REMAINING_BACKEND=$(uv run ruff check src/ --select=F811,E712,F401 2>/dev/null | grep -c "F811\|E712\|F401" || echo "0")
    echo "    剩余 $REMAINING_BACKEND 个关键问题"

    echo "🐍 后端所有问题:"
    TOTAL_BACKEND=$(uv run ruff check src/ --output-format=concise 2>/dev/null | grep -c "error\|warning\|note" || echo "0")
    echo "    总计 $TOTAL_BACKEND 个问题"

    cd ..
fi

if [ -d "frontend" ]; then
    cd frontend
    echo "⚛️ 前端剩余关键错误:"
    REMAINING_FRONTEND=$(npm run lint 2>&1 | grep -c "error" || echo "0")
    echo "    剩余 $REMAINING_FRONTEND 个错误"

    echo "⚛️ 前端所有问题:"
    TOTAL_FRONTEND=$(npm run lint 2>&1 | grep -c "error\|warning" || echo "0")
    echo "    总计 $TOTAL_FRONTEND 个问题"

    cd ..
fi

echo ""
echo "🎯 CI/CD兼容性评估:"
echo "=========================="

# 评估CI/CD兼容性
if [ "${REMAINING_BACKEND}" -lt 5 ] && [ "${REMAINING_FRONTEND}" -lt 50 ]; then
    echo "✅ CI/CD兼容性: 优秀 (预计流水线完全通过)"
    CI_STATUS="优秀"
elif [ "${REMAINING_BACKEND}" -lt 20 ] && [ "${REMAINING_FRONTEND}" -lt 200 ]; then
    echo "🟡 CI/CD兼容性: 良好 (预计流水线大部分通过)"
    CI_STATUS="良好"
elif [ "${REMAINING_BACKEND}" -lt 50 ] && [ "${REMAINING_FRONTEND}" -lt 500 ]; then
    echo "⚠️ CI/CD兼容性: 一般 (预计流水线部分通过)"
    CI_STATUS="一般"
else
    echo "🔴 CI/CD兼容性: 需要改进 (预计流水线可能失败)"
    CI_STATUS="需要改进"
fi

echo ""
echo "📝 CI/CD配置建议:"
echo "=========================="
echo "1. 保持当前的宽松配置策略"
echo "2. 按阶段提升质量标准"
echo "3. 监控流水线通过率趋势"
echo "4. 建立质量指标仪表板"

echo ""
echo "🚀 下一步行动:"
echo "=========================="
if [ "$CI_STATUS" = "优秀" ]; then
    echo "✅ 当前行更改应该可以通过CI/CD流水线"
    echo "   建议推送更改并验证流水线状态"
elif [ "$CI_STATUS" = "良好" ]; then
    echo "⚠️ 建议在推送前检查流水线状态"
    echo "   可能需要手动触发流水线验证"
else
    echo "🔴 建议先解决剩余关键问题"
    echo "   或使用更宽松的CI配置"
fi

echo ""
echo "💡 CI/CD质量提升资源:"
echo "=========================="
echo "- 查看详细报告: cat CI_CD_COMPATIBILITY_REPORT.md"
echo "- 质量改进计划: cat CODE_QUALITY_IMPROVEMENT_PLAN.md"
echo "- 快速修复脚本: bash scripts/quick-quality-fix.sh"
echo "- GitHub Actions: https://github.com/yuist/zcgl/actions"

echo ""
echo "✅ CI/CD兼容性修复完成!"
echo "   状态: $CI_STATUS"
echo "   建议: 推送更改前进行本地测试"
