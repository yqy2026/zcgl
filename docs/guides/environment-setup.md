# 环境配置指南

## 📋 Purpose
本文档详细说明土地物业资产运营管理系统的环境变量配置，包括开发环境、测试环境和生产环境的配置差异。

## 🎯 Scope
- 环境变量配置说明
- 后端配置详解
- 前端配置详解
- 不同环境的配置差异
- 安全配置最佳实践

## ✅ Status
**当前状态**: Active (2026-02-16 更新)
**适用版本**: v1.1.0
**配置文件位置**:
- 后端: `backend/.env.example`
- 前端: `frontend/.env.example`

## 🔧 快速开始

### 1. 复制环境变量模板
```bash
# 后端环境配置
cd backend
cp .env.example .env

# 前端环境配置
cd ../frontend
cp .env.example .env.development
```

### 2. 修改关键配置
```bash
# 编辑后端配置
nano backend/.env

# 必须修改的配置项:
# - SECRET_KEY (生产环境)
# - DATA_ENCRYPTION_KEY (生产环境，PII 加密)
# - REQUIRE_ENCRYPTION (生产环境建议 true)
# - DATABASE_URL
# - REDIS_HOST/REDIS_PORT/REDIS_DB (如使用缓存)
```

---

## 📦 后端环境配置

### 配置文件位置
- **模板文件**: `backend/.env.example`
- **实际配置**: `backend/.env` (需自行创建)
- **配置加载**: `backend/src/core/config.py` (Pydantic Settings)

### 核心配置项

#### 1. 应用基本配置
```bash
# 应用名称和版本
APP_NAME=土地物业资产管理系统
APP_VERSION=1.0.0

# 开发模式 (生产环境必须设为 false)
DEBUG=false
ENVIRONMENT=development  # development | staging | production

# 服务器配置
HOST=0.0.0.0
PORT=8002
API_PORT=8002  # run_dev.py / make dev-backend 优先读取
RELOAD=true
```

#### 2. 安全配置 ⚠️ **生产环境必须修改**
```bash
# JWT 密钥 - 必须设置为强随机字符串（至少32字符）
# 生成方法:
python -c "import secrets; print(secrets.token_urlsafe(32))"

SECRET_KEY=your-generated-secret-key-here

# PII 加密密钥 - 必须是标准 Base64（含 padding）并带版本号 :1
# 生成方法（在 backend 目录）:
# python -m src.core.encryption
DATA_ENCRYPTION_KEY=<base64_key>:1

# 是否强制要求加密密钥（生产环境建议 true；开发可 false）
REQUIRE_ENCRYPTION=true

# JWT 算法和过期时间
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120
REFRESH_TOKEN_EXPIRE_DAYS=7

# JWT 安全强化配置
JWT_ISSUER=zcgl-system
JWT_AUDIENCE=zcgl-users
ENABLE_JTI_CLAIM=true
TOKEN_BLACKLIST_ENABLED=true
```

**安全要求**:
- ❌ 禁止使用默认密钥 `EMERGENCY-ONLY-REPLACE-WITH-ENV-SECRET-KEY-NOW`
- ✅ 生产环境使用环境变量或密钥管理服务
- ✅ 密钥长度至少 32 字符
- ✅ `DATA_ENCRYPTION_KEY` 使用标准 Base64（含 `=` padding）并带版本号
- ✅ 定期轮换密钥

#### 3. 数据库配置
```bash
# PostgreSQL (开发/测试/生产必需)
DATABASE_URL=postgresql+psycopg://username:password@host:5432/database_name
TEST_DATABASE_URL=postgresql+psycopg://username:password@host:5432/test_database_name

# SQLite 已移除（开发/测试/生产均不支持）

# 连接池配置 (PostgreSQL)
# DATABASE_POOL_SIZE=20
# DATABASE_MAX_OVERFLOW=10
```

**数据库选择建议**:
| 环境 | 数据库 | 说明 |
|------|--------|------|
| 开发 | PostgreSQL | 与生产环境一致 |
| 测试 | PostgreSQL | 与生产环境一致 |
| 生产 | PostgreSQL | 高可用，支持并发 |

