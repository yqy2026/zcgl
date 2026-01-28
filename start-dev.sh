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

# Load backend/.env if present
if [ -f "$SCRIPT_DIR/backend/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  . "$SCRIPT_DIR/backend/.env"
  set +a
fi


# 设置开发环境变量
export ENVIRONMENT="${ENVIRONMENT:-development}"
export DEBUG="${DEBUG:-true}"
export TESTING_MODE="${TESTING_MODE:-false}"

# SECRET_KEY 提示
if [ -z "$SECRET_KEY" ]; then
    echo "[WARN] SECRET_KEY 未设置，请在 backend/.env 中配置"
fi

# 数据库配置
# Database config (SQLite deprecated)
if [ -z "$DATABASE_URL" ]; then
  echo "[ERROR] DATABASE_URL is not set. SQLite is deprecated."
  echo "Set DATABASE_URL in backend/.env, e.g.:"
  echo "  DATABASE_URL=postgresql://user:password@localhost:5432/zcgl"
  exit 1
fi


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
    python run_dev.py
}

# 函数：启动前端
start_frontend() {
    echo ""
    echo "[启动前端服务...]"
    cd "$SCRIPT_DIR/frontend"
    pnpm run dev
}

# 函数：同时启动
start_all() {
    echo ""
    echo "[启动所有服务...]"

    # 后台启动后端
    cd "$SCRIPT_DIR/backend"
    python run_dev.py &
    BACKEND_PID=$!
    echo "[INFO] 后端服务已启动 (PID: $BACKEND_PID)"

    # 等待后端启动
    sleep 3

    # 前台启动前端
    cd "$SCRIPT_DIR/frontend"
    pnpm run dev

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
