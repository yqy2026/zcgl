#!/bin/bash
# 完整项目检查脚本 (并行执行)
# 使用方法: ./scripts/check-all-parallel.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 开始时间
START_TIME=$(date +%s)

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              完整项目检查报告                              ║${NC}"
echo -e "${BLUE}║              $(date '+%Y-%m-%d %H:%M:%S')                     ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# 创建日志目录
mkdir -p logs

# ============================================
# 阶段 1: 代码质量检查 (并行执行)
# ============================================
echo -e "${BLUE}📋 阶段 1: 代码质量检查${NC}"

# 后端 Ruff 检查
echo -n "  ⏳ 后端 Ruff 检查... "
if cd backend && ruff check . > ../logs/ruff.log 2>&1; then
    echo -e "${GREEN}✓ 通过${NC}"
    RUFF_STATUS="✓"
else
    echo -e "${RED}✗ 失败${NC}"
    RUFF_STATUS="✗"
fi
cd ..

# 前端 TypeScript 检查
echo -n "  ⏳ 前端 TypeScript 检查... "
if cd frontend && pnpm type-check > ../logs/ts.log 2>&1; then
    echo -e "${GREEN}✓ 通过${NC}"
    TS_STATUS="✓"
else
    echo -e "${RED}✗ 失败${NC}"
    TS_STATUS="✗"
fi
cd ..

# 前端 ESLint 检查
echo -n "  ⏳ 前端 ESLint 检查... "
if cd frontend && pnpm lint > ../logs/eslint.log 2>&1; then
    echo -e "${GREEN}✓ 通过${NC}"
    ESLINT_STATUS="✓"
else
    echo -e "${RED}✗ 失败${NC}"
    ESLINT_STATUS="✗"
fi
cd ..

echo ""

# ============================================
# 阶段 2: 测试套件 (顺序执行)
# ============================================
echo -e "${BLUE}🧪 阶段 2: 测试套件${NC}"

# 后端单元测试
echo -n "  ⏳ 后端单元测试... "
if cd backend && pytest -m unit -v --tb=short > ../logs/backend-unit.log 2>&1; then
    echo -e "${GREEN}✓ 通过${NC}"
    BACKEND_TEST_STATUS="✓"
    # 提取测试结果
    BACKEND_TEST_SUMMARY=$(tail -20 ../logs/backend-unit.log)
else
    echo -e "${YELLOW}⚠ 有失败${NC}"
    BACKEND_TEST_STATUS="⚠"
    BACKEND_TEST_SUMMARY=$(tail -30 ../logs/backend-unit.log)
fi
cd ..

# 前端测试
echo -n "  ⏳ 前端单元测试... "
if cd frontend && pnpm test:ci > ../logs/frontend-test.log 2>&1; then
    echo -e "${GREEN}✓ 通过${NC}"
    FRONTEND_TEST_STATUS="✓"
    FRONTEND_TEST_SUMMARY=$(tail -20 ../logs/frontend-test.log)
else
    echo -e "${YELLOW}⚠ 有失败${NC}"
    FRONTEND_TEST_STATUS="⚠"
    FRONTEND_TEST_SUMMARY=$(tail -30 ../logs/frontend-test.log)
fi
cd ..

echo ""

# ============================================
# 阶段 3: 运行时诊断 (条件执行)
# ============================================
echo -e "${BLUE}🌐 阶段 3: 运行时诊断${NC}"

# 检查前端服务器是否运行
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo -n "  ⏳ 前端 Puppeteer 诊断... "
    if cd frontend && pnpm diagnose > ../logs/diagnose.log 2>&1; then
        echo -e "${GREEN}✓ 通过${NC}"
        DIAGNOSE_STATUS="✓"
    else
        echo -e "${YELLOW}⚠ 有问题${NC}"
        DIAGNOSE_STATUS="⚠"
    fi
    cd ..
else
    echo -e "${YELLOW}  ⚠ 前端服务器未运行，跳过诊断${NC}"
    DIAGNOSE_STATUS="⊘"
fi

# 检查后端服务器
if curl -s http://localhost:8002/api/v1/health > /dev/null 2>&1; then
    echo -n "  ⏳ 后端 API 健康检查... "
    if curl -s http://localhost:8002/api/v1/health | grep -q "ok"; then
        echo -e "${GREEN}✓ 通过${NC}"
        API_STATUS="✓"
    else
        echo -e "${RED}✗ 失败${NC}"
        API_STATUS="✗"
    fi
else
    echo -e "${YELLOW}  ⚠ 后端服务器未运行，跳过检查${NC}"
    API_STATUS="⊘"
fi

echo ""

# ============================================
# 阶段 4: 构建验证
# ============================================
echo -e "${BLUE}🏗️  阶段 4: 构建验证${NC}"

# 前端构建
echo -n "  ⏳ 前端生产构建... "
if cd frontend && pnpm build > ../logs/build.log 2>&1; then
    BUILD_SIZE=$(du -sh dist/ | cut -f1)
    echo -e "${GREEN}✓ 通过${NC} (dist/: ${BUILD_SIZE})"
    BUILD_STATUS="✓"
else
    echo -e "${RED}✗ 失败${NC}"
    BUILD_STATUS="✗"
fi
cd ..

# 后端导入测试
echo -n "  ⏳ 后端导入测试... "
if cd backend && python -c "from src.main import app; print('✓ 导入成功')" > ../logs/import.log 2>&1; then
    echo -e "${GREEN}✓ 通过${NC}"
    IMPORT_STATUS="✓"
else
    echo -e "${RED}✗ 失败${NC}"
    IMPORT_STATUS="✗"
fi
cd ..

echo ""

# ============================================
# 生成总结报告
# ============================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}【总结】${NC}"
echo ""
echo "【代码质量】"
echo "  前端 TypeScript:  ${TS_STATUS}"
echo "  前端 ESLint:      ${ESLINT_STATUS}"
echo "  后端 Ruff:        ${RUFF_STATUS}"
echo ""
echo "【测试套件】"
echo "  后端单元测试:     ${BACKEND_TEST_STATUS}"
echo "  前端单元测试:     ${FRONTEND_TEST_STATUS}"
echo ""
echo "【运行时诊断】"
echo "  前端诊断:         ${DIAGNOSE_STATUS}"
echo "  后端 API:         ${API_STATUS}"
echo ""
echo "【构建验证】"
echo "  前端构建:         ${BUILD_STATUS}"
echo "  后端导入:         ${IMPORT_STATUS}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "⏱️  总耗时: ${MINUTES} 分 ${SECONDS} 秒"
echo ""
echo "📁 详细日志: logs/"
echo "   - ruff.log (后端代码检查)"
echo "   - ts.log (前端类型检查)"
echo "   - backend-unit.log (后端单元测试)"
echo "   - frontend-test.log (前端测试)"
echo "   - diagnose.log (前端诊断)"
echo "   - build.log (前端构建)"
echo ""

# 判断整体状态
if [[ "$BACKEND_TEST_STATUS" == "✗" ]] || [[ "$FRONTEND_TEST_STATUS" == "✗" ]] || [[ "$BUILD_STATUS" == "✗" ]]; then
    echo -e "${RED}❌ 存在严重问题，请查看日志${NC}"
    exit 1
elif [[ "$BACKEND_TEST_STATUS" == "⚠" ]] || [[ "$FRONTEND_TEST_STATUS" == "⚠" ]]; then
    echo -e "${YELLOW}⚠️  部分测试失败，请查看日志${NC}"
    exit 0
else
    echo -e "${GREEN}✅ 所有检查通过！${NC}"
    exit 0
fi
