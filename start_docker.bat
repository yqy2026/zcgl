@echo off
chcp 65001 >nul
title 土地物业资产管理系统 - Docker版

echo.
echo 🐳 启动土地物业资产管理系统 - Docker版
echo.

REM 检查Docker
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker 未运行，请启动Docker Desktop
    echo [INFO] 下载地址: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo [SUCCESS] Docker环境检查通过
echo.

REM 停止可能存在的容器
echo [INFO] 清理旧容器...
docker-compose -f docker-compose.dev.yml down >nul 2>&1

REM 构建并启动服务
echo [INFO] 构建并启动服务...
docker-compose -f docker-compose.dev.yml up --build -d

REM 等待服务启动
echo [INFO] 等待服务启动完成...
timeout /t 15 /nobreak >nul

REM 检查服务状态
echo [INFO] 检查服务状态...
docker-compose -f docker-compose.dev.yml ps

echo.
echo 🎉 系统启动完成！
echo.
echo 📱 访问地址：
echo   前端应用: http://localhost:5173
echo   后端API: http://localhost:8001
echo   API文档: http://localhost:8001/docs
echo   数据库: localhost:5432 (postgres/postgres123)
echo.
echo 💡 使用说明：
echo   1. 所有服务运行在Docker容器中
echo   2. 代码修改会自动同步到容器
echo   3. 数据库数据持久化保存
echo   4. 使用 stop_docker.bat 停止服务
echo.

REM 自动打开浏览器
echo [INFO] 正在打开浏览器...
start http://localhost:5173

echo 按任意键查看日志（Ctrl+C退出日志查看）...
pause >nul

REM 显示日志
docker-compose -f docker-compose.dev.yml logs -f