@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
echo 🛑 Stopping Land Property Asset Management System (UV Version)
echo ========================================
echo.

REM Navigate to project root directory
cd /d "%~dp0../../"
echo [INFO] Current directory: %cd%
echo.

REM Stop all related processes
echo [INFO] Stopping services...

REM Stop Python/uv processes
taskkill /f /im python.exe >nul 2>nul
taskkill /f /im uv.exe >nul 2>nul

REM Stop Node.js processes
taskkill /f /im node.exe >nul 2>nul

REM Stop processes on ports 8002, 5173 and 5174
call :StopProcessesByPort 8002
call :StopProcessesByPort 5173
call :StopProcessesByPort 5174

echo [SUCCESS] All services stopped
echo.
echo 🔄 To restart, run start_uv.bat
echo.
goto :eof

:StopProcessesByPort
setlocal
set PORT=%1
netstat -aon | findstr ":%PORT%" >nul 2>nul
if %errorlevel% equ 0 (
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

pause
