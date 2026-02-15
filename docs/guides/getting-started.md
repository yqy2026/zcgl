# 快速开始指南

## ✅ Status
**当前状态**: Active (2026-02-03)

## 🎯 目标
帮助新成员在最短时间内完成本地开发环境搭建并成功启动系统。

## ✅ 前置条件
- Python 3.12+
- Node.js 20+ / pnpm
- PostgreSQL 18.2+
- Redis 8.6（可选）
- Docker / Docker Compose（可选）

## 1. 获取代码
```bash
git clone <your-repo-url>
cd zcgl
```

## 2. 配置环境变量
```bash
# 后端
cp backend/.env.example backend/.env

# 前端
cp frontend/.env.example frontend/.env.development
```

详细配置说明见：
- [环境配置指南](environment-setup.md)
- [数据库指南](database.md)

## 3. 初始化数据库
```bash
# 创建数据库后运行迁移
make migrate
```

## 4. 启动开发环境
```bash
# 一键启动前后端
make dev

# 或分别启动
make dev-backend
make dev-frontend
```

## 5. 验证启动是否成功
- 前端: http://localhost:5173
- 后端健康检查: http://localhost:8002/api/v1/admin/health

## 常见问题
- 数据库连接失败: 请检查 `DATABASE_URL` 并确认 PostgreSQL 服务运行
- 前端端口占用: 修改 `frontend/vite.config.ts` 或停止占用进程
