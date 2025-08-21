# 生产环境部署指南

## 概述

本指南详细说明如何将土地物业资产管理系统部署到生产环境。系统采用Docker容器化部署，支持高可用、可扩展的架构。

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │     Frontend    │    │     Backend     │
│     (Nginx)     │────│   (React SPA)   │────│   (FastAPI)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐    ┌─────────────────┐
                       │      Redis      │    │   PostgreSQL    │
                       │    (Cache)      │    │   (Database)    │
                       └─────────────────┘    └─────────────────┘
```

## 系统要求

### 硬件要求

**最低配置：**
- CPU: 2核心
- 内存: 4GB RAM
- 存储: 20GB SSD
- 网络: 100Mbps

**推荐配置：**
- CPU: 4核心
- 内存: 8GB RAM
- 存储: 50GB SSD
- 网络: 1Gbps

### 软件要求

- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: 2.25+

## 部署前准备

### 1. 安装Docker和Docker Compose

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 克隆项目代码

```bash
git clone https://github.com/your-org/land-property-management.git
cd land-property-management
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.production.template .env.production

# 编辑配置文件
nano .env.production
```

**重要配置项：**

```bash
# 数据库密码（必须修改）
POSTGRES_PASSWORD=your_secure_password_here

# 应用密钥（必须修改）
SECRET_KEY=your_very_secure_secret_key_here

# 域名配置
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
VITE_API_BASE_URL=https://your-domain.com/api

# 应用配置
APP_TITLE=土地物业资产管理系统
```

### 4. 配置SSL证书（可选）

如果启用HTTPS，需要准备SSL证书：

```bash
# 创建SSL目录
mkdir -p nginx/ssl

# 复制证书文件
cp your-cert.pem nginx/ssl/cert.pem
cp your-key.pem nginx/ssl/key.pem

