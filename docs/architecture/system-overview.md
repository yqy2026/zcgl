# 系统架构概览

## 📋 Purpose
本页提供土地物业资产管理系统的高层架构概览，作为新成员快速理解系统结构与关键组件的入口文档。

## 🎯 Scope
- 前后端核心组件与职责
- 关键数据流与集成点
- 部署拓扑与运行环境
- 配置入口与安全边界

## ✅ Status
**当前状态**: Active (2026-01-28 更新)
**适用版本**: v2.0.0

---

## 🧭 架构总览（逻辑视图）

```
┌──────────────────────────────────────────────────────────────┐
│                         Frontend (React)                      │
│   - React 19 + Ant Design 6 + Vite                             │
│   - 调用 /api/v1/*                                             │
└──────────────────────────────────────────────────────────────┘
                 │ HTTP(S) / REST
                 ▼
┌──────────────────────────────────────────────────────────────┐
│                       Backend (FastAPI)                       │
│   - API 路由 (src/api/v1)                                      │
│   - 业务服务层 (src/services)                                  │
│   - 配置入口 (src/core/config.py)                              │
│   - 数据访问 (SQLAlchemy)                                      │
└──────────────────────────────────────────────────────────────┘
        │                         │
        ▼                         ▼
┌──────────────────────┐   ┌──────────────────────┐
│  PostgreSQL (主库)    │   │     Redis (缓存)     │
└──────────────────────┘   └──────────────────────┘
```

---

## 🧩 关键组件

### 前端（Frontend）
- UI: React 19 + Ant Design 6
- 状态管理: Zustand + React Query
- 构建工具: Vite 6

### 后端（Backend）
- Web 框架: FastAPI + Uvicorn
- ORM: SQLAlchemy 2.0
- 配置: `src/core/config.py`（Pydantic Settings）
- 认证: JWT
- 文档处理: LLM Vision API（Qwen/DeepSeek/GLM 等）

### 数据与缓存
- PostgreSQL：核心业务数据
- Redis：缓存与会话/队列支持（可选）

---

## 🔁 关键数据流（简化）

1. 前端发起 API 请求（`/api/v1/*`）
2. FastAPI 路由分发 → 服务层处理业务逻辑
3. SQLAlchemy 访问 PostgreSQL
4. 若启用缓存：读取/写入 Redis
5. PDF/合同识别：调用 LLM Vision 提供商

---

## 🚢 部署拓扑（Docker Compose）

- `frontend`：静态资源由 Nginx 或容器提供
- `backend`：FastAPI + Uvicorn
- `postgres`：主数据库
- `redis`：缓存（可选）
- `nginx`：反向代理（可选）

详见 `docker-compose.yml` 与 `docs/guides/deployment.md`。

---

## 🔐 配置与安全边界

- **唯一配置入口**: `backend/src/core/config.py`
- **密钥来源**: 生产环境必须由外部注入（环境变量或密钥管理服务）
- **数据库策略**: PostgreSQL 为唯一生产数据库；SQLite 仅用于测试（显式开启）

---

## 📎 Evidence Sources
- `README.md`
- `backend/src/core/config.py`
- `backend/src/main.py`
- `docker-compose.yml`
- `docs/guides/backend.md`
