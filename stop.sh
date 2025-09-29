#!/bin/bash

echo "🛑 停止土地物业资产管理系统"
echo.

# 查找并停止Python进程
echo "[INFO] 停止后端API服务..."
pkill -f "python.*run.py" 2>/dev/null || echo "[INFO] 后端服务未运行"

# 查找并停止Node.js进程
echo "[INFO] 停止前端开发服务器..."
pkill -f "npm.*run.*dev" 2>/dev/null || echo "[INFO] 前端服务未运行"
pkill -f "vite" 2>/dev/null || echo "[INFO] Vite进程未运行"

# 等待进程完全停止
sleep 2

echo "[SUCCESS] ✅ 所有服务已停止"