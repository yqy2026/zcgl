#!/bin/bash
# ==========================================
# 土地物业资产管理系统 - 开发环境启动脚本
# ==========================================

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║    土地物业资产管理系统 - 开发环境启动                     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 设置开发环境变量
export ENVIRONMENT=development
export DEBUG=true
export TESTING_MODE=false

# 设置安全的开发密钥（至少32字符）
if [ -z "$SECRET_KEY" ]; then
    export SECRET_KEY="dev-local-secret-key-at-least-32-chars-long-for-security"
    echo "[INFO] 使用默认开发密钥 SECRET_KEY"
fi

# 数据库配置
export DATABASE_URL="sqlite:///./data/land_property.db"

# 端口配置
export API_PORT=8002
export FRONTEND_PORT=5173

echo "[配置信息]"
echo "  环境: $ENVIRONMENT"
echo "  调试模式: $DEBUG"
echo "  后端端口: $API_PORT"
echo "  前端端口: $FRONTEND_PORT"
echo ""

# 函数：启动后端
start_backend() {
    echo ""
    echo "[启动后端服务...]"
    cd "$SCRIPT_DIR/backend"
    mkdir -p data
    python -m uvicorn src.main:app --reload --host 127.0.0.1 --port $API_PORT
}

# 函数：启动前端
start_frontend() {
    echo ""
    echo "[启动前端服务...]"
    cd "$SCRIPT_DIR/frontend"
    npm run dev
}

# 函数：同时启动
start_all() {
    echo ""
    echo "[启动所有服务...]"

    # 后台启动后端
    cd "$SCRIPT_DIR/backend"
    mkdir -p data
    python -m uvicorn src.main:app --reload --host 127.0.0.1 --port $API_PORT &
    BACKEND_PID=$!
    echo "[INFO] 后端服务已启动 (PID: $BACKEND_PID)"

    # 等待后端启动
    sleep 3

    # 前台启动前端
    cd "$SCRIPT_DIR/frontend"
    npm run dev

    # 前端退出后杀死后端
    kill $BACKEND_PID 2>/dev/null
}

# 显示帮助
show_help() {
    echo "使用方法:"
    echo "  ./start-dev.sh backend   - 仅启动后端"
    echo "  ./start-dev.sh frontend  - 仅启动前端"
    echo "  ./start-dev.sh all       - 同时启动前后端"
    echo ""
    echo "建议: 在两个终端窗口分别运行 backend 和 frontend"
}

# 主逻辑
case "$1" in
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    all)
        start_all
        ;;
    *)
        show_help
        ;;
esac
