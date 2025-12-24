# 部署指南

## 📋 Purpose
本文档详细说明土地物业管理系统的部署流程，包括 Docker 部署、生产环境配置、SSL 证书设置和监控告警。

## 🎯 Scope
- Docker Compose 部署
- 生产环境配置
- Nginx 反向代理配置
- SSL/HTTPS 配置
- 数据库备份策略
- 监控和日志
- 故障排除

## ✅ Status
**当前状态**: Active (2025-12-23 创建)
**适用版本**: v1.0.0
**部署方式**: Docker Compose

---

## 🐳 Docker 部署（推荐）

### 系统要求

| 组件 | 最低要求 | 推荐配置 |
|------|----------|----------|
| **操作系统** | Ubuntu 20.04+ / CentOS 8+ | Ubuntu 22.04 LTS |
| **CPU** | 2 核心 | 4 核心+ |
| **内存** | 4 GB | 8 GB+ |
| **磁盘** | 20 GB | 50 GB+ SSD |
| **Docker** | 20.10+ | 24.0+ |
| **Docker Compose** | 2.0+ | 2.20+ |

### 快速部署

```bash
# 1. 克隆项目
git clone <repository-url>
cd zcgl

# 2. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env 设置生产环境配置

# 3. 启动所有服务
docker-compose up -d

# 4. 查看服务状态
docker-compose ps

# 5. 查看日志
docker-compose logs -f
```

### 服务端口

| 服务 | 容器端口 | 主机端口 | 说明 |
|------|----------|----------|------|
| **Frontend** | 80 | 3000 | React 前端应用 |
| **Backend** | 8002 | 8002 | FastAPI 后端服务 |
| **Redis** | 6379 | 6379 | 缓存服务 |
| **Nginx** | 80, 443 | 80, 443 | 反向代理 |

**证据来源**: `docker-compose.yml`

### 停止和重启

```bash
# 停止所有服务
docker-compose down

# 重启所有服务
docker-compose restart

# 重启单个服务
docker-compose restart backend

# 查看资源使用
docker stats
```

---

## 🔧 生产环境配置

### 环境变量配置

创建 `backend/.env.production`:

```bash
# =============================================================================
# 生产环境配置 - 土地物业资产管理系统
# =============================================================================

# 应用配置
APP_NAME=土地物业资产管理系统
APP_VERSION=1.0.0
DEBUG=false
ENVIRONMENT=production

# 服务器配置
HOST=0.0.0.0
PORT=8002
RELOAD=false

# ============================================================================
# 安全配置 - 必须修改！
# ============================================================================

# JWT 密钥 - 必须设置为强随机字符串（至少32字符）
# 生成方法: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=<your-production-secret-key-here>

# ============================================================================
# 数据库配置
# ============================================================================

# 生产环境使用 PostgreSQL
DATABASE_URL=postgresql://zcgl_user:<strong-password>@postgres:5432/zcgl_prod

# 连接池配置
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600
DATABASE_POOL_PRE_PING=true

# ============================================================================
# Redis 配置
# ============================================================================

REDIS_ENABLED=true
REDIS_URL=redis://redis:6379/0
REDIS_HOST=redis
REDIS_PORT=6379

# ============================================================================
# CORS 配置 - 设置为实际域名
# ============================================================================

CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com

# ============================================================================
# 文件上传配置
# ============================================================================

UPLOAD_DIR=./uploads
MAX_FILE_SIZE=52428800  # 50MB
PDF_MAX_FILE_SIZE_MB=50

# ============================================================================
# 日志配置
# ============================================================================

LOG_LEVEL=WARNING
LOG_FILE=logs/app.log

# ============================================================================
# 性能监控
# ============================================================================

ENABLE_METRICS=true
SLOW_QUERY_THRESHOLD=1.0
```

### PostgreSQL 数据库配置

```bash
# 1. 创建 PostgreSQL 服务
# 在 docker-compose.yml 中添加：

postgres:
  image: postgres:15-alpine
  container_name: zcgl-postgres
  restart: unless-stopped
  environment:
    POSTGRES_USER: zcgl_user
    POSTGRES_PASSWORD: <strong-password>
    POSTGRES_DB: zcgl_prod
  volumes:
    - postgres_data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U zcgl_user"]
    interval: 10s
    timeout: 5s
    retries: 5
  networks:
    - zcgl-network

# 2. 更新后端 DATABASE_URL
DATABASE_URL=postgresql://zcgl_user:<strong-password>@postgres:5432/zcgl_prod

# 3. 添加到 volumes
volumes:
  postgres_data:
    driver: local
```

