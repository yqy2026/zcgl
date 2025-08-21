@echo off
chcp 65001 >nul
title 停止服务

echo.
echo 🛑 停止土地物业资产管理系统服务
echo.

REM 停止Python进程（后端）
echo [INFO] 停止后端服务...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im py.exe >nul 2>&1

REM 停止Node.js进程（前端）
echo [INFO] 停止前端服务...
taskkill /f /im node.exe >nul 2>&1

REM 停止可能的端口占用
echo [INFO] 释放端口占用...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8001" ^| find "LISTENING"') do (
    echo 停止端口8001上的进程 %%a
    taskkill /f /pid %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5173" ^| find "LISTENING"') do (
    echo 停止端口5173上的进程 %%a
    taskkill /f /pid %%a >nul 2>&1
)

echo.
echo [SUCCESS] ✅ 所有服务已停止
echo.
echo 💡 提示：如需重新启动，请运行 start_final.bat
echo.
pause