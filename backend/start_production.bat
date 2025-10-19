@echo off
title Production Server Startup

echo Starting Production Server...
cd /d %~dp0

REM Check for production environment file
if not exist ".env.production" (
    echo ERROR: .env.production file not found
    echo Please run: python configure_production_security.py
    pause
    exit /b 1
)

REM Set environment to production
set ENVIRONMENT=production

REM Check if SSL certificates exist (optional)
if exist "ssl\cert.pem" (
    echo SSL certificates found, starting HTTPS server...
    uv run python -m uvicorn src.main:app --host 0.0.0.0 --port 8002 --ssl-keyfile=ssl\key.pem --ssl-certfile=ssl\cert.pem
) else (
    echo Starting HTTP server (SSL recommended for production)...
    uv run python -m uvicorn src.main:app --host 0.0.0.0 --port 8002 --workers 4
)

pause