### Nginx 配置

创建 `deployment/nginx/nginx.conf`:

```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 2048;
    use epoll;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    # 性能优化
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 50M;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss
               application/rss+xml font/truetype font/opentype
               application/vnd.ms-fontobject image/svg+xml;

    # 前端代理
    upstream frontend {
        server frontend:80;
    }

    # 后端代理
    upstream backend {
        server backend:8002;
    }

    # HTTP 重定向到 HTTPS
    server {
        listen 80;
        server_name your-domain.com www.your-domain.com;

        # Let's Encrypt 验证路径
        location /.well-known/acme-challenge/ {
            root /var/www/html;
        }

        # 其他请求重定向到 HTTPS
        location / {
            return 301 https://$server_name$request_uri;
        }
    }

    # HTTPS 配置
    server {
        listen 443 ssl http2;
        server_name your-domain.com www.your-domain.com;

        # SSL 证书配置
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        # SSL 安全配置
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        # HSTS
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        # 安全头
        add_header X-Frame-Options DENY always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-XSS-Protection "1; mode=block" always;

        # 前端静态文件
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # API 代理
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # 超时配置
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # WebSocket 支持（如需要）
        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

**证据来源**: `docker-compose.yml`, `frontend/nginx.conf`

---

## 🔒 SSL/HTTPS 配置

### 使用 Let's Encrypt 免费证书

```bash
# 1. 安装 Certbot
sudo apt-get update
sudo apt-get install certbot

# 2. 获取证书
sudo certbot certonly --standalone \
  -d your-domain.com \
  -d www.your-domain.com

# 3. 证书位置
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem

# 4. 复制证书到项目目录
mkdir -p deployment/nginx/ssl
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem deployment/nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem deployment/nginx/ssl/

# 5. 设置自动续期
sudo certbot renew --dry-run
```

### 自动续期配置

```bash
# 添加 cron 任务
crontab -e

# 每天凌晨 2 点检查证书续期
0 2 * * * certbot renew --quiet --post-hook "docker-compose restart nginx"
```

---

## 💾 数据备份策略

### 数据库备份

创建备份脚本 `scripts/backup_db.sh`:

```bash
#!/bin/bash
# 数据库备份脚本

BACKUP_DIR="/path/to/backups"
DB_NAME="zcgl_prod"
DB_USER="zcgl_user"
DB_HOST="postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# PostgreSQL 备份
docker-compose exec -T postgres pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

# SQLite 备份（如果使用）
cp database/data/zcgl.db "$BACKUP_DIR/db_backup_$TIMESTAMP.db"

# 删除 30 天前的备份
find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "db_backup_*.db" -mtime +30 -delete

echo "数据库备份完成: db_backup_$TIMESTAMP"
```

### 文件备份

```bash
# 备份上传的文件
rsync -avz uploads/ backup/uploads_$(date +%Y%m%d)/

# 备份配置文件
cp backend/.env backup/.env_$(date +%Y%m%d)
```

### 恢复流程

```bash
# PostgreSQL 恢复
gunzip < backup_file.sql.gz | docker-compose exec -T postgres psql -U zcgl_user zcgl_prod

# SQLite 恢复
cp backup_file.db database/data/zcgl.db
```

---

## 📊 监控和日志

### 健康检查端点

系统提供以下健康检查端点：

| 端点 | 说明 |
|------|------|
| `GET /api/v1/monitoring/health` | 系统健康状态 |
| `GET /api/v1/monitoring/metrics` | 性能指标 |
| `GET /api/v1/monitoring/stats` | 统计信息 |

### 日志管理

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 查看最近 100 行日志
docker-compose logs --tail=100 backend

# 日志轮转配置
# 在 docker-compose.yml 中添加：
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 性能监控

```bash
# 容器资源使用
docker stats

# 磁盘使用
docker system df

