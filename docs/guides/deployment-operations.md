# 系统部署与运维指南

## 📋 概述

本指南详细说明了地产资产管理系统的部署架构、运维流程和最佳实践。涵盖了从开发环境到生产环境的完整部署流程，以及系统的监控、维护和故障排除方法。

## 🏗️ 系统架构

### 整体架构图

```mermaid
graph TB
    subgraph "负载均衡层 Load Balancer"
        LB[Nginx Load Balancer]
    end

    subgraph "应用层 Application Layer"
        APP1[FastAPI App 1]
        APP2[FastAPI App 2]
        APP3[FastAPI App 3]
    end

    subgraph "服务层 Service Layer"
        PDF[PDF处理服务]
        OCR[OCR识别服务]
        NOTIFY[通知服务]
    end

    subgraph "数据层 Data Layer"
        DB[(PostgreSQL)]
        CACHE[(Redis Cache)]
        FILES[文件存储]
    end

    subgraph "监控层 Monitoring Layer"
        PROM[Prometheus]
        GRAF[Grafana]
        ALERT[AlertManager]
    end

    LB --> APP1
    LB --> APP2
    LB --> APP3

    APP1 --> DB
    APP1 --> CACHE
    APP1 --> PDF
    APP1 --> OCR
    APP1 --> NOTIFY

    APP2 --> DB
    APP2 --> CACHE
    APP2 --> PDF
    APP2 --> OCR
    APP2 --> NOTIFY

    APP3 --> DB
    APP3 --> CACHE
    APP3 --> PDF
    APP3 --> OCR
    APP3 --> NOTIFY

    PDF --> FILES
    OCR --> FILES

    APP1 --> PROM
    APP2 --> PROM
    APP3 --> PROM
    DB --> PROM
    CACHE --> PROM

    PROM --> GRAF
    PROM --> ALERT

    style LB fill:#e1f5fe
    style DB fill:#f3e5f5
    style CACHE fill:#fff3e0
    style PROM fill:#e8f5e8
```

### 技术栈

| 组件 | 技术选型 | 版本要求 | 作用 |
|------|----------|----------|------|
| **Web服务器** | Nginx | 1.18+ | 负载均衡、静态文件、反向代理 |
| **应用框架** | FastAPI | 0.104+ | API服务框架 |
| **Python运行时** | Python | 3.9+ | 应用程序运行环境 |
| **数据库** | PostgreSQL | 13+ | 数据持久化 |
| **缓存** | Redis | 6.0+ | 缓存和会话存储 |
| **进程管理** | Gunicorn | 20.1+ | WSGI服务器 |
| **包管理** | UV | 0.1+ | Python包管理 |
| **监控** | Prometheus + Grafana | 2.40+/9.0+ | 系统监控 |
| **容器化** | Docker | 20.10+ | 容器化部署 |

## 🚀 部署流程

### 1. 环境准备

#### 系统要求
```bash
# 最低配置要求
CPU: 2核心
内存: 4GB
存储: 50GB SSD
网络: 100Mbps

# 推荐配置
CPU: 4核心
内存: 8GB
存储: 100GB SSD
网络: 1Gbps
```

#### 操作系统配置
```bash
# Ubuntu/Debian 系统更新
sudo apt update && sudo apt upgrade -y

# 安装基础依赖
sudo apt install -y \
    python3.9 \
    python3.9-dev \
    python3.9-venv \
    nginx \
    redis-server \
    git \
    curl \
    wget \
    htop \
    build-essential

# CentOS/RHEL 系统更新
sudo yum update -y

# 安装基础依赖
sudo yum groupinstall -y "Development Tools"
sudo yum install -y \
    python39 \
    python39-devel \
    nginx \
    redis \
    git \
    curl \
    wget
```

### 2. 应用部署

#### 获取源代码
```bash
# 克隆项目代码
git clone https://github.com/your-org/asset-management.git
cd asset-management/backend

# 切换到指定分支
git checkout main
git pull origin main
```

#### 环境配置
```bash
# 安装UV包管理器
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装项目依赖
uv sync --dev

# 激活虚拟环境
source .venv/bin/activate

# 验证安装
python -c "import fastapi; print('FastAPI installed successfully')"
```

