#!/bin/bash

# 设置日志目录和文件
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/startup_$(date +%Y%m%d_%H%M%S).log"

echo "🚀 启动土地物业资产管理系统 (UV版本)"
echo "========================================"
echo
echo "[INFO] 日志文件: $LOG_FILE"

# 记录启动信息
echo "[$(date +'%Y-%m-%d %H:%M:%S')] 启动土地物业资产管理系统 (UV版本)" | tee -a "$LOG_FILE"
echo "[$(date +'%Y-%m-%d %H:%M:%S')] 命令行参数: $*" | tee -a "$LOG_FILE"

# 检查命令行参数
UPDATE_DEPS=0
if [[ "$1" == "--update" || "$1" == "-u" ]]; then
    UPDATE_DEPS=1
    echo "[INFO] 启用依赖更新模式" | tee -a "$LOG_FILE"
fi

# 函数：记录日志
log_info() {
    echo "[INFO] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "❌ 错误: $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo "✅ $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo "⚠️ $1" | tee -a "$LOG_FILE"
}

# 检查uv是否安装
if ! command -v uv &> /dev/null; then
    log_error "未找到uv包管理器"
    echo "[HINT] 安装命令: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "[HINT] 或使用 pip: pip install uv"
    exit 1
fi

log_success "检测到uv包管理器"
echo

# 检查运行环境
log_info "检查运行环境..."
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    log_error "未找到Python，请先安装Python 3.12+"
    echo "[HINT] 下载地址: https://www.python.org/downloads/"
    echo "[HINT] Ubuntu/Debian: sudo apt install python3.12"
    echo "[HINT] macOS: brew install python@3.12"
    exit 1
fi

# 检查Python版本
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
MAJOR_VERSION=$(echo $PYTHON_VERSION | cut -d'.' -f1)
MINOR_VERSION=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [[ $MAJOR_VERSION -lt 3 ]] || [[ $MAJOR_VERSION -eq 3 && $MINOR_VERSION -lt 12 ]]; then
    log_error "Python版本过低，需要Python 3.12+"
    echo "[CURRENT] 当前版本: $PYTHON_VERSION"
    echo "[HINT] 请升级Python版本"
    exit 1
fi

log_success "Python版本检查通过: $PYTHON_VERSION"

# 检查项目文件
if [ ! -f "backend/pyproject.toml" ]; then
    echo "❌ 错误: 未找到backend/pyproject.toml文件"
    echo "请确保在项目根目录运行此脚本"
    exit 1
fi

if [ ! -f "frontend/package.json" ]; then
    echo "❌ 错误: 未找到frontend/package.json文件"
    echo "请确保在项目根目录运行此脚本"
    exit 1
fi

echo "[SUCCESS] 环境检查通过"
echo

# 准备后端环境
echo "[INFO] 准备后端环境..."
cd backend

# 检查是否存在虚拟环境
if [ ! -d ".venv" ]; then
    echo "[INFO] 创建虚拟环境..."
    uv sync
else
    echo "[INFO] 虚拟环境已存在，同步依赖..."
    uv sync
fi

echo "[SUCCESS] 后端环境准备完成"
cd ..

echo
echo "[INFO] 准备前端环境..."
cd frontend

# 检查node_modules是否存在
if [ ! -d "node_modules" ]; then
    echo "[INFO] 安装前端依赖..."
    npm install
else
    echo "[INFO] 前端依赖已存在，跳过安装"
fi

echo "[SUCCESS] 前端环境准备完成"
cd ..

echo
echo "🚀 启动服务..."
echo "[INFO] 启动后端API服务..."
cd backend
start_in_terminal "uv run python run_dev.py" "Backend API Server"
cd ..

echo "[INFO] 等待后端服务启动..."
sleep 5

echo "[INFO] 启动前端开发服务器..."
cd frontend
start_in_terminal "npm run dev" "Frontend Dev Server"
cd ..

echo
echo "[SUCCESS] 🎉 系统启动完成！"
echo "📱 访问地址："
echo "   ┌─ 前端应用: http://localhost:5173"
echo "   ├─ 后端API: http://localhost:8002"
echo "   └─ API文档: http://localhost:8002/docs"
echo
echo "💡 使用提示："
echo "   ├─ 系统已预置演示数据，可直接体验"
echo "   ├─ 前端支持热重载，修改代码自动刷新"
echo "   ├─ 两个服务窗口已打开，请保持运行"
echo "   └─ 运行 stop_uv.sh 可停止所有服务"
echo
echo "[INFO] 等待服务完全启动..."
sleep 10

# 尝试打开浏览器
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5173
elif command -v open &> /dev/null; then
    open http://localhost:5173
elif command -v start &> /dev/null; then
    start http://localhost:5173
else
    echo "[INFO] 请手动打开浏览器访问: http://localhost:5173"
fi

echo
echo "✅ 启动完成！服务已在后台运行"
echo

# 函数定义
start_in_terminal() {
    local command="$1"
    local title="$2"

    # 保存当前目录
    local current_dir="$PWD"

    if command -v gnome-terminal &> /dev/null; then
        echo "[INFO] 使用 gnome-terminal 启动: $title"
        gnome-terminal --title="$title" -- bash -c "$command; exec bash"
    elif command -v konsole &> /dev/null; then
        echo "[INFO] 使用 konsole 启动: $title"
        konsole -e "$command"
    elif command -v xterm &> /dev/null; then
        echo "[INFO] 使用 xterm 启动: $title"
        xterm -e "$command"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "[INFO] 使用 macOS Terminal 启动: $title"
        osascript -e "tell application \"Terminal\" to do script \"cd '$current_dir' && $command\""
    else
        echo "[WARNING] 无法自动打开终端，请手动运行: $command"
        echo "[HINT] 在后台运行: nohup $command > /dev/null 2>&1 &"
        nohup $command > /dev/null 2>&1 &
    fi
}

check_service_health() {
    local url="$1"
    local service_name="$2"
    local max_attempts=30
    local attempt=1

    echo "[INFO] 检查 $service_name 健康状态..."

    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" > /dev/null; then
            echo "[SUCCESS] $service_name 响应正常"
            return 0
        fi
        echo "[INFO] 等待 $service_name 响应... ($attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done

    echo "[ERROR] $service_name 启动超时"
    return 1
}