#### 4. Redis 缓存配置
```bash
# 本地推荐使用 docker-compose.override.yml 中的 Redis
REDIS_ENABLED=true
REDIS_HOST=127.0.0.1
REDIS_PORT=16379
REDIS_DB=0
REDIS_PASSWORD=
```

```bash
make redis-up
make redis-health  # 返回 PONG
make redis-down
```

宿主机后端连接 `127.0.0.1:16379`；完整 Compose 中的后端容器连接 `redis:6379`。Redis 明确启用后连接失败会阻止后端启动，不会静默降级为内存缓存。仅在确实不需要验证分布式缓存、鉴权失效广播和持久化 Token 黑名单的单进程场景中，才显式设置 `REDIS_ENABLED=false`。

**Redis 使用场景**:
- 会话存储
- API 响应缓存
- 任务队列状态
- 分布式锁

#### 5. CORS 配置
```bash
# 允许的前端域名（逗号分隔）
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000
```

**生产环境示例**:
```bash
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

#### 6. 文件上传配置
```bash
# 上传目录
UPLOAD_DIR=./uploads

# 最大文件大小 (字节)
MAX_FILE_SIZE=52428800  # 50MB

# PDF 处理配置
PDF_MAX_FILE_SIZE_MB=50
PDF_PROCESSING_TIMEOUT=300
```

#### 7. 分页配置
```bash
DEFAULT_PAGE_SIZE=20
MAX_PAGE_SIZE=100
```

#### 8. 日志配置
```bash
# 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# 日志文件路径 (可选)
LOG_FILE=logs/app.log
```

#### 9. Document extraction configuration

RapidOCR and PyMuPDF provide the required local document-text stage. DeepSeek is an optional text-only enrichment stage and must be configured only when enabled.

```bash
DOCUMENT_LLM_ENABLED=false
# DEEPSEEK_API_KEY=your_deepseek_api_key
# DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
# DEEPSEEK_MODEL=deepseek-v4-flash
```

The extraction workflow does not use vision-provider selection, provider aliases, or fallback configuration. When `DOCUMENT_LLM_ENABLED=true`, all three DeepSeek values are validated at startup.
#### 10. 性能监控配置
```bash
# 是否启用性能监控
ENABLE_METRICS=true

# 慢查询阈值 (秒)
SLOW_QUERY_THRESHOLD=1.0

# Sentry APM / Error Tracking（可选）
SENTRY_ENABLED=false
SENTRY_DSN=
SENTRY_ENVIRONMENT=development
SENTRY_TRACES_SAMPLE_RATE=0.0
SENTRY_PROFILES_SAMPLE_RATE=0.0
SENTRY_SEND_DEFAULT_PII=false
```

#### 11. 企业微信通知配置 (V2.0)
```bash
# 是否启用企业微信应用消息通知
WECOM_ENABLED=false

# 企业微信企业 ID / 自建应用 AgentId / Secret
WECOM_CORP_ID=wwxxxxxxxxxxxxxxxx
WECOM_AGENT_ID=1000011
WECOM_SECRET=your-wecom-app-secret

# 本地联调接收人企业微信 userid；多人用 user1|user2
WECOM_TEST_TOUSER=user1

# 群机器人通道已下线：不要再使用 WECOM_WEBHOOK_URL 承载业务通知正文
```

---

## 🌐 前端环境配置

### 配置文件位置
- **模板文件**: `frontend/.env.example`
- **开发配置**: `frontend/.env.development`
- **生产配置**: `frontend/.env.production`
- **本地配置**: `frontend/.env.local` (不提交到 Git)

### 核心配置项

#### 1. API 配置
```bash
# API 基础 URL (版本化)
VITE_API_BASE_URL=http://localhost:8002/api/v1

# API 超时时间 (毫秒)
VITE_API_TIMEOUT=30000
```

**不同环境的 API URL**:
| 环境 | VITE_API_BASE_URL |
|------|-------------------|
| 开发 | `http://localhost:8002/api/v1` |
| 测试 | `http://test-server:8002/api/v1` |
| 生产 | `https://api.your-domain.com/api/v1` |

