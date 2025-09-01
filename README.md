# 土地物业资产管理系统

一个现代化的全栈Web应用，用于管理土地和物业资产信息。

## 🚀 快速开始

### 方式一：一键启动（推荐）
```bash
start.bat
```

### 方式二：分别启动

#### 启动后端
```bash
cd backend
python run.py
```

#### 启动前端
```bash
cd frontend
npm run dev
```

## 📱 访问地址

- **前端界面**: http://localhost:5173/
- **后端API**: http://localhost:8001/
- **API文档**: http://localhost:8001/docs

## 🔍 系统检查

运行系统状态检查：
```bash
python system_check.py
```

## 📋 主要功能

- 📊 资产信息管理
- 📈 统计分析和可视化
- 🏠 出租率计算
- 📤 Excel数据导入导出
- 📝 操作历史记录
- 💾 数据备份与恢复

## 🛠️ 技术栈

### 后端
- FastAPI + SQLAlchemy
- Python 3.11+
- SQLite数据库

### 前端
- React + TypeScript
- Vite + Ant Design
- Chart.js + Recharts

## 📁 项目结构

```
zcgl/
├── backend/           # 后端API服务
├── frontend/          # 前端React应用
├── start.bat          # 一键启动脚本
├── stop.bat           # 停止服务脚本
├── start_docker.bat   # Docker版启动脚本
└── stop_docker.bat    # Docker版停止脚本
```

## 📖 详细文档

查看 [PROJECT_STATUS.md](PROJECT_STATUS.md) 了解完整的项目状态和技术细节。

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License