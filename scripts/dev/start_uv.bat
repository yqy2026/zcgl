@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
echo 🚀 启动土地物业资产管理系统 (UV版本)
echo ========================================
echo.

REM 检查命令行参数
set UPDATE_DEPS=0
if "%1"=="--update" set UPDATE_DEPS=1
if "%1"=="-u" set UPDATE_DEPS=1
if %UPDATE_DEPS% equ 1 (
    echo [INFO] 启用依赖更新模式
)

REM 设置日志文件
set LOG_FILE=logs\startup_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%.log
if not exist "logs" mkdir logs
echo [INFO] 日志文件: %LOG_FILE%
echo [%date% %time%] 启动土地物业资产管理系统 (UV版本) > "%LOG_FILE%"
echo [%date% %time%] 命令行参数: %* >> "%LOG_FILE%"

REM 检查uv是否安装
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到uv包管理器
    echo 请先安装uv: https://docs.astral.sh/uv/getting-started/installation/
    echo [HINT] 安装命令: pip install uv
    pause
    exit /b 1
)

echo ✅ 检测到uv包管理器
echo.

REM 检查运行环境
echo [INFO] 检查运行环境...
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到Python，请先安装Python 3.12+
    echo [HINT] 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查Python版本
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR_VERSION=%%a
    set MINOR_VERSION=%%b
)

if !MAJOR_VERSION! lss 3 (
    echo ❌ 错误: Python版本过低，需要Python 3.12+
    echo [CURRENT] 当前版本: %PYTHON_VERSION%
    pause
    exit /b 1
)

if !MAJOR_VERSION! equ 3 (
    if !MINOR_VERSION! lss 12 (
        echo ❌ 错误: Python版本过低，需要Python 3.12+
        echo [CURRENT] 当前版本: %PYTHON_VERSION%
        pause
        exit /b 1
    )
)

echo ✅ Python版本检查通过: %PYTHON_VERSION%

REM 检查项目文件
if not exist "backend\pyproject.toml" (
    echo ❌ 错误: 未找到backend\pyproject.toml文件
    echo 请确保在项目根目录运行此脚本
    pause
    exit /b 1
)

if not exist "frontend\package.json" (
    echo ❌ 错误: 未找到frontend\package.json文件
    echo 请确保在项目根目录运行此脚本
    pause
    exit /b 1
)

echo [SUCCESS] 环境检查通过
echo.

REM 准备后端环境
echo [INFO] 准备后端环境...
cd backend

REM 检查是否存在虚拟环境
if not exist ".venv" (
    echo [INFO] 创建虚拟环境...
    uv sync
) else (
    if %UPDATE_DEPS% equ 1 (
        echo [INFO] 强制更新依赖...
        uv sync --refresh
    ) else (
        echo [INFO] 虚拟环境已存在，同步依赖...
        uv sync
    )
)

echo [SUCCESS] 后端环境准备完成
cd ..

echo.
echo [INFO] 准备前端环境...
cd frontend

REM 检查node_modules是否存在
if not exist "node_modules" (
    echo [INFO] 安装前端依赖...
    npm install
) else (
    echo [INFO] 前端依赖已存在，跳过安装
)

echo [SUCCESS] 前端环境准备完成
cd ..

echo.
echo 🚀 启动服务...

REM 启动前清理可能存在的服务
echo [INFO] 清理可能存在的服务...
call :CleanExistingServices

echo [INFO] 启动后端API服务...
cd backend
start "Backend API Server" cmd /k "uv run python run_dev.py"
cd ..

echo [INFO] 等待后端服务启动...
timeout /t 5 /nobreak >nul

REM 检查后端服务健康状态
echo [INFO] 检查后端服务健康状态...
call :CheckServiceHealth http://localhost:8002 "后端API服务"

echo [INFO] 启动前端开发服务器...
cd frontend
start "Frontend Dev Server" cmd /k "npm run dev"
cd ..

echo.
echo [SUCCESS] 🎉 系统启动完成！
echo 📱 访问地址：
echo    ┌─ 前端应用: http://localhost:5173
echo    ├─ 后端API: http://localhost:8002
echo    └─ API文档: http://localhost:8002/docs
echo.
echo 💡 使用提示：
echo    ├─ 系统已预置演示数据，可直接体验
echo    ├─ 前端支持热重载，修改代码自动刷新
echo    ├─ 两个服务窗口已打开，请保持运行
echo    └─ 运行 stop_uv.bat 可停止所有服务
echo.
echo [INFO] 等待服务完全启动...
timeout /t 10 /nobreak >nul

REM 检查前端服务健康状态
echo [INFO] 检查前端服务健康状态...
call :CheckServiceHealth http://localhost:5173 "前端开发服务器"

echo [INFO] 正在打开浏览器...
start http://localhost:5173

echo.
echo ✅ 启动完成！服务已在后台运行
echo.
pause
goto :eof

:CleanExistingServices
echo [INFO] 清理可能存在的服务...
taskkill /f /im python.exe >nul 2>nul
taskkill /f /im uv.exe >nul 2>nul
taskkill /f /im node.exe >nul 2>nul
call :StopProcessesByPort 8002
call :StopProcessesByPort 5173
call :StopProcessesByPort 5174
echo [SUCCESS] 现有服务清理完成
goto :eof

:CheckServiceHealth
setlocal
set URL=%1
set SERVICE_NAME=%2
set MAX_ATTEMPTS=15
set ATTEMPT=1

echo [INFO] 检查 %SERVICE_NAME% 健康状态...

:health_check_loop
curl -s "%URL%" >nul 2>&1
if !errorlevel! equ 0 (
    echo [SUCCESS] %SERVICE_NAME% 响应正常
    goto :health_check_success
)

if !ATTEMPT! geq %MAX_ATTEMPTS% (
    echo [WARNING] %SERVICE_NAME% 启动超时，请检查服务状态
    goto :health_check_success
)

echo [INFO] 等待 %SERVICE_NAME% 响应... (!ATTEMPT!/%MAX_ATTEMPTS%)
timeout /t 2 /nobreak >nul
set /a ATTEMPT+=1
goto :health_check_loop

:health_check_success
endlocal
goto :eof

:StopProcessesByPort
setlocal
set PORT=%1
netstat -aon | findstr ":%PORT%" >nul 2>nul
if !errorlevel! equ 0 (
    echo [INFO] 停止端口 %PORT% 上的进程...
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%PORT%"') do (
        taskkill /f /pid %%a >nul 2>nul
        if !errorlevel! equ 0 (
            echo [SUCCESS] 已停止进程 %%a (端口 %PORT%)
        )
    )
) else (
    echo [INFO] 端口 %PORT% 未被占用
)
endlocal
goto :eof