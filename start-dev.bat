@echo off
REM ==========================================
REM 土地物业资产管理系统 - 开发环境启动脚本
REM ==========================================

setlocal EnableExtensions

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║    土地物业资产管理系统 - 开发环境启动                     ║
echo ╚══════════════════════════════════════════════════════╝
echo.

REM 尝试加载 backend/.env
if exist "%~dp0backend\.env" (
  for /f "usebackq tokens=1,* delims==" %%A in ("%~dp0backend\.env") do (
    if not "%%A"=="" if not "%%A:~0,1"=="#" set "%%A=%%B"
  )
)

REM 设置开发环境变量（如果未提供）
if not defined ENVIRONMENT set ENVIRONMENT=development
if not defined DEBUG set DEBUG=true
if not defined TESTING_MODE set TESTING_MODE=false

REM SECRET_KEY 提示
if not defined SECRET_KEY (
  echo [WARN] SECRET_KEY 未设置，请在 backend\.env 中配置
)

REM 检查数据库配置（SQLite 已弃用）
if not defined DATABASE_URL (
  echo [ERROR] DATABASE_URL 未设置，SQLite 已弃用。
  echo 请在 backend\.env 中配置 PostgreSQL 连接字符串，例如:
  echo   DATABASE_URL=postgresql://user:password@localhost:5432/zcgl
  exit /b 1
)

REM 后端API端口
if not defined API_PORT set API_PORT=8002

REM 前端开发端口（Vite默认）
if not defined FRONTEND_PORT set FRONTEND_PORT=5173

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
python run_dev.py
goto end

:start_frontend
echo.
echo [启动前端服务...]
cd /d %~dp0frontend
call pnpm run dev
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
call pnpm run dev
goto end

:end
endlocal