#### 配置文件设置
```bash
# 复制环境配置文件
cp .env.example .env

# 编辑配置文件
nano .env
```

```bash
# .env 配置示例
# 应用配置
APP_NAME=地产资产管理系统
APP_VERSION=1.0.0
APP_ENV=production
DEBUG=false
SECRET_KEY=your-super-secret-key-change-this-in-production

# 数据库配置（SQLite 已移除）
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/asset_management

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-redis-password

# 文件存储配置
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=50MB

# PDF处理配置
PDF_PROCESSING_TIMEOUT=300
# 使用 LLM Vision 提取（提供商配置在环境变量中）
LLM_PROVIDER=qwen

# 监控配置
ENABLE_METRICS=true
METRICS_PORT=9090

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
LOG_MAX_SIZE=100MB
LOG_BACKUP_COUNT=5

# 安全配置
CORS_ORIGINS=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

#### 数据库初始化
```bash
# 创建数据目录
mkdir -p data logs uploads

# 运行数据库迁移
uv run alembic upgrade head

# 创建初始管理员用户
uv run python scripts/create_admin.py
```

### 3. 服务配置

#### Gunicorn配置
```python
# gunicorn.conf.py
import multiprocessing

# 服务器套接字
bind = "127.0.0.1:8000"
backlog = 2048

# 工作进程
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# 超时设置
timeout = 30
keepalive = 2

# 日志配置
accesslog = "./logs/gunicorn_access.log"
errorlog = "./logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程命名
proc_name = 'asset_management'

# 安全设置
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
```

#### Systemd服务配置
```ini
# /etc/systemd/system/asset-management.service
[Unit]
Description=Asset Management API Server
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/asset-management/backend
Environment=PATH=/opt/asset-management/backend/.venv/bin
ExecStart=/opt/asset-management/backend/.venv/bin/gunicorn -c gunicorn.conf.py main:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/asset-management/backend/data
ReadWritePaths=/opt/asset-management/backend/logs
ReadWritePaths=/opt/asset-management/backend/uploads

[Install]
WantedBy=multi-user.target
```

#### Nginx配置
```nginx
# /etc/nginx/sites-available/asset-management
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # 重定向到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL配置
    ssl_certificate /etc/ssl/certs/yourdomain.com.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # 日志配置
    access_log /var/log/nginx/asset-management_access.log;
    error_log /var/log/nginx/asset-management_error.log;

    # 文件上传大小限制
    client_max_body_size 50M;

    # 静态文件
    location /static/ {
        alias /opt/asset-management/backend/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # 上传文件
    location /uploads/ {
        alias /opt/asset-management/backend/uploads/;
        expires 1M;
        add_header Cache-Control "public";
    }

    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # 缓冲设置
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;

        # 健康检查
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;
    }

    # 健康检查端点
    location /health {
        proxy_pass http://127.0.0.1:8000/api/v1/health;
        access_log off;
    }

    # 监控端点（限制访问）
    location /metrics {
        proxy_pass http://127.0.0.1:8000/metrics;
        allow 127.0.0.1;
        allow 10.0.0.0/8;
        deny all;
    }

    # 前端应用（如果有）
    location / {
        root /opt/asset-management/frontend/dist;
        try_files $uri $uri/ /index.html;
        expires 1h;
    }
}
```

### 4. 启动服务

#### 启动应用服务
```bash
# 创建系统用户
sudo useradd -r -s /bin/false www-data

# 设置目录权限
sudo chown -R www-data:www-data /opt/asset-management/backend
sudo chmod -R 755 /opt/asset-management/backend

# 启动服务
sudo systemctl enable asset-management
sudo systemctl start asset-management

# 检查状态
sudo systemctl status asset-management
```

#### 配置Nginx
```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/asset-management /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

#### 配置Redis
```bash
# 配置Redis
sudo nano /etc/redis/redis.conf

# 关键配置项
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000

# 启动Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

## 📊 监控配置

### 1. Prometheus配置

#### prometheus.yml
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'asset-management'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/metrics'
    scrape_interval: 15s

  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']

  - job_name: 'nginx'
    static_configs:
      - targets: ['localhost:9113']
```

