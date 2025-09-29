@echo off
chcp 65001 >nul
title 土地物业资产管理系统

echo.
echo 🚀 启动土地物业资产管理系统
echo.

REM 检查环境
echo [INFO] 检查运行环境...

py --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 未找到！请安装 Python 3.8+
    echo [INFO] 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js 未找到！请安装 Node.js 18+
    echo [INFO] 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

echo [SUCCESS] 环境检查通过
echo.

REM 检查项目文件
if not exist "backend\run.py" (
    echo [ERROR] 后端文件缺失: backend\run.py
    pause
    exit /b 1
)

if not exist "frontend\package.json" (
    echo [ERROR] 前端文件缺失: frontend\package.json
    pause
    exit /b 1
)

echo [INFO] 项目文件检查通过
echo.

REM 安装后端依赖
echo [INFO] 准备后端环境...
cd backend
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt 不存在
    cd ..
    pause
    exit /b 1
)

echo [INFO] 安装后端依赖...
py -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] 后端依赖安装失败
    cd ..
    pause
    exit /b 1
)

REM 安装额外的必需依赖
echo [INFO] 安装额外必需依赖...
py -m pip install email-validator --quiet
if errorlevel 1 (
    echo [ERROR] email-validator 安装失败
    cd ..
    pause
    exit /b 1
)

echo [SUCCESS] 后端依赖安装完成
cd ..

REM 安装前端依赖
echo [INFO] 准备前端环境...
cd frontend
if not exist "node_modules" (
    echo [INFO] 安装前端依赖（首次运行可能需要几分钟）...
    npm install --silent
    if errorlevel 1 (
        echo [ERROR] 前端依赖安装失败
        cd ..
        pause
        exit /b 1
    )
    echo [SUCCESS] 前端依赖安装完成
) else (
    echo [INFO] 前端依赖已存在，跳过安装
)
cd ..

echo.
echo [INFO] 启动服务...

REM 启动后端
echo [INFO] 启动后端API服务...
cd backend
start "后端API服务 - 端口8001" cmd /k "echo 后端服务启动中... && py run.py"
cd ..

REM 等待后端启动
echo [INFO] 等待后端服务启动...
timeout /t 8 /nobreak >nul

REM 启动前端
echo [INFO] 启动前端开发服务器...
cd frontend
start "前端开发服务器 - 端口5173" cmd /k "echo 前端服务启动中... && npm run dev"
cd ..

echo.
echo [SUCCESS] 🎉 系统启动完成！
echo.
echo 📱 访问地址：
echo   ┌─ 前端应用: http://localhost:5173
echo   ├─ 后端API: http://localhost:8001  
echo   └─ API文档: http://localhost:8001/docs
echo.
echo 💡 使用提示：
echo   ├─ 系统已预置演示数据，可直接体验
echo   ├─ 前端支持热重载，修改代码自动刷新
echo   ├─ 两个服务窗口已打开，请保持运行
echo   └─ 运行 stop.bat 可停止所有服务
echo.

REM 等待服务完全启动
echo [INFO] 等待服务完全启动...
timeout /t 12 /nobreak >nul

REM 打开浏览器
echo [INFO] 正在打开浏览器...
start http://localhost:5173

echo.
echo ✅ 启动完成！按任意键关闭此窗口（服务将继续运行）
pause >nul