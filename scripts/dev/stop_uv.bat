@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
echo 🛑 停止土地物业资产管理系统 (UV版本)
echo ========================================

REM 停止所有相关进程
echo [INFO] 正在停止服务...

REM 停止Python/uv进程
taskkill /f /im python.exe >nul 2>nul
taskkill /f /im uv.exe >nul 2>nul

REM 停止Node.js进程
taskkill /f /im node.exe >nul 2>nul

REM 停止端口8002、5173和5174上的进程
call :StopProcessesByPort 8002
call :StopProcessesByPort 5173
call :StopProcessesByPort 5174

echo [SUCCESS] 所有服务已停止
echo.
echo 🔄 如果需要重新启动，请运行 start_uv.bat
echo.
goto :eof

:StopProcessesByPort
setlocal
set PORT=%1
netstat -aon | findstr ":%PORT%" >nul 2>nul
if %errorlevel% equ 0 (
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

pause