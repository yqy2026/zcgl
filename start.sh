#!/bin/bash

echo "🚀 启动土地物业资产管理系统"
echo.

# 检查环境
echo "[INFO] 检查运行环境..."

if ! command -v python &> /dev/null; then
    echo "[ERROR] Python 未找到！请安装 Python 3.8+"
    echo "[INFO] 下载地址: https://www.python.org/downloads/"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js 未找到！请安装 Node.js 18+"
    echo "[INFO] 下载地址: https://nodejs.org/"
    exit 1
fi

echo "[SUCCESS] 环境检查通过"
echo.

# 检查项目文件
if [ ! -f "backend/run.py" ]; then
    echo "[ERROR] 后端文件缺失: backend/run.py"
    exit 1
fi

if [ ! -f "frontend/package.json" ]; then
    echo "[ERROR] 前端文件缺失: frontend/package.json"
    exit 1
fi

echo "[INFO] 项目文件检查通过"
echo.

# 安装后端依赖
echo "[INFO] 准备后端环境..."
cd backend

if [ ! -f "requirements.txt" ]; then
    echo "[ERROR] requirements.txt 不存在"
    cd ..
    exit 1
fi

echo "[INFO] 安装后端依赖..."
python -m pip install -r requirements.txt -q
if [ $? -ne 0 ]; then
    echo "[ERROR] 后端依赖安装失败"
    cd ..
    exit 1
fi

# 安装额外的必需依赖
echo "[INFO] 安装额外必需依赖..."
python -m pip install email-validator -q
if [ $? -ne 0 ]; then
    echo "[ERROR] email-validator 安装失败"
    cd ..
    exit 1
fi

echo "[SUCCESS] 后端依赖安装完成"
cd ..

# 安装前端依赖
echo "[INFO] 准备前端环境..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "[INFO] 安装前端依赖（首次运行可能需要几分钟）..."
    npm install --silent
    if [ $? -ne 0 ]; then
        echo "[ERROR] 前端依赖安装失败"
        cd ..
        exit 1
    fi
    echo "[SUCCESS] 前端依赖安装完成"
else
    echo "[INFO] 前端依赖已存在，跳过安装"
fi
cd ..

echo.
echo "[INFO] 启动服务..."

# 启动后端
echo "[INFO] 启动后端API服务..."
cd backend
gnome-terminal -- bash -c "echo '后端服务启动中...' && python run.py; exec bash" 2>/dev/null || \
xterm -e "echo '后端服务启动中...' && python run.py" 2>/dev/null || \
start "后端API服务 - 端口8001" cmd /k "echo 后端服务启动中... && python run.py" 2>/dev/null || \
echo "[WARNING] 无法打开新终端窗口，请手动启动后端：python run.py"

cd ..

# 等待后端启动
echo "[INFO] 等待后端服务启动..."
sleep 8

# 启动前端
echo "[INFO] 启动前端开发服务器..."
cd frontend
gnome-terminal -- bash -c "echo '前端服务启动中...' && npm run dev; exec bash" 2>/dev/null || \
xterm -e "echo '前端服务启动中...' && npm run dev" 2>/dev/null || \
start "前端开发服务器 - 端口5173" cmd /k "echo 前端服务启动中... && npm run dev" 2>/dev/null || \
echo "[WARNING] 无法打开新终端窗口，请手动启动前端：npm run dev"

cd ..

echo.
echo "[SUCCESS] 🎉 系统启动完成！"
echo.
echo "📱 访问地址："
echo "   ┌─ 前端应用: http://localhost:5173"
echo "   ├─ 后端API: http://localhost:8001"
echo "   └─ API文档: http://localhost:8001/docs"
echo.
echo "💡 使用提示："
echo "   ├─ 系统已预置演示数据，可直接体验"
echo "   ├─ 前端支持热重载，修改代码自动刷新"
echo "   ├─ 两个服务窗口已打开，请保持运行"
echo "   └─ 运行 stop.sh 可停止所有服务"
echo.

# 等待服务完全启动
echo "[INFO] 等待服务完全启动..."
sleep 12

# 尝试打开浏览器
if command -v xdg-open &> /dev/null; then
    echo "[INFO] 正在打开浏览器..."
    xdg-open http://localhost:5173
elif command -v open &> /dev/null; then
    echo "[INFO] 正在打开浏览器..."
    open http://localhost:5173
elif command -v start &> /dev/null; then
    echo "[INFO] 正在打开浏览器..."
    start http://localhost:5173
fi

echo.
echo "✅ 启动完成！服务已在后台运行"