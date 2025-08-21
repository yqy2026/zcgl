@echo off
chcp 65001 >nul
title 停止Docker服务

echo.
echo 🛑 停止土地物业资产管理系统 - Docker版
echo.

echo [INFO] 停止Docker服务...
docker-compose -f docker-compose.dev.yml down

echo [SUCCESS] Docker服务已停止
echo.
echo 📊 清理完成：
echo   ✓ 所有容器已停止
echo   ✓ 网络已清理
echo   ✓ 数据已保留（下次启动时恢复）
echo.

pause