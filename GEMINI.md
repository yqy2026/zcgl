# GEMINI.md

本文件为 Gemini 提供 **模型专属** 上下文补充。共享项目上下文与执行规则见 `AGENTS.md`（12-rule 通用规则以 `AGENTS.md` 为准，本文件不再重复）。

**Last Updated**: 2026-08-16

---

## Gemini 专属规则

以下规则补充 `AGENTS.md`，仅在使用 Gemini 时适用：

### 手动启动命令

除 `make` 目标外，也可手动启动（后端命令一律走 `uv run`，禁止系统 `python/pip`）：

```bash
# 前端
cd frontend && pnpm dev
cd frontend && pnpm lint && pnpm type-check

# 后端
cd backend && uv run --frozen --extra dev python run_dev.py   # 默认 :8002，占用时用 :8003
cd backend && uv run --frozen --extra dev python -m ruff check . && uv run --frozen --extra dev mypy src

# 进程监控启动（异常退出记录日志）
pwsh -File scripts/dev_watch.ps1
```

### 密钥生成

`make secrets` 生成 `SECRET_KEY` / `DATA_ENCRYPTION_KEY`。密钥格式、环境行为与注意事项见 [`docs/security/encryption.md`](docs/security/encryption.md)。