#### alert_rules.yml
```yaml
groups:
  - name: asset-management-alerts
    rules:
      - alert: HighResponseTime
        expr: http_request_duration_seconds{quantile="0.95"} > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }}s"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"

      - alert: DatabaseConnectionFailure
        expr: database_connected == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failure"
          description: "Cannot connect to the database"

      - alert: RedisConnectionFailure
        expr: redis_connected == 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Redis connection failure"
          description: "Cannot connect to Redis"
```

### 2. Grafana仪表板

#### 应用性能仪表板
```json
{
  "dashboard": {
    "title": "Asset Management Performance",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, http_request_duration_seconds_bucket)",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, http_request_duration_seconds_bucket)",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          }
        ]
      }
    ]
  }
}
```

#### 系统资源仪表板
```json
{
  "dashboard": {
    "title": "System Resources",
    "panels": [
      {
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(process_cpu_seconds_total[5m])",
            "legendFormat": "CPU Usage"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "process_resident_memory_bytes / 1024 / 1024",
            "legendFormat": "Memory (MB)"
          }
        ]
      },
      {
        "title": "Database Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "database_active_connections",
            "legendFormat": "Active Connections"
          }
        ]
      }
    ]
  }
}
```

## 🔧 运维流程

### 1. 日常维护

#### 日志管理
```bash
# 日志轮转配置
# /etc/logrotate.d/asset-management
/opt/asset-management/backend/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload asset-management
    endscript
}

# 查看应用日志
tail -f /opt/asset-management/backend/logs/app.log

# 查看Nginx日志
tail -f /var/log/nginx/asset-management_access.log
tail -f /var/log/nginx/asset-management_error.log
```

#### 数据库维护
```bash
# 每日维护脚本
#!/bin/bash
# daily_maintenance.sh

# 备份数据库
cd /opt/asset-management/backend
uv run python scripts/backup_database.py

# 清理旧日志
find logs/ -name "*.log" -mtime +30 -delete

# 清理临时文件
find /tmp -name "asset_management_*" -mtime +1 -delete

# 更新数据库统计信息
uv run python scripts/update_database_stats.py

echo "Daily maintenance completed: $(date)"
```

#### 系统监控脚本
```bash
#!/bin/bash
# health_check.sh

# 检查应用健康状态
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/health)
if [ $response -ne 200 ]; then
    echo "Application health check failed: $response"
    systemctl restart asset-management
fi

# 检查数据库连接
if ! uv run python -c "from src.database import engine; engine.connect()"; then
    echo "Database connection failed"
    # 发送告警
fi

# 检查磁盘空间
disk_usage=$(df /opt/asset-management | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $disk_usage -gt 85 ]; then
    echo "Disk usage high: ${disk_usage}%"
    # 发送告警
fi
```

### 2. 备份策略

#### 数据库备份
```python
# scripts/backup_database.py
import os
from datetime import datetime
from src.core.config import settings

def backup_database():
    """备份数据库 (PostgreSQL)"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backups/{timestamp}"

    os.makedirs(backup_dir, exist_ok=True)

    if not settings.DATABASE_URL.startswith("postgresql"):
        raise ValueError("仅支持 PostgreSQL 备份")

    import subprocess

    backup_file = os.path.join(backup_dir, "asset_management.dump")
    cmd = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "-f",
        backup_file,
        settings.DATABASE_URL,
    ]
    subprocess.run(cmd, check=True)

    # 备份文件
    files_backup = os.path.join(backup_dir, "uploads")
    if os.path.exists("uploads"):
        import shutil
        shutil.copytree("uploads", files_backup)

    print(f"Backup completed: {backup_dir}")
    return backup_dir

if __name__ == "__main__":
    backup_database()
```

#### 自动备份配置
```bash
# 添加到crontab
# crontab -e

# 每日凌晨2点备份数据库
0 2 * * * cd /opt/asset-management/backend && /opt/asset-management/backend/.venv/bin/python scripts/backup_database.py

# 每周日凌晨3点清理旧备份
0 3 * * 0 find /opt/asset-management/backend/backups -type d -mtime +30 -exec rm -rf {} \;
```

