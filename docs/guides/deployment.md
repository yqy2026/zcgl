# 部署指南（快速参考）

> 完整运维手册（架构图、监控、故障排查）见 [部署运维手册](deployment-operations.md)。

## ✅ Status
**当前状态**: Active (2026-03-04 更新)

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

## 凭证泄露应急处置

判定规则：
- 任何生产/安全凭证（如 `SECRET_KEY`、`SESSION_SECRET`、`API_KEY`、数据库密码）只要出现在 Git 历史，即使已删除或已轮换，仍必须视为“已泄露”。

立即执行：
1. 从当前分支移除敏感文件跟踪：
```bash
git rm --cached backend/config/backend.env.secure
```
2. 清理历史提交中的明文凭证（变更窗口内执行）：
```bash
git filter-repo --force --invert-paths --path backend/config/backend.env.secure
# 或使用 BFG Repo-Cleaner 完成同等清理
```
3. 强制轮换所有受影响凭证并失效旧凭证：JWT 密钥、会话密钥、第三方 API keys、数据库密码等。
4. 通知运维/安全负责人完成轮换、会话失效、审计记录与回归验证。

防复发：
- 在 `.gitignore` 中持续屏蔽 `*.env`、`*.secure` 及 `backend/config/*.env.secure`。
- 建议启用提交前密钥扫描（如 `gitleaks` 或 `trufflehog`）。
