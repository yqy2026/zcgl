#!/bin/bash

echo "🛑 停止土地物业资产管理系统 (UV版本)"
echo "========================================"

echo "[INFO] 正在停止服务..."

# 停止所有相关进程
pkill -f "python.*run_dev.py" 2>/dev/null
pkill -f "uvicorn" 2>/dev/null
pkill -f "npm.*dev" 2>/dev/null
pkill -f "vite" 2>/dev/null

# 停止端口上的进程
lsof -ti:8002 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null
lsof -ti:5174 | xargs kill -9 2>/dev/null

echo "[SUCCESS] 所有服务已停止"
echo
echo "🔄 如果需要重新启动，请运行 start_uv.sh"
echo