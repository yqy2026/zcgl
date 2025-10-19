@echo off
REM 启动 UV 包管理器的开发服务器
REM Land Property Asset Management System - UV Development Startup

echo ========================================
echo  Land Property Asset Management System
echo  UV Development Server Startup
echo ========================================
echo.

REM 检查 UV 是否安装
echo [1/5] Checking UV installation...
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: UV is not installed or not in PATH
    echo Please install UV from: https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)
echo UV installation: OK

REM 检查 pyproject.toml 是否存在
echo [2/5] Checking project configuration...
if not exist "pyproject.toml" (
    echo ERROR: pyproject.toml not found in backend directory
    echo Make sure you are running this script from the backend directory
    pause
    exit /b 1
)
echo Project configuration: OK

REM 检查 Python 环境
echo [3/5] Checking Python environment...
uv run python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python environment not available
    echo Running: uv sync to setup environment...
    uv sync
    if %errorlevel% neq 0 (
        echo ERROR: Failed to sync dependencies
        pause
        exit /b 1
    )
)
echo Python environment: OK

REM 检查数据库连接
echo [4/5] Checking database connection...
uv run python -c "from src.database import engine; print('Database connection: OK')" 2>nul
if %errorlevel% neq 0 (
    echo WARNING: Database connection test failed
    echo This might be normal on first startup - the database will be created automatically
)

REM 启动开发服务器
echo [5/5] Starting development server...
echo Server will be available at: http://localhost:8002
echo API Documentation: http://localhost:8002/docs
echo Press Ctrl+C to stop the server
echo.

uv run python run_dev.py

echo.
echo Server stopped.
pause