# 设置权限
chmod 600 nginx/ssl/*
```

## 部署步骤

### 方式一：自动化部署（推荐）

```bash
# 给部署脚本执行权限
chmod +x scripts/deploy-production.sh

# 执行部署
./scripts/deploy-production.sh
```

部署脚本会自动执行以下步骤：
1. 环境检查
2. 代码测试
3. 数据备份
4. 镜像构建
5. 服务部署
6. 健康检查
7. 性能优化
8. 监控设置

### 方式二：手动部署

#### 1. 构建镜像

```bash
# 设置构建优化
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# 构建所有镜像
docker-compose -f docker-compose.production.yml build --no-cache
```

#### 2. 启动服务

```bash
# 启动所有服务
docker-compose -f docker-compose.production.yml up -d

# 查看服务状态
docker-compose -f docker-compose.production.yml ps
```

#### 3. 数据库迁移

```bash
# 等待数据库启动
sleep 30

# 运行数据库迁移
docker-compose -f docker-compose.production.yml exec backend alembic upgrade head
```

#### 4. 创建性能索引

```bash
# 创建数据库索引
docker-compose -f docker-compose.production.yml exec backend python -c "
from src.services.performance_service import PerformanceService
from src.database import get_db
db = next(get_db())
service = PerformanceService(db)
result = service.create_performance_indexes()
print('索引创建结果:', result)
"
```

## 服务访问

部署完成后，可以通过以下地址访问各个服务：

- **前端应用**: http://your-domain.com
- **后端API**: http://your-domain.com:8001
- **API文档**: http://your-domain.com:8001/docs

## 健康检查

### 自动健康检查

系统内置了健康检查机制：

```bash
# 查看所有服务健康状态
docker-compose -f docker-compose.production.yml ps

# 查看具体服务的健康检查日志
docker-compose -f docker-compose.production.yml logs backend
```

### 手动健康检查

```bash
# 检查数据库
curl -f http://localhost:8001/health/database

# 检查Redis
curl -f http://localhost:8001/health/redis

# 检查API
curl -f http://localhost:8001/health

# 检查前端
curl -f http://localhost/health.html
```

## 日志管理

### 日志查看

```bash
# 查看所有服务日志
docker-compose -f docker-compose.production.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.production.yml logs -f backend
docker-compose -f docker-compose.production.yml logs -f frontend
docker-compose -f docker-compose.production.yml logs -f database

# 查看最近的错误日志
docker-compose -f docker-compose.production.yml logs --tail=100 backend | grep ERROR
```

## 备份和恢复

### 自动备份

系统配置了自动备份机制：

```bash
# 查看备份任务状态
docker-compose -f docker-compose.production.yml logs backup

# 手动触发备份
docker-compose -f docker-compose.production.yml run --rm backup
```

### 手动备份

```bash
# 备份数据库
docker-compose -f docker-compose.production.yml exec database pg_dump -U postgres land_property > backup_$(date +%Y%m%d_%H%M%S).sql

# 备份上传文件
tar -czf uploads_backup_$(date +%Y%m%d_%H%M%S).tar.gz uploads/
```

### 数据恢复

```bash
# 恢复数据库
docker-compose -f docker-compose.production.yml exec -T database psql -U postgres land_property < backup_file.sql

# 恢复上传文件
tar -xzf uploads_backup.tar.gz
```

## 扩展和优化

### 水平扩展

```bash
# 扩展后端服务实例
docker-compose -f docker-compose.production.yml up -d --scale backend=3

# 扩展前端服务实例
docker-compose -f docker-compose.production.yml up -d --scale frontend=2
```

### 性能优化

1. **数据库优化**
   ```bash
   # 执行数据库优化
   docker-compose -f docker-compose.production.yml exec backend python -c "
   from src.services.performance_service import PerformanceService
   from src.database import get_db
   db = next(get_db())
   service = PerformanceService(db)
   result = service.optimize_database()
   print('优化结果:', result)
   "
   ```

2. **缓存优化**
   - 调整Redis内存限制
   - 配置缓存策略
   - 启用查询缓存

3. **网络优化**
   - 启用HTTP/2
   - 配置CDN
   - 优化静态资源缓存

## 安全配置

### 1. 防火墙配置

```bash
# Ubuntu UFW
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# CentOS/RHEL firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 2. SSL/TLS配置

```bash
# 使用Let's Encrypt获取免费证书
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com

# 配置自动续期
sudo crontab -e
# 添加：0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. 安全加固

- 定期更新系统和Docker镜像
- 使用强密码和密钥认证
- 限制网络访问和端口暴露
- 启用审计日志
- 配置入侵检测

## 故障排除

### 常见问题

1. **服务启动失败**
   ```bash
   # 查看详细错误信息
   docker-compose -f docker-compose.production.yml logs service_name
   
   # 检查资源使用情况
   docker stats
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据库状态
   docker-compose -f docker-compose.production.yml exec database pg_isready -U postgres
   
   # 检查网络连接
   docker-compose -f docker-compose.production.yml exec backend ping database
   ```

3. **内存不足**
   ```bash
   # 查看内存使用
   free -h
   docker stats
   
   # 清理Docker资源
   docker system prune -f
   ```

4. **磁盘空间不足**
   ```bash
   # 查看磁盘使用
   df -h
   
   # 清理日志文件
   docker-compose -f docker-compose.production.yml exec backend find /app/logs -name "*.log" -mtime +7 -delete
   ```

### 紧急恢复

如果系统出现严重问题，可以使用以下步骤快速恢复：

```bash
# 1. 停止所有服务
docker-compose -f docker-compose.production.yml down

# 2. 恢复最近的备份
# （根据备份策略执行相应的恢复操作）

# 3. 重新启动服务
docker-compose -f docker-compose.production.yml up -d

# 4. 验证服务状态
./scripts/health-check.sh
```

## 维护计划

### 日常维护

- 检查服务状态和日志
- 监控系统资源使用
- 验证备份完整性
- 更新安全补丁

### 周期性维护

**每周：**
- 清理旧日志文件
- 检查磁盘空间
- 更新监控告警规则

**每月：**
- 更新Docker镜像
- 优化数据库性能
- 审查安全配置
- 测试备份恢复流程

**每季度：**
- 系统安全审计
- 性能基准测试
- 容量规划评估
- 灾难恢复演练

## 联系支持

如果在部署过程中遇到问题，请：

1. 查看本文档的故障排除部分
2. 检查项目的GitHub Issues
3. 联系技术支持团队

---

**注意**: 在生产环境部署前，请务必在测试环境中验证所有配置和流程。