# 清理未使用的资源
docker system prune -a
```

---

## 🚀 CI/CD 自动部署

### GitHub Actions 示例

创建 `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /path/to/app
            git pull origin main
            docker-compose pull
            docker-compose up -d --build
            docker-compose restart
```

---

## 🚨 故障排除

### 常见问题

#### Q1: 容器启动失败
**症状**: `docker-compose up` 失败
**解决**:
```bash
# 查看详细日志
docker-compose logs backend

# 检查端口占用
netstat -tuln | grep -E ':(3000|8002|6379|80|443)'

# 重新构建镜像
docker-compose build --no-cache
docker-compose up -d
```

#### Q2: 数据库连接失败
**症状**: `could not connect to server`
**解决**:
```bash
# 检查数据库容器状态
docker-compose ps postgres

# 进入数据库容器
docker-compose exec postgres bash

# 测试连接
psql -U zcgl_user -d zcgl_prod

# 检查网络
docker network inspect zcgl_zcgl-network
```

#### Q3: Nginx 502 错误
**症状**: Nginx 返回 502 Bad Gateway
**解决**:
```bash
# 检查后端服务
docker-compose ps backend

# 查看后端日志
docker-compose logs backend

# 重启后端服务
docker-compose restart backend

# 检查 Nginx 配置
docker-compose exec nginx nginx -t
docker-compose restart nginx
```

#### Q4: SSL 证书错误
**症状**: 浏览器显示不安全的连接
**解决**:
```bash
# 检查证书有效期
openssl x509 -in deployment/nginx/ssl/fullchain.pem -noout -dates

# 重新获取证书
sudo certbot renew

# 重启 Nginx
docker-compose restart nginx
```

### 应急回滚

```bash
# 1. 查看部署历史
git log --oneline

# 2. 回滚到上一个版本
git checkout <previous-commit-hash>

# 3. 重新部署
docker-compose up -d --build

# 4. 如果需要，恢复数据库
gunzip < backup_file.sql.gz | docker-compose exec -T postgres psql -U zcgl_user zcgl_prod
```

---

## 📋 部署检查清单

### 部署前
- [ ] 服务器资源充足（CPU/内存/磁盘）
- [ ] Docker 和 Docker Compose 已安装
- [ ] 域名已解析到服务器 IP
- [ ] SSL 证书已获取
- [ ] 防火墙端口已开放（80, 443）
- [ ] 数据库备份策略已配置

### 配置检查
- [ ] `.env` 文件已配置
- [ ] `SECRET_KEY` 已设置为强密钥
- [ ] `DEBUG=false`（生产环境）
- [ ] 数据库连接正常
- [ ] Redis 连接正常
- [ ] CORS 域名已设置
- [ ] Nginx 配置正确

### 部署后验证
- [ ] 所有容器正常运行
- [ ] 前端页面可访问
- [ ] API 响应正常
- [ ] 数据库连接正常
- [ ] 日志正常输出
- [ ] 健康检查通过
- [ ] 备份任务已设置

---

## 🔗 相关链接

### 文档
- [环境配置指南](environment-setup.md)
- [数据库指南](database.md)
- [API 文档](../integrations/api-overview.md)

### 外部资源
- [Docker 文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Nginx 文档](https://nginx.org/en/docs/)
- [Let's Encrypt](https://letsencrypt.org/)

### 代码位置
- [Docker 配置](../../docker-compose.yml)
- [后端 Dockerfile](../../backend/Dockerfile)
- [前端 Dockerfile](../../frontend/Dockerfile)
- [Nginx 配置](../../frontend/nginx.conf)

## 📋 Changelog

### 2025-12-23 v1.0.0 - 初始版本
- ✨ 新增：部署完整指南
- 🐳 新增：Docker Compose 部署流程
- 🔧 新增：生产环境配置说明
- 🔒 新增：SSL/HTTPS 配置步骤
- 💾 新增：数据库备份和恢复策略
- 📊 新增：监控和日志管理
- 🚨 新增：故障排除和应急回滚

## 🔍 Evidence Sources
- **Docker 配置**: `docker-compose.yml`
- **后端 Dockerfile**: `backend/Dockerfile`
- **前端 Dockerfile**: `frontend/Dockerfile`
- **Nginx 配置**: `frontend/nginx.conf`
- **环境配置**: `backend/.env.example`
