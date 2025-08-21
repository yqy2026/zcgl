# 土地物业资产管理系统

一个现代化的土地物业资产管理系统，专为资产管理经理设计，帮助高效管理土地物业资产。

## 🌟 主要特性

- **资产信息管理** - 完整的资产CRUD操作，支持权属、面积、用途等详细信息管理
- **智能搜索筛选** - 多维度搜索和高级筛选功能，快速定位目标资产
- **Excel导入导出** - 支持批量数据导入导出，兼容现有Excel工作流
- **数据可视化** - 丰富的图表和统计分析，直观展示资产状况
- **现代化界面** - 基于React + Ant Design的专业UI设计

## 🚀 快速启动

### 系统要求
- **Python 3.8+** (后端运行环境)
- **Node.js 18+** (前端开发环境)

### 一键启动

#### Windows用户
```bash
# 双击运行或在命令行执行
start.bat

# 或使用PowerShell（推荐）
start_local.ps1
```

#### Linux/Mac用户
```bash
# 使用PowerShell脚本（需要安装PowerShell）
pwsh start_local.ps1
```

### 访问系统
启动成功后访问：
- **前端应用**: http://localhost:5173
- **后端API**: http://localhost:8001
- **API文档**: http://localhost:8001/docs

## 📊 技术架构

### 技术栈
- **前端**: React 18 + TypeScript + Ant Design + Vite
- **后端**: FastAPI + Python + SQLite
- **开发工具**: 热重载、自动重启、类型检查

### 项目结构
```
├── frontend/          # React前端应用
│   ├── src/
│   │   ├── pages/         # 页面组件
│   │   ├── components/    # 可复用组件
│   │   └── hooks/         # 自定义Hooks
├── backend/           # FastAPI后端应用
│   ├── src/
│   │   └── main_simple.py # 简化版API服务
├── start.bat          # Windows启动脚本
├── start_local.ps1    # PowerShell启动脚本
└── stop.bat           # 停止服务脚本
```

## 🎯 核心功能

### 1. 工作台
- 关键指标概览（资产总数、出租率、月收入等）
- 今日待办事项
- 资产状态图表
- 快速操作入口

### 2. 资产管理
- 资产清单浏览（表格/卡片视图）
- 多维度搜索筛选
- 资产详情查看和编辑
- 批量导入导出

### 3. 数据分析
- 出租率统计和趋势
- 资产分布分析
- 面积统计图表

## 🛑 停止服务

```bash
# Windows用户
stop.bat

# 或手动关闭服务窗口
```

## 💡 使用说明

1. **演示数据**: 系统启动时自动创建演示数据，可直接体验
2. **数据存储**: 使用SQLite数据库，数据保存在 `backend/assets.db`
3. **热重载**: 前端支持热重载，修改代码后自动刷新
4. **API文档**: 访问 http://localhost:8001/docs 查看完整API文档

## 🔧 开发说明

### 手动启动（高级用户）
```bash
# 启动后端
cd backend
pip install fastapi uvicorn pydantic
python src/main_simple.py

# 启动前端
cd frontend
npm install
npm run dev
```

### Docker部署（推荐生产环境）
```bash
# 开发环境
docker-compose -f docker-compose.dev.yml up -d

# 生产环境
docker-compose -f docker-compose.prod.yml up -d

# 使用部署脚本
./scripts/deploy.sh production
```

### 项目特点
- **多种部署方式**: 支持本地开发、Docker容器化部署
- **快速启动**: 一键启动脚本，自动处理依赖安装
- **开发友好**: 支持热重载和自动重启
- **数据持久化**: SQLite数据库，数据不会丢失
- **生产就绪**: 完整的Docker配置和部署脚本

## 📚 更多文档

- [快速启动指南](QUICK_START.md) - 详细的安装和启动说明
- [架构设计文档](frontend/ARCHITECTURE_REDESIGN.md) - 前端架构设计说明
- [部署指南](DEPLOYMENT_GUIDE.md) - 生产环境部署说明
- [清理总结](CLEANUP_SUMMARY.md) - 项目清理记录

## 🆘 故障排除

### 环境检测
如果遇到启动问题，`start.bat` 脚本已包含环境检测功能，会自动检查Python和Node.js环境。

### 常见问题

#### 1. Python未找到错误
**症状**: 显示"Python 未安装"或"Python 未找到"
**解决方案**:
- 确认Python已安装：访问 https://www.python.org/downloads/
- 安装时勾选"Add Python to PATH"选项
- 重启命令行窗口或重启电脑
- 尝试不同命令：`python`、`python3`、`py`

#### 2. Node.js未找到错误
**症状**: 显示"Node.js 未安装"
**解决方案**:
- 下载安装Node.js：https://nodejs.org/
- 选择LTS版本（推荐18+）
- 重启命令行窗口

#### 3. 端口被占用
**症状**: 端口8001或5173被占用
**解决方案**:
```bash
# 停止服务
stop.bat

# 或手动清理端口
netstat -ano | findstr :8001
netstat -ano | findstr :5173
```

#### 4. 依赖安装失败
**症状**: pip或npm安装失败
**解决方案**:
- 检查网络连接
- 使用国内镜像源
- 清理缓存后重试

### 手动诊断步骤
1. **检查Python**: 在命令行运行 `python --version`
2. **检查Node.js**: 在命令行运行 `node --version`
3. **检查端口**: 运行 `netstat -an | findstr :8001`
4. **查看日志**: 检查启动脚本的输出信息

---

**快速体验**: 双击 `start.bat` 即可开始使用！