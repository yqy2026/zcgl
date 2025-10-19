@echo off
REM Wrapper script for start_uv.bat
REM This script should be run from the project root directory

echo 🚀 启动土地物业资产管理系统 (UV版本)
echo ========================================
echo.

REM Check if we're in the right directory
if not exist "backend\pyproject.toml" (
    echo ❌ 错误: 请在项目根目录运行此脚本
    echo 当前目录未找到 backend\pyproject.toml
    pause
    exit /b 1
)

if not exist "frontend\package.json" (
    echo ❌ 错误: 请在项目根目录运行此脚本
    echo 当前目录未找到 frontend\package.json
    pause
    exit /b 1
)

REM Call the actual startup script
call scripts\start_uv.bat %*