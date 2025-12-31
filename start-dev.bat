@echo off
REM ==========================================
REM 土地物业资产管理系统 - 开发环境启动脚本
REM ==========================================

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║    土地物业资产管理系统 - 开发环境启动                     ║
echo ╚══════════════════════════════════════════════════════╝
echo.

REM 设置开发环境变量
set ENVIRONMENT=development
set DEBUG=true
set TESTING_MODE=false

REM 设置安全的开发密钥（至少32字符）
if not defined SECRET_KEY (
    set SECRET_KEY=dev-local-secret-key-at-least-32-chars-long-for-security
    echo [INFO] 使用默认开发密钥 SECRET_KEY
)

REM 数据库配置
set DATABASE_URL=sqlite:///./data/land_property.db

REM 后端API端口
set API_PORT=8002

REM 前端开发端口（Vite默认）
set FRONTEND_PORT=5173

echo [配置信息]
echo   环境: %ENVIRONMENT%
echo   调试模式: %DEBUG%
echo   后端端口: %API_PORT%
echo   前端端口: %FRONTEND_PORT%
echo.

REM 检查启动选项
if "%1"=="backend" goto start_backend
if "%1"=="frontend" goto start_frontend
if "%1"=="all" goto start_all
if "%1"=="help" goto show_help
REM 默认启动所有服务
goto start_all

:show_help
echo 使用方法:
echo   start-dev.bat           - 启动前后端（默认，打开新窗口）
echo   start-dev.bat backend   - 仅启动后端
echo   start-dev.bat frontend  - 仅启动前端
echo   start-dev.bat all       - 同时启动前后端
echo   start-dev.bat help      - 显示此帮助
echo.
goto end

:start_backend
echo.
echo [启动后端服务...]
cd /d %~dp0backend
if not exist "data" mkdir data
python -m uvicorn src.main:app --reload --host 127.0.0.1 --port %API_PORT%
goto end

:start_frontend
echo.
echo [启动前端服务...]
cd /d %~dp0frontend
call npm run dev
goto end

:start_all
echo.
echo [启动所有服务...]
echo 注意：将在新窗口中启动后端服务
start "Backend" cmd /k "%~f0 backend"
timeout /t 3 >nul
echo.
echo [启动前端服务...]
cd /d %~dp0frontend
call npm run dev
goto end

:end