#### 2. 应用配置
```bash
# 应用标题
VITE_APP_TITLE=Real Estate Asset Management & Operations System

# 应用版本
VITE_APP_VERSION=2.0.0
```

#### 3. 构建配置
```bash
# 是否生成 Source Map
VITE_SOURCEMAP=false
```

**Source Map 建议**:
- 开发环境: `true` (便于调试)
- 生产环境: `false` (保护源代码)

### 环境变量加载顺序

Vite 按以下优先级加载环境变量:
1. `.env.local` - 最高优先级（不提交）
2. `.env.[mode].local` - 如 `.env.development.local`
3. `.env.[mode]` - 如 `.env.development`
4. `.env` - 最低优先级

---

## 🌍 不同环境的配置差异

### 开发环境 (Development)
```bash
# backend/.env
DEBUG=true
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/zcgl
REDIS_ENABLED=false
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
LOG_LEVEL=DEBUG
SECRET_KEY=dev-secret-key-do-not-use-in-production
```

```bash
# frontend/.env.development
VITE_API_BASE_URL=http://localhost:8002/api/v1
VITE_SOURCEMAP=true
```

**特点**:
- ✅ 详细的调试日志
- ✅ PostgreSQL 数据库（与生产一致）
- ✅ 热重载
- ✅ Source Map 支持

### 测试环境 (Staging)
```bash
# backend/.env
DEBUG=false
DATABASE_URL=postgresql+psycopg://user:pass@staging-db:5432/zcgl_staging
REDIS_ENABLED=true
REDIS_HOST=staging-redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=<staging-redis-password>
CORS_ORIGINS=https://staging.your-domain.com
LOG_LEVEL=INFO
SECRET_KEY=<staging-secret-key>
```

```bash
# frontend/.env.staging
VITE_API_BASE_URL=https://staging-api.your-domain.com/api/v1
VITE_SOURCEMAP=false
```

**特点**:
- ✅ 模拟生产环境
- ✅ PostgreSQL 数据库
- ✅ Redis 缓存启用
- ✅ 完整的安全配置

### 生产环境 (Production)
```bash
# backend/.env (通过环境变量或密钥管理服务)
DEBUG=false
ENVIRONMENT=production
DATABASE_URL=postgresql+psycopg://user:pass@prod-db:5432/zcgl_prod
REDIS_ENABLED=true
REDIS_HOST=prod-redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=<prod-redis-password>
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
LOG_LEVEL=WARNING
SECRET_KEY=<strong-random-key-from-vault>
DATA_ENCRYPTION_KEY=<base64_key>:1
REQUIRE_ENCRYPTION=true
```

```bash
# frontend/.env.production
VITE_API_BASE_URL=https://api.your-domain.com/api/v1
VITE_SOURCEMAP=false
```

**特点**:
- ✅ 生产级数据库
- ✅ Redis 高可用
- ✅ 严格的安全配置
- ✅ 最小日志输出

---

## 🔐 安全最佳实践

### 1. 密钥管理
```bash
# ❌ 错误做法
SECRET_KEY=hardcoded-secret-key

# ✅ 正确做法
# 使用环境变量
export SECRET_KEY=$(openssl rand -base64 32)

# 或使用密钥管理服务
# AWS Secrets Manager
# Azure Key Vault
# HashiCorp Vault
```

### 2. 敏感配置隔离
```bash
# 不应提交到 Git 的文件
.env
.env.local
.env.*.local

# 应提交到 Git 的文件
.env.example
```

### 3. 配置验证
```python
# backend/src/core/config.py 提供配置验证
from src.core.config import validate_config

try:
    validate_config()
except ValueError as exc:
    logger.error(f"配置验证失败: {exc}")
```

启动时会自动检查:
- [x] JWT 密钥强度
- [x] 调试模式状态
- [x] 数据库配置
- [x] Redis 配置完整性

---

## 🧪 配置验证