#### 台账补偿任务（REQ-RNT-006 M3）
```bash
# 每日凌晨 01:30 执行台账补偿
30 1 * * * cd /opt/asset-management && \
  TEST_DATABASE_URL='' DATABASE_URL='postgresql+psycopg://app:***@127.0.0.1:5432/zcgl_db' \
  /opt/asset-management/backend/.venv/bin/python backend/scripts/maintenance/run_ledger_compensation.py \
  >> /var/log/zcgl/ledger-compensation.log 2>&1
```

```ini
# systemd timer 方案（可替代 crontab）
# /etc/systemd/system/zcgl-ledger-compensation.service
[Unit]
Description=Run zcgl ledger compensation
After=network.target postgresql.service

[Service]
Type=oneshot
WorkingDirectory=/opt/asset-management
Environment=DATABASE_URL=postgresql+psycopg://app:***@127.0.0.1:5432/zcgl_db
ExecStart=/opt/asset-management/backend/.venv/bin/python backend/scripts/maintenance/run_ledger_compensation.py

# /etc/systemd/system/zcgl-ledger-compensation.timer
[Unit]
Description=Daily zcgl ledger compensation

[Timer]
OnCalendar=*-*-* 01:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

- 必填环境：`DATABASE_URL`。不要给生产补偿任务注入 `TEST_DATABASE_URL`。
- 工作目录必须指向仓库根或能正确解析 `backend/scripts/maintenance/run_ledger_compensation.py` 的目录。
- 首次启用前先手工执行一次脚本，确认输出 JSON 中 `failures` 为空。
- 回滚方式：先停用 cron/timer，再通过 `POST /api/v1/ledger/compensation/run` 做一次人工验证；如需回退代码，恢复到上一个已验证版本后重新启用定时任务。

### 3. 更新部署

#### 零停机部署脚本
```bash
#!/bin/bash
# deploy.sh

set -e

PROJECT_DIR="/opt/asset-management/backend"
BACKUP_DIR="/opt/backups/asset-management"
NEW_VERSION=$1

