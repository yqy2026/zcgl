@echo off
setlocal enabledelayedexpansion

REM Set the script directory as working directory
cd /d "%~dp0"

chcp 65001 >nul
title Land Property Asset Management System

echo.
echo Starting Land Property Asset Management System
echo Script directory: %CD%
echo.

REM Check environment
echo [INFO] Checking environment...

py --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.8+
    echo [INFO] Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found! Please install Node.js 18+
    echo [INFO] Download: https://nodejs.org/
    pause
    exit /b 1
)

echo [SUCCESS] Environment check passed
echo.

REM Check project files
echo [INFO] Checking project files...
if not exist "%CD%\backend\run_dev.py" (
    echo [ERROR] Backend file missing: %CD%\backend\run_dev.py
    pause
    exit /b 1
)

if not exist "%CD%\frontend\package.json" (
    echo [ERROR] Frontend file missing: %CD%\frontend\package.json
    pause
    exit /b 1
)

echo [INFO] Project files check passed
echo.

REM Install backend dependencies
echo [INFO] Preparing backend environment...
cd /d "%CD%\backend"
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found
    cd /d "%~dp0"
    pause
    exit /b 1
)

echo [INFO] Installing backend dependencies...
py -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Backend dependencies installation failed
    cd /d "%~dp0"
    pause
    exit /b 1
)

REM Install additional required dependencies
echo [INFO] Installing additional required dependencies...
py -m pip install email-validator --quiet
if errorlevel 1 (
    echo [WARNING] email-validator installation failed, continuing...
)

echo [SUCCESS] Backend dependencies installed
cd /d "%~dp0"

REM Install frontend dependencies
echo [INFO] Preparing frontend environment...
cd /d "%CD%\frontend"
if not exist "node_modules" (
    echo [INFO] Installing frontend dependencies, first run may take several minutes
    npm install --silent
    if errorlevel 1 (
        echo [ERROR] Frontend dependencies installation failed
        cd /d "%~dp0"
        pause
        exit /b 1
    )
    echo [SUCCESS] Frontend dependencies installed
) else (
    echo [INFO] Frontend dependencies already exist, skipping installation
)
cd /d "%~dp0"

echo.
echo [INFO] Starting services...

REM Start backend
echo [INFO] Starting backend API service...
cd /d "%CD%\backend"
start "Backend API Service - Port 8002" cmd /k "echo Backend service starting... && py run_dev.py"
cd /d "%~dp0"

REM Wait for backend startup
echo [INFO] Waiting for backend service to start...
timeout /t 8 /nobreak >nul

REM Start frontend
echo [INFO] Starting frontend development server...
cd /d "%CD%\frontend"
start "Frontend Dev Server - Port 5173" cmd /k "echo Frontend service starting... && npm run dev"
cd /d "%~dp0"

echo.
echo [SUCCESS] System startup complete!
echo.
echo Access URLs:
echo   Frontend App: http://localhost:5173
echo   Backend API: http://localhost:8002
echo   API Docs: http://localhost:8002/docs
echo.
echo Tips:
echo   Demo data pre-loaded, ready to experience
echo   Frontend supports hot reload, auto-refresh on code changes
echo   Two service windows opened, keep them running
echo   Run stop.bat to stop all services
echo.

REM Wait for services to fully start
echo [INFO] Waiting for services to fully start...
timeout /t 12 /nobreak >nul

REM Open browser
echo [INFO] Opening browser...
start http://localhost:5173

echo.
echo Startup complete! Press any key to close this window (services will continue running)
pause >nul