### 后端配置验证
```bash
# 启动后端时会自动验证配置
cd backend
python run_dev.py

# 查看安全配置输出
# 安全配置检查通过
# 或
# 警告: 使用了默认或不安全的JWT密钥！
```

### 前端配置验证
```bash
# 检查环境变量是否正确加载
cd frontend
npm run dev

# 在浏览器控制台检查
console.log(import.meta.env.VITE_API_BASE_URL)
# 应输出: http://localhost:8002/api/v1
```

---

## 🚨 常见问题

### Q1: SECRET_KEY 警告
**问题**: 启动时提示 "使用默认或不安全的JWT密钥"
**解决**:
```bash
# 生成新的密钥
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 在 .env 中设置
SECRET_KEY=<生成的密钥>
```

### Q2: CORS 错误
**问题**: 前端请求被 CORS 策略阻止
**解决**:
```bash
# 在后端 .env 中添加前端域名
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Q3: 数据库连接失败
**问题**: 无法连接到数据库
**解决**:
```bash
# 检查 DATABASE_URL 格式
# PostgreSQL: postgresql+psycopg://user:pass@host:port/db

# 确认 PostgreSQL 服务运行
pg_isready -h host -p port

# 用 psql 验证连接
psql "$DATABASE_URL" -c "SELECT 1;"
```

### Q4: Redis 连接失败
**问题**: Redis 连接错误
**解决**:
```bash
# Docker daemon 必须先启动
make redis-up
make redis-health  # 应返回 PONG

# 宿主机启动后端时使用 Compose 映射端口
REDIS_HOST=127.0.0.1
REDIS_PORT=16379
```

如果当前任务明确不需要 Redis，设置 `REDIS_ENABLED=false` 后重启后端；不要在 `REDIS_ENABLED=true` 时依赖内存降级。

---

## 📋 配置检查清单

### 开发环境
- [ ] `.env` 文件已从 `.env.example` 复制
- [ ] `DATABASE_URL` 正确配置
- [ ] `CORS_ORIGINS` 包含前端地址
- [ ] `DEBUG=true` (开发环境)
- [ ] 前端 `.env.development` 已配置

### 生产环境
- [ ] `SECRET_KEY` 已设置为强随机值
- [ ] `DATA_ENCRYPTION_KEY` 已设置为标准 Base64（含 padding）并带版本号
- [ ] `REQUIRE_ENCRYPTION=true`（生产环境）
- [ ] `DEBUG=false`
- [ ] `DATABASE_URL` 使用 PostgreSQL
- [ ] `REDIS_ENABLED=true`
- [ ] `CORS_ORIGINS` 设置为实际域名
- [ ] 日志级别设为 `WARNING` 或 `ERROR`
- [ ] 所有敏感配置通过环境变量设置

---

## 🔗 相关链接

### 配置文件
- [后端配置模板](../../backend/.env.example)
- [前端配置模板](../../frontend/.env.example)
- [Pydantic Settings 文档](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Vite 环境变量](https://vitejs.dev/guide/env-and-mode.html)

### 相关文档
- [快速开始指南](getting-started.md)
- [部署指南](deployment.md)
- [API 文档](../integrations/api-overview.md)

## 📋 Changelog

### 2025-12-23 v1.0.0 - 初始版本
- ✨ 新增：环境配置完整指南
- 📦 新增：后端和前端配置详解
- 🔐 新增：安全配置最佳实践
- 🌍 新增：不同环境的配置差异说明
- 🧪 新增：配置验证和检查清单
- 🚨 新增：常见问题排除方案

### 2026-02-03 v1.1.1 - 安全配置补充
- 🔐 新增：`REQUIRE_ENCRYPTION` 配置说明与生产环境示例

## 🔍 Evidence Sources
- **后端配置**: `backend/src/core/config.py`
- **后端环境模板**: `backend/.env.example`
- **前端配置**: `frontend/src/api/config.ts`
- **前端环境模板**: `frontend/.env.example`
- **Vite 配置**: `frontend/vite.config.ts`
- **Docker 环境变量**: `docker-compose.yml`
