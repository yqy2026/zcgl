# 部署指南

## ✅ Status
**当前状态**: Draft (2026-02-03)

## 推荐方式：Docker Compose

### 1. 准备环境变量
- 后端: `backend/.env`
- 前端: `frontend/.env.production`（如需）

生产环境必须配置：
- `SECRET_KEY`
- `DATA_ENCRYPTION_KEY`
- `DATABASE_URL`
- `REQUIRE_ENCRYPTION=true`

### 2. 启动服务
```bash
docker-compose up -d
```

### 3. 执行数据库迁移
```bash
# 进入后端容器执行迁移
# docker-compose exec backend alembic upgrade head
make migrate
```

### 4. 验证
```bash
curl http://localhost:8002/api/v1/admin/health
```

## 端口与服务
- Frontend: 3000 (生产)
- Backend: 8002
- PostgreSQL: 5432
- Redis: 6379
- Nginx: 80/443

## 生产注意事项
- 使用强随机密钥并妥善保管
- 开启 HTTPS 与反向代理
- 启用日志与监控
- 定期备份数据库与上传文件
