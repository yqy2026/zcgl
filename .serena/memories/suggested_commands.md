# 推荐命令

## 开发命令

### 一键启动（前后端）
```bash
make dev
```

### 进程监控启动（异常退出会记录日志）
```bash
pwsh -File scripts/dev_watch.ps1
```

### 单独启动
```bash
make dev-backend      # 后端 :8002
make dev-frontend     # 前端 :5173
```

## 代码质量
```bash
make lint            # 代码检查
make type-check      # 类型检查
```

## 测试
```bash
make test            # 全部测试
make test-backend    # 后端测试
make test-frontend   # 前端测试
```

### 后端测试（带标记）
```bash
cd backend
pytest -m unit                  # 单元测试
pytest -m integration           # 集成测试
pytest -m "not slow"            # 排除慢测试
pytest -m database              # 数据库测试
```

## 迁移/构建
```bash
make migrate         # 数据库迁移
make build-frontend  # 前端构建
```

## 密钥生成
```bash
make secrets         # 生成 SECRET_KEY
cd backend && python -m src.core.encryption  # 生成 DATA_ENCRYPTION_KEY
```

## Git 工作流
```bash
# 分支: main (生产) ← develop ← feature/* / hotfix/*
# 提交格式: type(scope): description
```

## 系统工具（Linux）
```bash
git, ls, cd, grep, find, rg
```