if [ -z "$NEW_VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

echo "Deploying version: $NEW_VERSION"

# 1. 备份当前版本
echo "Backing up current version..."
BACKUP_NAME="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"
cp -r "$PROJECT_DIR"/* "$BACKUP_DIR/$BACKUP_NAME/"

# 2. 下载新版本
echo "Downloading new version..."
cd /tmp
git clone https://github.com/your-org/asset-management.git asset-management-$NEW_VERSION
cd asset-management-$NEW_VERSION
git checkout $NEW_VERSION

# 3. 构建新版本
echo "Building new version..."
cd backend
uv sync --dev

# 4. 运行测试
echo "Running tests..."
uv run python -m pytest tests/ -v

# 5. 停止当前服务
echo "Stopping current service..."
sudo systemctl stop asset-management

# 6. 部署新版本
echo "Deploying new version..."
rsync -av --exclude='.git' --exclude='__pycache__' \
    /tmp/asset-management-$NEW_VERSION/backend/ "$PROJECT_DIR/"

# 7. 运行数据库迁移
echo "Running database migrations..."
cd "$PROJECT_DIR"
uv run alembic upgrade head

# 8. 启动新服务
echo "Starting new service..."
sudo systemctl start asset-management

# 9. 健康检查
echo "Performing health check..."
sleep 10
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/health)
if [ $response -eq 200 ]; then
    echo "Deployment successful!"
else
    echo "Deployment failed, rolling back..."
    sudo systemctl stop asset-management
    rsync -av "$BACKUP_DIR/$BACKUP_NAME/" "$PROJECT_DIR/"
    sudo systemctl start asset-management
    exit 1
fi

# 10. 清理临时文件
echo "Cleaning up..."
rm -rf /tmp/asset-management-$NEW_VERSION

echo "Deployment completed successfully!"
```

## 🚨 故障排除

### 1. 常见问题

#### 应用启动失败
```bash
# 检查服务状态
sudo systemctl status asset-management

# 查看详细日志
sudo journalctl -u asset-management -f

# 检查配置文件
cd /opt/asset-management/backend
uv run python -c "from src.core.config import settings; print(settings.DATABASE_URL)"

# 检查依赖
uv run python -c "import fastapi, sqlalchemy, redis; print('Dependencies OK')"
```

#### 数据库连接问题
```bash
# 检查数据库服务状态
sudo systemctl status postgresql

# 测试数据库连接
uv run python -c "
from src.database import engine
try:
    with engine.connect() as conn:
        print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
"

# 检查数据库权限
psql -d zcgl_db -c "SELECT grantee, privilege_type FROM information_schema.role_table_grants WHERE grantee='asset_user';"
```

#### Redis连接问题
```bash
# 检查Redis状态
sudo systemctl status redis-server

# 测试Redis连接
redis-cli ping

# 检查Redis配置
redis-cli config get maxmemory
redis-cli config get maxmemory-policy
```

### 2. 性能问题诊断

#### 慢查询分析
```bash
# 启用慢查询日志
uv run python -c "
from src.database import engine
import logging

logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# 模拟慢查询检测
import time
start = time.time()
# 执行查询
end = time.time()
if end - start > 1.0:
    print(f'Slow query detected: {end - start:.2f}s')
"
```

#### 内存使用分析
```bash
# 检查内存使用
ps aux | grep gunicorn
top -p $(pgrep gunicorn)

# 内存泄漏检测
uv run python -m memory_profiler scripts/profile_memory.py
```

### 3. 安全检查

#### SSL证书检查
```bash
# 检查证书有效期
openssl x509 -in /etc/ssl/certs/yourdomain.com.crt -noout -dates

# 检查证书链
openssl verify -CAfile /etc/ssl/certs/ca-bundle.crt /etc/ssl/certs/yourdomain.com.crt
```

#### 防火墙配置
```bash
# 检查防火墙状态
sudo ufw status

# 允许必要端口
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

## 📈 性能优化

### 1. 应用层优化

#### Gunicorn调优
```python
# 高负载配置
workers = multiprocessing.cpu_count() * 4 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 2000
max_requests = 5000
preload_app = True

# 内存优化
max_requests = 1000
max_requests_jitter = 100
```

#### 应用缓存
```python
# Redis缓存配置
CACHE_CONFIG = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "MAX_ENTRIES": 10000,
            "COMPRESS_MIN_LEN": 50,
        }
    }
}
```

### 2. 数据库优化

#### 索引优化
```sql
-- 分析查询性能
EXPLAIN QUERY PLAN SELECT * FROM assets WHERE status = 'active';

-- 添加缺失索引
CREATE INDEX CONCURRENTLY idx_assets_status ON assets(status);

-- 复合索引
CREATE INDEX CONCURRENTLY idx_assets_status_category ON assets(status, business_category);
```

#### 连接池优化
```python
# 数据库连接池配置
DATABASE_CONFIG = {
    "pool_size": 50,
    "max_overflow": 100,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "pool_pre_ping": True,
    "pool_reset_on_return": "commit"
}
```

### 3. 系统级优化

#### 内核参数调优
```bash
# /etc/sysctl.conf
# 网络优化
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.core.netdev_max_backlog = 5000

# 内存优化
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5

# 文件描述符限制
fs.file-max = 2097152
```

#### 限制配置
```bash
# /etc/security/limits.conf
www-data soft nofile 65535
www-data hard nofile 65535
www-data soft nproc 65535
www-data hard nproc 65535
```

## 📋 运维检查清单

### 日常检查（每日）
- [ ] 应用服务状态检查
- [ ] 数据库连接状态
- [ ] Redis连接状态
- [ ] 磁盘空间检查
- [ ] 错误日志检查
- [ ] 性能指标检查

### 周期检查（每周）
- [ ] 备份完整性验证
- [ ] SSL证书有效期检查
- [ ] 安全更新检查
- [ ] 性能趋势分析
- [ ] 日志轮转检查
- [ ] 监控告警测试

### 月度检查（每月）
- [ ] 系统更新和补丁
- [ ] 数据库优化分析
- [ ] 备份恢复测试
- [ ] 容量规划评估
- [ ] 文档更新
- [ ] 灾备演练

---

*本指南会根据系统变化和运维经验持续更新和完善。如有问题或建议，请联系运维团队。*
