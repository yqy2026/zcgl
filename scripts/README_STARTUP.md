# 启动脚本使用说明

## 问题修复记录

2025-10-16 修复了启动脚本的路径问题：

### 问题描述
在项目清理过程中，将 `start_uv.bat` 和 `stop_uv.bat` 移动到 `scripts/` 目录后，脚本无法正常工作，因为：

1. 脚本使用相对路径访问 `backend/` 和 `frontend/` 目录
2. 脚本从 `scripts/` 目录运行时，相对路径不正确
3. 日志路径和其他文件路径也需要调整

### 解决方案

#### 1. 根目录 Wrapper 脚本
- 在项目根目录创建 `start_uv.bat` 和 `stop_uv.bat` 作为 wrapper 脚本
- 这些脚本检查项目结构并调用 `scripts/` 目录下的实际脚本

#### 2. 脚本路径修复
修改 `scripts/start_uv.bat`：
- 添加 `cd ..` 切换到项目根目录
- 使用 `%PROJECT_ROOT%` 变量存储根目录路径
- 所有文件路径使用绝对路径

修改 `scripts/stop_uv.bat`：
- 添加 `cd ..` 切换到项目根目录
- 确保停止操作在正确的工作目录进行

### 使用方法

#### 推荐方式（从项目根目录）：
```bash
# 启动系统
start_uv.bat

# 停止系统
stop_uv.bat

# 启动并更新依赖
start_uv.bat --update
```

#### 直接调用脚本目录：
```bash
# 从项目根目录
scripts\start_uv.bat
scripts\stop_uv.bat

# 或者从scripts目录
cd scripts
start_uv.bat
stop_uv.bat
```

### 脚本功能

#### start_uv.bat
- 检查 Python 3.12+ 和 uv 包管理器
- 检查项目文件结构
- 准备后端环境（虚拟环境 + 依赖同步）
- 准备前端环境（npm install）
- 启动后端 API 服务（端口 8002）
- 启动前端开发服务器（端口 5173）
- 健康检查和自动打开浏览器

#### stop_uv.bat
- 停止 Python/uv/Node.js 进程
- 释放端口 8002、5173、5174
- 完整清理所有相关服务

### 故障排除

#### 如果启动失败：
1. 确保在项目根目录运行脚本
2. 检查 Python 3.12+ 是否已安装
3. 检查 uv 包管理器是否已安装
4. 检查端口 8002 和 5173 是否被占用

#### 手动启动方式：
```bash
# 后端
cd backend
uv run python run_dev.py

# 前端（新终端）
cd frontend
npm run dev
```

### 项目结构
```
project-root/
├── start_uv.bat          # 根目录 wrapper 脚本
├── stop_uv.bat           # 根目录 wrapper 脚本
├── scripts/
│   ├── start_uv.bat      # 实际启动脚本
│   ├── stop_uv.bat       # 实际停止脚本
│   └── cleanup.sh        # 项目清理脚本
├── backend/              # 后端代码
└── frontend/             # 前端代码
```

### 维护说明
- 保持根目录和 scripts/ 目录的脚本同步
- 如果修改 scripts/ 中的脚本，确保路径逻辑正确
- 定期运行 `scripts/cleanup.sh` 清理临时文件