# GEMINI.md

本文件为 Gemini 提供 **模型专属** 上下文补充。共享项目上下文见 `AGENTS.md`。

**Last Updated**: 2026-02-18

---

## Gemini 专属规则

以下规则补充 `AGENTS.md`，仅在使用 Gemini 时适用：

### 手动启动命令

除 `make` 命令外，也可手动启动：

```bash
# 前端
cd frontend && pnpm dev
cd frontend && pnpm lint && pnpm type-check

# 后端
cd backend && python run_dev.py          # 默认 :8002，占用时用 :8003
cd backend && ruff check . && mypy src

# 进程监控启动（异常退出记录日志）
pwsh -File scripts/dev_watch.ps1
```

### 密钥生成

```bash
# SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# DATA_ENCRYPTION_KEY（标准 Base64 + 版本号）
cd backend && python -m src.core.encryption
```

### 维护文档

每次修改后请更新 `CHANGELOG.md`。
