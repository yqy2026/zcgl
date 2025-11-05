@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
echo 🚀 Starting Land Property Asset Management System (UV Version)
echo ========================================
echo.

REM Navigate to project root directory
cd /d "%~dp0../.."
echo [INFO] Current directory: %cd%
echo.

REM Check command line parameters
set UPDATE_DEPS=0
if "%1"=="--update" set UPDATE_DEPS=1
if "%1"=="-u" set UPDATE_DEPS=1
if %UPDATE_DEPS% equ 1 (
    echo [INFO] Dependency update mode enabled
)

REM Set log file
set LOG_FILE=logs\startup_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%.log
if not exist "logs" mkdir logs
echo [INFO] Log file: %LOG_FILE%
echo [%date% %time%] Starting Land Property Asset Management System (UV Version) > "%LOG_FILE%"
echo [%date% %time%] Command line parameters: %* >> "%LOG_FILE%"

REM Check if uv is installed
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Error: uv package manager not found
    echo Please install uv first: https://docs.astral.sh/uv/getting-started/installation/
    echo [HINT] Install command: pip install uv
    pause
    exit /b 1
)

echo ✅ uv package manager detected
echo.

REM Check runtime environment
echo [INFO] Checking runtime environment...
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Error: Python not found, please install Python 3.12+
    echo [HINT] Download: https://www.python.org/downloads/
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
    echo ❌ Error: Python version is too low, need Python 3.12+
    echo [CURRENT] Current version: %PYTHON_VERSION%
    pause
    exit /b 1
)

if !MAJOR_VERSION! equ 3 (
    if !MINOR_VERSION! lss 12 (
        echo ❌ Error: Python version is too low, need Python 3.12+
        echo [CURRENT] Current version: %PYTHON_VERSION%
        pause
        exit /b 1
    )
)

echo ✅ Python version check passed: %PYTHON_VERSION%

REM Check project files
if not exist "backend\pyproject.toml" (
    echo ❌ Error: backend\pyproject.toml file not found
    echo Please make sure to run this script from the project root directory
    pause
    exit /b 1
)

if not exist "frontend\package.json" (
    echo ❌ Error: frontend\package.json file not found
    echo Please make sure to run this script from the project root directory
    pause
    exit /b 1
)

echo [SUCCESS] Environment check passed
echo.

REM Prepare backend environment
echo [INFO] Preparing backend environment...
cd backend

REM Check if virtual environment exists
if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    uv sync
) else (
    if %UPDATE_DEPS% equ 1 (
        echo [INFO] Forcing dependency update...
        uv sync --refresh
    ) else (
        echo [INFO] Virtual environment exists, syncing dependencies...
        uv sync
    )
)

echo [SUCCESS] Backend environment prepared
cd ..

echo.
echo [INFO] Preparing frontend environment...
cd frontend

REM Check if node_modules exists
if not exist "node_modules" (
    echo [INFO] Installing frontend dependencies...
    npm install
) else (
    echo [INFO] Frontend dependencies exist, skipping installation
)

echo [SUCCESS] Frontend environment prepared
cd ..

echo.
echo 🚀 Starting services...

REM Clean up existing services before startup
echo [INFO] Cleaning up existing services...
call :CleanExistingServices

echo [INFO] Starting backend API service...
cd backend
start "Backend API Server" cmd /k "uv run python run_dev.py"
cd ..

echo [INFO] Waiting for backend service to start...
timeout /t 5 /nobreak >nul

REM Check backend service health status
echo [INFO] Checking backend service health status...
call :CheckServiceHealth http://localhost:8002 "Backend API Service"

echo [INFO] Starting frontend development server...
cd frontend
start "Frontend Dev Server" cmd /k "npm run dev"
cd ..

echo.
echo [SUCCESS] 🎉 System startup complete!
echo 📱 Access addresses:
echo    ├─ Frontend: http://localhost:5173
echo    ├─ Backend API: http://localhost:8002
echo    └─ API Documentation: http://localhost:8002/docs
echo.
echo 💡 Usage tips:
echo    ├─ System has demo data loaded, ready to use
echo    ├─ Frontend supports hot reload, code changes auto-refresh
echo    ├─ Two service windows have opened, keep them running
echo    └─ Run stop_uv.bat to stop all services
echo.
echo [INFO] Waiting for services to fully start...
timeout /t 10 /nobreak >nul

REM Check frontend service health status
echo [INFO] Checking frontend service health status...
call :CheckServiceHealth http://localhost:5173 "Frontend Development Server"

echo [INFO] Opening browser...
start http://localhost:5173

echo.
echo ✅ Startup complete! Services are running in the background
echo.
pause
goto :eof

:CleanExistingServices
echo [INFO] Cleaning up existing services...
taskkill /f /im python.exe >nul 2>nul
taskkill /f /im uv.exe >nul 2>nul
taskkill /f /im node.exe >nul 2>nul
call :StopProcessesByPort 8002
call :StopProcessesByPort 5173
call :StopProcessesByPort 5174
echo [SUCCESS] Existing services cleaned up
goto :eof

:CheckServiceHealth
setlocal
set URL=%1
set SERVICE_NAME=%2
set MAX_ATTEMPTS=15
set ATTEMPT=1

echo [INFO] Checking %SERVICE_NAME% health status...

:health_check_loop
powershell -Command "try { Invoke-WebRequest -Uri '%URL%' -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if !errorlevel! equ 0 (
    echo [SUCCESS] %SERVICE_NAME% is responding normally
    goto :health_check_success
)

if !ATTEMPT! geq %MAX_ATTEMPTS% (
    echo [WARNING] %SERVICE_NAME% startup timeout, please check service status
    goto :health_check_success
)

echo [INFO] Waiting for %SERVICE_NAME% response... (!ATTEMPT!/%MAX_ATTEMPTS%)
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
    echo [INFO] Stopping processes on port %PORT%...
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%PORT%"') do (
        taskkill /f /pid %%a >nul 2>nul
        if !errorlevel! equ 0 (
            echo [SUCCESS] Stopped process %%a (port %PORT%)
        )
    )
) else (
    echo [INFO] Port %PORT% is not in use
)
endlocal
goto :eof
