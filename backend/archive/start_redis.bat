@echo off
title Redis Server Startup

echo Starting Redis Server...
cd /d %~dp0

REM Check if Redis is installed
where redis-server >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Redis not found in PATH
    echo Please install Redis first
    echo Download from: https://github.com/microsoftarchive/redis/releases
    pause
    exit /b 1
)

REM Start Redis service
echo Starting Redis on port 6379...
redis-server --port 6379 --bind 127.0.0.1

pause
